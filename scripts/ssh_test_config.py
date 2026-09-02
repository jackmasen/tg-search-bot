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

# 手动测试配置加载
run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python -c \"from app.config import Config; print('BOT_TOKEN:', Config.BOT_TOKEN[:20] if Config.BOT_TOKEN else 'EMPTY')\"", "配置加载测试")

# 查看最近启动日志
run("journalctl -u tg-search-bot --no-pager -n 40", "最新journal日志")

# 检查数据库是否完好
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"PRAGMA integrity_check;\"", "DB完整性检查")

client.close()
