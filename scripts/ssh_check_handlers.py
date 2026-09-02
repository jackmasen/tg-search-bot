import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# 检查服务器上的 handlers.py 是否包含 ai_search_command
stdin, stdout, stderr = ssh.exec_command('grep -n "ai_search_command" /www/wwwroot/tg-search-bot/app/bot/handlers.py || echo "NOT_FOUND"')
print('=== 服务器 handlers.py 中 ai_search_command ===')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查服务器上的 handlers.py 行数
stdin, stdout, stderr = ssh.exec_command('wc -l /www/wwwroot/tg-search-bot/app/bot/handlers.py')
print('=== 服务器 handlers.py 行数 ===')
print(stdout.read().decode())

# 检查服务器 main.py 的导入
stdin, stdout, stderr = ssh.exec_command('grep -n "ai_search_command" /www/wwwroot/tg-search-bot/main.py || echo "NOT_FOUND"')
print('=== 服务器 main.py 中 ai_search_command ===')
print(stdout.read().decode())
print(stderr.read().decode())

# 检查服务器上的 main.py 行数
stdin, stdout, stderr = ssh.exec_command('wc -l /www/wwwroot/tg-search-bot/main.py')
print('=== 服务器 main.py 行数 ===')
print(stdout.read().decode())

# 检查本地 handlers.py 行数
local_path = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\app\bot\handlers.py'
with open(local_path, 'r', encoding='utf-8') as f:
    local_lines = f.readlines()
print(f'=== 本地 handlers.py 行数: {len(local_lines)} ===')

# 检查本地 main.py 行数
local_main = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\main.py'
with open(local_main, 'r', encoding='utf-8') as f:
    local_main_lines = f.readlines()
print(f'=== 本地 main.py 行数: {len(local_main_lines)} ===')

# 检查服务器 bot 目录有哪些文件
stdin, stdout, stderr = ssh.exec_command('ls -la /www/wwwroot/tg-search-bot/app/bot/')
print('=== 服务器 bot 目录 ===')
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
