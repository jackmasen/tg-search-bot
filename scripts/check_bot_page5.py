import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', 22, 'root', 'Aa13910828867@&', timeout=10)

print('=== 1. 直接检查 let currentUser 赋值 ===')
stdin, stdout, stderr = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep "let currentUser"',
    timeout=10
)
print(repr(stdout.read().decode()))

print('\n=== 2. 检查 $DEFAULT_USER_ID 是否在页面中残留 ===')
stdin2, stdout2, stderr2 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | grep "DEFAULT_USER_ID"',
    timeout=10
)
print(repr(stdout2.read().decode()))

print('\n=== 3. 检查 page 完整 HTML 中的关键 JS 片段 ===')
stdin3, stdout3, stderr3 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | sed -n "/let currentUser/,/runCmd/p" | head -10',
    timeout=10
)
print(stdout3.read().decode()[:500])

print('\n=== 4. 检查 bot service 运行的是哪个 server.py ===')
stdin4, stdout4, stderr4 = client.exec_command(
    'cat /etc/systemd/system/tg-search-bot.service',
    timeout=10
)
print(stdout4.read().decode())

print('\n=== 5. 检查 admin service 运行的是哪个 server.py ===')
stdin5, stdout5, stderr5 = client.exec_command(
    'cat /etc/systemd/system/tg-search-admin.service',
    timeout=10
)
print(stdout5.read().decode())

print('\n=== 6. 检查端口 8001 进程对应的 server.py 位置 ===')
stdin6, stdout6, stderr6 = client.exec_command(
    'ls -la /proc/16479/cwd && readlink /proc/16479/cmdline | tr \'\\0\' \' \'',
    timeout=10
)
print(stdout6.read().decode())

print('\n=== 7. 检查 server.py 中 DEMO_USERS 和 DEFAULT_ACTIVE_USER ===')
stdin7, stdout7, stderr7 = client.exec_command(
    'grep -n "DEMO_USERS\\|DEFAULT_ACTIVE_USER" /www/wwwroot/tg-search-bot/server.py | head -10',
    timeout=10
)
print(stdout7.read().decode())

print('\n=== 8. 实际测试：首页 HTML 中 currentUser 赋值 ===')
stdin8, stdout8, stderr8 = client.exec_command(
    'curl -s http://jsou.tgjsbot.kdns.fr/ | python3 -c '
    '"import sys;content=sys.stdin.read();idx=content.find(\'let currentUser\');print(repr(content[idx:idx+80]))"',
    timeout=10
)
print(stdout8.read().decode())

client.close()
print('Done.')
