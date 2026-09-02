import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. Check socksio in venv ===')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/pip show socksio')
print(f'show: {out}')
if err: print(f'err: {err}')

print('=== 2. Try import ===')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python -c "import socksio; print(\'OK\')"')
print(f'out: [{out}] err: [{err}]')

print('=== 3. Check which python the bot uses ===')
out, _ = run('ps aux | grep main.py | grep -v grep')
print(out)

print('=== 4. Check bot venv ===')
out, _ = run('ls -la /www/wwwroot/tg-search-bot/venv/bin/python*')
print(out)

print('=== 5. List installed packages with socks ===')
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/pip list | grep -i sock')
print(out)

print('=== 6. Check bot logs after latest restart ===')
out, _ = run('journalctl -u tg-search-bot --no-pager -n 15 --since "10 min ago"')
print(out)

print('=== 7. Check stderr log tail ===')
out, _ = run('tail -15 /www/wwwroot/tg-search-bot/logs/stderr.log')
print(out)

client.close()
print('DONE')
