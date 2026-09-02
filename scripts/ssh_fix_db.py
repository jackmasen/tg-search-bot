import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. DB Files ===')
print(run('ls -la /www/wwwroot/tg-search-bot/data/')[0])

print('=== 2. search_bot.db tables ===')
print(run('sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db ".tables"')[0])

print('=== 3. tg_search.db tables ===')
print(run('sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db ".tables"')[0])

print('=== 4. tg_search.db credentials ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, length(setting_value), is_encrypted FROM system_settings WHERE setting_key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','CRYPTO_SECRET') ORDER BY setting_key;\"")
print(out)

print('=== 5. .env DB path ===')
out, _ = run('grep -i database /www/wwwroot/tg-search-bot/.env 2>/dev/null; grep -i db_path /www/wwwroot/tg-search-bot/.env 2>/dev/null')
print(out)

print('=== 6. server.py service env ===')
out, _ = run('systemctl cat tg-search-admin')
print(out[:2000])

print('=== 7. config.py DB_PATH ===')
out, _ = run('grep -n "DB_PATH" /www/wwwroot/tg-search-bot/app/config.py')
print(out)

print('=== 8. Copy empty search_bot.db to fix ===')
out, _ = run('cp /www/wwwroot/tg-search-bot/data/tg_search.db /www/wwwroot/tg-search-bot/data/search_bot.db')
print(out)

print('=== 9. Verify search_bot.db now has data ===')
out, _ = run('ls -la /www/wwwroot/tg-search-bot/data/search_bot.db')
print(out)
out, _ = run('sqlite3 /www/wwwroot/tg-search-bot/data/search_bot.db ".tables"')
print(out)

print('=== 10. Test login ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
print(out)

print('=== 11. If still fails, restart admin ===')
if '"ok":true' not in out:
    print('Restarting admin...')
    run('systemctl restart tg-search-admin')
    import time
    time.sleep(4)
    out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
    print(out)

client.close()
print('DONE')
