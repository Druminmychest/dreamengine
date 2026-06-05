from flask import Flask, request, jsonify, render_template, render_template_string, redirect, url_for, Response
import psycopg2
import psycopg2.extras
import random
import uuid
import os
import anthropic
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
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/submit', methods=['POST'])
def submit():
    phrase = request.form.get('phrase', '').strip()
    if not phrase:
        return redirect(url_for('index'))

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

    return render_template('result.html', result=result)

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
    cursor.execute("""
        SELECT h.hexagram_id, h.number, h.name_english,
               COUNT(p.phrase_id) as phrase_count
        FROM hexagrams h
        LEFT JOIN phrases p ON h.hexagram_id = p.hexagram_id AND p.status = 'approved'
        GROUP BY h.hexagram_id, h.number, h.name_english
        ORDER BY phrase_count ASC
        LIMIT 10
    """)
    hexagrams = cursor.fetchall()
    cursor.execute("""
        SELECT h.hexagram_id, h.number, h.name_english, h.judgment_text
        FROM hexagrams h
        ORDER BY h.number
    """)
    all_hexagrams = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'pending'")
    remaining = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'approved'")
    total_approved = cursor.fetchone()['total']
    conn.close()
    return render_template_string('''
        <h1>Curation Queue</h1>
        <p>Total phrases in pool: <strong>{{ total_approved }}</strong></p>
        {% if request.args.get('error') %}
        <p style="color:red; font-weight:bold;">Please assign a hexagram before approving.</p>
        {% endif %}   
<table style="width:100%; border-collapse:collapse; margin-bottom:20px; font-size:13px;">
    <tr>
        <th style="text-align:left; padding:4px 8px; border-bottom:1px solid #ccc;">№</th>
        <th style="text-align:left; padding:4px 8px; border-bottom:1px solid #ccc;">Name</th>
        <th style="text-align:right; padding:4px 8px; border-bottom:1px solid #ccc;">Phrases</th>
    </tr>
    {% for h in hexagrams %}
    <tr style="background: {% if h['phrase_count'] < 3 %}#fff3cd{% elif h['phrase_count'] < 6 %}#fff{% else %}#f0fff0{% endif %}">
        <td style="padding:3px 8px;">{{ h['number'] }}</td>
        <td style="padding:3px 8px;">{{ h['name_english'] }}</td>
        <td style="padding:3px 8px; text-align:right;">{{ h['phrase_count'] }}</td>
    </tr>
    {% endfor %}
</table>
<a name="queue"></a>
        {% for p in phrases %}
        <form method="POST" action="/admin/curate"
            style="border:1px solid #ccc; margin:10px 0; padding:12px;">
            <input type="hidden" name="phrase_id" value="{{ p.phrase_id }}">
            <input type="hidden" name="redirect_to" value="/admin/phrases">
            <div style="margin-bottom:10px;">
                <textarea name="edited_text" rows="2" cols="60"
                    style="font-size:14px;">{{ p.raw_text }}</textarea>
            </div>
            <div style="margin-bottom:10px;">
                <select name="hexagram_id" style="font-size:14px; padding:4px;">
                    <option value="">-- Assign hexagram --</option>
                    {% for h in all_hexagrams %}
                    <option value="{{ h.hexagram_id }}">
                        {{ h.number }} — {{ h.name_english }}: {{ h['judgment_text'][:50] }}...
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
    ''', phrases=phrases, hexagrams=hexagrams, all_hexagrams=all_hexagrams, remaining=remaining, total_approved=total_approved)
@app.route('/admin/mobile')
@require_auth
def admin_mobile():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM phrases
        WHERE status = 'pending'
        ORDER BY submission_timestamp
        LIMIT 1
    """)
    phrase = cursor.fetchone()
    cursor.execute("SELECT hexagram_id, number, name_english, judgment_text FROM hexagrams ORDER BY number")
    hexagrams = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'pending'")
    remaining = cursor.fetchone()['total']
    conn.close()
    return render_template('admin_mobile.html',
        phrase=phrase,
        hexagrams=hexagrams,
        remaining=remaining
    )

@app.route('/admin/curate', methods=['POST'])
@require_auth
def curate():
    phrase_id = request.form.get('phrase_id')
    hexagram_id = request.form.get('hexagram_id')
    edited_text = request.form.get('edited_text', '').strip()
    action = request.form.get('action')

    # Guard: block approval without a hexagram
    if action == 'approve' and not hexagram_id:
        return redirect(url_for('admin_phrases') + '?error=1')

    redirect_to = request.form.get('redirect_to', '/admin/phrases')

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

    return redirect(redirect_to + '#queue')
@app.route('/distill', methods=['POST'])
def distill():
    lines = request.json.get('lines', [])
    if not lines:
        return jsonify({'error': 'no lines provided'}), 400

    poem_text = '\n'.join(lines)

    recipes = [
        {
            "name": "structured",
            "instruction": """Distill each line into this exact pattern: Adjective Noun, Verb — Adjective Noun
Rules:
- Each line must follow exactly: Adjective Noun, Verb — Adjective Noun
- Preserve the emotional and imagistic essence
- If a line resists parsing, draw from the emotional territory of surrounding lines"""
        },
        {
            "name": "imagist",
            "instruction": """Distill this poem in the imagist tradition.
Rules:
- Each line should be a single concrete image, no abstraction
- Short, direct, sensory — what can be seen, heard, felt
- No explanation, no metaphor stated explicitly — only the image itself
- 3 to 5 words per line maximum"""
        },
        {
            "name": "incantatory",
            "instruction": """Distill this poem as an incantation or ritual chant.
Rules:
- Use repetition and accumulation deliberately
- Lines should build on each other rhythmically
- Anaphora encouraged — beginning multiple lines with the same word or phrase
- Should feel like something spoken aloud in darkness"""
        },
        {
            "name": "fragmented",
            "instruction": """Distill this poem as fragmented consciousness.
Rules:
- Incomplete thoughts are acceptable and encouraged
- Use ellipses to suggest continuation or absence
- Lines can be as short as two words
- Gaps and silences are part of the poem
- Do not resolve or complete what resists completion"""
        },
        {
            "name": "declarative",
            "instruction": """Distill this poem as a series of strange declarative statements.
Rules:
- Each line states something as plain fact, however surreal
- No questions, no conditionals, no hedging
- The stranger the fact the better, as long as it feels true to the original
- Simple subject-verb-object construction preferred"""
        },
    ]

    recipe = random.choice(recipes)

    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are distilling a surrealist dream poem into a specific poetic form.

{recipe['instruction']}

General rules for all forms:
- Preserve the emotional and imagistic essence of the original
- Return ONLY the distilled poem lines, one per line
- No explanation, no preamble, no labels

Original poem:
{poem_text}"""
            }
        ]
    )

    distilled = message.content[0].text.strip()
    return jsonify({'distilled': distilled, 'form': recipe['name']})

@app.route('/time-machine')
def time_machine():
    return render_template('time_machine.html')


@app.route('/api/rocky', methods=['POST'])
def rocky_api():
    from datetime import date
    data          = request.json
    system_prompt = data.get('system', '')
    user_prompt   = data.get('prompt', '')
    era_id        = data.get('era_id', '')

    if not system_prompt or not user_prompt or not era_id:
        return jsonify({'error': 'missing system, prompt, or era_id'}), 400

    today = date.today()

    # ── Check cache first ──
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "SELECT title, narrative, context_pills FROM time_machine_cache WHERE cache_date = %s AND era = %s",
            (today, era_id)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            title      = row['title']
            narrative  = row['narrative']
            context_pills = row['context_pills']
            return jsonify({
                'cached': True,
                'title': title,
                'narrative': narrative,
                'context_pills': context_pills
            })

    except Exception as e:
        # If cache check fails, fall through to API call
        pass

    # ── Cache miss — call Anthropic ──
    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}]
        )
        text = message.content[0].text

        # ── Parse and store in cache ──
        import re
        title_match     = re.search(r'TITLE:\s*(.+)', text, re.IGNORECASE)
        narrative_match = re.search(r'NARRATIVE:\s*([\s\S]+?)(?=\nCONTEXT:|CONTEXT:|$)', text, re.IGNORECASE)
        context_match   = re.search(r'CONTEXT:\s*(.+)', text, re.IGNORECASE)

        title         = title_match.group(1).strip()     if title_match     else 'A moment in history'
        narrative     = narrative_match.group(1).strip() if narrative_match else text
        context_pills = context_match.group(1).strip()   if context_match   else ''

        try:
            conn = get_db()
            cur  = conn.cursor()
            cur.execute(
                """INSERT INTO time_machine_cache (cache_date, era, title, narrative, context_pills)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (cache_date, era) DO NOTHING""",
                (today, era_id, title, narrative, context_pills)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as cache_err:
            print(f"CACHE WRITE ERROR: {cache_err}")

        return jsonify({'text': text, 'cached': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/coming-soon/<lobe>')
def coming_soon(lobe):
    lobes = {
        'reasoning': {
            'name': "Rocky Reasoning",
            'description': "Rocky thinking through a problem with you. His particular brand of straight-talking, no-nonsense wisdom applied to the present.",
            'dot_class': 'dot-reason',
            'dot_color': '#85B7EB',
        },
        'listening': {
            'name': "Rocky Listening",
            'description': "Rocky as confessor, sounding board, old friend in the chair across from you.",
            'dot_class': 'dot-listen',
            'dot_color': '#AFA9EC',
        },
    }
    lobe_data = lobes.get(lobe, lobes['reasoning'])
    return render_template('coming_soon.html', lobe=lobe_data)
 
if __name__ == '__main__':
    app.run(debug=True)
