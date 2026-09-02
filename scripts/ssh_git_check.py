import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 检查 git 状态
stdin, stdout, stderr = ssh.exec_command('cd /www/wwwroot/tg-search-bot && git status --short')
print('=== git status ===')
print(stdout.read().decode())

# 检查 git remote
stdin, stdout, stderr = ssh.exec_command('cd /www/wwwroot/tg-search-bot && git remote -v')
print('=== git remote ===')
print(stdout.read().decode())

# 检查本地和远端的差异
stdin, stdout, stderr = ssh.exec_command('cd /www/wwwroot/tg-search-bot && git log --oneline -3 && echo "---" && git log --oneline origin/main -3')
print('=== git log ===')
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
