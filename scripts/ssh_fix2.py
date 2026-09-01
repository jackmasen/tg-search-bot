import paramiko, json, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"  OUT: {out[:600]}")
    if err: print(f"  ERR: {err[:600]}")
    return out, err

# ===== Step 1: 修复 git remote =====
print("=" * 50)
print("STEP 1: 修复 Git 远程仓库")
print("=" * 50)
run('git config --global --add safe.directory /www/wwwroot/tg-search-bot', 'safe.directory')
run('git remote set-url origin https://github.com/jackmasen/tg-search-bot.git', 'Set remote URL')
run('git remote -v', 'Verify remote')
run('git fetch origin main 2>&1', 'Fetch from GitHub')
run('git pull origin main --force 2>&1', 'Pull latest code')

# ===== Step 2: 检查 TELETHON 实际值 =====
print("\n" + "=" * 50)
print("STEP 2: 检查 TELETHON 配置实际值")
print("=" * 50)
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES');\"", 'TELETHON raw values')

# ===== Step 3: 修复配置数量不一致 =====
print("\n" + "=" * 50)
print("STEP 3: 修复 TELETHON 配置数量对齐")
print("=" * 50)
# 获取三组值的原始内容
_, ids_out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_value FROM system_settings WHERE setting_key='TELETHON_API_IDS';\"")
_, hashes_out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_value FROM system_settings WHERE setting_key='TELETHON_API_HASHS';\"")
_, phones_out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_value FROM system_settings WHERE setting_key='TELETHON_PHONES';\"")

ids_val = ids_out.read().decode().strip()
hashes_val = hashes_out.read().decode().strip()
phones_val = phones_out.read().decode().strip()

print(f"API_IDS: {ids_val}")
print(f"API_HASHS: {hashes_val}")
print(f"PHONES: {phones_val}")

# 解析为列表，取最少条数对齐
ids_list = [x.strip() for x in ids_val.split(',') if x.strip()]
hashes_list = [x.strip() for x in hashes_val.split(',') if x.strip()]
phones_list = [x.strip() for x in phones_val.split(',') if x.strip()]

min_len = min(len(ids_list), len(hashes_list), len(phones_list))
print(f"\n三组数量: IDs={len(ids_list)}, HASHS={len(hashes_list)}, PHONES={len(phones_list)}")
print(f"取最小值: {min_len} 组")

if min_len > 0:
    # 对齐到最小数量
    new_ids = ','.join(ids_list[:min_len])
    new_hashes = ','.join(hashes_list[:min_len])
    new_phones = ','.join(phones_list[:min_len])
    print(f"对齐后: IDs={new_ids}, HASHS={new_hashes}, PHONES={new_phones}")

    # 更新数据库
    cmd = f"""sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db "
UPDATE system_settings SET setting_value='{new_ids}' WHERE setting_key='TELETHON_API_IDS';
UPDATE system_settings SET setting_value='{new_hashes}' WHERE setting_key='TELETHON_API_HASHS';
UPDATE system_settings SET setting_value='{new_phones}' WHERE setting_key='TELETHON_PHONES';
SELECT 'DONE' as status;
"""
    run(cmd, 'Fix config in DB')
else:
    print("所有配置均为空，无需修复")

# ===== Step 4: 重启服务 =====
print("\n" + "=" * 50)
print("STEP 4: 重启服务")
print("=" * 50)
run('systemctl restart tg-search-admin tg-search-bot', 'Restart services')
time.sleep(5)

# ===== Step 5: 验证状态 =====
print("\n" + "=" * 50)
print("STEP 5: 验证状态")
print("=" * 50)
run('systemctl is-active tg-search-admin tg-search-bot', 'Service status')
run('journalctl -u tg-search-bot --no-pager -n 20', 'Bot logs')
run('curl -s http://127.0.0.1:8001/health', 'Admin health')

client.close()
print("\n=== 修复完成 ===")
