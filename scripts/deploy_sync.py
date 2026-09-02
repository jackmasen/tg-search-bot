# -*- coding: utf-8 -*-
import paramiko
import os

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'
LOCAL_BASE = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot'
REMOTE_BASE = '/www/wwwroot/tg-search-bot'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)
sftp = client.open_sftp()

files = [
    ('app/advertising/ad_manager.py',  f'{REMOTE_BASE}/app/advertising/ad_manager.py'),
    ('app/bot/handlers.py',            f'{REMOTE_BASE}/app/bot/handlers.py'),
]

for local_rel, remote_path in files:
    local_path = os.path.join(LOCAL_BASE, local_rel)
    sftp.put(local_path, remote_path)
    print(f'Uploaded: {local_rel}')

sftp.close()

# Restart bot service
_, out, err = client.exec_command('systemctl restart tg-search-bot.service && sleep 2 && systemctl is-active tg-search-bot.service')
print(f'Bot status: {out.read().decode().strip()}')

_, out, _ = client.exec_command('journalctl -u tg-search-bot -n 15 --no-pager')
print('Recent logs:')
print(out.read().decode().strip())

client.close()
print('Deploy complete!')
