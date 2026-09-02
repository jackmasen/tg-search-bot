# -*- coding: utf-8 -*-
"""诊断脚本：检查三个问题"""
import paramiko, os, tempfile

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)
local_tmp = os.path.join(tempfile.gettempdir(), '_diag.py')
sftp = client.open_sftp()

# 1. 检查channels表是否有status列
_, out, err = client.exec_command(
    "python3 -c \"import sqlite3; conn=sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db'); cur=conn.cursor(); cur.execute('PRAGMA table_info(channels)'); print('\\n'.join([str(r) for r in cur.fetchall()]))\""
)
print("=== channels表结构 ===")
print(out.read().decode())
print(err.read().decode())

# 2. 检查is_featured=1的记录数
_, out2, err2 = client.exec_command(
    "python3 -c \"import sqlite3; conn=sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM channels WHERE is_featured=1'); print('featured:', cur.fetchone()[0]); cur.execute('SELECT COUNT(*) FROM channels'); print('total:', cur.fetchone()[0]); cur.execute('SELECT id, title, is_featured FROM channels LIMIT 5'); print('sample:', cur.fetchall())\""
)
print("=== featured频道 ===")
print(out2.read().decode())

# 3. 检查ad_campaigns数据
_, out3, err3 = client.exec_command(
    "python3 -c \"import sqlite3; conn=sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM ad_campaigns'); print('total ads:', cur.fetchone()[0]); cur.execute('SELECT COUNT(*) FROM ad_campaigns WHERE is_featured=1'); print('featured ads:', cur.fetchone()[0]); cur.execute('SELECT COUNT(*) FROM hot_keywords WHERE is_active=1'); print('active keywords:', cur.fetchone()[0])\""
)
print("=== 广告/关键词统计 ===")
print(out3.read().decode())

# 4. 检查SyntaxError - 看server.py中有没有重复的_ai_health_status
_, out4, err4 = client.exec_command('grep -n "_ai_health_status" /www/wwwroot/tg-search-bot/server.py | head -30')
print("=== _ai_health_status usage ===")
print(out4.read().decode())

# 5. 检查admin_stderr.log最后100行
_, out5, err5 = client.exec_command('tail -100 /www/wwwroot/tg-search-bot/logs/admin_stderr.log')
print("=== admin_stderr.log ===")
print(out5.read().decode())

# 6. 搜索 不连接 关键词
_, out6, err6 = client.exec_command('grep -rn "不连接\\|未连接\\|connected" /www/wwwroot/tg-search-bot/server.py /www/wwwroot/tg-search-bot/admin_template.html 2>/dev/null | head -20')
print("=== not connected search ===")
print(out6.read().decode())

sftp.close()
client.close()
print("Done")
