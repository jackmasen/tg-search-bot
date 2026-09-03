import paramiko
host = '186.244.251.12'
user = 'root'
pwd = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pwd)

# Check what admin users exist
_, stdout, stderr = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "from app.admin.system_settings_manager import load_all_settings_from_db; import asyncio; r = asyncio.run(load_all_settings_from_db(None)); print(list(r.keys())[:30])"'
)
print('=== SETTINGS KEYS ===')
print(stdout.read().decode())
print(stderr.read().decode())

# Check the admin password from settings
_, stdout, stderr = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "from app.admin.system_settings_manager import load_all_settings_from_db; import asyncio; r = asyncio.run(load_all_settings_from_db(None)); print(r.get(chr(39)+chr(39)+chr(39)+'ADMIN_USERNAME'+chr(39)+chr(39)+chr(39),chr(39)+'not found'+chr(39)))"'
)
print('=== ADMIN USERNAME ===')
print(stdout.read().decode())

# Check if there is a separate admin DB
_, stdout, stderr = client.exec_command('find /www/wwwroot/tg-search-bot -name "*.db" -o -name "*.sqlite" 2>/dev/null | head -5')
print('=== DB FILES ===')
print(stdout.read().decode())

# Check env file
_, stdout, stderr = client.exec_command('cat /www/wwwroot/tg-search-bot/.env 2>/dev/null | grep -i admin | head -10')
print('=== ENV ADMIN ===')
print(stdout.read().decode())

client.close()
print('Done')
