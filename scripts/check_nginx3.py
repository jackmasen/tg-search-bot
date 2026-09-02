import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

# 找出sou.tgjsbot.kdns.fr 的完整 nginx 配置
print('=== Full nginx config for jsou.tgjsbot.kdns.fr ===')
stdin, stdout, stderr = client.exec_command('nginx -T 2>/dev/null | grep -A 50 "jsou.tgjsbot" | head -80', timeout=10)
print(stdout.read().decode()[:2000])

print('\n=== Full nginx config for flashlink ===')
stdin2, stdout2, stderr2 = client.exec_command('nginx -T 2>/dev/null | grep -A 50 "flashlink" | head -80', timeout=10)
print(stdout2.read().decode()[:2000])

print('\n=== curl to domain directly ===')
stdin3, stdout3, stderr3 = client.exec_command('curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST -H "Content-Type: application/json" -d \'{"command":"/start","tg_user_id":999}\' 2>&1 | head -c 500', timeout=10)
print(stdout3.read().decode()[:500])

print('\n=== curl to domain / endpoint ===')
stdin4, stdout4, stderr4 = client.exec_command('curl -s http://jsou.tgjsbot.kdns.fr/ 2>&1 | head -c 300', timeout=10)
print(stdout4.read().decode()[:300])

print('\n=== check all nginx sites ===')
stdin5, stdout5, stderr5 = client.exec_command('ls -la /etc/nginx/sites-enabled/ 2>/dev/null; echo "---"; ls -la /etc/nginx/conf.d/ 2>/dev/null', timeout=10)
print(stdout5.read().decode())

print('\n=== check for include paths ===')
stdin6, stdout6, stderr6 = client.exec_command('grep -r "include" /etc/nginx/nginx.conf 2>/dev/null; grep "include" /etc/nginx/conf.d/*.conf 2>/dev/null | head -20', timeout=10)
print(stdout6.read().decode())

print('\n=== test domain from outside ===')
stdin7, stdout7, stderr7 = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ 2>&1', timeout=10)
print('localhost /:', stdout7.read().decode())

stdin8, stdout8, stderr8 = client.exec_command('curl -s -o /dev/null -w "%{http_code}" -H "Host:jou.tgjsbot.kdns.fr" http://127.0.0.1/ 2>&1', timeout=10)
print('localhost with host header:', stdout8.read().decode())

client.close()
print('Done.')
