import random
import sqlite3

def toss_three_coins():
    coins = [random.choice([2, 3]) for _ in range(3)]
    return sum(coins)

def generate_lines():
    return [toss_three_coins() for _ in range(6)]

def lines_to_pattern(lines):
    return ''.join(['1' if line in [7, 9] else '0' for line in lines])

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

def get_changing_lines(lines):
    return [i + 1 for i, line in enumerate(lines) if line in [6, 9]]

def lookup_hexagram(cursor, pattern):
    cursor.execute(
        "SELECT number, name_english, name_chinese FROM hexagrams WHERE binary_pattern = ?",
        (pattern,)
    )
    return cursor.fetchone()

def consult(db_path='dreamengine.db'):
    lines = generate_lines()
    primary_pattern = lines_to_pattern(lines)
    secondary_pattern = transform_to_secondary(lines)
    changing = get_changing_lines(lines)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    primary = lookup_hexagram(cursor, primary_pattern)
    secondary = lookup_hexagram(cursor, secondary_pattern)

    conn.close()

    print(f"\nLines cast (bottom to top): {lines}")
    print(f"Primary pattern: {primary_pattern}")

    if primary:
        print(f"Primary hexagram: #{primary[0]} {primary[2]} — {primary[1]}")
    else:
        print(f"Primary hexagram: NOT FOUND for pattern {primary_pattern}")

    if changing:
        print(f"Changing lines: {changing}")
        if secondary and secondary_pattern != primary_pattern:
            print(f"Secondary hexagram: #{secondary[0]} {secondary[2]} — {secondary[1]}")
    else:
        print("No changing lines — reading is locked")

consult()
