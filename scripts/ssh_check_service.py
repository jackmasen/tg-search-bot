import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 查看systemd服务文件
stdin, stdout, stderr = ssh.exec_command('cat /etc/systemd/system/tg-search-bot.service')
print('=== systemd服务文件 ===')
print(stdout.read().decode())

# 检查进程
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "python.*(main|server)" | grep -v grep')
print('=== 进程 ===')
print(stdout.read().decode())

# 检查端口
stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep -E "8000|8001"')
print('=== 端口 ===')
print(stdout.read().decode())

# 测试前端
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8001/ | head -30')
print('=== 前端测试(8001) ===')
print(stdout.read().decode()[:500])

# 检查health
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8001/health')
print('=== health测试 ===')
print(stdout.read().decode())

ssh.close()
