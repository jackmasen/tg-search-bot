import paramiko, sys, time
HOST='186.244.251.12'
USER='root'
PASS='Aa13910828867@&'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Upload the fix script
sftp = ssh.open_sftp()
fix_script = """
import sqlite3, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.admin.system_settings_manager import _decrypt
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'")
row = cur.fetchone()
secret = (row[0] if row else '') or ''
print('CRYPTO_SECRET exists:', bool(secret))
results = {}
for key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:
    cur.execute("SELECT setting_value FROM system_settings WHERE setting_key=?", (key,))
    val = (cur.fetchone() or [None])[0] or ''
    if val.startswith('ENC:') and secret:
        try:
            dec = _decrypt(val, secret)
            parts = [x.strip() for x in dec.split(',') if x.strip()]
            results[key] = parts
            print(f'{key}: decrypted OK, {len(parts)} items')
        except Exception as e:
            print(f'{key}: DECRYPT ERROR: {e}')
            results[key] = []
    else:
        parts = [x.strip() for x in val.split(',') if x.strip()] if val else []
        results[key] = parts
        print(f'{key}: plain, {len(parts)} items')
min_len = min(len(results[k]) for k in results) if results else 0
print(f'Min length: {min_len}')
if min_len > 0:
    cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_IDS'", (','.join(results['TELETHON_API_IDS'][:min_len]),))
    cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_HASHS'", (','.join(results['TELETHON_API_HASHS'][:min_len]),))
    cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_PHONES'", (','.join(results['TELETHON_PHONES'][:min_len]),))
    conn.commit()
    print('Aligned to', min_len, 'groups')
else:
    print('ERROR: No valid config found!')
conn.close()
"""
with open('/tmp/fix_tg.py', 'w') as f:
    f.write(fix_script)
sftp.put('/tmp/fix_tg.py', '/tmp/fix_tg.py')
sftp.close()

# Run the fix
chan = ssh.invoke_shell()
def shell_run(cmd, wait=2):
    chan.sendall((cmd+'\n').encode())
    time.sleep(wait)
    out = ''
    for _ in range(20):
        if chan.recv_ready():
            out += chan.recv(65536).decode(errors='replace')
        time.sleep(0.3)
    return out

print('=== Fixing TELETHON config ===')
r = shell_run('cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 /tmp/fix_tg.py 2>&1', wait=5)
print(r)

print('=== Restarting services ===')
r = shell_run('systemctl restart tg-search-bot && sleep 3 && systemctl status tg-search-bot --no-pager 2>&1', wait=6)
print(r)

print('=== Check journal logs ===')
r = shell_run('journalctl -u tg-search-bot --no-pager -n 30 --since "1 minute ago" 2>&1', wait=4)
print(r)

ssh.close()
print('\nDone!')
