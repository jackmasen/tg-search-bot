# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Check DB schema and all settings
_, out1, _ = client.exec_command(
    "cd /www/wwwroot/tg-search-bot && source venv/bin/activate && "
    "python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/tg_search.db')
cur = conn.cursor()
# Check tables
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
print('Tables:', [r[0] for r in cur.fetchall()])
# Check settings table
try:
    cur.execute(\"SELECT COUNT(*) FROM settings\")
    print('Settings count:', cur.fetchone()[0])
    cur.execute(\"SELECT key, substr(value,1,60) FROM settings LIMIT 20\")
    for r in cur.fetchall():
        print(f'  {r[0]} = {repr(r[1])}')
except Exception as e:
    print('Settings error:', e)
# Check all tables content
for table in ['settings', 'users', 'channels']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        print(f'{table} count:', cur.fetchone()[0])
    except:
        pass
conn.close()
PYEOF"
)
print("=== DB Schema ===")
print(out1.read().decode('utf-8', errors='replace'))

client.close()
