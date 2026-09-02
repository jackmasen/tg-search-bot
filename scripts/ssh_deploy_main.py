import paramiko
import os
import sys

SERVER_IP = '186.244.251.12'
SERVER_USER = 'root'
SERVER_PASS = 'Aa13910828867@&'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'

LOCAL_BASE = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'

files_to_deploy = [
    ('main.py', f'{REMOTE_BASE}/main.py'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f'连接服务器 {SERVER_IP}...')
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)
sftp = ssh.open_sftp()

success_count = 0
error_count = 0

for local_rel, remote_path in files_to_deploy:
    local_path = os.path.join(LOCAL_BASE, local_rel)
    if not os.path.exists(local_path):
        print(f'[跳过] 本地文件不存在: {local_path}')
        continue
    try:
        print(f'[上传] {local_rel} -> {remote_path}')
        sftp.put(local_path, remote_path)
        print(f'[成功] {local_rel}')
        success_count += 1
    except Exception as e:
        print(f'[失败] {local_rel}: {e}')
        error_count += 1

sftp.close()
ssh.close()

print(f'\n完成: 成功 {success_count}, 失败 {error_count}')

if error_count == 0:
    print('\n重启服务...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    stdin, stdout, stderr = ssh.exec_command('systemctl restart tg-search-bot.service')
    stdout.read()
    stderr.read()

    import time
    time.sleep(8)

    stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
    status = stdout.read().decode().strip()
    print(f'服务状态: {status}')

    stdin, stdout, stderr = ssh.exec_command('tail -30 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null || journalctl -u tg-search-bot.service --no-pager -n 30')
    print(f'>>> 日志\n{stdout.read().decode()}')

    ssh.close()
else:
    print('\n有文件部署失败')
    sys.exit(1)
