import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

time.sleep(5)

# 检查状态
stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
status = stdout.read().decode().strip()
print(f'=== 服务状态: {status} ===')

# 查看最新日志（从bot日志文件）
stdin, stdout, stderr = ssh.exec_command('tail -30 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null')
print('=== bot日志 ===')
print(stdout.read().decode())

# 检查进程
stdin, stdout, stderr = ssh.exec_command('pgrep -f "python main.py"')
pids = stdout.read().decode().strip()
print(f'=== 进程: {pids} ===')

# 测试前端页面
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/')
print(f'=== 前端页面HTTP状态: {stdout.read().decode()} ===')

# 测试API
stdin, stdout, stderr = ssh.exec_command('curl -s -X POST http://127.0.0.1:8000/api/bot/command -H "Content-Type: application/json" -d \'{"command":"/start","user_id":123456789}\'')
print('=== /start API测试 ===')
print(stdout.read().decode()[:500])

ssh.close()
