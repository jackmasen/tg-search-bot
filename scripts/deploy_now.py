import paramiko, time

host = '186.244.251.12'
user = 'root'
pwd = 'Aa13910828867@&'
remote_base = '/www/wwwroot/tg-search-bot'

local_files = {
    'admin_template.html': r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\admin_template.html',
    'server.py': r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\server.py',
    'app/advertising/ad_manager.py': r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\app\advertising\ad_manager.py',
    'app/ai/model_service.py': r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\app\ai\model_service.py',
}

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pwd)

transport = paramiko.Transport((host, 22))
transport.connect(username=user, password=pwd)
sftp = paramiko.SFTPClient.from_transport(transport)

for rel, local_path in local_files.items():
    remote_path = remote_base + '/' + rel
    try:
        stat = sftp.stat(remote_path)
        old_size = stat.st_size
    except:
        old_size = 0
    sftp.put(local_path, remote_path)
    new_stat = sftp.stat(remote_path)
    print(f'{rel}: {old_size} -> {new_stat.st_size} bytes')

sftp.close()
client.close()
print('Upload done')

# Restart
client2 = paramiko.SSHClient()
client2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client2.connect(host, username=user, password=pwd)
client2.exec_command('pkill -9 -f "python.*server.py" 2>/dev/null; sleep 1')
time.sleep(2)
client2.exec_command('systemctl restart tg-search-admin')
time.sleep(5)

stdin, stdout, stderr = client2.exec_command('systemctl status tg-search-admin --no-pager')
out = stdout.read().decode()
print(out)
client2.close()
print('DONE')
