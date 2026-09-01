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

# Step 1: Fix any remaining issues
print('=== Step 1: Check .env ===')
print(run('cat /www/wwwroot/tg-search-bot/.env 2>/dev/null | grep -v HASH | grep -v TOKEN | grep -v MNEMONIC | grep -v SECRET | grep -v KEY || echo "(no .env or empty)"', wait=3))

print('=== Step 2: Check current bot config in DB ===')
print(run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c \"import sqlite3;c=sqlite3.connect('data/tg_search.db');cur=c.cursor();[print(r[0],'|',r[2],'|',repr(r[1][:100]) if r[1] else 'NULL') for r in cur.execute('SELECT setting_key,value_type,setting_value FROM system_settings')];c.close()\"", wait=5))

print('=== Step 3: Restart bot ===')
print(run('systemctl restart tg-search-bot && sleep 3 && systemctl status tg-search-bot --no-pager 2>&1', wait=6))

print('=== Step 4: Get last errors ===')
print(run('journalctl -u tg-search-bot --no-pager -n 50 --since "2 min ago" 2>&1', wait=4))

ssh.close()
print('Done')
