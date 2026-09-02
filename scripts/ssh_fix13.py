# -*- coding: utf-8 -*-
"""Fix admin credentials and check admin panel"""
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

# 1. Fix admin credentials in DB
print("=" * 60)
print("1. Fixing Admin Credentials")
print("=" * 60)
fix_sql = r'''import sqlite3
import hashlib
conn = sqlite3.connect("/www/wwwroot/tg-search-bot/data/tg_search.db")
cursor = conn.cursor()
# Check current state
rows = cursor.execute('SELECT setting_key, substr(setting_value,1,30), is_encrypted FROM system_settings WHERE setting_key IN ("ADMIN_USERNAME","ADMIN_PASSWORD")').fetchall()
print("Before:", rows)
# Set admin username
cursor.execute("""
    INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at)
    VALUES ("ADMIN_USERNAME", "admin", "str", 0, "后台登录账号", CURRENT_TIMESTAMP)
    ON CONFLICT(setting_key) DO UPDATE SET
        setting_value=excluded.setting_value, value_type=excluded.value_type,
        is_encrypted=excluded.is_encrypted, description=excluded.description, updated_at=CURRENT_TIMESTAMP
""")
# Set admin password - stored as plain text (as per server.py login logic)
cursor.execute("""
    INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at)
    VALUES ("ADMIN_PASSWORD", "Admin@123456", "str", 0, "后台登录密码", CURRENT_TIMESTAMP)
    ON CONFLICT(setting_key) DO UPDATE SET
        setting_value=excluded.setting_value, value_type=excluded.value_type,
        is_encrypted=excluded.is_encrypted, description=excluded.description, updated_at=CURRENT_TIMESTAMP
""")
conn.commit()
rows = cursor.execute('SELECT setting_key, substr(setting_value,1,20) as val FROM system_settings WHERE setting_key IN ("ADMIN_USERNAME","ADMIN_PASSWORD")').fetchall()
print("After:", rows)
conn.close()
print("Done!")
'''
out, err = run(f"cat > /tmp/fix_admin.py << 'PYEOF'\n{fix_sql}\nPYEOF\n./venv/bin/python /tmp/fix_admin.py")
print(out or err)

# 2. Check admin panel endpoints
print("\n" + "=" * 60)
print("2. Check Admin Panel")
print("=" * 60)
out, err = run("curl -s -o /dev/null -w 'HTTP status: %{http_code}\n' http://127.0.0.1:8001/admin/ 2>&1")
print(out or err)
out, err = run("curl -s http://127.0.0.1:8001/api/admin/check_auth 2>&1")
print(out or err)

# 3. Test admin login
print("\n" + "=" * 60)
print("3. Test Admin Login")
print("=" * 60)
out, err = run("curl -s -X POST http://127.0.0.1:8001/api/admin/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Admin@123456\"}' 2>&1")
print(out or err)

# 4. Check bot push test endpoint
print("\n" + "=" * 60)
print("4. Check Bot Push Test Endpoint")
print("=" * 60)
out, err = run("curl -s http://127.0.0.1:8001/api/admin/bot/push-test 2>&1")
print(out or err)

# 5. List all admin API endpoints
print("\n" + "=" * 60)
print("5. Admin API Endpoints")
print("=" * 60)
out, err = run("grep -n '@app\.' /www/wwwroot/tg-search-bot/server.py | grep -E 'admin|bot' | head -30")
print(out or err)

# 6. Restart admin service to apply credential changes
print("\n" + "=" * 60)
print("6. Restart Admin Service")
print("=" * 60)
out, err = run("systemctl restart tg-search-admin && sleep 3 && systemctl status tg-search-admin --no-pager | head -8")
print(out or err)

# 7. Test admin login after restart
print("\n" + "=" * 60)
print("7. Test Admin Login After Restart")
print("=" * 60)
out, err = run("curl -s -X POST http://127.0.0.1:8001/api/admin/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Admin@123456\"}' 2>&1")
print(out or err)

# 8. Check admin panel access from outside
print("\n" + "=" * 60)
print("8. Check Admin Panel from External")
print("=" * 60)
out, err = run("curl -s -o /dev/null -w 'HTTP status: %{http_code}\n' http://186.244.251.12:8001/admin/ 2>&1")
print(out or err)

# 9. Check bot is still running
print("\n" + "=" * 60)
print("9. Bot Service Status After Restart")
print("=" * 60)
out, err = run("systemctl status tg-search-bot --no-pager | head -10")
print(out or err)

# 10. Check bot logs for any new errors
print("\n" + "=" * 60)
print("10. Latest Bot Logs")
print("=" * 60)
out, err = run("tail -15 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null")
print(out or err)

ssh.close()
print("\nDone!")
