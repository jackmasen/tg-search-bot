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

# 检查数据库中是否已有 TG_BOT_TOKEN
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT key, substr(value,1,50) FROM system_settings WHERE key='TG_BOT_TOKEN';\"", "DB中的TG_BOT_TOKEN")

# 查看完整 .env
run("cat /www/wwwroot/tg-search-bot/.env", "完整.env")

# 检查启动时的配置加载日志
run("grep -i 'bot_token\\|config\\|load' /www/wwwroot/tg-search-bot/logs/stderr.log | tail -20", "配置加载日志")

# 检查 main.py 的校验逻辑
run("grep -n 'TG_BOT_TOKEN' /www/wwwroot/tg-search-bot/main.py | head -20", "main.py中的TG_BOT_TOKEN检查")

client.close()
