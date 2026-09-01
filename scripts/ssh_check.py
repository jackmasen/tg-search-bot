import paramiko, json, subprocess

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd):
    _, stdout, _ = client.exec_command(cmd)
    return stdout.read().decode().strip()

# 1. Check git remote
print('=== GIT REMOTE ===')
print(run('cd /www/wwwroot/tg-search-bot && git remote -v 2>/dev/null || echo NO_REMOTE'))

# 2. Check TELETHON config lengths
print('=== DB TELETHON CONFIG ===')
sql = "SELECT key, length(value) FROM system_settings WHERE key IN ('TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES');"
print(run(f"sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"{sql}\""))

# 3. Bot log
print('=== BOT LOG ===')
print(run('journalctl -u tg-search-bot --no-pager -n 15 2>/dev/null'))

# 4. Admin health
print('=== ADMIN HEALTH ===')
print(run('curl -s http://127.0.0.1:8001/health'))

# 5. Services status
print('=== SERVICES ===')
print(run('systemctl is-active tg-search-admin tg-search-bot'))

client.close()
