from flask import Flask, request, jsonify, render_template_string, redirect, url_for, Response
import psycopg2
import psycopg2.extras
import random
import uuid
import os
from functools import wraps

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def check_auth(username, password):
    admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'changeme')
    return username == admin_user and password == admin_pass

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Authentication required.',
                401,
                {'WWW-Authenticate': 'Basic realm="Admin"'}
            )
        return f(*args, **kwargs)
    return decorated

def toss_three_coins():
    coins = [random.choice([2, 3]) for _ in range(3)]
    return sum(coins)

def generate_lines():
    return [toss_three_coins() for _ in range(6)]

def lines_to_pattern(lines):
    return ''.join(['1' if line in [7, 9] else '0' for line in lines])

def get_changing_lines(lines):
    return [i + 1 for i, line in enumerate(lines) if line in [6, 9]]

def transform_to_secondary(lines):
    result = []
    for line in lines:
        if line == 6:
            result.append('1')
        elif line == 9:
            result.append('0')
        elif line == 7:
            result.append('1')
        else:
            result.append('0')
    return ''.join(result)

def lookup_hexagram(cursor, pattern):
    cursor.execute(
        "SELECT * FROM hexagrams WHERE binary_pattern = %s",
        (pattern,)
    )
    return cursor.fetchone()

def generate_poem(hexagram_id, num_lines=5):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT raw_text FROM phrases
        WHERE status = 'approved' AND hexagram_id = %s
        ORDER BY RANDOM()
        LIMIT %s
    """, (hexagram_id, num_lines))
    phrases = cursor.fetchall()
    conn.close()
    if not phrases:
        return None
    return '\n'.join([p['raw_text'] for p in phrases])

@app.route('/')
def index():
    return render_template_string('''
        <h1>Rocky's Dream Engine</h1>
        <form method="POST" action="/submit">
            <textarea name="phrase" rows="4" cols="50"
                placeholder="Enter your phrase, image, or fragment..."></textarea>
            <br><br>
            <button type="submit">Consult the Oracle</button>
        </form>
    ''')

@app.route('/submit', methods=['POST'])
def submit():
    phrase = request.form.get('phrase', '').strip()
    if not phrase:
        return jsonify({'error': 'No phrase provided'}), 400

    session_id = str(uuid.uuid4())
    lines = generate_lines()
    primary_pattern = lines_to_pattern(lines)
    secondary_pattern = transform_to_secondary(lines)
    changing = get_changing_lines(lines)

    conn = get_db()
    cursor = conn.cursor()

    primary = lookup_hexagram(cursor, primary_pattern)
    secondary = lookup_hexagram(cursor, secondary_pattern)

    cursor.execute("""
        INSERT INTO phrases (raw_text, contributor_token, status)
        VALUES (%s, %s, 'pending')
    """, (phrase, session_id))

    cursor.execute("""
        SELECT phrase_id FROM phrases 
        WHERE contributor_token = %s 
        ORDER BY submission_timestamp DESC LIMIT 1
    """, (session_id,))
    phrase_row = cursor.fetchone()
    phrase_id = phrase_row['phrase_id'] if phrase_row else None

    cursor.execute("""
        INSERT INTO sessions
            (session_id, submission_phrase_id, hexagram_result)
        VALUES (%s, %s, %s)
    """, (session_id, phrase_id, primary['hexagram_id'] if primary else None))

    conn.commit()
    conn.close()

    poem = generate_poem(primary['hexagram_id']) if primary else None

    result = {
        'hexagram': dict(primary) if primary else None,
        'changing_lines': changing,
        'secondary_hexagram': dict(secondary) if secondary and secondary_pattern != primary_pattern else None,
        'poem': poem
    }

    return render_template_string('''
        <h1>Rocky's Dream Engine</h1>
        <h2>Hexagram {{ result.hexagram.number }} — {{ result.hexagram.name_english }}</h2>
        <p><strong>Chinese:</strong> {{ result.hexagram.name_chinese }}</p>
        {% if result.changing_lines %}
            <p><strong>Changing lines:</strong> {{ result.changing_lines }}</p>
            {% if result.secondary_hexagram %}
                <p><strong>Becomes:</strong> Hexagram {{ result.secondary_hexagram.number }}
                — {{ result.secondary_hexagram.name_english }}</p>
            {% endif %}
        {% else %}
            <p><strong>No changing lines</strong> — reading is locked</p>
        {% endif %}
        {% if result.poem %}
            <hr>
            <h3>From the dream pool:</h3>
            <p style="font-style:italic; white-space:pre-line;">{{ result.poem }}</p>
        {% else %}
            <hr>
            <p><em>The dream pool is silent for this hexagram.</em></p>
        {% endif %}
        <br>
        <a href="/">Consult again</a>
    ''', result=result)

@app.route('/admin/phrases')
@require_auth
def admin_phrases():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM phrases
        WHERE status = 'pending'
        ORDER BY submission_timestamp
    """)
    phrases = cursor.fetchall()
    cursor.execute("SELECT hexagram_id, number, name_english FROM hexagrams ORDER BY number")
    hexagrams = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'pending'")
    remaining = cursor.fetchone()['total']
    conn.close()
    return render_template_string('''
        <h1>Curation Queue</h1>
        <p><strong>{{ remaining }} phrases pending</strong></p>
        {% for p in phrases %}
        <form method="POST" action="/admin/curate"
            style="border:1px solid #ccc; margin:10px 0; padding:12px;">
            <input type="hidden" name="phrase_id" value="{{ p.phrase_id }}">
            <div style="margin-bottom:10px;">
                <textarea name="edited_text" rows="2" cols="60"
                    style="font-size:14px;">{{ p.raw_text }}</textarea>
            </div>
            <div style="margin-bottom:10px;">
                <select name="hexagram_id" style="font-size:14px; padding:4px;">
                    <option value="">-- Assign hexagram --</option>
                    {% for h in hexagrams %}
                    <option value="{{ h.hexagram_id }}">
                        {{ h.number }} — {{ h.name_english }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            <button type="submit" name="action" value="approve"
                style="padding:8px 20px; margin-right:8px;">Approve</button>
            <button type="submit" name="action" value="reject"
                style="padding:8px 20px;">Reject</button>
        </form>
        {% endfor %}
        {% if not phrases %}
            <p>The queue is empty.</p>
        {% endif %}
    ''', phrases=phrases, hexagrams=hexagrams, remaining=remaining)

@app.route('/admin/curate', methods=['POST'])
@require_auth
def curate():
    phrase_id = request.form.get('phrase_id')
    hexagram_id = request.form.get('hexagram_id')
    edited_text = request.form.get('edited_text', '').strip()
    action = request.form.get('action')

    status = 'approved' if action == 'approve' else 'rejected'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE phrases
        SET status = %s,
            hexagram_id = %s,
            raw_text = %s,
            curation_timestamp = CURRENT_TIMESTAMP
        WHERE phrase_id = %s
    """, (
        status,
        hexagram_id if status == 'approved' and hexagram_id else None,
        edited_text if edited_text else None,
        phrase_id
    ))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_phrases'))

if __name__ == '__main__':
    app.run(debug=True)
