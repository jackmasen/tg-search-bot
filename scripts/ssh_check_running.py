import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 检查进程
stdin, stdout, stderr = ssh.exec_command('pgrep -f "python main.py" || echo "NOT_RUNNING"')
pid_out = stdout.read().decode().strip()
print(f'=== 进程PID: {pid_out} ===')

# 检查systemd
stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
print(f'=== systemd状态: {stdout.read().decode().strip()} ===')

# 查看日志
stdin, stdout, stderr = ssh.exec_command('tail -50 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null')
print('=== 最新日志 ===')
print(stdout.read().decode())

# 查看nohup输出
stdin, stdout, stderr = ssh.exec_command('cat /tmp/bot_stdout.log 2>/dev/null || echo "NO_LOG"')
print('=== nohup日志 ===')
print(stdout.read().decode())

ssh.close()
