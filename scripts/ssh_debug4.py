import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== 1. Write debug script to server ===')
script_content = '''import sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
import asyncio
from app.database import get_db
from app.admin.system_settings_manager import load_all_settings_from_db

async def debug():
    async with get_db() as db:
        settings = await load_all_settings_from_db(db)
    un = settings.get('ADMIN_USERNAME')
    pw = settings.get('ADMIN_PASSWORD')
    print(f'DEBUG_UN={repr(un)} len={len(un) if un else 0}')
    print(f'DEBUG_PW={repr(pw)} len={len(pw) if pw else 0}')

asyncio.run(debug())
'''
# Write via SSH using python -c
run(f'python3 -c "open(\'/tmp/d.py\',\'w\').write(\'{script_content.replace(chr(10),chr(92)+chr(10)).replace(chr(39),chr(92)+chr(39))}\')" 2>&1 || echo "using heredoc"')
run("cat > /tmp/d.py << 'PYEOF'")
run("import sys")
run("sys.path.insert(0, '/www/wwwroot/tg-search-bot')")
run("import asyncio")
run("from app.database import get_db")
run("from app.admin.system_settings_manager import load_all_settings_from_db")
run("async def debug():")
run("    async with get_db() as db:")
run("        settings = await load_all_settings_from_db(db)")
run("    un = settings.get('ADMIN_USERNAME')")
run("    pw = settings.get('ADMIN_PASSWORD')")
run("    print(f'DEBUG_UN={repr(un)} len={len(un) if un else 0}')")
run("    print(f'DEBUG_PW={repr(pw)} len={len(pw) if pw else 0}')")
run("asyncio.run(debug())")
run("PYEOF")
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/d.py 2>&1')
print(f'Debug output: {out}')

print('=== 2. Check what DB path server is using ===')
run("cat > /tmp/d2.py << 'PYEOF'")
run("import sys")
run("sys.path.insert(0, '/www/wwwroot/tg-search-bot')")
run("from app.config import Config")
run("print(f'DB_PATH={Config.DB_PATH}')")
run("print(f'APP_VERSION={Config.APP_VERSION}')")
run("PYEOF")
out, _ = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/d2.py 2>&1')
print(out)

print('=== 3. Check server.py login code line by line ===')
out, _ = run('sed -n "1080,1095p" /www/wwwroot/tg-search-bot/server.py')
print(out)

print('=== 4. Check server.py _load_admin_credentials_from_db ===')
out, _ = run('sed -n "91,103p" /www/wwwroot/tg-search-bot/server.py')
print(out)

print('=== 5. Full admin logs ===')
out, _ = run('tail -50 /www/wwwroot/tg-search-bot/logs/admin_stdout.log 2>/dev/null')
print(out)

print('=== 6. Check if there is another server.py being used ===')
out, _ = run('md5sum /www/wwwroot/tg-search-bot/server.py')
print(out)
out, _ = run('ps aux | grep server.py | grep -v grep')
print(out)

print('=== 7. Test login with verbose ===')
out, _ = run('curl -v -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"Admin@123456"}\' 2>&1 | grep -E "< |>|{')
print(out)

print('=== 8. Check system_settings in the actual DB server.py uses ===')
out, _ = run('sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db "SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN (\'ADMIN_USERNAME\',\'ADMIN_PASSWORD\');"')
print(out)

client.close()
print('DONE')
