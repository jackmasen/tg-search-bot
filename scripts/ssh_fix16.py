# -*- coding: utf-8 -*-
"""Debug admin login issue"""
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

# 1. Check what the server actually loads
print("=" * 60)
print("1. Debug: What does server.py load from DB?")
print("=" * 60)
out, err = run("cat > /tmp/debug_login.py << 'PYEOF'\nimport sys\nsys.path.insert(0, '/www/wwwroot/tg-search-bot')\nimport asyncio\nfrom app.database import init_db, get_db\n\nasync def test():\n    await init_db()\n    from app.admin.system_settings_manager import load_all_settings_from_db\n    async with get_db() as db:\n        settings = await load_all_settings_from_db(db)\n    print('ADMIN_USERNAME:', repr(settings.get('ADMIN_USERNAME')))\n    print('ADMIN_PASSWORD:', repr(settings.get('ADMIN_PASSWORD')))\n    print('All settings keys:', list(settings.keys()))\n\nasyncio.run(test())\nPYEOF\npython3 /tmp/debug_login.py")
print(out or err)

# 2. Check server.py start-up log
print("\n" + "=" * 60)
print("2. Admin Service Logs")
print("=" * 60)
out, err = run("journalctl -u tg-search-admin -n 30 --no-pager")
print(out or err)

# 3. Check the actual admin template HTML for login form
print("\n" + "=" * 60)
print("3. Check Admin Template Login Form")
print("=" * 60)
out, err = run("grep -n 'password\\|login\\|ADMIN' /www/wwwroot/tg-search-bot/admin_template.html | head -20")
print(out or err)

# 4. Direct DB query to verify password
print("\n" + "=" * 60)
print("4. Direct DB Query")
print("=" * 60)
out, err = run('sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db "SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN (\\"ADMIN_USERNAME\\",\\"ADMIN_PASSWORD\\")"')
print(out or err)

# 5. Try to login with debug output
print("\n" + "=" * 60)
print("5. Try Login with Debug")
print("=" * 60)
out, err = run('curl -v -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}" 2>&1')
print(out[:2000] or err)

ssh.close()
print("\nDone!")
