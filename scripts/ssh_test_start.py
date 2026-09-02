import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 手动运行main.py看完整报错
stdin, stdout, stderr = ssh.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python main.py 2>&1',
    timeout=15
)
print('=== stdout ===')
print(stdout.read().decode())
print('=== stderr ===')
print(stderr.read().decode())

ssh.close()
