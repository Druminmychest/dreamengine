import sqlite3
import random

def generate_poem(hexagram_id, db_path='dreamengine.db', num_lines=5):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT raw_text FROM phrases 
        WHERE status = 'approved' AND hexagram_id = ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (hexagram_id, num_lines))
    
    phrases = cursor.fetchall()
    conn.close()
    
    if not phrases:
        return None
    
    poem = '\n'.join([p[0] for p in phrases])
    return poem

def generate_poem_from_pattern(pattern, db_path='dreamengine.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT hexagram_id, number, name_english FROM hexagrams WHERE binary_pattern = ?",
        (pattern,)
    )
    hexagram = cursor.fetchone()
    conn.close()
    
    if not hexagram:
        return None, None
    
    poem = generate_poem(hexagram[0], db_path)
    return hexagram, poem

if __name__ == '__main__':
    # Test with hexagram 36
    conn = sqlite3.connect('dreamengine.db')
    cursor = conn.cursor()
    cursor.execute("SELECT hexagram_id FROM hexagrams WHERE number = 36")
    h = cursor.fetchone()
    conn.close()
    
    poem = generate_poem(h[0])
    if poem:
        print("Generated poem:")
        print(poem)
    else:
        print("No approved phrases found for this hexagram yet")
