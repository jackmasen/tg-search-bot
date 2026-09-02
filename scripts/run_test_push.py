# -*- coding: utf-8 -*-
"""
通过 admin API 测试 bot_push_test 功能
用法: python run_test_push.py
"""
import paramiko, os, tempfile

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'

test_script = """import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post('http://127.0.0.1:8001/api/admin/login',
            json={'username': 'admin', 'password': 'Admin@123456'})
        ld = lr.json()
        print(f"Login: {ld}")
        if not ld.get('ok'):
            print("❌ 登录失败")
            return
        sid = ld['session_id']
        print(f"✅ 登录成功, session: {sid[:16]}...")

        pr = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test',
            json={'session_id': sid})
        rd = pr.json()
        print(f"Push test: {pr.status_code} {rd}")
        if rd.get('ok'):
            print(f"✅ 推送成功! 已发送 {rd.get('sent_count', 0)} 条消息")
            for r in rd.get('results', []):
                print(f"  {r}")
        else:
            print(f"❌ 推送失败: {rd.get('error', '')}")

asyncio.run(test())
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

sftp = client.open_sftp()
local_tmp = os.path.join(tempfile.gettempdir(), '_push_test.py')
with open(local_tmp, 'w') as f:
    f.write(test_script)
sftp.put(local_tmp, '/tmp/_push_test.py')
print("Uploaded test script")
sftp.close()

_, out, err = client.exec_command(f'cd {REMOTE_BASE} && source venv/bin/activate && python3 /tmp/_push_test.py')
print('=== output ===')
print(out.read().decode().strip())
print('=== stderr ===')
print(err.read().decode().strip())
client.close()
os.unlink(local_tmp)
print("\nDone")
