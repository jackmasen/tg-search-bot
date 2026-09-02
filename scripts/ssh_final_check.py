import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. Check both DB files ===')
out, _ = run('ls -la /www/wwwroot/tg-search-bot/data/*.db')
print(out)

print('=== 2. Check which DB the admin service actually uses ===')
out, _ = run('grep -r "search_bot.db\\|tg_search.db" /www/wwwroot/tg-search-bot/server.py /www/wwwroot/tg-search-bot/app/config.py /www/wwwroot/tg-search-bot/.env 2>/dev/null')
print(out)

print('=== 3. Check bot service DB path ===')
out, _ = run('systemctl cat tg-search-bot')
print(out)

print('=== 4. Check .env ===')
out, _ = run('cat /www/wwwroot/tg-search-bot/.env | grep -v "^#" | grep -v "^$"')
print(out)

print('=== 5. Remove empty search_bot.db (bot uses tg_search.db by default) ===')
out, _ = run('rm -f /www/wwwroot/tg-search-bot/data/search_bot.db')
print(out)

print('=== 6. Verify only tg_search.db remains ===')
out, _ = run('ls -la /www/wwwroot/tg-search-bot/data/*.db')
print(out)

print('=== 7. Test admin login ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Admin login: {out}')

print('=== 8. Check admin session ===')
if '"ok":true' in out:
    session_id = out.split('"session_id":"')[1].split('"')[0]
    out, _ = run(f'curl -s "http://127.0.0.1:8001/api/admin/session?session_id={session_id}"')
    print(f'Session: {out}')

print('=== 9. Check bot service status ===')
out, _ = run('systemctl is-active tg-search-bot && echo "OK" || echo "FAIL"')
print(f'Bot: {out}')

print('=== 10. Check bot recent logs ===')
out, _ = run('journalctl -u tg-search-bot --no-pager -n 10 --since "3 min ago"')
print(out)

print('=== 11. Check admin recent logs ===')
out, _ = run('journalctl -u tg-search-admin --no-pager -n 10 --since "3 min ago"')
print(out)

print('=== 12. Verify DB credentials ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN ('ADMIN_USERNAME','ADMIN_PASSWORD','CRYPTO_SECRET') ORDER BY setting_key;\"")
print(out)

print('=== 13. Check git status ===')
out, _ = run('cd /www/wwwroot/tg-search-bot && git status --short')
print(out)

print('=== 14. Check git log ===')
out, _ = run('cd /www/wwwroot/tg-search-bot && git log --oneline -5')
print(out)

client.close()
print('\n=== ALL CHECKS COMPLETE ===')
