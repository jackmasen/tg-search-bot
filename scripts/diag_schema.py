# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Check system_settings schema and content
remote_script = '/tmp/diag_schema.py'
script = '''
import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
# Get schema
cur.execute("PRAGMA table_info(system_settings)")
cols = cur.fetchall()
print("Columns:", [(c[1], c[2]) for c in cols])
# Get all data
cur.execute("SELECT * FROM system_settings LIMIT 20")
rows = cur.fetchall()
print(f"Rows ({len(rows)}):")
for r in rows:
    print(f"  {r}")
conn.close()
'''
client.exec_command(f'cat > {remote_script} << \'EOF\'\n{script}\nEOF')
_, out, err = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_script}')
print("=== Schema ===")
print(out.read().decode('utf-8', errors='replace'))
print(err.read().decode('utf-8', errors='replace'))

# Check admin credentials
remote_cred = '/tmp/diag_cred.py'
cred_script = '''
import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(users)")
cols = cur.fetchall()
print("Users cols:", [(c[1], c[2]) for c in cols])
cur.execute("SELECT * FROM users LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print(f"  User: {r}")
conn.close()
'''
client.exec_command(f'cat > {remote_cred} << \'EOF\'\n{cred_script}\nEOF')
_, out2, err2 = client.exec_command(f'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 {remote_cred}')
print("=== Users ===")
print(out2.read().decode('utf-8', errors='replace'))
print(err2.read().decode('utf-8', errors='replace'))

client.close()
