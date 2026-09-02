import paramiko, time
HOST='186.244.251.12'
USER='root'
PASS='Aa13910828867@&'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
s = ssh.invoke_shell()

def run(cmd, wait=2):
    s.sendall((cmd+'\n').encode())
    time.sleep(wait)
    out = ''
    for _ in range(25):
        if s.recv_ready():
            out += s.recv(65536).decode(errors='replace')
        time.sleep(0.3)
    return out

print('=== Bot status ===')
print(run('systemctl status tg-search-bot --no-pager 2>&1', wait=3))
print('=== Admin status ===')
print(run('systemctl status tg-search-admin --no-pager 2>&1', wait=3))
print('=== Recent bot logs ===')
print(run('journalctl -u tg-search-bot --no-pager -n 15 --since "2 min ago" 2>&1', wait=4))

ssh.close()
print('\nDone')
