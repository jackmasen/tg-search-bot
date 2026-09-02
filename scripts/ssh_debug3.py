import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. Get exact DB values ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN ('ADMIN_USERNAME','ADMIN_PASSWORD') ORDER BY setting_key;\"")
print(out)

print('=== 2. Check exact password length ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT length(setting_value), setting_value FROM system_settings WHERE setting_key='ADMIN_PASSWORD';\"")
print(out)

print('=== 3. Check exact username length ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT length(setting_value), setting_value FROM system_settings WHERE setting_key='ADMIN_USERNAME';\"")
print(out)

print('=== 4. Write and run debug script ===')
script = r"""import sys
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
    print(f'DEBUG_UN_HEX={un.hex() if un else "NONE"}')
    print(f'DEBUG_PW_HEX={pw.hex() if pw else "NONE"}')

asyncio.run(debug())
"""
with open('/tmp/debug_login.py', 'w') as f:
    f.write(script)
run('cat /tmp/debug_login.py | head -5')

out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/debug_login.py 2>&1')
print('=== debug output ===')
print(out)
print('=== debug stderr ===')
print(err)

print('=== 5. Check if admin is using the right DB ===')
out, _ = run('grep -n "DB_PATH\\|get_db\\|database" /www/wwwroot/tg-search-bot/server.py | head -15')
print(out)

print('=== 6. Check server.py get_db implementation ===')
out, _ = run('grep -n -A 5 "async def get_db" /www/wwwroot/tg-search-bot/server.py')
print(out)
out, _ = run('grep -n -A 5 "async def get_db" /www/wwwroot/tg-search-bot/app/database.py')
print(out)

print('=== 7. Check actual login flow ===')
out, _ = run('sed -n "1080,1095p" /www/wwwroot/tg-search-bot/server.py')
print(out)

print('=== 8. Check for any other login endpoints ===')
out, _ = run('grep -n "api_admin_login\\|/api/admin/login" /www/wwwroot/tg-search-bot/server.py')
print(out)

print('=== 9. Test with both passwords ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
print(f'Admin@123456: {out}')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"demo123456\"}"')
print(f'demo123456: {out}')

print('=== 10. Check admin stdout logs ===')
out, _ = run('tail -30 /www/wwwroot/tg-search-bot/logs/admin_stdout.log 2>/dev/null')
print(out)

print('=== 11. Check admin stderr logs ===')
out, _ = run('tail -30 /www/wwwroot/tg-search-bot/logs/admin_stderr.log 2>/dev/null')
print(out)

print('=== 12. Check admin logs with journalctl ===')
out, _ = run('journalctl -u tg-search-admin --no-pager -n 20 --since "2 min ago"')
print(out)

client.close()
print('DONE')
