# -*- coding: utf-8 -*-
import paramiko, tempfile, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Write a temp script on remote and run it
remote_script = '/tmp/diag_db.py'
script_content = '''
import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [r[0] for r in cur.fetchall()])
try:
    cur.execute("SELECT COUNT(*) FROM settings")
    print('Settings count:', cur.fetchone()[0])
    cur.execute("SELECT key, substr(value,1,80) FROM settings LIMIT 30")
    for r in cur.fetchall():
        print(f"  {r[0]} = {repr(r[1])}")
except Exception as e:
    print('Settings error:', e)
conn.close()
'''

client.exec_command(f'cat > {remote_script} << \'EOF\'\n{script_content}\nEOF')
_, out, err = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_script}')
print("=== DB Info ===")
print(out.read().decode('utf-8', errors='replace'))
print(err.read().decode('utf-8', errors='replace'))

# Also test direct Telegram API
script2 = '''
import asyncio, httpx, os, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')
from app.config import Config
from app.admin.system_settings_manager import load_all_settings_from_db
from app.database import get_db

async def test():
    async with get_db() as db:
        v = await load_all_settings_from_db(db)
        Config.apply_overrides(v)
    print('BOT_TOKEN:', repr(Config.BOT_TOKEN[:30] if Config.BOT_TOKEN else None))
    print('ADMIN_TG_IDS:', Config.ADMIN_TG_IDS)
    token = Config.BOT_TOKEN
    admins = Config.ADMIN_TG_IDS or []
    if not token:
        print('ERROR: BOT_TOKEN empty')
        return
    if not admins:
        print('ERROR: ADMIN_TG_IDS empty')
        return
    msg = "Test from diag"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=8.0)) as c:
        for uid in admins:
            try:
                r = await c.post(f'https://api.telegram.org/bot{token}/sendMessage',
                    json={'chat_id': int(uid), 'text': msg, 'parse_mode': 'HTML'})
                data = r.json()
                print(f'Chat {uid}: ok={data.get("ok")}, desc={data.get("description","")}')
            except Exception as e:
                print(f'Chat {uid}: exception={str(e)[:80]}')

asyncio.run(test())
'''

remote_script2 = '/tmp/diag_telegram.py'
client.exec_command(f'cat > {remote_script2} << \'EOF\'\n{script2}\nEOF')
_, out2, err2 = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_script2}')
print("=== Telegram Test ===")
print(out2.read().decode('utf-8', errors='replace'))
print(err2.read().decode('utf-8', errors='replace'))

client.close()
