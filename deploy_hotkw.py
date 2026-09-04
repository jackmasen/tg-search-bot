import paramiko

local_dir = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'
remote_base = '/www/wwwroot/tg-search-bot'
host = '186.244.251.12'
user = 'root'
password = 'Aa13910828867@&'

files = [
    ('server.py', 'server.py'),
    ('app/bot/handlers.py', 'app/bot/handlers.py'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=10)
sftp = ssh.open_sftp()

for local_rel, remote_rel in files:
    lp = local_dir + '/' + local_rel
    rp = remote_base + '/' + remote_rel
    print(f'  {local_rel} -> {rp}')
    sftp.put(lp, rp)

sftp.close()

_, stdout, _ = ssh.exec_command('systemctl restart tg-search-bot && sleep 2 && systemctl status tg-search-bot --no-pager | head -10')
print(stdout.read().decode())
ssh.close()
print('Done.')
