import paramiko, sys, time
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

print('=== [1] Check if bot runs manually ===')
print(run('cd /www/wwwroot/tg-search-bot && source venv/bin/activate && timeout 8 python3 main.py 2>&1 || true', wait=12))

print('=== [2] Check DB state ===')
print(run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c \"import sqlite3;c=sqlite3.connect('data/tg_search.db');cur=c.cursor();[print(r[0],'=',repr(r[1][:80] if r[1] else ''),r[2]) for r in cur.execute('SELECT setting_key,setting_value,value_type FROM system_settings WHERE setting_key IN (\\'CRYPTO_SECRET\\',\\'TELETHON_API_IDS\\',\\'TELETHON_API_HASHS\\',\\'TELETHON_PHONES\\',\\'TG_BOT_TOKEN\\')')];c.close()\"", wait=5))

print('=== [3] Check git status ===')
print(run('cd /www/wwwroot/tg-search-bot && git status --short && git log --oneline -3', wait=3))

print('=== [4] Check service ===')
print(run('systemctl status tg-search-bot --no-pager 2>&1 | head -25', wait=3))

print('=== [5] Check systemd journal ===')
print(run('journalctl -u tg-search-bot --no-pager -n 40 2>&1', wait=3))

ssh.close()
print('\nDone')
