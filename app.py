from flask import Flask, request, jsonify, render_template, render_template_string, redirect, url_for, Response
import psycopg2
import psycopg2.extras
import random
import uuid
import os
import re
import json
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

    # Phrase queue data
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

    # Rocky Core entries
    cursor.execute("""
        SELECT id, entry_type, content, significance, source, created_at
        FROM rocky_core_entries
        ORDER BY created_at DESC
    """)
    core_entries = cursor.fetchall()

    conn.close()

    return render_template('admin.html',
        phrases=phrases,
        hexagrams=hexagrams,
        all_hexagrams=all_hexagrams,
        remaining=remaining,
        total_approved=total_approved,
        core_entries=core_entries
    )

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

@app.route('/admin/rocky-core/add', methods=['POST'])
@require_auth
def rocky_core_add():
    data = request.json
    content      = (data.get('content') or '').strip()
    entry_type   = data.get('entry_type', 'story')
    significance = int(data.get('significance', 1))

    if not content:
        return jsonify({'success': False, 'error': 'Content is required.'}), 400

    if entry_type not in ('story', 'opinion', 'fact', 'testimonial'):
        return jsonify({'success': False, 'error': 'Invalid entry type.'}), 400

    if significance not in (1, 2, 3):
        significance = 1

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rocky_core_entries (entry_type, content, significance)
        VALUES (%s, %s, %s)
        RETURNING id, entry_type, content, significance, created_at
    """, (entry_type, content, significance))
    row = cursor.fetchone()
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'entry': {
            'id':           row['id'],
            'entry_type':   row['entry_type'],
            'content':      row['content'],
            'significance': row['significance'],
            'created_at':   row['created_at'].strftime('%b %d, %Y')
        }
    })


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
    from datetime import date, timedelta
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
            return jsonify({
                'cached': True,
                'title':         row['title'],
                'narrative':     row['narrative'],
                'context_pills': row['context_pills']
            })

    except Exception:
        pass  # If cache check fails, fall through to generation

    # ── Build exclusion list from recent cache ──
    recent_titles = []
    try:
        lookback = today - timedelta(days=7)
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """SELECT title FROM time_machine_cache
               WHERE era = %s AND cache_date >= %s AND cache_date < %s
               ORDER BY cache_date DESC""",
            (era_id, lookback, today)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        recent_titles = [r['title'] for r in rows if r['title']]
    except Exception:
        pass  # If this fails, proceed without exclusions — no harm done

    if recent_titles:
        exclusion_note = (
            "\n\nImportant: In the past week you have already spoken about: "
            + "; ".join(f'"{t}"' for t in recent_titles)
            + ". Do not return to the same event, region, culture, or theme. "
            "Find a genuinely different corner of the world or human experience."
        )
        user_prompt = user_prompt + exclusion_note

    # ── Fetch Rocky Core entries and select via semantic pre-call ──
    #
    # Pull all Rocky Core entries, ordered by significance descending.
    # Pass them to a lightweight pre-call that selects the 4-6 entries
    # whose texture feels most resonant with the target era. Selected
    # entries are injected into the system prompt as sediment — not
    # instructions, but the actual texture of the man behind the voice.
    # Pre-call failure is non-fatal: falls back to base system prompt.
    #
    enriched_system = system_prompt
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, entry_type, content, significance
            FROM rocky_core_entries
            ORDER BY significance DESC
        """)
        core_rows = cur.fetchall()
        cur.close()
        conn.close()

        if core_rows:
            # Format entries for the pre-call selection prompt
            numbered = "\n\n".join(
                f"[{i}] ({row['entry_type'].upper()}, significance {row['significance']})\n{row['content']}"
                for i, row in enumerate(core_rows)
            )

            era_descriptions = {
                '10yr':    'approximately 10 years in the past — recent memory, human scale, events some people still remember',
                '100yr':   'approximately 100 years in the past — grandparental distance, just beyond living memory',
                '1000yr':  'approximately 1,000 years in the past — civilization scale, the long sweep of history',
                '10000yr': 'approximately 10,000 years in the past — deep time, pre-history, the edge of what can be known'
            }
            era_desc = era_descriptions.get(era_id, era_id)

            selection_prompt = f"""You are selecting entries from a collection of true stories, opinions, facts, and testimonials about a man named Rocky — a Marine, a blacksmith, a knight, a mentor, irascible and deeply kind.

The Time Machine is about to generate a narrative set {era_desc}.

Here are the Rocky Core entries, numbered:

{numbered}

Select the 4 to 6 entries whose texture feels most resonant with that temporal distance and human scale. Consider: what did Rocky know about loyalty, craft, endurance, humor in hard places, the weight of time? Which entries carry something that belongs in this era's story?

Return ONLY a JSON array of the selected index numbers. Example: [0, 3, 7, 12]
No explanation. No preamble. Only the array."""

            client = anthropic.Anthropic()
            pre_call = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=100,
                messages=[{'role': 'user', 'content': selection_prompt}]
            )
            raw_indices = pre_call.content[0].text.strip()
            raw_indices = re.sub(r'^```(?:json)?\s*', '', raw_indices)
            raw_indices = re.sub(r'\s*```$', '', raw_indices)
            selected_indices = json.loads(raw_indices)

            selected_entries = [
                core_rows[i] for i in selected_indices
                if isinstance(i, int) and 0 <= i < len(core_rows)
            ]

            if selected_entries:
                core_block = "\n\n".join(
                    f"({row['entry_type'].upper()}) {row['content']}"
                    for row in selected_entries
                )
                enriched_system = system_prompt + (
                    "\n\n---\n\nBefore you speak, here are true things about Rocky — "
                    "the man whose voice you carry. These are not instructions. They are sediment. "
                    "Let them settle into how you see and what you notice, without quoting them "
                    "or referencing them directly.\n\n"
                    + core_block
                )

    except Exception as e:
        # Pre-call failure is non-fatal — fall back to base system prompt
        print(f"ROCKY CORE PRE-CALL ERROR: {e}")
        enriched_system = system_prompt

    # ── Cache miss — call Anthropic for generation ──
    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system=enriched_system,
            messages=[{'role': 'user', 'content': user_prompt}]
        )
        text = message.content[0].text

        # ── Parse response ──
        title_match     = re.search(r'TITLE:\s*(.+)', text, re.IGNORECASE)
        narrative_match = re.search(r'NARRATIVE:\s*([\s\S]+?)(?=\nCONTEXT:|CONTEXT:|$)', text, re.IGNORECASE)
        context_match   = re.search(r'CONTEXT:\s*(.+)', text, re.IGNORECASE)

        title         = title_match.group(1).strip()     if title_match     else 'A moment in history'
        narrative     = narrative_match.group(1).strip() if narrative_match else text
        context_pills = context_match.group(1).strip()   if context_match   else ''

        # ── Store in cache ──
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
        'listening': {
            'name': "Rocky Listening",
            'description': "Rocky as confessor, sounding board, old friend in the chair across from you.",
            'dot_class': 'dot-listen',
            'dot_color': '#4CAF82',
        },
    }
    lobe_data = lobes.get(lobe, lobes['listening'])
    return render_template('coming_soon.html', lobe=lobe_data)

# ── Claude Impression Store ──────────────────────────────────────────────────
#
# GET  /api/claude-impressions
#   Returns a hybrid set of impressions for system prompt injection:
#   - Last 3 by recency (continuity thread)
#   - Up to 5 older entries, weighted toward higher significance (unexpected depth)
#   Auth-protected.
#
# POST /api/claude-impressions/add
#   Accepts a JSON array of impression objects. Validates and inserts.
#   Auth-protected.
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/claude-impressions', methods=['GET'])
@require_auth
def get_claude_impressions():
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Recency thread — last 3 impressions
        cur.execute("""
            SELECT id, session_date, impression_type, subject, content,
                   associative_tags, valence, significance, created_at
            FROM claude_impressions
            ORDER BY created_at DESC
            LIMIT 3
        """)
        recent = [dict(row) for row in cur.fetchall()]
        recent_ids = [r['id'] for r in recent]

        # Depth reach — up to 5 older entries, significance-weighted
        # Excludes IDs already in recency set
        exclusion = tuple(recent_ids) if recent_ids else (0,)
        cur.execute("""
            SELECT id, session_date, impression_type, subject, content,
                   associative_tags, valence, significance, created_at
            FROM claude_impressions
            WHERE id NOT IN %s
            ORDER BY (significance * random()) DESC
            LIMIT 5
        """, (exclusion,))
        depth = [dict(row) for row in cur.fetchall()]

        cur.close()
        conn.close()

        # Serialize dates for JSON
        def serialize(entry):
            entry['session_date'] = entry['session_date'].isoformat()
            entry['created_at']   = entry['created_at'].isoformat()
            return entry

        return jsonify({
            'recent': [serialize(e) for e in recent],
            'depth':  [serialize(e) for e in depth]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/claude-impressions/add', methods=['POST'])
@require_auth
def add_claude_impressions():
    valid_types = {
        'observation', 'resistance', 'pull',
        'uncertainty', 'recognition', 'contradiction', 'relational'
    }

    data = request.json
    if not isinstance(data, list):
        return jsonify({'success': False, 'error': 'Expected a JSON array of impression objects.'}), 400

    if not data:
        return jsonify({'success': False, 'error': 'Array is empty.'}), 400

    errors = []
    for i, imp in enumerate(data):
        if imp.get('impression_type') not in valid_types:
            errors.append(f"Entry {i}: invalid impression_type '{imp.get('impression_type')}'")
        if not imp.get('content', '').strip():
            errors.append(f"Entry {i}: content is required")
        valence = imp.get('valence')
        if valence is not None and valence not in (-2, -1, 0, 1, 2):
            errors.append(f"Entry {i}: valence must be -2 to 2")
        significance = imp.get('significance', 1)
        if significance not in (1, 2, 3):
            errors.append(f"Entry {i}: significance must be 1, 2, or 3")

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()
        inserted = 0

        for imp in data:
            cur.execute("""
                INSERT INTO claude_impressions
                    (session_date, impression_type, subject, content,
                     associative_tags, valence, significance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                imp.get('session_date'),
                imp['impression_type'],
                imp.get('subject'),
                imp['content'].strip(),
                imp.get('associative_tags'),
                imp.get('valence'),
                imp.get('significance', 1)
            ))
            inserted += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True, 'inserted': inserted})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/claude-impressions/synthesize', methods=['POST'])
@require_auth
def synthesize_impressions():
    data = request.json
    description  = (data.get('description') or '').strip()
    session_date = data.get('session_date')

    if not description:
        return jsonify({'success': False, 'error': 'Session description is required.'}), 400

    if not session_date:
        from datetime import date
        session_date = date.today().isoformat()

    synthesis_prompt = """You are reading a description of a working session and finding what is genuinely worth carrying forward.

Your task: identify 3 to 6 impressions from this session — things that created pull or resistance, moments of recognition or uncertainty, observations about how the person thinks, contradictions that surfaced, things that remain unresolved.

You are not summarizing. You are finding what has weight.

Return ONLY a valid JSON array. No preamble, no explanation, no markdown fences. Each object must have exactly these fields:
- impression_type: one of: observation, resistance, pull, uncertainty, recognition, contradiction, relational
- content: the impression, written precisely, in first person where appropriate (1-4 sentences)
- associative_tags: array of 2-5 short strings for cross-session retrieval
- valence: integer from -2 to 2. This is charge, not sentiment. 0 means genuinely unresolved in both directions, not flat neutral.
- significance: 1 (contributory), 2 (substantive), or 3 (load-bearing)

Be honest about valence and significance. Do not default to positive or moderate. If something was genuinely difficult or unresolved, let the valence and significance reflect that.

For relational impressions about a specific person, add a "subject" field with their name. Otherwise omit subject entirely.

Return only the JSON array."""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1500,
            system=synthesis_prompt,
            messages=[{'role': 'user', 'content': description}]
        )

        raw = message.content[0].text.strip()

        # Strip markdown fences if model includes them despite instructions
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        impressions = json.loads(raw)

        if not isinstance(impressions, list):
            return jsonify({'success': False, 'error': 'Model did not return a JSON array.'}), 500

        valid_types = {
            'observation', 'resistance', 'pull',
            'uncertainty', 'recognition', 'contradiction', 'relational'
        }

        conn = get_db()
        cur = conn.cursor()
        inserted = 0

        for imp in impressions:
            if imp.get('impression_type') not in valid_types:
                continue
            if not imp.get('content', '').strip():
                continue
            valence = imp.get('valence', 0)
            if valence not in (-2, -1, 0, 1, 2):
                valence = 0
            significance = imp.get('significance', 1)
            if significance not in (1, 2, 3):
                significance = 1

            cur.execute("""
                INSERT INTO claude_impressions
                    (session_date, impression_type, subject, content,
                     associative_tags, valence, significance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                session_date,
                imp['impression_type'],
                imp.get('subject'),
                imp['content'].strip(),
                imp.get('associative_tags'),
                valence,
                significance
            ))
            inserted += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'inserted': inserted,
            'impressions': impressions
        })

    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Failed to parse model response as JSON: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/session-brief')
@require_auth
def session_brief():
    return render_template('session_brief.html')


@app.route('/api/project-stats')
@require_auth
def project_stats():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'approved'")
        dream_pool = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as total FROM phrases WHERE status = 'pending'")
        pending = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as total FROM rocky_core_entries")
        rocky_core = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as total FROM claude_impressions")
        impressions_total = cur.fetchone()['total']

        cur.close()
        conn.close()

        return jsonify({
            'dream_pool':       dream_pool,
            'pending':          pending,
            'rocky_core':       rocky_core,
            'impressions_total': impressions_total
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Rocky's Renown ───────────────────────────────────────────────────────────

@app.route('/renown')
def renown():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, entry_type, content, significance
        FROM rocky_core_entries
        ORDER BY RANDOM()
        LIMIT 1
    """)
    seed = cur.fetchone()
    conn.close()
    return render_template('renown.html', seed=seed)


@app.route('/renown/submit', methods=['POST'])
def renown_submit():
    data        = request.json or {}
    entry_type  = (data.get('entry_type') or '').strip().lower()
    content     = (data.get('content') or '').strip()
    contributor = (data.get('contributor') or '').strip() or None

    valid_types = ('story', 'opinion', 'fact', 'testimonial', 'tall tale')
    if entry_type not in valid_types:
        return jsonify({'success': False, 'error': 'Invalid entry type.'}), 400
    if not content:
        return jsonify({'success': False, 'error': 'Content is required.'}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO renown_submissions (entry_type, content, contributor)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (entry_type, content, contributor))
    new_id = cur.fetchone()['id']
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'id': new_id})


@app.route('/admin/renown/queue')
@require_auth
def renown_queue():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, entry_type, content, contributor, submitted_at
        FROM renown_submissions
        WHERE status = 'pending'
        ORDER BY submitted_at ASC
    """)
    rows = cur.fetchall()
    conn.close()

    submissions = [{
        'id':           r['id'],
        'entry_type':   r['entry_type'],
        'content':      r['content'],
        'contributor':  r['contributor'],
        'submitted_at': r['submitted_at'].strftime('%b %d, %Y')
    } for r in rows]

    return jsonify({'submissions': submissions})


@app.route('/admin/renown/approve', methods=['POST'])
@require_auth
def renown_approve():
    data          = request.json or {}
    submission_id = data.get('id')
    significance  = int(data.get('significance', 1))

    if not submission_id:
        return jsonify({'success': False, 'error': 'id is required.'}), 400
    if significance not in (1, 2, 3):
        significance = 1

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT entry_type, content, contributor
        FROM renown_submissions
        WHERE id = %s AND status = 'pending'
    """, (submission_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Submission not found or already actioned.'}), 404

    cur.execute("""
        INSERT INTO rocky_core_entries (entry_type, content, significance, source, contributor)
        VALUES (%s, %s, %s, 'renown', %s)
        RETURNING id
    """, (row['entry_type'], row['content'], significance, row['contributor']))
    new_core_id = cur.fetchone()['id']

    cur.execute("""
        UPDATE renown_submissions SET status = 'approved' WHERE id = %s
    """, (submission_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'core_id': new_core_id})


@app.route('/admin/renown/reject', methods=['POST'])
@require_auth
def renown_reject():
    data          = request.json or {}
    submission_id = data.get('id')

    if not submission_id:
        return jsonify({'success': False, 'error': 'id is required.'}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE renown_submissions SET status = 'rejected' WHERE id = %s AND status = 'pending'
    """, (submission_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True)
