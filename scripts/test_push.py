# -*- coding: utf-8 -*-
"""Direct test of bot_push_test logic to isolate the issue"""
import sys
sys.path.insert(0, '/www/wwwroot/tg-search-bot')

from app.config import Config
from app.admin.system_settings_manager import load_all_settings_from_db
from app.database import get_db
import asyncio, httpx, datetime

print(f"BOT_TOKEN: {repr(Config.BOT_TOKEN[:30] if Config.BOT_TOKEN else 'EMPTY')}")
print(f"ADMIN_TG_IDS: {repr(Config.ADMIN_TG_IDS)}")
print(f"CRYPTO_SECRET len: {len(Config.CRYPTO_SECRET) if Config.CRYPTO_SECRET else 0}")

# Try loading from DB
async def test():
    async with get_db() as db:
        vals = await load_all_settings_from_db(db)
        print(f"\nDB ADMIN_TG_IDS: {repr(vals.get('ADMIN_TG_IDS'))}")
        print(f"DB BOT_TOKEN len: {len(vals.get('TG_BOT_TOKEN', ''))}")

        # Apply overrides
        Config.apply_overrides(vals)
        print(f"\nAfter apply_overrides:")
        print(f"  BOT_TOKEN: {repr(Config.BOT_TOKEN[:30] if Config.BOT_TOKEN else 'EMPTY')}")
        print(f"  ADMIN_TG_IDS: {repr(Config.ADMIN_TG_IDS)}")

    # Try sending test message
    token = Config.BOT_TOKEN
    admins = Config.ADMIN_TG_IDS or []
    print(f"\nSending test message...")
    print(f"  token empty: {not bool(token)}")
    print(f"  admins: {admins}")

    if not token:
        print("ERROR: BOT_TOKEN is empty!")
        return
    if not admins:
        print("ERROR: ADMIN_TG_IDS is empty!")
        return

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    msg = f"🔔 后台手动推送测试\n⏰ {now_str}\n\n✅ Bot 消息通道正常！请查看 Telegram。"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=8.0)) as client:
            for uid in admins:
                try:
                    r = await client.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": int(uid), "text": msg, "parse_mode": "HTML"},
                    )
                    data = r.json()
                    if data.get("ok"):
                        print(f"  ✅ 推送至 {uid} 成功")
                    else:
                        print(f"  ⚠️ 推送至 {uid} 失败：{data.get('description','')}")
                except Exception as e:
                    print(f"  ❌ 推送至 {uid} 异常：{str(e)[:80]}")
    except Exception as e:
        print(f"  ❌ HTTP 请求失败：{str(e)[:100]}")

asyncio.run(test())
