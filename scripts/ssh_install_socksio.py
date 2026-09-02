import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== Installing socksio ===')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/pip install socksio')
print(out)
if err:
    print(f'stderr: {err}')

print('=== Verify installation ===')
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/python -c "import socksio; print(f socksio version: {socksio.__version__})" 2>&1 || /www/wwwroot/tg-search-bot/venv/bin/python -c "import socksio; print(\'socksio imported OK\')"')
print(out)

print('=== Check if bot needs restart ===')
out, _ = run('tail -5 /www/wwwroot/tg-search-bot/logs/stderr.log')
print(out)

client.close()
print('DONE')
