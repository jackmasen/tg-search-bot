import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 检查进程详情
stdin, stdout, stderr = ssh.exec_command('ps aux | grep "python main" | grep -v grep')
print('=== 进程详情 ===')
print(stdout.read().decode())

# 检查systemd详情
stdin, stdout, stderr = ssh.exec_command('systemctl status tg-search-bot.service --no-pager')
print('=== systemd状态详情 ===')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查最新日志
stdin, stdout, stderr = ssh.exec_command('journalctl -u tg-search-bot.service --no-pager -n 20')
print('=== journalctl最新 ===')
print(stdout.read().decode())

# 检查bot日志文件
stdin, stdout, stderr = ssh.exec_command('ls -la /www/wwwroot/tg-search-bot/logs/ 2>/dev/null')
print('=== 日志文件 ===')
print(stdout.read().decode())

# 检查前端页面
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8000/ | head -20')
print('=== 前端页面头部 ===')
print(stdout.read().decode()[:300])

ssh.close()
