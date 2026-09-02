import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

print('=== 1. DB: featured channels data ===')
stdin, stdout, stderr = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT COUNT(*) c FROM channels WHERE is_featured=1\'); r=await c.fetchone(); print(\'featured:\',r[0]); '
    'c2=await db.execute(\'SELECT id,title,username,is_featured FROM channels WHERE is_featured=1 LIMIT 5\'); '
    'rows=await c2.fetchall(); print(\'rows:\',rows); '
    'c3=await db.execute(\'SELECT COUNT(*) c FROM hot_keywords\'); r=await c3.fetchone(); print(\'hot_keywords:\',r[0]); '
    'c4=await db.execute(\'SELECT COUNT(*) c FROM messages\'); r=await c4.fetchone(); print(\'messages:\',r[0]); '
    'c5=await db.execute(\'SELECT COUNT(*) c FROM channels\'); r=await c5.fetchone(); print(\'total_channels:\',r[0]); '
    'asyncio.run(f())"'
)
print(stdout.read().decode())

print('\n=== 2. DB: hot_keywords content ===')
stdin2, stdout2, stderr2 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite,json; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT * FROM hot_keywords LIMIT 10\'); '
    'rows=await c.fetchall(); cols=[d[0] for d in c.description]; '
    'for r in rows: print(dict(zip(cols,r))); '
    'asyncio.run(f())"'
)
print(stdout2.read().decode()[:800])

print('\n=== 3. Bot full /start response (formatted) ===')
stdin3, stdout3, stderr3 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/start","tg_user_id":10000001}\' | python3 -m json.tool',
    timeout=15
)
resp = stdout3.read().decode()
try:
    data = json.loads(resp)
    print("reply_html preview (first 1500 chars):")
    print(data.get('reply_html','')[:1500])
    print("\nactions:", data.get('actions'))
except:
    print(resp[:1000])

print('\n=== 4. Check search_with_ads_priority function ===')
stdin4, stdout4, stderr4 = client.exec_command(
    'grep -n "async def search_with_ads_priority" /www/wwwroot/tg-search-bot/server.py',
    timeout=10
)
print(stdout4.read().decode())

print('\n=== 5. Test actual search ===')
stdin5, stdout5, stderr5 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"比特币","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);print(\'search_results:\',len(d.get(\'search_results\',[])));print(\'priority_channels:\',len(d.get(\'priority_channels\',[])));print(\'priority_ads:\',len(d.get(\'priority_ads\',[])));print(\'reply_html:\',d.get(\'reply_html\',\'\')[:300])"',
    timeout=15
)
print(stdout5.read().decode())

print('\n=== 6. Check if messages table has data ===')
stdin6, stdout6, stderr6 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; async def f(): '
    'async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT channel_title, content FROM messages LIMIT 3\'); '
    'rows=await c.fetchall(); [print(r) for r in rows]; '
    'asyncio.run(f())"',
    timeout=10
)
print(stdout6.read().decode()[:500])

client.close()
print('Done.')
