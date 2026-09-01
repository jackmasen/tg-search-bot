import paramiko, time

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

# ===== Step 1: 上传修复脚本到服务器 =====
print("=" * 60)
print("STEP 1: 上传修复脚本")
print("=" * 60)

script_content = r'''
import sqlite3, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.admin.system_settings_manager import _decrypt

conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()

# Get CRYPTO_SECRET
cur.execute("SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'")
row = cur.fetchone()
crypto_secret = (row[0] if row else '') or ''
print('CRYPTO_SECRET: ' + ('exists' if crypto_secret else 'EMPTY'))

results = {}
for key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:
    cur.execute("SELECT setting_value FROM system_settings WHERE setting_key=?", (key,))
    val = (cur.fetchone() or [None])[0] or ''
    if val.startswith('ENC:') and crypto_secret:
        try:
            decrypted = _decrypt(val, crypto_secret)
            parts = [x.strip() for x in decrypted.split(',') if x.strip()]
            results[key] = parts
            print(key + ': ' + str(len(parts)) + ' items')
            for i, p in enumerate(parts):
                d = p[:40] + '...' if len(p) > 40 else p
                print('  [' + str(i) + '] ' + d)
        except Exception as e:
            results[key] = [val]
            print(key + ': DECRYPT ERROR: ' + str(e))
    else:
        parts = [x.strip() for x in val.split(',') if x.strip()] if val else []
        results[key] = parts
        print(key + ': ' + str(len(parts)) + ' items (raw)')

# Align to minimum
if results:
    min_len = min(len(results[k]) for k in results)
    print('Minimum count: ' + str(min_len))
    if min_len > 0:
        new_ids = ','.join(results['TELETHON_API_IDS'][:min_len])
        new_hashes = ','.join(results['TELETHON_API_HASHS'][:min_len])
        new_phones = ','.join(results['TELETHON_PHONES'][:min_len])
        print('Aligning to ' + str(min_len) + ' groups...')
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_IDS'", (new_ids,))
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_API_HASHS'", (new_hashes,))
        cur.execute("UPDATE system_settings SET setting_value=? WHERE setting_key='TELETHON_PHONES'", (new_phones,))
        conn.commit()
        print('Config aligned and saved!')
    else:
        print('All configs are empty, no alignment needed')
conn.close()
'''

# Upload script
sftp = client.open_sftp()
sftp.putfo(__import__('io').StringIO(script_content), '/tmp/fix_telethon.py')
sftp.close()
print('Script uploaded to /tmp/fix_telethon.py')

# ===== Step 2: 执行修复脚本 =====
print("\n" + "=" * 60)
print("STEP 2: 执行 TELETHON 配置修复")
print("=" * 60)
run('python3 /tmp/fix_telethon.py', 'Fix TELETHON config')

# ===== Step 3: 重启两个服务 =====
print("\n" + "=" * 60)
print("STEP 3: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart')
time.sleep(6)
run('systemctl is-active tg-search-admin tg-search-bot', 'Status')
run('journalctl -u tg-search-bot --no-pager -n 20', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Health')

# ===== Step 4: 验证 git =====
print("\n" + "=" * 60)
print("STEP 4: 验证更新功能")
print("=" * 60)
# Login and check update
login_out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'', 'Login')
print(f'Login: {login_out[:200]}')

client.close()
print("\n=== 修复完成 ===")
