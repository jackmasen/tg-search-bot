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

# 1. 解密 TELETHON_API_HASHS
print("=" * 60)
run("python3 -c \"\nimport sqlite3, base64\nconn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')\ncur = conn.cursor()\ncur.execute(\\\"SELECT setting_value FROM system_settings WHERE setting_key='TELETHON_API_HASHS'\\\")\nrow = cur.fetchone()\nval = row[0] if row else ''\nprint(f'Raw: {val[:80]}')\nif val.startswith('ENC:'):\n    print('Encrypted - cannot decrypt without CRYPTO_SECRET')\nelif val.startswith('B64:'):\n    print('Base64 encoded')\nelse:\n    print(f'Decrypted value: {val}')\nconn.close()\n\"", 'Decrypt API_HASHS')

# 2. 查看 .env 中的 TELETHON 配置
print("\n" + "=" * 60)
run('grep -i "TELETHON" /www/wwwroot/tg-search-bot/.env', '.env TELETHON settings')

# 3. 查看 bot 实际崩溃信息
print("\n" + "=" * 60)
run('journalctl -u tg-search-bot --no-pager -n 30 --output=short-iso', 'Bot full logs')

# 4. 查看 admin 服务版本信息
print("\n" + "=" * 60)
run('curl -s http://127.0.0.1:8001/api/admin/health', 'Admin health')

# 5. 检查 app/config.py 中 TELETHON 的解析逻辑
print("\n" + "=" * 60)
run('head -70 /www/wwwroot/tg-search-bot/app/config.py | tail -20', 'Config parse functions')

client.close()
print("\n=== 诊断完成 ===")
