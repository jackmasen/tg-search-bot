import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

# 1. 检查数据库表结构
print('=== DB Tables ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT name FROM sqlite_master WHERE type=\'table\'\"); [print(r[0]) for r in cur]"')
print(s.read().decode())

# 2. 检查Telethon配置
print('=== Telethon Config ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT key, substr(value,1,80) FROM system_config WHERE key LIKE \'%TELETHON%\' OR key LIKE \'%API_ID%\' OR key LIKE \'%PHONE%\' OR key LIKE \'%PROXY%\'); [print(f\"{r[0]}={r[1]}\") for r in cur]"')
print(s.read().decode())

# 3. 检查AI配置
print('=== AI Config ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT key, substr(value,1,100) FROM system_config WHERE key LIKE \'%AI%\'); [print(f\"{r[0]}={r[1]}\") for r in cur]"')
print(s.read().decode())

# 4. 检查账号池
print('=== Crawler Accounts ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT id, phone, is_active, last_error FROM crawler_accounts LIMIT 5\"); [print(r) for r in cur]"')
print(s.read().decode())

# 5. 检查AI pool JSON
print('=== AI API Keys JSON ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT setting_value, is_encrypted FROM system_settings WHERE setting_key=\'AI_API_KEYS\'); v=cur.fetchone(); print(repr(v[0]) if v else \'NULL\"); print(len(v[0]) if v and v[0] else 0)"')
print(s.read().decode()[:500])

# 6. 检查crawler_proxies表
print('=== Crawler Proxies ===')
_, s, _ = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "import sqlite3; conn=sqlite3.connect(\'data/tg_search.db\'); cur=conn.execute(\"SELECT * FROM crawler_proxies\"); [print(r) for r in cur]"')
print(s.read().decode())

# 7. 检查systemd服务配置
print('=== Bot Service Config ===')
_, s, _ = client.exec_command('systemctl cat tg-search-bot.service')
print(s.read().decode()[:500])

# 8. 查看最近的bot日志中关于添加AI接口的错误
print('=== Bot log around AI pool add ===')
_, s, _ = client.exec_command(
    'grep -i "pool\|api_key\|AI_API" /www/wwwroot/tg-search-bot/logs/stderr.log | tail -30')
print(s.read().decode()[:1000])

client.close()
print('Done!')
