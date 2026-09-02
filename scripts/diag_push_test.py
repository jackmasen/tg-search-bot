# -*- coding: utf-8 -*-
import paramiko

HOST = '186.244.251.12'
USER = 'root'
PASS = 'Aa13910828867@&'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

# 1. Check BOT_TOKEN in .env
_, out, _ = client.exec_command('grep "TG_BOT_TOKEN" /www/wwwroot/tg-search-bot/.env 2>/dev/null | head -3')
print('=== .env TG_BOT_TOKEN ===')
print(out.read().decode().strip())

# 2. Check BOT_TOKEN length in DB
_, out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, length(setting_value) as len_val, substr(setting_value,1,15) as prefix FROM system_settings WHERE setting_key='TG_BOT_TOKEN';\" 2>/dev/null")
print('=== DB TG_BOT_TOKEN ===')
print(out.read().decode().strip())

# 3. Check ADMIN_TG_IDS in .env
_, out, _ = client.exec_command('grep "ADMIN_TG_IDS" /www/wwwroot/tg-search-bot/.env 2>/dev/null | head -3')
print('=== .env ADMIN_TG_IDS ===')
print(out.read().decode().strip())

# 4. Check ADMIN_TG_IDS in DB
_, out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value FROM system_settings WHERE setting_key='ADMIN_TG_IDS';\" 2>/dev/null")
print('=== DB ADMIN_TG_IDS ===')
print(out.read().decode().strip())

# 5. Check admin Telegram ID (from Telegram chat or previous config)
_, out, _ = client.exec_command("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('ADMIN_TG_IDS','BOT_TOKEN','ADMIN_USERNAME','ADMIN_PASSWORD');\" 2>/dev/null")
print('=== Key system_settings ===')
print(out.read().decode().strip())

# 6. Try the API directly
_, out, err = client.exec_command(
    'cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python3 -c "'
    'import asyncio, httpx; '
    'from app.config import Config; '
    'print(\"BOT_TOKEN:\", repr(Config.BOT_TOKEN[:20] if Config.BOT_TOKEN else \"EMPTY\")); '
    'print(\"ADMIN_TG_IDS:\", Config.ADMIN_TG_IDS); '
    'asyncio.run(Config._load_from_db()) if hasattr(Config, \"_load_from_db\") else None; '
    'print(\"After DB:\", repr(Config.BOT_TOKEN[:20] if Config.BOT_TOKEN else \"EMPTY\")); '
    'print(\"ADMIN_TG_IDS after DB:\", Config.ADMIN_TG_IDS)'
    '"'
)
print('=== Config runtime check ===')
print(out.read().decode().strip())
print(err.read().decode().strip())

client.close()
