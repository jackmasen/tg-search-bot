# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Check system_settings table
remote_script = '/tmp/diag_settings.py'
script = '''
import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT key, substr(value,1,100) FROM system_settings WHERE key IN ('TG_BOT_TOKEN','ADMIN_TG_IDS')")
rows = cur.fetchall()
print(f"Found {len(rows)} rows")
for r in rows:
    print(f"  {r[0]} = {repr(r[1])}")
conn.close()
'''
client.exec_command(f'cat > {remote_script} << \'EOF\'\n{script}\nEOF')
_, out, err = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_script}')
print("=== system_settings ===")
print(out.read().decode('utf-8', errors='replace'))
print(err.read().decode('utf-8', errors='replace'))

# Now test the actual API endpoint through the server process
# Get a valid session and test
remote_test = '/tmp/test_push_api.py'
test_script = '''
import asyncio, httpx, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        # Login first
        lr = await c.post('http://127.0.0.1:8001/api/admin/login',
            json={'username': 'admin', 'password': 'demo123456'})
        ld = lr.json()
        print('Login:', ld)
        sid = ld.get('session_id', '')
        if not sid:
            print('Login failed')
            return
        # Now test bot_push_test
        pr = await c.post('http://127.0.0.1:8001/api/admin/ops/bot_push_test',
            json={'session_id': sid})
        print('Push test:', pr.status_code, pr.text)

asyncio.run(test())
'''
client.exec_command(f'cat > {remote_test} << \'EOF\'\n{test_script}\nEOF')
_, out2, err2 = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_test}')
print("=== API Test ===")
print(out2.read().decode('utf-8', errors='replace'))
print(err2.read().decode('utf-8', errors='replace'))

client.close()
