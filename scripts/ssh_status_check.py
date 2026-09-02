import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. Bot service status ===')
out, _ = run('systemctl is-active tg-search-bot && echo "OK" || echo "FAIL"')
print(f'Bot active: {out}')
out, _ = run('systemctl status tg-search-bot --no-pager -n0 | tail -8')
print(out)

print('=== 2. Bot recent logs ===')
out, _ = run('journalctl -u tg-search-bot --no-pager -n 20 --since "5 min ago"')
print(out)

print('=== 3. Bot process ===')
out, _ = run('ps aux | grep main.py | grep -v grep')
print(out)

print('=== 4. Bot stdout log tail ===')
out, _ = run('tail -20 /www/wwwroot/tg-search-bot/logs/stdout.log 2>/dev/null')
print(out)

print('=== 5. Bot stderr log tail ===')
out, _ = run('tail -20 /www/wwwroot/tg-search-bot/logs/stderr.log 2>/dev/null')
print(out)

print('=== 6. Admin service status ===')
out, _ = run('systemctl is-active tg-search-admin && echo "OK" || echo "FAIL"')
print(f'Admin active: {out}')

print('=== 7. Test admin login ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Admin login: {out}')

print('=== 8. Test admin panel page ===')
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/admin/')
print(f'Admin panel HTTP: {out}')

print('=== 9. Test user page ===')
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/')
print(f'User page HTTP: {out}')

print('=== 10. Test health check ===')
out, _ = run('curl -s http://127.0.0.1:8001/health')
print(f'Health: {out}')

print('=== 11. System resources ===')
out, _ = run('free -h | head -2')
print(out)
out, _ = run('df -h /www/wwwroot/tg-search-bot/data/')
print(out)

print('=== 12. DB file check ===')
out, _ = run('ls -la /www/wwwroot/tg-search-bot/data/*.db')
print(out)

client.close()
print('\n=== ALL CHECKS COMPLETE ===')
