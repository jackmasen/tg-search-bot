import paramiko
import os

SERVER_IP = '186.244.251.12'
SERVER_USER = 'root'
SERVER_PASS = 'Aa13910828867@&'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'
LOCAL_BASE = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)
sftp = ssh.open_sftp()

local_path = os.path.join(LOCAL_BASE, 'app/admin/version_manager.py')
remote_path = f'{REMOTE_BASE}/app/admin/version_manager.py'

print(f'上传 version_manager.py...')
sftp.put(local_path, remote_path)
print('上传成功')

sftp.close()
ssh.close()

# 重启服务
print('重启服务...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)
ssh.exec_command('systemctl restart tg-search-bot.service')
ssh.close()

import time
time.sleep(8)

# 验证
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
print(f'服务状态: {stdout.read().decode().strip()}')

stdin, stdout, stderr = ssh.exec_command('grep "perform_update" /www/wwwroot/tg-search-bot/app/admin/version_manager.py | head -3')
print(f'version_manager.py 验证: {stdout.read().decode().strip()}')

ssh.close()
print('完成')
