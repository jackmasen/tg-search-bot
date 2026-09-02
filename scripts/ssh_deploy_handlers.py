import paramiko
import os
import sys

SERVER_IP = '186.244.251.12'
SERVER_USER = 'root'
SERVER_PASS = 'Aa13910828867@&'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'

LOCAL_BASE = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'

files_to_deploy = [
    ('app/bot/handlers.py', f'{REMOTE_BASE}/app/bot/handlers.py'),
    ('app/bot/__init__.py', f'{REMOTE_BASE}/app/bot/__init__.py'),
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

# 清除 pycache
print('\n[清理] 清除 Python 缓存...')
ssh.exec_command(f'find {REMOTE_BASE}/app/bot/__pycache__ -name "*.pyc" -delete 2>/dev/null')
ssh.exec_command(f'rm -f {REMOTE_BASE}/app/bot/__pycache__/*.pyc 2>/dev/null')

sftp.close()
ssh.close()

print(f'\n完成: 成功 {success_count}, 失败 {error_count}')

if error_count == 0:
    print('\n重启服务...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    # 重启服务
    stdin, stdout, stderr = ssh.exec_command('systemctl restart tg-search-bot.service')
    stdout.read()
    stderr.read()

    import time
    time.sleep(5)

    # 检查服务状态
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
    status = stdout.read().decode().strip()

    stdin, stdout, stderr = ssh.exec_command('systemctl status tg-search-bot.service --no-pager -n5')
    status_out = stdout.read().decode()
    status_err = stderr.read().decode()

    print(f'=== 服务状态: {status} ===')
    print(f'>>> status输出\n{status_out}')
    if status_err:
        print(f'>>> stderr\n{status_err}')

    # 检查启动日志
    stdin, stdout, stderr = ssh.exec_command('tail -20 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null || journalctl -u tg-search-bot.service --no-pager -n 20')
    log_out = stdout.read().decode()
    log_err = stderr.read().decode()
    print(f'>>> 最新日志\n{log_out}')
    if log_err:
        print(f'>>> 错误\n{log_err}')

    # 验证导入是否正确
    stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_BASE} && source venv/bin/activate && python -c "from app.bot.handlers import ai_search_command, ai_command; print(\"导入成功\")" 2>&1')
    import_check = stdout.read().decode()
    import_err = stderr.read().decode()
    print(f'>>> 导入验证\n{import_check}')
    if import_err:
        print(f'>>> 导入错误\n{import_err}')

    ssh.close()
else:
    print('\n有文件部署失败，请检查后重试')
    sys.exit(1)
