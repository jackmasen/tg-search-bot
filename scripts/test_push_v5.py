# -*- coding: utf-8 -*-
import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Use a local temp file, then copy via SCP/FTP
local_tmp = os.path.join(os.environ.get('TEMP', '/tmp'), '_remote_check.py')
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT key, substr(value,1,100) FROM system_settings WHERE key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','TG_BOT_TOKEN','ADMIN_TG_IDS')")
for r in cur.fetchall():
    print(f"{r[0]}={repr(r[1])}")
conn.close()
''')

# Upload and run
sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_check.py')
_, out1, err1 = client.exec_command('python3 /tmp/_check.py')
print("=== DB Settings ===")
print(out1.read().decode())
print(err1.read().decode())
sftp.close()

# Also upload and run the API test
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
sftp.put(local_tmp, '/tmp/_test.py')
_, out2, err2 = client.exec_command('python3 /tmp/_test.py')
print("=== Push API Test ===")
print(out2.read().decode())
print(err2.read().decode())
sftp.close()
client.close()
os.unlink(local_tmp)
print("Done")
