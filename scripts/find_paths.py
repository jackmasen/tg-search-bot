# -*- coding: utf-8 -*-
import paramiko

HOST='186.244.251.12'
USER='root'
PASS='Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

# Find correct path
_, out, _ = client.exec_command('find / -name "ad_manager.py" -type f 2>/dev/null | head -5')
print('=== ad_manager.py locations ===')
print(out.read().decode().strip())

_, out, _ = client.exec_command('find / -name "handlers.py" -path "*/bot/*" 2>/dev/null | head -5')
print('=== handlers.py locations ===')
print(out.read().decode().strip())

_, out, _ = client.exec_command('ls /home/')
print('=== /home/ ===')
print(out.read().decode().strip())

_, out, _ = client.exec_command('ls /www/wwwroot/')
print('=== /www/wwwroot/ ===')
print(out.read().decode().strip())

# Get bot service working directory
_, out, _ = client.exec_command('systemctl show tg-search-bot --property=WorkingDirectory --no-pager')
print('=== Bot WorkingDirectory ===')
print(out.read().decode().strip())

client.close()
