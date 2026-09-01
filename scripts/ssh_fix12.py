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

print('=== Pull latest code ===')
r = run('cd /www/wwwroot/tg-search-bot && git fetch origin && git reset --hard origin/main', wait=8)
print(r)

print('=== Verify main.py fix ===')
r = run("grep -n 'new_event_loop\\|load_config_from_db\\|post_init' /www/wwwroot/tg-search-bot/main.py", wait=3)
print(r)

print('=== Test bot manually ===')
r = run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && timeout 10 python3 main.py 2>&1 || true", wait=15)
print(r)

print('=== Restart services ===')
r = run('systemctl restart tg-search-bot tg-search-admin && sleep 4 && systemctl status tg-search-bot --no-pager 2>&1', wait=8)
print(r)

print('=== Check recent logs ===')
r = run('journalctl -u tg-search-bot --no-pager -n 20 --since "1 min ago" 2>&1', wait=4)
print(r)

ssh.close()
print('\nDone')
