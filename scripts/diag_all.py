# -*- coding: utf-8 -*-
"""综合诊断三个问题"""
import paramiko, os, tempfile

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

local_tmp = os.path.join(tempfile.gettempdir(), '_diag.py')
sftp = client.open_sftp()

# ============================================================
# 问题1: 检查置顶频道数据是否同步
# ============================================================
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()

print("=== 置顶频道 (is_featured=1) ===")
cur.execute("SELECT id, name, is_featured, sort_order, description, target_url FROM channels WHERE is_featured=1 ORDER BY sort_order ASC")
for r in cur.fetchall():
    print(f"  id={r[0]} name={r[1]} sort={r[3]} desc={r[4][:50] if r[4] else ''} url={r[5]}")

print("\n=== 全部频道 (前10条) ===")
cur.execute("SELECT id, name, is_featured, sort_order FROM channels ORDER BY id DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  id={r[0]} name={r[1]} featured={r[2]} sort={r[3]}")

print("\n=== 热门关键词 ===")
cur.execute("SELECT id, keyword, category, display_order, is_active FROM hot_keywords ORDER BY id DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  id={r[0]} kw={r[1]} cat={r[2]} order={r[3]} active={r[4]}")

print("\n=== 热门关键词分类 ===")
cur.execute("SELECT id, name, icon, sort_order FROM keyword_categories ORDER BY sort_order")
for r in cur.fetchall():
    print(f"  id={r[0]} name={r[1]} icon={r[2]} order={r[3]}")

conn.close()
''')

sftp.put(local_tmp, '/tmp/_diag1.py')
_, out1, err1 = client.exec_command('python3 /tmp/_diag1.py')
print("=== 问题1: 置顶频道和热门关键词 ===")
print(out1.read().decode())
print(err1.read().decode())
sftp.close()

# ============================================================
# 问题2: 检查API调用和前端页面连接
# ============================================================
sftp = client.open_sftp()
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys, json
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        # Login
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Admin@123456'})
        ld = lr.json()
        sid = ld.get('session_id', '')
        if not sid:
            print("Login failed")
            return
        print(f"Login OK, session={sid[:16]}...")

        # Test bot command endpoint
        print("\n=== /api/bot/command (start) ===")
        cr = await c.post('http://127.0.0.1:8001/api/bot/command', json={'command': '/start', 'user_id': 999999})
        cd = cr.json()
        print(f"Status: {cr.status_code}")
        if cr.status_code == 200:
            print(f"priority_channels: {cd.get('priority_channels', [])[:2]}")
            print(f"priority_ads: {cd.get('priority_ads', [])[:2]}")
            print(f"hot_keywords: {str(cd.get('hot_keywords', []))[:200]}")
        else:
            print(f"Error: {cr.text[:200]}")

        # Test channels API
        print("\n=== /api/admin/channels ===")
        chr = await c.get('http://127.0.0.1:8001/api/admin/channels', params={'session_id': sid})
        chd = chr.json()
        print(f"Status: {chr.status_code}, channels count: {len(chd.get('channels', []))}")

        # Test hot keywords API
        print("\n=== /api/admin/hot_keywords ===")
        hwr = await c.get('http://127.0.0.1:8001/api/admin/hot_keywords', params={'session_id': sid})
        hwd = hwr.json()
        print(f"Status: {hwr.status_code}, keywords count: {len(hwd.get('keywords', []))}")
        print(f"Categories: {hwd.get('categories', [])[:3]}")

asyncio.run(test())
''')

sftp.put(local_tmp, '/tmp/_diag2.py')
_, out2, err2 = client.exec_command('python3 /tmp/_diag2.py')
print("=== 问题2: API连通性 ===")
print(out2.read().decode())
print(err2.read().decode())
sftp.close()

# ============================================================
# 问题3: 检查AI接口配置和闪退原因
# ============================================================
sftp = client.open_sftp()
with open(local_tmp, 'w') as f:
    f.write(r'''import asyncio, httpx, sys, json
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import os
os.environ.setdefault('DB_PATH', '/www/wwwroot/tg-search-bot/data/tg_search.db')
from dotenv import load_dotenv
load_dotenv('/www/wwwroot/tg-search-bot/.env')

async def test():
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
        lr = await c.post('http://127.0.0.1:8001/api/admin/login', json={'username': 'admin', 'password': 'Admin@123456'})
        sid = lr.json().get('session_id', '')
        if not sid:
            print("Login failed")
            return

        # Get AI config
        print("=== GET /api/admin/ai/config ===")
        ar = await c.get(f'http://127.0.0.1:8001/api/admin/ai/config', params={'session_id': sid})
        print(f"Status: {ar.status_code}")
        print(ar.text[:500])

        # Get AI pool
        print("\n=== GET /api/admin/ai/pool ===")
        pr = await c.get(f'http://127.0.0.1:8001/api/admin/ai/pool', params={'session_id': sid})
        print(f"Status: {pr.status_code}")
        print(pr.text[:500])

        # Try adding an AI key
        print("\n=== POST /api/admin/ai/pool/add (test) ===")
        try:
            add_r = await c.post(f'http://127.0.0.1:8001/api/admin/ai/pool/add',
                json={'session_id': sid, 'name': '测试接口', 'api_base': 'https://api.openai.com', 'api_key': 'sk-test123', 'model': 'gpt-4o', 'priority': 1})
            print(f"Status: {add_r.status_code}")
            print(add_r.text[:500])
        except Exception as e:
            print(f"Exception: {e}")

asyncio.run(test())
''')

sftp.put(local_tmp, '/tmp/_diag3.py')
_, out3, err3 = client.exec_command('python3 /tmp/_diag3.py')
print("=== 问题3: AI接口 ===")
print(out3.read().decode())
print(err3.read().decode())
sftp.close()

# ============================================================
# 检查服务器日志
# ============================================================
sftp = client.open_sftp()
with open(local_tmp, 'w') as f:
    f.write(r'''import sqlite3
conn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')
cur = conn.cursor()
cur.execute("SELECT setting_key, substr(setting_value,1,80) FROM system_settings WHERE setting_key LIKE 'AI_%'")
for r in cur.fetchall():
    print(f"{r[0]}={repr(r[1])}")
conn.close()
''')
sftp.put(local_tmp, '/tmp/_diag4.py')
_, out4, err4 = client.exec_command('python3 /tmp/_diag4.py')
print("=== AI配置 ===")
print(out4.read().decode())
print(err4.read().decode())
sftp.close()

# Check server logs
_, out5, err5 = client.exec_command('tail -100 /www/wwwroot/tg-search-bot/logs/server.log 2>/dev/null || echo "No server.log"')
print("=== Server Logs (last 100 lines) ===")
print(out5.read().decode())
print(err5.read().decode())

_, out6, err6 = client.exec_command('tail -100 /www/wwwroot/tg-search-bot/logs/bot.log 2>/dev/null || echo "No bot.log"')
print("=== Bot Logs (last 100 lines) ===")
print(out6.read().decode())
print(err6.read().decode())

client.close()
os.unlink(local_tmp)
print("Done")
