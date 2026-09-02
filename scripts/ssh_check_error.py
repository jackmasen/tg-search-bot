import paramiko, time

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
        for line in err.splitlines()[:20]:
            print(f"  ERR: {line}")
    return out, err

# 检查服务状态和错误日志
run("systemctl status tg-search-bot --no-pager -n 30", "服务状态")
run("journalctl -u tg-search-bot --no-pager -n 30 --since '5 min ago'", "journal日志")
run("tail -50 /www/wwwroot/tg-search-bot/logs/stderr.log", "stderr日志")
run("tail -50 /www/wwwroot/tg-search-bot/logs/stdout.log", "stdout日志")

# 尝试手动启动看具体错误
run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python -c 'from server import app; print(\"import ok\")' 2>&1", "验证server导入")

client.close()
