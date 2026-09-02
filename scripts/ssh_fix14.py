# -*- coding: utf-8 -*-
"""Fix admin credentials - corrected script"""
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

# 1. Check current DB state
print("=" * 60)
print("1. Check Current DB Admin Settings")
print("=" * 60)
out, err = run("cat /www/wwwroot/tg-search-bot/venv/bin/python")
print("Python path check:", out or err)

out, err = run("ls -la /www/wwwroot/tg-search-bot/venv/bin/ | head -5")
print("Venv bin:", out or err)

out, err = run("which python3 && python3 --version")
print("Python3:", out or err)

# 2. Fix admin credentials using python3
print("\n" + "=" * 60)
print("2. Fix Admin Credentials")
print("=" * 60)
fix_script = '''
import sqlite3
import sys

conn = sqlite3.connect("/www/wwwroot/tg-search-bot/data/tg_search.db")
cursor = conn.cursor()

# Check current state
rows = cursor.execute('SELECT setting_key, substr(setting_value,1,50), is_encrypted FROM system_settings WHERE setting_key IN ("ADMIN_USERNAME","ADMIN_PASSWORD")').fetchall()
print("Before:", rows)

# Set admin username
cursor.execute("""
    INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at)
    VALUES ("ADMIN_USERNAME", "admin", "str", 0, "后台登录账号", CURRENT_TIMESTAMP)
    ON CONFLICT(setting_key) DO UPDATE SET
        setting_value=excluded.setting_value, value_type=excluded.value_type,
        is_encrypted=excluded.is_encrypted, description=excluded.description, updated_at=CURRENT_TIMESTAMP
""")

# Set admin password - plain text (server.py compares plain text)
cursor.execute("""
    INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at)
    VALUES ("ADMIN_PASSWORD", "Admin@123456", "str", 0, "后台登录密码", CURRENT_TIMESTAMP)
    ON CONFLICT(setting_key) DO UPDATE SET
        setting_value=excluded.setting_value, value_type=excluded.value_type,
        is_encrypted=excluded.is_encrypted, description=excluded.description, updated_at=CURRENT_TIMESTAMP
""")

conn.commit()

# Verify
rows = cursor.execute('SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN ("ADMIN_USERNAME","ADMIN_PASSWORD")').fetchall()
print("After:", rows)
conn.close()
print("Done!")
'''

# Write script to server and run
run(f"cat > /tmp/fix_admin2.py << 'PYEOF'\n{fix_script}\nPYEOF")
out, err = run("python3 /tmp/fix_admin2.py")
print(out or err)

# 3. Restart admin service
print("\n" + "=" * 60)
print("3. Restart Admin Service")
print("=" * 60)
out, err = run("systemctl restart tg-search-admin && sleep 2 && systemctl status tg-search-admin --no-pager | head -8")
print(out or err)

# 4. Test admin login
print("\n" + "=" * 60)
print("4. Test Admin Login")
print("=" * 60)
out, err = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
print(out or err)

# 5. Check bot status
print("\n" + "=" * 60)
print("5. Bot Service Status")
print("=" * 60)
out, err = run("systemctl status tg-search-bot --no-pager | head -8")
print(out or err)

# 6. Check bot logs
print("\n" + "=" * 60)
print("6. Latest Bot Logs")
print("=" * 60)
out, err = run("tail -20 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null || journalctl -u tg-search-bot -n 20 --no-pager")
print(out or err)

ssh.close()
print("\nDone!")
