import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"  {out[:1000]}")
    if err: print(f"  ERR: {err[:500]}")
    return out, err

# ===== Step 1: 修复 git remote =====
print("=" * 60)
print("STEP 1: 修复 Git")
print("=" * 60)
run('git config --global --add safe.directory /www/wwwroot/tg-search-bot', 'Safe directory')
run('cd /www/wwwroot/tg-search-bot && git remote add origin https://github.com/jackmasen/tg-search-bot.git 2>&1', 'Add remote')
run('cd /www/wwwroot/tg-search-bot && git remote -v', 'Verify remote')
run('cd /www/wwwroot/tg-search-bot && git fetch origin main 2>&1', 'Fetch')
run('cd /www/wwwroot/tg-search-bot && git pull origin main --force 2>&1', 'Pull')

# ===== Step 2: 在服务器上用 Python 解密并检查 TELETHON 配置 =====
print("\n" + "=" * 60)
print("STEP 2: 解密 TELETHON 配置")
print("=" * 60)
run('''python3 << 'PYEOF'
import sqlite3, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.admin.system_settings_manager import _decrypt

conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get crypto secret
cur.execute("SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'")
row = cur.fetchone()
crypto_secret = row[0] if row else ''
print(f'CRYPTO_SECRET exists: {bool(crypto_secret)}')

for key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:
    cur.execute(f"SELECT setting_value, is_encrypted FROM system_settings WHERE setting_key='{key}'")
    row = cur.fetchone()
    val = row[0] if row else ''
    enc = row[1] if row else 0
    if val.startswith('ENC:') and crypto_secret:
        try:
            decrypted = _decrypt(val, crypto_secret)
            parts = [x.strip() for x in decrypted.split(',') if x.strip()]
            print(f'{key}: {len(parts)} items')
            for i, p in enumerate(parts):
                print(f'  [{i}] {p[:30]}...' if len(p) > 30 else f'  [{i}] {p}')
        except Exception as e:
            print(f'{key}: DECRYPT ERROR: {e}')
    else:
        print(f'{key}: {val}')
conn.close()
PYEOF''', 'Decrypt TELETHON')

# ===== Step 3: 重启服务 =====
print("\n" + "=" * 60)
print("STEP 3: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart')
import time
time.sleep(5)
run('systemctl is-active tg-search-admin tg-search-bot', 'Status')
run('journalctl -u tg-search-bot --no-pager -n 20', 'Bot logs')

client.close()
print("\n=== 完成 ===")
