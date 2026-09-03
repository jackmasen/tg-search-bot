import sys
sys.path.insert(0, r"C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot")
import asyncio, requests, json

async def main():
    BASE = "http://jsou.tgjsbot.kdns.fr"
    for pwd in ["demo123456", "Admin@123456", "admin123", "password123"]:
        try:
            r = requests.post(f"{BASE}/api/admin/login", json={"username": "admin", "password": pwd}, timeout=10)
            data = r.json()
            print(f"password={pwd!r}: {r.status_code} -> {json.dumps(data)[:200]}")
            if data.get("ok"):
                sid = data["session_id"]
                r2 = requests.post(f"{BASE}/api/admin/bot_push_start_page", json={"session_id": sid}, timeout=15)
                print(f"  push: {r2.status_code} -> {r2.text[:300]}")
                return
        except Exception as e:
            print(f"password={pwd!r}: error {e}")

asyncio.run(main())
