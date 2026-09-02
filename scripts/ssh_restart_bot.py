import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== Restarting bot ===')
run('systemctl restart tg-search-bot')
time.sleep(5)

print('=== Bot status ===')
out, _ = run('systemctl is-active tg-search-bot')
print(f'Bot active: {out}')

print('=== Bot logs (check socksio warning gone) ===')
out, _ = run('tail -15 /www/wwwroot/tg-search-bot/logs/stderr.log')
print(out)

print('=== Verify socksio installed ===')
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/python -c "import socksio; print(\"socksio imported OK\")"')
print(out)

print('=== Admin login test ===')
out, _ = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\'')
print(f'Admin login: {out}')

client.close()
print('DONE')
