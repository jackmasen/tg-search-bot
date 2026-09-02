import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

print('=== 1. 检查 hot_keyword_categories 表 ===')
stdin, stdout, stderr = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT * FROM hot_keyword_categories\'); '
    'rows=await c.fetchall(); cols=[d[0] for d in c.description]; '
    'for r in rows: print(dict(zip(cols,r))); '
    'if not rows: print(\'(空表)\'); '
    'asyncio.run(f())"'
)
print(stdout.read().decode()[:500])

print('\n=== 2. 检查 hot_keywords 表 ===')
stdin2, stdout2, stderr2 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT * FROM hot_keywords LIMIT 10\'); '
    'rows=await c.fetchall(); cols=[d[0] for d in c.description]; '
    'for r in rows: print(dict(zip(cols,r))); '
    'if not rows: print(\'(空表)\'); '
    'asyncio.run(f())"'
)
print(stdout2.read().decode()[:500])

print('\n=== 3. 检查 channels 表所有数据 ===')
stdin3, stdout3, stderr3 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT id,title,username,target_url,is_featured,status,member_count,category FROM channels\'); '
    'rows=await c.fetchall(); cols=[d[0] for d in c.description]; '
    'for r in rows: print(dict(zip(cols,r))); '
    'asyncio.run(f())"'
)
print(stdout3.read().decode()[:800])

print('\n=== 4. 测试 /start 的完整响应（检查 hot_kw_html 部分）===')
stdin4, stdout4, stderr4 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/start","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);h=d[\'reply_html\'];print(\'has 热门搜索:\', \'热门搜索\' in h);print(\'has 比特币:\', \'比特币\' in h);print(h[-600:])"',
    timeout=15
)
print(stdout4.read().decode())

print('\n=== 5. 测试 /help 命令 ===')
stdin5, stdout5, stderr5 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/help","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);print(d.get(\'reply_html\',\'\')[:300]);print(\'actions:\',d.get(\'actions\',[]))"',
    timeout=10
)
print(stdout5.read().decode())

print('\n=== 6. 测试 /wallet 命令 ===')
stdin6, stdout6, stderr6 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/wallet","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);print(d.get(\'reply_html\',\'\')[:400]);print(\'actions:\',d.get(\'actions\',[]))"',
    timeout=10
)
print(stdout6.read().decode())

client.close()
print('Done.')
