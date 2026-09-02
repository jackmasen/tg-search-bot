# -*- coding: utf-8 -*-
import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Test the actual API with a dummy session_id to see the real error
stdin, stdout, stderr = client.exec_command(
    'curl -s -X POST http://127.0.0.1:8001/api/admin/ops/bot_push_test '
    '-H "Content-Type: application/json" -d \'{"session_id":"test123"}\' 2>&1'
)
resp = stdout.read().decode('utf-8', errors='replace').strip()
print("API Response (no session):", resp)

# Check recent admin server logs
_, out2, _ = client.exec_command('tail -30 /www/wwwroot/tg-search-bot/logs/stderr.log 2>/dev/null || echo "no stderr.log"')
print("\n=== stderr.log ===")
print(out2.read().decode('utf-8', errors='replace'))

# Check admin service logs
_, out3, _ = client.exec_command('journalctl -u tg-search-admin --no-pager -n 30 2>&1')
print("\n=== admin journal ===")
print(out3.read().decode('utf-8', errors='replace'))

# Check the DB for ADMIN_TG_IDS and BOT_TOKEN
q = "SELECT key, substr(value,1,60) FROM settings WHERE key IN ('TG_BOT_TOKEN','ADMIN_TG_IDS')"
cmd = "cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c \"import sqlite3; c=sqlite3.connect('data/tg_search.db'); r=c.execute('" + q + "').fetchall(); [print(x[0],'=',x[1]) for x in r]\""
_, out4, _ = client.exec_command(cmd)
print("\n=== DB settings ===")
print(out4.read().decode('utf-8', errors='replace'))

client.close()
