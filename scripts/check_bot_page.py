import paramiko
import json
import time

SSH_HOST = '186.244.251.12'
SSH_PORT = 22
SSH_USER = 'root'
SSH_PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode().strip(), stderr.read().decode().strip(), stdin.channel.recv_exit_status()

print("=== 1. 检查服务状态 ===")
out, err, rc = run('systemctl is-active tg-search-bot tg-search-admin')
print(out)

print("\n=== 2. 检查 bot 页面是否可访问 ===")
out, err, rc = run('curl -s -o /dev/null -w "%{http_code}" http://localhost/')
print(f"HTTP status: {out}")

print("\n=== 3. 检查 /api/bot/command 是否正常 ===")
out, err, rc = run('curl -s -X POST http://localhost/api/bot/command -H "Content-Type: application/json" -d \'{"command":"/start","tg_user_id":123456789}\'')
print(out[:2000])

print("\n=== 4. 检查 bot stderr 最新日志（最后30行） ===")
out, err, rc = run('tail -30 /tmp/tg-search-bot-stderr.log 2>/dev/null || journalctl -u tg-search-bot --no-pager -n 30')
print(out)

print("\n=== 5. 检查数据库 channels 表是否有 featured 数据 ===")
out, err, rc = run('cd /opt/tg-search-bot && python3 -c "import asyncio; from app.db import get_db; async def f(): async with get_db() as db: cur=await db.execute(\'SELECT COUNT(*) as c FROM channels WHERE is_featured=1\'); r=await cur.fetchone(); print(\'featured channels:\', r[\"c\"]); cur=await db.execute(\'SELECT COUNT(*) as c FROM hot_keywords\'); r=await cur.fetchone(); print(\'hot_keywords:\', r[\"c\"]); cur=await db.execute(\'SELECT COUNT(*) as c FROM system_settings WHERE setting_key LIKE \'AI%\'\'); r=await cur.fetchone(); print(\'AI settings:\', r[\"c\"])); asyncio.run(f)"')
print(out)

print("\n=== 6. 检查端口监听 ===")
out, err, rc = run('ss -tlnp | grep -E "800[0-9]|500[0-9]"')
print(out)

client.close()
print("\nDone.")
