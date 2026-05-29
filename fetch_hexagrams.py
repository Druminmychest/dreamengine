import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

url = "https://raw.githubusercontent.com/strobus/i-ching/main/lib/data.json"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    
    print("-- Binary pattern UPDATE statements for all 64 hexagrams")
    print("-- Source: strobus/i-ching (MIT license), Wilhelm/Baynes translation")
    print()
    
    for h in data['hexagrams']:
        number = h['number']
        binary = h['binary']
        name = h['names'][0]
        print(f"UPDATE hexagrams SET binary_pattern = '{binary}' WHERE number = {number};  -- {name}")
    
    print()
    print(f"-- Total: {len(data['hexagrams'])} hexagrams updated")
else:
    print(f"Failed: {response.status_code}")
