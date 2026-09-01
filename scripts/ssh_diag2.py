import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"  OUT: {out[:800]}")
    if err: print(f"  ERR: {err[:800]}")
    return out, err

# Check git status
run('ls -la /www/wwwroot/tg-search-bot/.git 2>/dev/null || echo NO_GIT_DIR', 'Check .git')
run('cd /www/wwwroot/tg-search-bot && git status 2>&1', 'Git status')

# Check DB schema
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db '.schema system_settings'", 'DB schema')
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db 'SELECT * FROM system_settings LIMIT 5;'", 'DB sample')

# Check admin login endpoint
run('curl -s -X POST http://127.0.0.1:8001/api/admin/auth/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'', 'Login')

# Check all service endpoints
run('curl -s http://127.0.0.1:8001/api/admin/health', 'Admin health')
run('curl -s http://127.0.0.1:8001/docs', 'Docs available')

# Check TELETHON config directly
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, length(setting_value) as len FROM system_settings WHERE setting_key LIKE '%TELETHON%';\"", 'TELETHON keys')

client.close()
