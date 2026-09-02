import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

# 检查 nginx 所有站点配置
print('=== NGINX all configs ===')
stdin, stdout, stderr = client.exec_command('ls /etc/nginx/conf.d/ && echo "---" && ls /etc/nginx/sites-enabled/ 2>/dev/null', timeout=10)
print(stdout.read().decode())

print('\n=== nginx main config ===')
stdin2, stdout2, stderr2 = client.exec_command('grep -r "jsou\|tgjsbot\|proxy_pass" /etc/nginx/ --include="*.conf" 2>/dev/null | head -50', timeout=10)
print(stdout2.read().decode()[:3000])

print('\n=== check HTTP host routing ===')
stdin3, stdout3, stderr3 = client.exec_command('curl -s -H "Host: jou.tgjsbot.kdns.fr" http://localhost/api/bot/command -X POST -H "Content-Type: application/json" -d \'{"command":"/start","tg_user_id":999}\' | head -c 300', timeout=10)
print(stdout3.read().decode()[:300])

print('\n=== check / endpoint via domain host header ===')
stdin4, stdout4, stderr4 = client.exec_command('curl -s -H "Host: jou.tgjsbot.kdns.fr" http://localhost/ | head -c 200', timeout=10)
print(stdout4.read().decode()[:200])

print('\n=== check all nginx server blocks ===')
stdin5, stdout5, stderr5 = client.exec_command('nginx -T 2>/dev/null | grep -E "server_name|proxy_pass|listen" | head -60', timeout=10)
print(stdout5.read().decode()[:2000])

print('\n=== check /etc/nginx/conf.d contents ===')
stdin6, stdout6, stderr6 = client.exec_command('cat /etc/nginx/conf.d/*.conf 2>/dev/null | head -200', timeout=10)
print(stdout6.read().decode()[:2000])

print('\n=== check domain DNS resolves to this IP ===')
stdin7, stdout7, stderr7 = client.exec_command('hostjou.tgjsbot.kdns.fr 2>/dev/null || dig +short jou.tgjsbot.kdns.fr 2>/dev/null || nslookup jou.tgjsbot.kdns.fr 2>/dev/null | head -10', timeout=10)
print(stdout7.read().decode())

client.close()
print('Done.')
