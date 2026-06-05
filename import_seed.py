import psycopg2
import os

def import_phrases(filepath, db_path=None):
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()

    inserted = 0
    for line in lines:
        cursor.execute("""
            INSERT INTO phrases (raw_text, contributor_token, status)
            VALUES (%s, 'seed_import', 'pending')
        """, (line,))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Imported {inserted} phrases as pending")

import_phrases('seed_phrases.txt')
