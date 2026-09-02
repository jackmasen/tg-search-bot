import paramiko
import base64

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

# Write debug script via base64 to avoid escaping issues
debug_script = '''import sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import asyncio
from app.database import get_db
from app.admin.system_settings_manager import load_all_settings_from_db

async def debug():
    async with get_db() as db:
        settings = await load_all_settings_from_db(db)
    un = settings.get('ADMIN_USERNAME')
    pw = settings.get('ADMIN_PASSWORD')
    print(f'DEBUG_UN={repr(un)} len={len(un) if un else 0}')
    print(f'DEBUG_PW={repr(pw)} len={len(pw) if pw else 0}')
    print(f'DEBUG_UN_HEX={un.encode().hex() if un else "NONE"}')
    print(f'DEBUG_PW_HEX={pw.encode().hex() if pw else "NONE"}')
    print(f'DEBUG_ALL_KEYS={sorted(settings.keys())}')

asyncio.run(debug())
'''

encoded = base64.b64encode(debug_script.encode()).decode()
print("=== 1. Write debug script via base64 ===")
run(f'echo {encoded} | base64 -d > /tmp/d.py')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/d.py 2>&1')
print(f'Output: [{out}]')
print(f'Error: [{err}]')

print("\n=== 2. Check if the script was written correctly ===")
out, _ = run('cat /tmp/d.py')
print(out)

print("\n=== 3. Check the actual login request handling ===")
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Login result: {out}')

print("\n=== 4. Test with demo default password ===")
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"demo123456"}\'')
print(f'Default password result: {out}')

print("\n=== 5. Check admin password change endpoint ===")
out, _ = run('sed -n "1096,1130p" /www/wwwroot/tg-search-bot/server.py')
print(out)

print("\n=== 6. Try to change password via API to verify system works ===")
# First need to login, but we can't. Let me check if there's another way.
# Let me directly modify the DB to test with a known simple password
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"UPDATE system_settings SET setting_value='test123' WHERE setting_key='ADMIN_PASSWORD';\"")
print(f'Update password: {out}')

print("\n=== 7. Test login with new password ===")
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"test123"}\'')
print(f'Login with test123: {out}')

print("\n=== 8. If that works, restore original password ===")
if '"ok":true' in out:
    print('Login works with test123! Restoring original password...')
    out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"UPDATE system_settings SET setting_value='Admin@123456' WHERE setting_key='ADMIN_PASSWORD';\"")
    print(f'Restore password: {out}')
    out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
    print(f'Login with Admin@123456 after restore: {out}')
else:
    print('Login still fails even with test123. Need deeper debug.')
    # Restore
    run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"UPDATE system_settings SET setting_value='Admin@123456' WHERE setting_key='ADMIN_PASSWORD';\"")

print("\n=== 9. Check for any cached data or compiled Python ===")
out, _ = run('find /www/wwwroot/tg-search-bot -name "*.pyc" -path "*/admin/*" 2>/dev/null | head -5')
print(out)
out, _ = run('ls -la /www/wwwroot/tg-search-bot/app/admin/__pycache__/ 2>/dev/null')
print(out)

print("\n=== 10. Touch server.py to force reload ===")
run('touch /www/wwwroot/tg-search-bot/server.py')
run('systemctl restart tg-search-admin')
import time
time.sleep(4)
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Login after restart: {out}')

client.close()
print('DONE')
