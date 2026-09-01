import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"  OUT: {out[:500]}")
    if err:
        print(f"  ERR: {err[:500]}")
    return out, err

# Step 1: Configure git safe directory and remote
run('git config --global --add safe.directory /www/wwwroot/tg-search-bot', 'Git safe directory')
run('git remote add origin https://github.com/jackmasen/tg-search-bot.git 2>/dev/null; git remote -v', 'Git remote')

# Step 2: Check DB config keys
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT key, length(value) FROM system_settings WHERE key LIKE '%TELETHON%';\"", 'TELETHON keys in DB')

# Step 3: Fetch and pull latest code
run('git fetch origin main 2>&1', 'Git fetch')
run('git pull origin main --force 2>&1', 'Git pull')

# Step 4: Get admin token and fix TELETHON config
run('curl -s -X POST http://127.0.0.1:8001/api/admin/auth/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'', 'Login token')

# Step 5: Check current TELETHON config
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT key, substr(value,1,200) FROM system_settings WHERE key IN ('TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES');\"", 'TELETHON values')

# Step 6: Restart services
run('systemctl restart tg-search-admin tg-search-bot', 'Restart services')

import time
time.sleep(5)

# Step 7: Check status
run('systemctl is-active tg-search-admin tg-search-bot', 'Service status')
run('journalctl -u tg-search-bot --no-pager -n 15', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Admin health')

client.close()
print("\n=== 修复完成 ===")
