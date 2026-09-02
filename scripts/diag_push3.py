# -*- coding: utf-8 -*-
import paramiko

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

# 1. Check DB values for key settings
_, out, _ = client.exec_command(
    "sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db "
    "\"SELECT setting_key, value_type, is_encrypted, length(setting_value) as len_val "
    "FROM system_settings WHERE setting_key IN ('ADMIN_TG_IDS','TG_BOT_TOKEN','CRYPTO_SECRET');\""
)
print('=== DB settings metadata ===')
print(out.read().decode().strip())

# 2. Test the actual Config values
script = '''
import sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')
from app.config import Config
print("BOT_TOKEN:", repr(Config.BOT_TOKEN[:20] if Config.BOT_TOKEN else "EMPTY"))
print("ADMIN_TG_IDS:", repr(Config.ADMIN_TG_IDS))
print("CRYPTO_SECRET len:", len(Config.CRYPTO_SECRET) if Config.CRYPTO_SECRET else 0)
'''
_, out, err = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c "' + script.replace('\n', ' ') + '"'
)
print('=== Config runtime ===')
print('OUT:', out.read().decode().strip())
print('ERR:', err.read().decode().strip())

# 3. Try calling the API directly to see the actual error
_, out, err = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c "'
    'import asyncio, httpx; '
    'from app.config import Config; '
    'print(\"ADMIN_TG_IDS type:\", type(Config.ADMIN_TG_IDS).__name__); '
    'print(\"ADMIN_TG_IDS value:\", repr(Config.ADMIN_TG_IDS)); '
    'print(\"BOT_TOKEN empty?:\", not bool(Config.BOT_TOKEN));'
    '"'
)
print('=== Config detail ===')
print('OUT:', out.read().decode().strip())
print('ERR:', err.read().decode().strip())

client.close()
