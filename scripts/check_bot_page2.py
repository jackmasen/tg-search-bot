import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

print('=== 1. /api/bot/command /start response (full) ===')
stdin, stdout, stderr = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/start","tg_user_id":10000001}\'',
    timeout=15
)
resp = stdout.read().decode()
# Parse JSON to check structure
try:
    data = json.loads(resp)
    print("Keys:", list(data.keys()))
    html = data.get('reply_html', '')
    print("reply_html length:", len(html))
    print("has featured_ads_html:", '今日热门推荐' in html)
    print("has hot_keywords:", '热门搜索' in html)
    print("has channels:", '加入' in html)
    print("actions:", data.get('actions', 'NONE'))
    print("\nFirst 800 chars of reply_html:")
    print(html[:800])
except Exception as e:
    print("JSON parse error:", e)
    print(resp[:500])

print('\n=== 2. DB featured channels ===')
stdin2, stdout2, stderr2 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python3 -c '
    '"import asyncio,aiosqlite; asyncio.run(async def f(): async with aiosqlite.connect(\'data/bot.db\') as db: '
    'c=await db.execute(\'SELECT COUNT(*) c FROM channels WHERE is_featured=1\'); r=await c.fetchone(); print(\'featured:\',r[0]); '
    'c2=await db.execute(\'SELECT COUNT(*) c FROM hot_keywords\'); r2=await c2.fetchone(); print(\'hot_kw:\',r2[0]))()"'
)
print(stdout2.read().decode()[:500])

print('\n=== 3. Test /api/bot/ad_templates ===')
stdin3, stdout3, stderr3 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/ad_templates | head -c 300',
    timeout=10
)
print(stdout3.read().decode()[:300])

print('\n=== 4. Test /api/bot/command with search query ===')
stdin4, stdout4, stderr4 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"比特币","tg_user_id":10000001}\' | python3 -c "import sys,json;d=json.load(sys.stdin);print(list(d.keys()));print(\'search_results:\',len(d.get(\'search_results\',[])));print(\'reply_html len:\',len(d.get(\'reply_html\',\'\')))\"',
    timeout=15
)
print(stdout4.read().decode()[:500])

print('\n=== 5. Check if server.py has CORS/middleware issues ===')
stdin5, stdout5, stderr5 = client.exec_command(
    'grep -n "CORSMiddleware\\|allow_origin\\|add_middleware" /www/wwwroot/tg-search-bot/server.py | head -20',
    timeout=10
)
print(stdout5.read().decode())

print('\n=== 6. Check bot service stderr for recent errors ===')
stdin6, stdout6, stderr6 = client.exec_command(
    'tail -30 /www/wwwroot/tg-search-bot/logs/stderr.log 2>/dev/null || tail -30 /tmp/tg-search-bot-stderr.log 2>/dev/null',
    timeout=10
)
print(stdout6.read().decode()[:1000])

client.close()
print('Done.')
