import paramiko

HOST = '186.244.251.12'
USER = 'root'
PASSWORD = 'Aa13910828867@&'

local_dir = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)
sftp = ssh.open_sftp()

remote_path = '/www/wwwroot/tg-search-bot/app/bot/handlers.py'
local_path = local_dir + '/app/bot/handlers.py'
print(f'Uploading {local_path} -> {remote_path}')
sftp.put(local_path, remote_path)
print('  OK')

sftp.close()

cmd = 'systemctl restart tg-bot && sleep 2 && systemctl status tg-bot --no-pager | head -15'
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(f'--- restart output ---')
print(out)
if err:
    print(f'--- stderr ---')
    print(err)

ssh.close()
print('Done.')
