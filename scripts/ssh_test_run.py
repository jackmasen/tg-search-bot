import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 停止并手动启动看完整输出
ssh.exec_command('systemctl stop tg-search-bot.service')
time.sleep(2)

# 后台启动并等待
stdin, stdout, stderr = ssh.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && nohup python main.py > /tmp/bot_stdout.log 2>&1 & echo $!; sleep 8; cat /tmp/bot_stdout.log'
)
print('=== 启动日志 ===')
print(stdout.read().decode())
print('=== stderr ===')
print(stderr.read().decode())

# 检查进程是否还在
stdin, stdout, stderr = ssh.exec_command('pgrep -f "python main.py" || echo "NOT_RUNNING"')
pid_out = stdout.read().decode().strip()
print(f'=== 进程PID: {pid_out} ===')

# 检查systemd服务状态
stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
print(f'=== systemd状态: {stdout.read().decode().strip()} ===')

# 查看最新日志
stdin, stdout, stderr = ssh.exec_command('tail -40 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null')
print('=== bot日志 ===')
print(stdout.read().decode())

ssh.close()
