"""Manual ad_campaign_status test via urllib to confirm resume works with the session"""
import urllib.request, json, sys
sys.path.insert(0, 'tg-search-bot')

BASE = "http://127.0.0.1:8001"
SID = "ee766c9d6a9946709108ef69c00040de6a95b83e"  # the current session in browser localStorage

def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type':'application/json'}
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read().decode())

# Resume ad #1 back to active
res = post('/api/admin/ad_campaign_status', {'session_id': SID, 'campaign_id': 1, 'status': 'active'})
print("Resume ad #1:", res)

# Verify DB state
import sqlite3
conn = sqlite3.connect('tg-search-bot/data/tg_search.db')
cur = conn.execute("SELECT id, keyword, status, updated_at FROM ad_campaigns WHERE id=1")
for row in cur.fetchall():
    print("DB row id=1:", row)
conn.close()
