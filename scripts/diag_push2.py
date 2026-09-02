# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Check DB directly with proper escaping
_, out1, _ = client.exec_command(
    "cd /www/wwwroot/tg-search-bot && source venv/bin/activate && "
    "python3 -c \"import sqlite3; c=sqlite3.connect('data/tg_search.db'); "
    "r=c.execute(\\\"SELECT key, substr(value,1,80) FROM settings WHERE key IN ('TG_BOT_TOKEN','ADMIN_TG_IDS')\\\").fetchall(); "
    "for x in r: print(x[0],'=',repr(x[1]))\""
)
print("=== DB settings ===")
print(out1.read().decode('utf-8', errors='replace'))

# Check if there's a different DB location
_, out2, _ = client.exec_command('find /www/wwwroot/tg-search-bot/data -name "*.db" 2>/dev/null')
print("=== DB files ===")
print(out2.read().decode('utf-8', errors='replace'))

# Direct Telegram API test
_, out3, _ = client.exec_command(
    "cd /www/wwwroot/tg-search-bot && source venv/bin/activate && "
    "python3 -c \"import os; os.environ.setdefault('DB_PATH','data/tg_search.db'); "
    "from dotenv import load_dotenv; load_dotenv(); "
    "from app.config import Config; "
    "from app.admin.system_settings_manager import load_all_settings_from_db; "
    "import asyncio; "
    "async def t(): "
    "  async from app.database import get_db; "
    "  async with get_db() as db: "
    "    v = await load_all_settings_from_db(db); "
    "    Config.apply_overrides(v); "
    "    print('BOT_TOKEN:', repr(Config.BOT_TOKEN[:30] if Config.BOT_TOKEN else None)); "
    "    print('ADMIN_TG_IDS:', Config.ADMIN_TG_IDS); "
    "asyncio.run(t())\""
)
print("=== Config test ===")
print(out3.read().decode('utf-8', errors='replace'))

# Test direct Telegram API call
_, out4, _ = client.exec_command(
    "cd /www/wwwroot/tg-search-bot && source venv/bin/activate && "
    "python3 -c \"import asyncio, httpx, os; "
    "os.environ.setdefault('DB_PATH','data/tg_search.db'); "
    "from dotenv import load_dotenv; load_dotenv(); "
    "from app.config import Config; "
    "from app.admin.system_settings_manager import load_all_settings_from_db; "
    "from app.database import get_db; "
    "async def t(): "
    "  async with get_db() as db: "
    "    v = await load_all_settings_from_db(db); "
    "    Config.apply_overrides(v); "
    "  token = Config.BOT_TOKEN; "
    "  admins = Config.ADMIN_TG_IDS or []; "
    "  print('Token empty:', not bool(token)); "
    "  print('Admins:', admins); "
    "  if token and admins: "
    "    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=8.0)) as c: "
    "      r = await c.post(f'https://api.telegram.org/bot{token}/sendMessage', "
    "        json={'chat_id': int(admins[0]), 'text': 'Test from diag', 'parse_mode': 'HTML'}); "
    "      print('Telegram API:', r.status_code, r.text[:200]); "
    "  else: print('SKIP: missing config'); "
    "asyncio.run(t())\""
)
print("=== Telegram test ===")
print(out4.read().decode('utf-8', errors='replace'))

client.close()
