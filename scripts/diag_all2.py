# -*- coding: utf-8 -*-
import paramiko, os, tempfile

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)
local_tmp = os.path.join(tempfile.gettempdir(), '_d.py')
sftp = client.open_sftp()

# 1. Check channels table schema and data
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(channels)")
print("=== channels columns ===")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT * FROM channels LIMIT 5")
cols = [d[1] for d in cur.description]
print("=== channels data ===")
for r in cur.fetchall():
    print(dict(zip(cols, r)))
cur.execute("PRAGMA table_info(ad_campaigns)")
print("\n=== ad_campaigns columns ===")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT id, title, is_featured, status, daily_budget, daily_spent FROM ad_campaigns LIMIT 5")
cols = [d[1] for d in cur.description]
print("=== ad_campaigns data ===")
for r in cur.fetchall():
    print(dict(zip(cols, r)))
cur.execute("PRAGMA table_info(hot_keywords)")
print("\n=== hot_keywords columns ===")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT * FROM hot_keywords LIMIT 5")
cols = [d[1] for d in cur.description]
print("=== hot_keywords data ===")
for r in cur.fetchall():
    print(dict(zip(cols, r)))
cur.execute("PRAGMA table_info(keyword_categories)")
print("\n=== keyword_categories columns ===")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT * FROM keyword_categories")
cols = [d[1] for d in cur.description]
print("=== keyword_categories data ===")
for r in cur.fetchall():
    print(dict(zip(cols, r)))
conn.close()
''')
sftp.put(local_tmp, '/tmp/_d1.py')
_, out1, err1 = client.exec_command('python3 /tmp/_d1.py')
print("=== 问题1: 数据库结构 ===")
print(out1.read().decode())
print(err1.read().decode())
sftp.close()

# 2. Test bot command endpoint with session
sftp = client.open_sftp()
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Admin@123456'})
        sid = lr.json().get('session_id', '')
        if not sid:
            print("Login failed")
            return

        # Test /start command
        print("=== POST /api/bot/command /start ===")
        cr = await c.post('http://127.0.0.1:8001/api/bot/command', json={'command': '/start', 'user_id': 999999, 'session_id': sid})
        print(f"Status: {cr.status_code}")
        cd = cr.json()
        print(f"priority_channels: {cd.get('priority_channels', [])}")
        print(f"priority_ads: {cd.get('priority_ads', [])}")
        hkw = cd.get('hot_keywords', [])
        print(f"hot_keywords count: {len(hkw) if hkw else 0}")
        if hkw:
            print(f"hot_keywords sample: {str(hkw)[:300]}")
        # Check if there's an error
        if not cd.get('reply_html', ''):
            print(f"Full response keys: {list(cd.keys())}")
            print(f"Full response: {str(cd)[:500]}")

        # Test search endpoint
        print("\n=== POST /api/bot/command search test ===")
        sr = await c.post('http://127.0.0.1:8001/api/bot/command', json={'command': '比特币', 'user_id': 999999, 'session_id': sid})
        print(f"Status: {sr.status_code}")
        sd = sr.json()
        print(f"priority_channels: {sd.get('priority_channels', [])}")
        print(f"priority_ads: {sd.get('priority_ads', [])}")
        hkw2 = sd.get('hot_keywords', [])
        print(f"hot_keywords count: {len(hkw2) if hkw2 else 0}")

asyncio.run(test())
''')
sftp.put(local_tmp, '/tmp/_d2.py')
_, out2, err2 = client.exec_command('python3 /tmp/_d2.py')
print("=== 问题1+2: API测试 ===")
print(out2.read().decode())
print(err2.read().decode())
sftp.close()

# 3. Check the AI pool add issue - what format does frontend send?
sftp = client.open_sftp()
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Admin@123456'})
        sid = lr.json().get('session_id', '')
        if not sid:
            print("Login failed")
            return

        # Try adding with item format (what backend expects)
        print("=== POST /api/admin/ai/pool/add with item ===")
        ar = await c.post(f'http://127.0.0.1:8001/api/admin/ai/pool/add',
            json={'session_id': sid, 'item': {'name': '测试OpenAI', 'api_base': 'https://api.openai.com', 'api_key': 'sk-test123', 'model': 'gpt-4o', 'priority': 1}})
        print(f"Status: {ar.status_code}")
        print(ar.text[:300])

        # Try adding without item format
        print("\n=== POST /api/admin/ai/pool/add without item ===")
        ar2 = await c.post(f'http://127.0.0.1:8001/api/admin/ai/pool/add',
            json={'session_id': sid, 'name': '测试OpenAI', 'api_base': 'https://api.openai.com', 'api_key': 'sk-test123', 'model': 'gpt-4o', 'priority': 1})
        print(f"Status: {ar2.status_code}")
        print(ar2.text[:300])

asyncio.run(test())
''')
sftp.put(local_tmp, '/tmp/_d3.py')
_, out3, err3 = client.exec_command('python3 /tmp/_d3.py')
print("=== 问题3: AI接口添加测试 ===")
print(out3.read().decode())
print(err3.read().decode())
sftp.close()

# 4. Check server logs
sftp = client.open_sftp()
_, out4, err4 = client.exec_command('ls -la /www/wwwroot/tg-search-bot/logs/ 2>/dev/null && echo "---" && tail -50 /www/wwwroot/tg-search-bot/logs/server.log 2>/dev/null || echo "No logs dir"')
print("=== 日志 ===")
print(out4.read().decode())
print(err4.read().decode())
sftp.close()

client.close()
os.unlink(local_tmp)
print("Done")
