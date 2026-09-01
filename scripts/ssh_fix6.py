import paramiko, json, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"  {out[:800]}")
    if err: print(f"  ERR: {err[:500]}")
    return out, err

# ===== Step 1: 强制拉取代码 =====
print("=" * 60)
print("STEP 1: 强制拉取代码")
print("=" * 60)
out, err = run('cd /www/wwwroot/tg-search-bot && git fetch origin main 2>&1', 'Fetch')
out, err = run('cd /www/wwwroot/tg-search-bot && git checkout -f origin/main -- . 2>&1', 'Checkout forced')
out, err = run('cd /www/wwwroot/tg-search-bot && git reset --hard origin/main 2>&1', 'Reset hard')
out, err = run('cd /www/wwwroot/tg-search-bot && git log --oneline -3 2>&1', 'Verify')

# ===== Step 2: 解密并修复 TELETHON 配置 =====
print("\n" + "=" * 60)
print("STEP 2: 解密 TELETHON_API_HASHS 并修复配置")
print("=" * 60)
out, err = run('''python3 << 'PYEOF'
import sqlite3, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.admin.system_settings_manager import _decrypt

conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()

# Get CRYPTO_SECRET
cur.execute("SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'")
row = cur.fetchone()
crypto_secret = (row[0] if row else '') or ''
print(f'CRYPTO_SECRET: {crypto_secret[:20]}...' if crypto_secret else 'CRYPTO_SECRET: EMPTY')

results = {}
for key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:
    cur.execute(f"SELECT setting_value FROM system_settings WHERE setting_key='{key}'")
    val = (cur.fetchone() or [None])[0] or ''
    if val.startswith('ENC:') and crypto_secret:
        try:
            decrypted = _decrypt(val, crypto_secret)
            parts = [x.strip() for x in decrypted.split(',') if x.strip()]
            results[key] = parts
            print(f'{key}: {len(parts)} items')
            for i, p in enumerate(parts):
                display = p[:40] + '...' if len(p) > 40 else p
                print(f'  [{i}] {display}')
        except Exception as e:
            results[key] = [val]
            print(f'{key}: DECRYPT ERROR: {e}')
    else:
        parts = [x.strip() for x in val.split(',') if x.strip()] if val else []
        results[key] = parts
        print(f'{key}: {len(parts)} items (raw)')

# Align to minimum
if results:
    min_len = min(len(results[k]) for k in results)
    print(f'\nMinimum count: {min_len}')
    if min_len > 0:
        new_ids = ','.join(results['TELETHON_API_IDS'][:min_len])
        new_hashes = ','.join(results['TELETHON_API_HASHS'][:min_len])
        new_phones = ','.join(results['TELETHON_PHONES'][:min_len])
        print(f'Aligning to {min_len} groups...')
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_IDS'", (new_ids,))
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_HASHS'", (new_hashes,))
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_PHONES'", (new_phones,))
        conn.commit()
        print('Config aligned and saved!')
    else:
        print('All configs are empty, no alignment needed')
conn.close()
PYEOF''', 'Decrypt and fix TELETHON')

# ===== Step 3: 重启服务 =====
print("\n" + "=" * 60)
print("STEP 3: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart')
time.sleep(6)
run('systemctl is-active tg-search-admin tg-search-bot', 'Status')
run('journalctl -u tg-search-bot --no-pager -n 25', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Health')

client.close()
print("\n=== 修复完成 ===")
