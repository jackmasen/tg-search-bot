# -*- coding: utf-8 -*-
import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

local_tmp = os.path.join(os.environ.get('TEMP', '/tmp'), '_remote.py')

with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        # Try correct password
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Admin@123456'})
        ld = lr.json()
        print("Login:", ld)
        sid = ld.get('session_id', '')
        if not sid:
            print("Login failed!")
            return
        print("Session OK:", sid[:20] + "...")
        pr = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test', json={'session_id': sid})
        print("Push test:", pr.status_code, pr.text)

asyncio.run(test())
''')

sftp = client.open_sftp()
sftp.put(local_tmp, '/tmp/_push.py')
_, out, err = client.exec_command('python3 /tmp/_push.py')
print("=== Push API Test ===")
print(out.read().decode())
print(err.read().decode())
sftp.close()
client.close()
os.unlink(local_tmp)
print("Done")
