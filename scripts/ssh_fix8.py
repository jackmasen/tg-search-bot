import paramiko, time

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

# ===== Step 1: 安装 cryptography 依赖 =====
print("=" * 60)
print("STEP 1: 安装 cryptography")
print("=" * 60)
run('pip3 install cryptography -q 2>&1', 'Install cryptography')
run("python3 -c 'from cryptography.fernet import Fernet; print(\\\"cryptography OK\\\")'", 'Verify')

# ===== Step 2: 重新执行修复脚本（cryptography 已安装）=====
print("\n" + "=" * 60)
print("STEP 2: 重新解密 TELETHON 配置")
print("=" * 60)
run('python3 /tmp/fix_telethon.py', 'Fix TELETHON config')

# ===== Step 3: 查看 bot 崩溃详细错误 =====
print("\n" + "=" * 60)
print("STEP 3: 查看 bot 崩溃详情")
print("=" * 60)
run('journalctl -u tg-search-bot --no-pager -n 30 --output=short-iso', 'Bot full logs')
run('cat /www/wwwroot/tg-search-bot/logs/bot_stderr.log 2>/dev/null | tail -30', 'Bot stderr')
run('cat /www/wwwroot/tg-search-bot/logs/bot_stdout.log 2>/dev/null | tail -30', 'Bot stdout')

# ===== Step 4: 检查 admin 密码 =====
print("\n" + "=" * 60)
print("STEP 4: 检查 admin 密码")
print("=" * 60)
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE '%ADMIN%';\"", 'Admin settings')

# ===== Step 5: 重启服务 =====
print("\n" + "=" * 60)
print("STEP 5: 重启服务")
print("=" * 60)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart')
time.sleep(6)
run('systemctl is-active tg-search-admin tg-search-bot', 'Status')
run('journalctl -u tg-search-bot --no-pager -n 15', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Health')

client.close()
print("\n=== 修复完成 ===")
