import paramiko
import sys
import time

SSH_HOST = '186.244.251.12'
SSH_USER = 'root'
SSH_PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode().strip(), stderr.read().decode().strip(), stdout.channel.recv_exit_status()

print("=== 1. Check admin service status ===")
_, out, _ = run_cmd('systemctl is-active tg-search-admin')
print(f"admin active: {out}")
_, out, _ = run_cmd('systemctl status tg-search-admin --no-pager -n0 | tail -5')
print(out)

print("\n=== 2. Check latest admin logs ===")
_, out, _ = run_cmd('journalctl -u tg-search-admin --no-pager -n 20 --since "5 min ago"')
print(out)

print("\n=== 3. Verify DB credentials ===")
_, out, _ = run_cmd("sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db \"SELECT setting_key, setting_value, is_encrypted, value_type FROM system_settings WHERE setting_key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','CRYPTO_SECRET') ORDER BY setting_key;\"")
print(out)

print("\n=== 4. Check server.py admin credentials function ===")
_, out, _ = run_cmd("sed -n '85,105p' /www/wwwroot/tg-search-bot/server.py")
print(out)

print("\n=== 5. Check admin login endpoint ===")
_, out, _ = run_cmd("sed -n '1078,1095p' /www/wwwroot/tg-search-bot/server.py")
print(out)

print("\n=== 6. Test login via curl ===")
_, out, _ = run_cmd('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f"login result: {out}")

print("\n=== 7. Run debug script with venv python ===")
_, out, _ = run_cmd("""cat > /tmp/debug_admin.py << 'PYEOF'
import sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import asyncio
from app.database import get_db
from app.admin.system_settings_manager import load_all_settings_from_db

async def debug():
    async with get_db() as db:
        settings = await load_all_settings_from_db(db)
    print('DEBUG_ADMIN_USERNAME:', repr(settings.get('ADMIN_USERNAME')))
    print('DEBUG_ADMIN_PASSWORD:', repr(settings.get('ADMIN_PASSWORD')))
    print('DEBUG_CRYPTO_SECRET:', repr(settings.get('CRYPTO_SECRET')))
    print('DEBUG_ALL_KEYS:', sorted(settings.keys()))

asyncio.run(debug())
PYEOF
""")
_, out, _ = run_cmd('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/debug_admin.py 2>&1')
print(out)

print("\n=== 8. Test with default password ===")
_, out, _ = run_cmd('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"demo123456"}\'')
print(f"default password result: {out}")

print("\n=== 9. Restart admin and test again ===")
run_cmd('systemctl restart tg-search-admin')
time.sleep(4)
_, out, _ = run_cmd('systemctl is-active tg-search-admin')
print(f"admin active after restart: {out}")
time.sleep(2)
_, out, _ = run_cmd('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f"login after restart: {out}")

print("\n=== 10. Check if there are other admin credentials in DB ===")
_, out, _ = run_cmd("sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db \"SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key LIKE '%ADMIN%' OR setting_key LIKE '%CREDENTIAL%';\"")
print(out)

print("\n=== 11. Check all system_settings keys ===")
_, out, _ = run_cmd("sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db \"SELECT setting_key, is_encrypted FROM system_settings ORDER BY setting_key;\"")
print(out)

print("\n=== 12. Check server.py imports and ADMIN_CREDENTIALS ===")
_, out, _ = run_cmd("grep -n 'ADMIN_CREDENTIALS' /www/wwwroot/tg-search-bot/server.py | head -10")
print(out)

client.close()
print("\nDone!")
