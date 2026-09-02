import paramiko

SSH_HOST = '186.244.251.12'
SSH_USER = 'root'
SSH_PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

# 1. Check service status
print("--- Service Status ---")
print(run('systemctl is-active tg-search-admin && echo "OK" || echo "FAIL"')[0])
print(run('systemctl is-active tg-search-bot && echo "OK" || echo "FAIL"')[0])

# 2. Check DB path and table
print("--- DB Check ---")
out, _ = run('ls -la /www/wwwroot/tg-search-bot/data/')
print(out)
out, _ = run('sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db ".tables"')
print(out)

# 3. Check system_settings table
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db \"SELECT setting_key, length(setting_value), is_encrypted FROM system_settings WHERE setting_key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','CRYPTO_SECRET') ORDER BY setting_key;\"")
print("--- DB Credentials ---")
print(out)

# 4. Check admin service logs
print("--- Admin Logs ---")
out, _ = run('journalctl -u tg-search-admin --no-pager -n 15 --since "3 min ago"')
print(out)

# 5. Test login
print("--- Login Test ---")
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
print(out)

# 6. Check what version of server.py is running
print("--- Server.py Version ---")
out, _ = run('head -5 /www/wwwroot/tg-search-bot/server.py')
print(out)
out, _ = run('grep -n "APP_VERSION\\|admin_login\\|ADMIN_CREDENTIALS" /www/wwwroot/tg-search-bot/server.py | head -10')
print(out)

# 7. Get the full admin credentials loading code
print("--- Admin Credentials Code ---")
out, _ = run('grep -n -A 15 "_load_admin_credentials_from_db" /www/wwwroot/tg-search-bot/server.py | head -30')
print(out)

# 8. Get the login endpoint code
print("--- Login Endpoint ---")
out, _ = run('grep -n -A 15 "api_admin_login" /www/wwwroot/tg-search-bot/server.py | head -20')
print(out)

# 9. Run debug script on server
print("--- Debug Script ---")
run("cat > /tmp/d.py << 'EOF'")
run("import sys; sys.path.insert(0, '/www/wwwroot/tg-search-bot')")
run("import asyncio")
run("from app.database import get_db")
run("from app.admin.system_settings_manager import load_all_settings_from_db")
run("async def f():")
run("    async with get_db() as db:")
run("        s = await load_all_settings_from_db(db)")
run("    print('UN:', repr(s.get('ADMIN_USERNAME')))")
run("    print('PW:', repr(s.get('ADMIN_PASSWORD')))")
run("    print('CS:', repr(s.get('CRYPTO_SECRET')))")
run("asyncio.run(f())")
run("EOF")
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/d.py 2>&1')
print(out)

# 10. Check if admin process is using the right code
print("--- Process Check ---")
out, _ = run('ps aux | grep server.py | grep -v grep')
print(out)

# 11. Check git status
print("--- Git Status ---")
out, _ = run('cd /www/wwwroot/tg-search-bot && git log --oneline -3')
print(out)

client.close()
print("DONE")
