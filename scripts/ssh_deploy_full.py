import paramiko
import os
import sys

SERVER_IP = '186.244.251.12'
SERVER_USER = 'root'
SERVER_PASS = 'Aa13910828867@&'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'

LOCAL_BASE = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'

files_to_deploy = [
    ('server.py', f'{REMOTE_BASE}/server.py'),
    ('app/bot/handlers.py', f'{REMOTE_BASE}/app/bot/handlers.py'),
    ('app/admin/version_manager.py', f'{REMOTE_BASE}/app/admin/version_manager.py'),
    ('app/config.py', f'{REMOTE_BASE}/app/config.py'),
    ('app/database.py', f'{REMOTE_BASE}/app/database.py'),
    ('main.py', f'{REMOTE_BASE}/main.py'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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

    # 重启两个服务
    ssh.exec_command('systemctl restart tg-search-bot.service')
    ssh.exec_command('pkill -f "python.*server.py" 2>/dev/null; sleep 2; cd /www/wwwroot/tg-search-bot && source venv/bin/activate && nohup python server.py > /tmp/server.log 2>&1 &')

    import time
    time.sleep(8)

    # 检查main.py服务
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
    main_status = stdout.read().decode().strip()
    print(f'main.py服务状态: {main_status}')

    # 检查server.py进程
    stdin, stdout, stderr = ssh.exec_command('pgrep -f "python.*server.py" && echo "server RUNNING" || echo "server NOT_RUNNING"')
    server_check = stdout.read().decode().strip()
    print(f'server.py状态: {server_check}')

    # 检查health
    stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8001/health')
    health = stdout.read().decode()
    print(f'health: {health}')

    # 检查日志
    stdin, stdout, stderr = ssh.exec_command('tail -20 /www/wwwroot/tg-search-bot/logs/stderr.log 2>/dev/null')
    stderr_log = stdout.read().decode()
    if stderr_log:
        print(f'stderr日志:\n{stderr_log}')

    stdin, stdout, stderr = ssh.exec_command('tail -20 /tmp/server.log 2>/dev/null')
    server_log = stdout.read().decode()
    if server_log:
        print(f'server日志:\n{server_log}')

    ssh.close()
else:
    print('\n有文件部署失败')
    sys.exit(1)
