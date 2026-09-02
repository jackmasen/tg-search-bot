import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

# 检查 nginx 配置
print('=== NGINX CONFIG ===')
stdin, stdout, stderr = client.exec_command('ls /etc/nginx/conf.d/ && echo "---" && cat /etc/nginx/conf.d/*.conf 2>/dev/null; cat /etc/nginx/sites-enabled/* 2>/dev/null', timeout=10)
print(stdout.read().decode()[:3000])

print('\n=== direct 8001 test ===')
stdin2, stdout2, stderr2 = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/bot/command', timeout=10)
print(stdout2.read().decode())

print('\n=== bot process ===')
stdin3, stdout3, stderr3 = client.exec_command('ps aux | grep -E "uvicorn|server.py" | grep -v grep', timeout=10)
print(stdout3.read().decode())

print('\n=== admin process ===')
stdin4, stdout4, stderr4 = client.exec_command('ps aux | grep "tg-search-admin" | grep -v grep', timeout=10)
print(stdout4.read().decode())

print('\n=== which service serves port 8001 ===')
stdin5, stdout5, stderr5 = client.exec_command('ss -tlnp | grep 8001', timeout=10)
print(stdout5.read().decode())

print('\n=== nginx error log tail ===')
stdin6, stdout6, stderr6 = client.exec_command('tail -20 /var/log/nginx/error.log 2>/dev/null || tail -20 /var/log/nginx/error.log', timeout=10)
print(stdout6.read().decode()[:1000])

print('\n=== check if /api/ works on port 8001 ===')
stdin7, stdout7, stderr7 = client.exec_command('curl -s http://localhost:8001/api/bot/command -X POST -H "Content-Type: application/json" -d \'{"command":"/start","tg_user_id":999}\' | head -c 500', timeout=10)
print(stdout7.read().decode()[:500])

client.close()
print('\nDone.')
