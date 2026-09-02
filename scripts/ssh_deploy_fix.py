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
        for line in out.splitlines()[:30]:
            print(f"  {line}")
    if err:
        for line in err.splitlines()[:10]:
            print(f"  ERR: {line}")
    return out, err

SRC = r"C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot"

# 上传修复后的文件
files = [
    ("app/config.py", "/www/wwwroot/tg-search-bot/app/config.py"),
    ("main.py", "/www/wwwroot/tg-search-bot/main.py"),
]
for local, remote in files:
    print(f"\n[scp] {local} -> {remote}")
    sftp = client.open_sftp()
    sftp.put(SRC + "/" + local, remote)
    sftp.close()

# 验证修复
run("grep -n 'errors.append.*TG_BOT_TOKEN' /www/wwwroot/tg-search-bot/app/config.py || echo '修复成功: BOT_TOKEN改为警告'", "验证validate修复")
run("grep -n '未配置' /www/wwwroot/tg-search-bot/main.py", "验证main.py修复")

# 重启服务
print("\n=== 重启服务 ===")
run("systemctl restart tg-search-bot", "重启bot服务")
time.sleep(5)

# 检查状态
run("systemctl is-active tg-search-bot", "服务状态")
run("journalctl -u tg-search-bot --no-pager -n 15", "最新日志")
run("tail -15 /www/wwwroot/tg-search-bot/logs/stderr.log", "stderr日志")
run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/", "前端页面")

print("\n=== 完成 ===")
client.close()
