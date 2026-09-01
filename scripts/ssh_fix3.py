import paramiko, json, time

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

# ===== Step 1: 检查 bot 崩溃详情 =====
print("=" * 60)
print("STEP 1: 检查 bot 崩溃详情")
print("=" * 60)
run('tail -50 /www/wwwroot/tg-search-bot/logs/bot_stderr.log', 'Bot stderr log')
run('tail -50 /www/wwwroot/tg-search-bot/logs/bot_stdout.log', 'Bot stdout log')

# ===== Step 2: 检查 config validation error =====
print("\n" + "=" * 60)
print("STEP 2: 检查配置校验")
print("=" * 60)
# 检查 TELETHON 配置是否已修复
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES');\"", 'Current TELETHON values')

# 检查 .env 是否存在
run('ls -la /www/wwwroot/tg-search-bot/.env 2>/dev/null || echo NO_ENV_FILE', '.env file')

# 检查 main.py 是否包含 _load_config_from_db
run('grep -n "_load_config_from_db" /www/wwwroot/tg-search-bot/main.py', 'Check _load_config_from_db')

# ===== Step 3: 修复 git remote =====
print("\n" + "=" * 60)
print("STEP 3: 修复 git remote 和拉取代码")
print("=" * 60)
run('cd /www/wwwroot/tg-search-bot && git remote set-url origin https://github.com/jackmasen/tg-search-bot.git', 'Set remote URL')
run('cd /www/wwwroot/tg-search-bot && git remote -v', 'Verify remote')
run('cd /www/wwwroot/tg-search-bot && git fetch origin main 2>&1', 'Fetch from GitHub')
run('cd /www/wwwroot/tg-search-bot && git pull origin main --force 2>&1', 'Pull latest code')

# ===== Step 4: 重启服务 =====
print("\n" + "=" * 60)
print("STEP 4: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart services')
time.sleep(5)
run('systemctl is-active tg-search-admin tg-search-bot', 'Service status')
run('journalctl -u tg-search-bot --no-pager -n 25', 'Bot recent logs')

# ===== Step 5: 检查 health =====
print("\n" + "=" * 60)
print("STEP 5: 最终验证")
print("=" * 60)
run('curl -s http://127.0.0.1:8001/health', 'Admin health')
run('curl -s -X POST "http://127.0.0.1:8001/api/admin/auth/login" -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'', 'Admin login')

client.close()
print("\n=== 修复完成 ===")
