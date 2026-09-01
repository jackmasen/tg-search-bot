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

print('=== Step 1: Pull latest code ===')
r = run('cd /www/wwwroot/tg-search-bot && git fetch origin && git reset --hard origin/main && git status --short', wait=8)
print(r)

print('=== Step 2: Verify the fix is in the pulled code ===')
r = run("grep -n '第一遍' /www/wwwroot/tg-search-bot/app/admin/system_settings_manager.py", wait=3)
print(r)

print('=== Step 3: Test bot manually (8 seconds) ===')
r = run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && timeout 8 python3 main.py 2>&1 || true", wait=12)
print(r)

print('=== Step 4: Restart services ===')
r = run('systemctl restart tg-search-bot tg-search-admin 2>&1 && sleep 3 && systemctl status tg-search-bot --no-pager 2>&1', wait=8)
print(r)

print('=== Step 5: Check logs ===')
r = run('journalctl -u tg-search-bot --no-pager -n 30 --since "1 min ago" 2>&1', wait=4)
print(r)

ssh.close()
print('\nDone')
