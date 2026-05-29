import requests
import sqlite3

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

url = "https://raw.githubusercontent.com/strobus/i-ching/main/lib/data.json"
response = requests.get(url, headers=headers)
data = response.json()

conn = sqlite3.connect('dreamengine.db')
cursor = conn.cursor()

for h in data['hexagrams']:
    cursor.execute("""
        INSERT INTO hexagrams 
            (number, name_chinese, name_english, binary_pattern)
        VALUES (?, ?, ?, ?)
    """, (
        h['number'],
        h['chineseName'],
        h['names'][0],
        h['binary']
    ))

conn.commit()
conn.close()

print(f"Inserted {len(data['hexagrams'])} hexagrams successfully")
