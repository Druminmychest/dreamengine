import random
import sqlite3

def toss_three_coins():
    coins = [random.choice([2, 3]) for _ in range(3)]
    return sum(coins)

def generate_lines():
    return [toss_three_coins() for _ in range(6)]

def lines_to_pattern(lines):
    return ''.join(['1' if line in [7, 9] else '0' for line in lines])

def lookup_hexagram(cursor, pattern):
    cursor.execute(
        "SELECT number, name_english FROM hexagrams WHERE binary_pattern = ?",
        (pattern,)
    )
    return cursor.fetchone()

def stress_test(iterations=1000, db_path='dreamengine.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    failures = 0
    for i in range(iterations):
        lines = generate_lines()
        pattern = lines_to_pattern(lines)
        result = lookup_hexagram(cursor, pattern)
        if not result:
            print(f"LOOKUP FAILURE: pattern {pattern}")
            failures += 1
    
    conn.close()
    print(f"Completed {iterations} consultations")
    print(f"Failures: {failures}")
    print(f"Success rate: {((iterations-failures)/iterations)*100:.1f}%")

stress_test()
