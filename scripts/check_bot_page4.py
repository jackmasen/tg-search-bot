import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

# 模拟浏览器请求，检查页面完整返回
print('=== 1. 获取完整 bot 页面 HTML，检查 JS 函数是否存在 ===')
stdin, stdout, stderr = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep -o "function runCmd\\|function send\\|function switchUser\\|function renderBotResponse\\|window.addEventListener" | head -10',
    timeout=10
)
print(stdout.read().decode())

print('\n=== 2. 检查页面中是否有模板变量替换 ===')
stdin2, stdout2, stderr2 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep -o "DEMO_USERS\\|currentUser\\|10000001\\|10000002\\|10000003" | head -10',
    timeout=10
)
print(stdout2.read().decode())

print('\n=== 3. 检查页面中的 $ 变量是否被替换 ===')
stdin3, stdout3, stderr3 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep -E "\\$MSG_COUNT|\\$CHANNEL_COUNT|\\$USER_OPTIONS|\\$DEFAULT_USER" | head -10',
    timeout=10
)
print(stdout3.read().decode()[:300] or "（所有模板变量已正确替换）")

print('\n=== 4. 检查首页返回的实际用户ID ===')
stdin4, stdout4, stderr4 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep -o "let currentUser = [0-9]*" | head -3',
    timeout=10
)
print(stdout4.read().decode())

print('\n=== 5. 检查首页返回的msg/channel计数 ===')
stdin5, stdout5, stderr5 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep -o "[0-9]*+ 消息索引\\|[0-9]* 频道" | head -5',
    timeout=10
)
print(stdout5.read().decode())

print('\n=== 6. 测试 /stats 命令 ===')
stdin6, stdout6, stderr6 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-d \'{"command":"/stats","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);print(d.get(\'reply_html\',\'\')[:400]);print(\'actions:\',d.get(\'actions\',[]))"',
    timeout=15
)
print(stdout6.read().decode()[:600])

print('\n=== 7. 检查 server.py 版本/commit ===')
stdin7, stdout7, stderr7 = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && git log --oneline -3 && echo "---" && git status --short',
    timeout=10
)
print(stdout7.read().decode())

print('\n=== 8. 检查 bot service 是否运行最新版本 ===')
stdin8, stdout8, stderr8 = client.exec_command(
    'systemctl show tg-search-bot --property=ExecStart,MainPID,ActiveState,Result 2>/dev/null',
    timeout=10
)
print(stdout8.read().decode())

print('\n=== 9. 完整测试：从浏览器视角模拟 ===')
stdin9, stdout9, stderr9 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | wc -c && '
    'curl -s http://jsou.tgjsbot.kdns.fr/api/bot/command -X POST '
    '-H "Content-Type: application/json" '
    '-H "Referer: http://jsou.tgjsbot.kdns.fr/" '
    '-H "Origin: http://jsou.tgjsbot.kdns.fr" '
    '-d \'{"command":"/start","tg_user_id":10000001}\' | python3 -c '
    '"import sys,json;d=json.load(sys.stdin);print(\'OK, keys:\',list(d.keys()),\'html_len:\',len(d.get(\'reply_html\',\'\')))"',
    timeout=15
)
print(stdout9.read().decode())

client.close()
print('Done.')
