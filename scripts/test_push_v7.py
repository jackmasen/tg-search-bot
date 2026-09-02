# -*- coding: utf-8 -*-
import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

local_tmp = os.path.join(os.environ.get('TEMP', '/tmp'), '_remote.py')

# 1. Check all admin-related settings
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT setting_key, substr(setting_value,1,100), value_type, is_encrypted FROM system_settings WHERE setting_key LIKE '%ADMIN%' OR setting_key LIKE '%BOT%' OR setting_key LIKE '%TG%'")
for r in cur.fetchall():
    print(r)
conn.close()
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_check.py')
_, out1, err1 = client.exec_command('python3 /tmp/_check.py')
print("=== Admin Settings ===")
print(out1.read().decode())
print(err1.read().decode())
sftp.close()

# 2. Test with default password
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        # Try default password
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'demo123456'})
        ld = lr.json()
        print("Login (demo123456):", ld)
        sid = ld.get('session_id', '')
        if sid:
            pr = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test', json={'session_id': sid})
            print("Push test:", pr.status_code, pr.text)
        else:
            # Try the SSH password as admin password
            lr2 = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Aa13910828867'})
            ld2 = lr2.json()
            print("Login (Aa13910828867):", ld2)
            sid2 = ld2.get('session_id', '')
            if sid2:
                pr2 = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test', json={'session_id': sid2})
                print("Push test:", pr2.status_code, pr2.text)
            else:
                print("All login attempts failed")

asyncio.run(test())
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_push.py')
_, out2, err2 = client.exec_command('python3 /tmp/_push.py')
print("=== Push API Test ===")
print(out2.read().decode())
print(err2.read().decode())
sftp.close()
client.close()
os.unlink(local_tmp)
print("Done")
