#!/bin/bash
# ============================================================
# 脚本：手动登录Telegram采集账号（生成session文件）
# 使用场景：首次部署、session过期、更换采集账号时
# 执行：
#   宝塔部署: cd /www/wwwroot/tg-search-bot && source venv/bin/activate && bash scripts/login_accounts.sh
#   Docker部署: docker compose exec bot bash scripts/login_accounts.sh
# ============================================================

set -e

echo "=========================================="
echo " Telegram采集账号登录工具"
echo "=========================================="
echo ""

# 检查.env文件
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
    echo "[ERROR] 未找到 .env 文件"
    echo "        请先复制 .env.example 为 .env 并填入配置"
    exit 1
fi

# 检查虚拟环境
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="python"
else
    PYTHON="python3"
fi

echo "[INFO] 使用Python: $($PYTHON --version)"
echo "[INFO] 项目目录: $PROJECT_DIR"
echo ""

# 执行登录
$PYTHON << 'PYEOF'
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

async def login():
    from app.config import Config
    from app.crawler.account_pool import account_pool
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"[ERROR] 配置校验失败: {e}")
        print("       请先完善 .env 中的 TELETHON_API_IDS/HASHS/PHONES")
        return
    
    print("准备登录以下账号:")
    for i, phone in enumerate(Config.PHONES):
        print(f"  [{i+1}] {phone}")
    print()
    
    # 先初始化
    await account_pool.initialize()
    
    # 逐个交互式登录
    await account_pool.manual_login_all()
    
    print("\n登录完成！session文件保存在:", Config.SESSION_DIR)
    print("请执行以下命令重启Bot:")
    print("  宝塔: systemctl restart tg-search-bot")
    print("  Docker: docker compose restart bot")

if __name__ == "__main__":
    try:
        asyncio.run(login())
    except KeyboardInterrupt:
        print("\n用户取消登录")
    except Exception as e:
        import traceback
        print(f"\n[ERROR] 登录出错: {e}")
        traceback.print_exc()
PYEOF
