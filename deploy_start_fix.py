"""部署 handlers.py 和 main.py 到服务器并重启 bot 服务"""
import paramiko
import os

SSH_HOST = "186.244.251.12"
SSH_USER = "root"
SSH_PASS = "Aa13910828867@&"
REMOTE_BASE = "/www/wwwroot/tg-search-bot"

local_handlers = os.path.join(os.path.dirname(__file__), "app", "bot", "handlers.py")
local_main = os.path.join(os.path.dirname(__file__), "main.py")
local_server = os.path.join(os.path.dirname(__file__), "server.py")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

def upload(path_local, path_remote):
    sftp = ssh.open_sftp()
    print(f"上传: {path_local} -> {path_remote}")
    sftp.put(path_local, path_remote)
    sftp.close()
    print(f"  完成: {path_remote}")

try:
    # 部署 server.py（包含 hot_keywords 字段）
    upload(local_server, REMOTE_BASE + "/server.py")

    # 部署 handlers.py（HTML模式 + 回调处理器）
    upload(local_handlers, REMOTE_BASE + "/app/bot/handlers.py")

    # 部署 main.py（回调处理器注册）
    upload(local_main, REMOTE_BASE + "/main.py")

    # 重启 bot 服务
    stdin, stdout, stderr = ssh.exec_command("systemctl restart tg-search-bot")
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"重启输出: {out}")
    if err:
        print(f"重启错误: {err}")

    # 等待服务启动
    import time
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active tg-search-bot")
    status = stdout.read().decode().strip()
    print(f"服务状态: {status}")

    # 检查日志
    stdin, stdout, stderr = ssh.exec_command("systemctl status tg-search-bot --no-pager -n 5")
    log = stdout.read().decode()
    print("最新状态日志:")
    for line in log.splitlines()[-8:]:
        print(f"  {line}")

    print("\n✅ 部署完成！请 Telegram 发送 /start 查看效果")
finally:
    ssh.close()
