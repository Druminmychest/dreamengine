# Replace your existing /api/rocky route in app.py with this version.
# Also requires: from datetime import date  — add to imports at top of app.py if not present.

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
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT title, narrative, context_pills FROM time_machine_cache WHERE cache_date = %s AND era = %s",
            (today, era_id)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            title, narrative, context_pills = row
            # Reconstruct the text format the frontend parser expects
            text = f"TITLE: {title}\nNARRATIVE: {narrative}\nCONTEXT: {context_pills}"
            return jsonify({'text': text, 'cached': True})

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
            conn = get_db_connection()
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
        except Exception:
            pass  # Cache write failure is non-fatal — still return the response

        return jsonify({'text': text, 'cached': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
