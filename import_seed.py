import sqlite3

def import_phrases(filepath, db_path='dreamengine.db'):
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    inserted = 0
    for line in lines:
        cursor.execute("""
            INSERT INTO phrases (raw_text, contributor_token, status)
            VALUES (?, 'seed_import', 'pending')
        """, (line,))
        inserted += 1
    
    conn.commit()
    conn.close()
    print(f"Imported {inserted} phrases as pending")

import_phrases('seed_phrases.txt')
