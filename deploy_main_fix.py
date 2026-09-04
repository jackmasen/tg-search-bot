"""重新部署 main.py 到服务器"""
import paramiko
import os

SSH_HOST = "186.244.251.12"
SSH_USER = "root"
SSH_PASS = "Aa13910828867@&"
REMOTE_BASE = "/www/wwwroot/tg-search-bot"
local_main = os.path.join(os.path.dirname(__file__), "main.py")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

sftp = ssh.open_sftp()
print(f"上传 main.py ...")
sftp.put(local_main, REMOTE_BASE + "/main.py")
sftp.close()
print("上传完成")

stdin, stdout, stderr = ssh.exec_command("systemctl restart tg-search-bot")
import time; time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active tg-search-bot")
status = stdout.read().decode().strip()
print(f"服务状态: {status}")

stdin, stdout, stderr = ssh.exec_command("journalctl -u tg-search-bot -n 10 --no-pager")
log = stdout.read().decode()
print("日志:")
for line in log.splitlines()[-8:]:
    print(f"  {line}")

# 尝试手动启动看是否有报错
stdin, stdout, stderr = ssh.exec_command(
    "cd /www/wwwroot/tg-search-bot && timeout 5 ./venv/bin/python main.py 2>&1 || true"
)
out = stdout.read().decode()
err = stderr.read().decode()
print("手动启动测试:")
if err:
    print(f"  err: {err[:500]}")
# 看有没有 NameError
if "NameError" in out or "NameError" in err:
    print("  ⚠️ 仍有 NameError!")
else:
    print("  ✅ 无 NameError")

ssh.close()
