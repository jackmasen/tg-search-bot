# -*- coding: utf-8 -*-
import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

local_tmp = os.path.join(os.environ.get('TEMP', '/tmp'), '_remote.py')

# 1. Check schema first
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(system_settings)")
cols = cur.fetchall()
print("Columns:", [c[1] for c in cols])
cur.execute("SELECT * FROM system_settings LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_schema.py')
_, out1, err1 = client.exec_command('python3 /tmp/_schema.py')
print("=== Schema ===")
print(out1.read().decode())
print(err1.read().decode())
sftp.close()

# 2. Check admin credentials based on actual column names
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT * FROM system_settings WHERE key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','TG_BOT_TOKEN','ADMIN_TG_IDS')")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_creds.py')
_, out2, err2 = client.exec_command('python3 /tmp/_creds.py')
print("=== Credentials ===")
print(out2.read().decode())
print(err2.read().decode())
sftp.close()

# 3. Test login and push
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Aa13910828867'})
        ld = lr.json()
        print("Login:", ld)
        sid = ld.get('session_id', '')
        if not sid:
            print("Cannot login, skipping push test")
            return
        print("Session ID:", sid)
        pr = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test', json={'session_id': sid})
        print("Push test:", pr.status_code, pr.text)

asyncio.run(test())
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_push.py')
_, out3, err3 = client.exec_command('python3 /tmp/_push.py')
print("=== Push API Test ===")
print(out3.read().decode())
print(err3.read().decode())
sftp.close()
client.close()
os.unlink(local_tmp)
print("Done")
