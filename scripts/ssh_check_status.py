import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 查看完整启动日志（最近50行）
stdin, stdout, stderr = ssh.exec_command('journalctl -u tg-search-bot.service --no-pager -n 50 2>/dev/null')
print('=== journalctl 最近50行 ===')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查handlers.py行数
stdin, stdout, stderr = ssh.exec_command('wc -l /www/wwwroot/tg-search-bot/app/bot/handlers.py')
print(f'handlers.py行数: {stdout.read().decode()}')

# 验证导入
stdin, stdout, stderr = ssh.exec_command('cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python -c "from app.bot.handlers import ai_search_command; print(\"OK\")" 2>&1')
print('=== 导入测试 ===')
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
