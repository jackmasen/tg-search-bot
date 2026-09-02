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
        for line in out.splitlines()[:30]:
            print(f"  {line}")
    if err:
        for line in err.splitlines()[:10]:
            print(f"  ERR: {line}")
    return out, err

# 查看服务器上 .env 的内容
run("cat /www/wwwroot/tg-search-bot/.env", "服务器.env当前内容")

# 查看是否有备份
run("ls -la /www/wwwroot/tg-search-bot/.env.bak.* 2>/dev/null || echo 'no backup'", "查找.env备份")

# 恢复备份或从环境变量重新生成
# 先检查是否有旧的备份
out, _ = run("ls -t /www/wwwroot/tg-search-bot/.env.bak.* 2>/dev/null | head -1", "最新备份")
backup_file = out.strip().split('\n')[-1].strip() if out.strip() else ""
print(f"\n备份文件: {backup_file}")

if backup_file and backup_file != "no backup":
    run(f"cp {backup_file} /www/wwwroot/tg-search-bot/.env", "从备份恢复.env")
else:
    # 从 .env.example 恢复并补充 VERSION_REPO_URL
    run("cp /www/wwwroot/tg-search-bot/.env.example /www/wwwroot/tg-search-bot/.env 2>/dev/null || true", "从example恢复")
    run("echo 'VERSION_REPO_URL=https://github.com/jackmasen/tg-search-bot.git' >> /www/wwwroot/tg-search-bot/.env", "补充VERSION_REPO_URL")

# 确认 TG_BOT_TOKEN 已配置
run("grep 'TG_BOT_TOKEN' /www/wwwroot/tg-search-bot/.env", "确认TG_BOT_TOKEN")

# 重启服务
print("\n=== 重启服务 ===")
run("systemctl restart tg-search-bot", "重启bot服务")
import time
time.sleep(5)
run("systemctl is-active tg-search-bot", "服务状态")
run("tail -10 /www/wwwroot/tg-search-bot/logs/stderr.log", "最新错误日志")
run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/", "前端页面")

print("\n=== 完成 ===")
client.close()
