import paramiko, os, time, pathlib

SRC = pathlib.Path(r"C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot")
HOST = "186.244.251.12"
USER = "root"
PASS = "Aa13910828867@&"
REMOTE_DIR = "/www/wwwroot/tg-search-bot"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        for line in out.splitlines()[:30]:
            print(f"  {line}")
    if err:
        for line in err.splitlines()[:10]:
            print(f"  ERR: {line}")
    return out, err

def scp_put(local_path, remote_path):
    print(f"\n  [scp] {local_path} -> {remote_path}")
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()

# 1. 上传修改的文件
files_to_deploy = [
    ("app/database.py", f"{REMOTE_DIR}/app/database.py"),
    ("app/admin/version_manager.py", f"{REMOTE_DIR}/app/admin/version_manager.py"),
    ("app/config.py", f"{REMOTE_DIR}/app/config.py"),
    ("server.py", f"{REMOTE_DIR}/server.py"),
    (".env", f"{REMOTE_DIR}/.env"),
]

for local, remote in files_to_deploy:
    local_path = SRC / local
    if local_path.exists():
        scp_put(local_path, remote)
    else:
        print(f"  [SKIP] 文件不存在: {local_path}")

# 2. 验证版本
run(f"grep 'APP_VERSION' {REMOTE_DIR}/app/config.py", "验证版本号")
run(f"grep '_ensure_git_safe' {REMOTE_DIR}/app/admin/version_manager.py", "验证_git_safe方法")
run(f"grep 'is_featured' {REMOTE_DIR}/app/database.py", "验证channels迁移")
run(f"grep 'search_with_ads_priority' {REMOTE_DIR}/server.py", "验证广告优先搜索")
run(f"grep 'VERSION_REPO_URL' {REMOTE_DIR}/.env", "验证仓库URL")

# 3. 重启服务
print("\n=== 重启服务 ===")
run("systemctl restart tg-search-bot", "重启bot服务")
time.sleep(4)

# 4. 检查状态
run("systemctl is-active tg-search-bot", "服务状态")
run("journalctl -u tg-search-bot --no-pager -n 15", "最新日志")
run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/", "前端页面响应")

# 5. 检查数据库迁移
run(f"sqlite3 {REMOTE_DIR}/data/tg_search.db \"PRAGMA table_info(channels);\"", "channels表结构")

print("\n=== 部署完成 ===")
client.close()
