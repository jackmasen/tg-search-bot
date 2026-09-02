import paramiko
import time

for attempt in range(5):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)
        print(f'连接成功 (尝试 {attempt+1})')
        break
    except Exception as e:
        print(f'连接失败 (尝试 {attempt+1}): {e}')
        if attempt < 4:
            time.sleep(5)
        else:
            raise

remote_base = '/www/wwwroot/tg-search-bot'

# 强制重置到远端最新代码
print('正在强制拉取最新代码...')
stdin, stdout, stderr = ssh.exec_command(f'cd {remote_base} && git fetch origin && git reset --hard origin/main', timeout=30)
print('fetch+reset 输出:')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查 git log
print('=== 当前 git log ===')
stdin, stdout, stderr = ssh.exec_command(f'cd {remote_base} && git log --oneline -5')
print(stdout.read().decode())

# 检查 git status
print('=== git status ===')
stdin, stdout, stderr = ssh.exec_command(f'cd {remote_base} && git status --short')
print(stdout.read().decode())

# 重启服务
print('重启服务...')
ssh.exec_command('systemctl restart tg-search-bot.service')
ssh.close()

time.sleep(10)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

# 检查服务状态
stdin, stdout, stderr = ssh.exec_command('systemctl is-active tg-search-bot.service')
print(f'服务状态: {stdout.read().decode().strip()}')

# 查看日志
stdin, stdout, stderr = ssh.exec_command('tail -20 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null')
print('=== 最新日志 ===')
print(stdout.read().decode())

ssh.close()
print('完成')
