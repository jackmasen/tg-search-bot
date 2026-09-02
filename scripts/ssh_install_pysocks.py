import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== Installing pysocks ===')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/pip install pysocks')
print(out)
if err: print(f'err: {err}')

print('=== Verify pysocks ===')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python -c "import socks; print(f\"pysocks {socks.__version__} OK\")"')
print(out)

print('=== Restart bot ===')
run('systemctl restart tg-search-bot')
import time
time.sleep(5)

print('=== Bot status ===')
out, _ = run('systemctl is-active tg-search-bot')
print(f'Bot active: {out}')

print('=== Bot logs (check no socksio warning) ===')
out, _ = run('tail -15 /www/wwwroot/tg-search-bot/logs/stderr.log')
print(out)

print('=== Admin login ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Login: {out}')

client.close()
print('DONE')
