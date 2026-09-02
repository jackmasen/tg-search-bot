# -*- coding: utf-8 -*-
"""Check DB config and admin status"""
import paramiko

SSH_HOST = "186.244.251.12"
SSH_USER = "root"
SSH_PASS = "Aa13910828867@&"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

# Write a SQL query script to server
sql_script = '''
import sqlite3
conn = sqlite3.connect("/www/wwwroot/tg-search-bot/data/tg_search.db")
rows = conn.execute('SELECT setting_key, length(setting_value) as val_len, value_type, is_encrypted FROM system_settings WHERE setting_key IN ("CRYPTO_SECRET","ADMIN_USERNAME","ADMIN_PASSWORD")').fetchall()
for r in rows:
    print(r)
conn.close()
'''

print("=== DB Config Check ===")
out, err = run(f"cd /www/wwwroot/tg-search-bot && cat > /tmp/check_db.py << 'PYEOF'\n{sql_script}\nPYEOF\n./venv/bin/python /tmp/check_db.py")
print(out or err)

# Get all settings keys
print("\n=== All system_settings Keys ===")
sql_script2 = '''
import sqlite3
conn = sqlite3.connect("/www/wwwroot/tg-search-bot/data/tg_search.db")
rows = conn.execute('SELECT setting_key, value_type, is_encrypted FROM system_settings ORDER BY setting_key').fetchall()
for r in rows:
    print(r[0], r[1], r[2])
conn.close()
'''
out, err = run(f"cd /www/wwwroot/tg-search-bot && cat > /tmp/check_keys.py << 'PYEOF'\n{sql_script2}\nPYEOF\n./venv/bin/python /tmp/check_keys.py")
print(out or err)

# Check admin login
print("\n=== Test Admin Panel ===")
out, err = run("curl -s http://127.0.0.1:8001/api/admin/session -X GET 2>&1 | head -20")
print(out or err)

# Check bot push test endpoint
print("\n=== Test Bot Push Test Endpoint ===")
out, err = run("curl -s http://127.0.0.1:8001/api/admin/bot/push-test 2>&1 | head -20")
print(out or err)

# Check admin web interface
print("\n=== Admin Web Interface ===")
out, err = run("curl -s -o /dev/null -w '%{http_code}' http://186.244.251.12:8001/admin/ 2>&1")
print(out or err)

# Check system uptime
print("\n=== System Uptime ===")
out, err = run("uptime")
print(out or err)

# Check memory usage
print("\n=== Memory Usage ===")
out, err = run("free -h")
print(out or err)

# Check disk usage
print("\n=== Disk Usage ===")
out, err = run("df -h /www")
print(out or err)

ssh.close()
print("\nDone!")
