import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 停止手动启动的进程
ssh.exec_command('pkill -f "python main.py" 2>/dev/null; sleep 2')

# 用systemd启动
stdin, stdout, stderr = ssh.exec_command('systemctl start tg-search-bot.service')
stdout.read()
stderr.read()

time.sleep(8)

# 检查状态
stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
status = stdout.read().decode().strip()
print(f'=== systemd状态: {status} ===')

# 查看日志
stdin, stdout, stderr = ssh.exec_command('journalctl -u tg-search-bot.service --no-pager -n 30')
print('=== journalctl日志 ===')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查进程
stdin, stdout, stderr = ssh.exec_command('pgrep -f "python main.py" || echo "NOT_RUNNING"')
print(f'=== 进程: {stdout.read().decode().strip()} ===')

ssh.close()
