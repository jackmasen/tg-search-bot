import paramiko
host = '186.244.251.12'
user = 'root'
pwd = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pwd)

# Check what .env says
_, stdout, stderr = client.exec_command('cat /www/wwwroot/tg-search-bot/.env 2>/dev/null')
print('=== .ENV ===')
print(stdout.read().decode())

# Check DB files
_, stdout, stderr = client.exec_command('find /www/wwwroot/tg-search-bot -name "*.db" -o -name "*.sqlite3" 2>/dev/null | head -10')
print('=== DB FILES ===')
print(stdout.read().decode())

# Check how admin login works
_, stdout, stderr = client.exec_command(
    'grep -n "def api_admin_login\\|def.*login\\|ADMIN_USERNAME\\|ADMIN_PASSWORD\\|verify_admin_session" /www/wwwroot/tg-search-bot/server.py | head -20'
)
print('=== AUTH LOGIC ===')
print(stdout.read().decode())
print(stderr.read().decode())

client.close()
print('Done')
