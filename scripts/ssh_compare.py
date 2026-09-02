import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        for line in out.splitlines()[:50]:
            print(f"  {line}")
    if err:
        for line in err.splitlines()[:10]:
            print(f"  ERR: {line}")
    return out, err

# 对比服务器和本地的 main.py 差异
run("md5sum /www/wwwroot/tg-search-bot/main.py", "服务器main.py md5")
run("grep -n 'validate\\|load_config\\|post_init\\|BOT_TOKEN' /www/wwwroot/tg-search-bot/main.py | head -20", "服务器main.py验证逻辑")

# 检查服务器main.py的validate相关代码
run("sed -n '83,100p' /www/wwwroot/tg-search-bot/main.py", "服务器main.py 83-100行")

# 检查服务器config.py的validate
run("grep -n 'def validate\\|BOT_TOKEN\\|errors.append' /www/wwwroot/tg-search-bot/app/config.py", "服务器config.py验证逻辑")

# 检查数据库中的TG_BOT_TOKEN
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, length(setting_value) as val_len FROM system_settings WHERE setting_key='TG_BOT_TOKEN';\"", "DB中TG_BOT_TOKEN长度")

client.close()
