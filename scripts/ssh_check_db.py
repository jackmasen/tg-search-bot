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

# 查看 system_settings 表结构
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \".schema system_settings\"", "system_settings表结构")
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, length(setting_value) as val_len FROM system_settings WHERE setting_key='TG_BOT_TOKEN';\"", "DB中TG_BOT_TOKEN")
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key FROM system_settings LIMIT 5;\"", "DB中所有setting_key")

client.close()
