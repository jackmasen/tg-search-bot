import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 强制停止服务
ssh.exec_command('systemctl stop tg-search-bot.service')
time.sleep(2)

# 手动运行看完整错误
stdin, stdout, stderr = ssh.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && timeout 10 python main.py 2>&1 || true',
    timeout=15
)
print('=== stdout ===')
print(stdout.read().decode())
print('=== stderr ===')
print(stderr.read().decode())

ssh.close()
