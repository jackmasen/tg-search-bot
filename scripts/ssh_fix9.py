import paramiko, sys, time, os
HOST='186.244.251.12'
USER='root'
PASS='Aa13910828867@&'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
s = ssh.invoke_shell()
def run(cmd, wait=1.5):
    s.sendall((cmd+'\n').encode())
    time.sleep(wait)
    out = ''
    for _ in range(30):
        if s.recv_ready():
            out += s.recv(65536).decode(errors='replace')
        time.sleep(0.2)
    lines = [l for l in out.split('\n') if l.strip()]
    return '\n'.join(lines[-80:]) if lines else out

print('=== [1/5] Check bot crash reason ===')
print(run('cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 main.py 2>&1 | head -50', wait=8))

print('\n=== [2/5] Check TELETHON configs ===')
r = run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c \"\nimport sqlite3, sys\nsys.path.insert(0, '.')\nfrom app.admin.system_settings_manager import _decrypt\nconn = sqlite3.connect('data/tg_search.db')\ncur = conn.cursor()\ncur.execute(\\\"SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'\\\")\nrow = cur.fetchone()\nsecret = (row[0] if row else '') or ''\nprint('CRYPTO_SECRET:', secret[:20] if secret else 'EMPTY')\nfor key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:\n    cur.execute(\\\"SELECT setting_value FROM system_settings WHERE setting_key=?\\\", (key,))\n    val = (cur.fetchone() or [None])[0] or ''\n    if val.startswith('ENC:') and secret:\n        try:\n            dec = _decrypt(val, secret)\n            parts = [x.strip() for x in dec.split(',') if x.strip()]\n            print(f'{key}: OK ({len(parts)} items)')\n            for i,p in enumerate(parts): print(f'  [{i}] {p[:30] if len(p)>30 else p}')\n        except Exception as e:\n            print(f'{key}: DECRYPT ERROR {e}')\n    else:\n        parts = [x.strip() for x in val.split(',') if x.strip()] if val else []\n        print(f'{key}: plain ({len(parts)} items)')\n        for i,p in enumerate(parts): print(f'  [{i}] {p[:50]}')\nconn.close()\n\"", wait=5))
print(r)

print('\n=== [3/5] Check service status ===')
print(run('systemctl status tg-search-bot --no-pager -l 2>&1 | head -20', wait=3))

print('\n=== [4/5] Check git status ===')
print(run('cd /www/wwwroot/tg-search-bot && git status --short && git log --oneline -3', wait=3))

print('\n=== [5/5] Restart services ===')
print(run('systemctl restart tg-search-bot && sleep 2 && systemctl status tg-search-bot --no-pager 2>&1 | head -20', wait=6))

ssh.close()
print('\nDone!')
