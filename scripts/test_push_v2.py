# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 1. Check admin credentials and bot config
script1 = '''
import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT key, substr(value,1,100) FROM system_settings WHERE key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','TG_BOT_TOKEN','ADMIN_TG_IDS')")
for r in cur.fetchall():
    print(f"{r[0]}={repr(r[1])}")
conn.close()
'''
with open('/tmp/check1.py','w') as f: f.write(script1)
_, out, err = client.exec_command('python3 /tmp/check1.py')
print("=== DB Settings ===")
print(out.read().decode())

# 2. Test login and push via API
script2 = '''
import asyncio, httpx, sys
sys.path.insert(0, \'/www/wwwroot/tg-search-bot\')
import os
os.environ.setdefault(\'DB_PATH\', \'/www/wwwroot/tg-search-bot/data/tg_search.db\')
from dotenv import load_dotenv
load_dotenv(\'/www/wwwroot/tg-search-bot/.env\')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post(\'http://127.0.0.1:8001/api/admin/login\', json={\'username\': \'admin\', \'password\': \'Aa13910828867\'})
        ld = lr.json()
        print("Login:", ld)
        sid = ld.get(\'session_id\', \'\')
        if not sid:
            print("Cannot login, skipping push test")
            return
        print("Session ID:", sid)
        pr = await c.post(\'http://127.0.0.1:8001/api/admin/ops/bot_push_test\', json={\'session_id\': sid})
        print("Push test:", pr.status_code, pr.text)

asyncio.run(test())
'''
with open('/tmp/check2.py','w') as f: f.write(script2)
_, out2, err2 = client.exec_command('python3 /tmp/check2.py')
print("=== Push API Test ===")
print(out2.read().decode())
print(err2.read().decode())
client.close()
print("Done")
