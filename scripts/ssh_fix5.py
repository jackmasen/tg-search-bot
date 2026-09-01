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

# ===== Step 1: 强制拉取代码（保留本地 .env） =====
print("=" * 60)
print("STEP 1: 强制拉取代码")
print("=" * 60)
run('cd /www/wwwroot/tg-search-bot && git fetch origin main 2>&1', 'Fetch')
run('cd /www/wwwroot/tg-search-bot && git stash 2>/dev/null; git checkout --force 2>&1', 'Force checkout')
run('cd /www/wwwroot/tg-search-bot && git pull origin main --force 2>&1', 'Pull')
run('cd /www/wwwroot/tg-search-bot && git log --oneline -3', 'Verify pull')

# ===== Step 2: 生成 CRYPTO_SECRET 并写入 DB =====
print("\n" + "=" * 60)
print("STEP 2: 生成 CRYPTO_SECRET")
print("=" * 60)
run("python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"", 'Generate secret')

# 保存生成的 secret
result = run("python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"", 'Gen secret')
secret = result[0].strip() if result[0] else ''
print(f'Generated CRYPTO_SECRET: {secret}')

if secret:
    # 写入 DB
    run(f"sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"INSERT OR REPLACE INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description) VALUES ('CRYPTO_SECRET', '{secret}', 'str', 0, '数据库加密密钥');\"", 'Save CRYPTO_SECRET to DB')

# ===== Step 3: 现在可以解密 TELETHON_API_HASHS =====
print("\n" + "=" * 60)
print("STEP 3: 解密 TELETHON_API_HASHS")
print("=" * 60)
run(f'''python3 << 'PYEOF'
import sqlite3, sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.admin.system_settings_manager import _decrypt

conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()

# Get CRYPTO_SECRET
cur.execute("SELECT setting_value FROM system_settings WHERE setting_key='CRYPTO_SECRET'")
crypto_secret = (cur.fetchone() or [None])[0] or ''
print(f'CRYPTO_SECRET: {crypto_secret[:20]}...' if crypto_secret else 'CRYPTO_SECRET: EMPTY')

for key in ['TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES']:
    cur.execute(f"SELECT setting_value FROM system_settings WHERE setting_key='{key}'")
    val = (cur.fetchone() or [None])[0] or ''
    if val.startswith('ENC:') and crypto_secret:
        try:
            decrypted = _decrypt(val, crypto_secret)
            parts = [x.strip() for x in decrypted.split(',') if x.strip()]
            print(f'{key}: {len(parts)} items')
            for i, p in enumerate(parts):
                display = p[:40] + '...' if len(p) > 40 else p
                print(f'  [{i}] {display}')
        except Exception as e:
            print(f'{key}: DECRYPT ERROR: {e}')
    else:
        print(f'{key}: {val}')
conn.close()
PYEOF''', 'Decrypt hashes')

# ===== Step 4: 重启服务 =====
print("\n" + "=" * 60)
print("STEP 4: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart')
time.sleep(6)
run('systemctl is-active tg-search-admin tg-search-bot', 'Status')
run('journalctl -u tg-search-bot --no-pager -n 25', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Health')

client.close()
print("\n=== 修复完成 ===")
