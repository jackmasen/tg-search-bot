#!/bin/bash
# ============================================================
# TG搜索机器人 - 部署后自检脚本
# 执行方式：
#   宝塔: cd /www/wwwroot/tg-search-bot && source venv/bin/activate && bash deploy/scripts/health_check.sh
#   Docker: docker compose exec bot bash deploy/scripts/health_check.sh
# 功能：检查配置、数据库、session、Bot连通性、定时任务
# ============================================================

set +e  # 不退出，跑完所有检查

PASS=0
FAIL=0
WARN=0
TOTAL=0

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          TG搜索机器人 - 部署后健康自检                       ║"
echo "║          时间: $(date '+%Y-%m-%d %H:%M:%S')                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

check() {
    TOTAL=$((TOTAL+1))
    local name="$1"
    local result="$2"
    local detail="$3"
    if [ "$result" = "PASS" ]; then
        echo -e "  ✅ \033[32mPASS\033[0m  $name"
        PASS=$((PASS+1))
    elif [ "$result" = "WARN" ]; then
        echo -e "  ⚠️  \033[33mWARN\033[0m  $name - $detail"
        WARN=$((WARN+1))
    else
        echo -e "  ❌ \033[31mFAIL\033[0m  $name - $detail"
        FAIL=$((FAIL+1))
    fi
    [ -n "$detail" ] && [ "$result" = "PASS" ] && echo "          $detail"
}

echo "【1/6】环境检查"
echo "─────────────────────────────────────────"

# Python版本
PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null)
if [[ "$PY_VER" =~ ^3\.1[0-9] ]]; then
    check "Python版本" "PASS" "$PY_VER"
else
    check "Python版本" "FAIL" "需要3.10+，当前$PY_VER"
fi

# 依赖包检查
$PYTHON -c "import telethon, telegram, aiosqlite, jieba, loguru, dotenv" 2>/dev/null
if [ $? -eq 0 ]; then
    check "Python依赖包" "PASS"
else
    check "Python依赖包" "FAIL" "请先 pip install -r requirements.txt"
fi

# .env文件
if [ -f ".env" ]; then
    check ".env配置文件" "PASS" "$(wc -l < .env)行配置"
else
    check ".env配置文件" "FAIL" "请从 .env.production 复制并填写"
fi

echo ""
echo "【2/6】配置项检查"
echo "─────────────────────────────────────────"

$PYTHON << 'PYEOF' > /tmp/check_config.txt 2>&1
import os, sys
from dotenv import load_dotenv
load_dotenv()

issues = []
checks = []

def chk(name, value, required=True, validator=None):
    if not value or value == "":
        if required:
            issues.append(("FAIL", name, "未配置"))
        else:
            issues.append(("WARN", name, "未配置（可选）"))
    else:
        if validator and not validator(value):
            issues.append(("FAIL", name, "格式不正确"))
        else:
            issues.append(("PASS", name, "已配置"))

# 必填项
chk("TG_BOT_TOKEN", os.getenv("TG_BOT_TOKEN"), True,
    lambda v: ":" in v and len(v) > 20)
chk("TELETHON_API_IDS", os.getenv("TELETHON_API_IDS"))
chk("TELETHON_API_HASHS", os.getenv("TELETHON_API_HASHS"))
chk("TELETHON_PHONES", os.getenv("TELETHON_PHONES"))

# 一致性检查
ids = os.getenv("TELETHON_API_IDS","").split(",")
hashes = os.getenv("TELETHON_API_HASHS","").split(",")
phones = os.getenv("TELETHON_PHONES","").split(",")
ids = [x for x in ids if x.strip()]
hashes = [x for x in hashes if x.strip()]
phones = [x for x in phones if x.strip()]
if ids and hashes and phones and (len(ids) != len(hashes) or len(ids) != len(phones)):
    issues.append(("FAIL", "账号池一致性", f"API_ID({len(ids)}) != HASH({len(hashes)}) != PHONE({len(phones)})"))
elif ids:
    issues.append(("PASS", "账号池一致性", f"共{len(ids)}个账号"))

# 安全密钥（第2步用可选）
chk("SESSION_SECRET", os.getenv("SESSION_SECRET"), False)
chk("CRYPTO_SECRET", os.getenv("CRYPTO_SECRET"), False)

# 第2步可选
chk("TRONGRID_API_KEY", os.getenv("TRONGRID_API_KEY"), False)
mnemonic = os.getenv("HD_WALLET_MNEMONIC","")
if mnemonic:
    word_count = len(mnemonic.split())
    if word_count in (12,24):
        issues.append(("PASS", "HD_WALLET_MNEMONIC", f"{word_count}个单词"))
    else:
        issues.append(("FAIL", "HD_WALLET_MNEMONIC", f"应12或24词，当前{word_count}个"))
else:
    issues.append(("WARN", "HD_WALLET_MNEMONIC", "未配置（USDT充值功能不可用）"))

for level, name, detail in issues:
    print(f"{level}|{name}|{detail}")
PYEOF

while IFS='|' read -r level name detail; do
    [ -z "$level" ] && continue
    check "$name" "$level" "$detail"
done < /tmp/check_config.txt

echo ""
echo "【3/6】目录与权限"
echo "─────────────────────────────────────────"

for d in "data" "data/sessions" "data/backups" "logs"; do
    if [ -d "$d" ]; then
        if [ -w "$d" ]; then
            check "目录 $d" "PASS" "存在且可写"
        else
            check "目录 $d" "FAIL" "无写入权限，执行 chmod -R 755 $d"
        fi
    else
        check "目录 $d" "FAIL" "不存在，执行 mkdir -p $d"
    fi
done

# .env文件权限
if [ -f ".env" ]; then
    if command -v stat &> /dev/null; then
        PERM=$(stat -c "%a" .env 2>/dev/null || stat -f "%OLp" .env 2>/dev/null)
        if [ "$PERM" = "600" ]; then
            check ".env文件权限" "PASS" "$PERM（安全）"
        else
            check ".env文件权限" "WARN" "$PERM，建议改为600: chmod 600 .env"
        fi
    fi
fi

echo ""
echo "【4/6】数据库与Session"
echo "─────────────────────────────────────────"

$PYTHON << 'PYEOF' > /tmp/check_db.txt 2>&1
import asyncio, sys, os
sys.path.insert(0, os.getcwd())

async def main():
    from app.config import Config
    from app.database import init_db, get_db
    from app.crawler.account_pool import account_pool
    
    # 初始化DB
    try:
        await init_db()
    except Exception as e:
        print(f"FAIL|数据库初始化|{e}")
        return
    print("PASS|数据库初始化|成功")
    
    # 检查数据文件
    db_size = os.path.getsize(Config.DB_PATH) if os.path.exists(Config.DB_PATH) else 0
    print(f"PASS|数据库文件|{Config.DB_PATH} ({db_size/1024/1024:.2f} MB)")
    
    # 检查session文件
    sessions = []
    if os.path.isdir(Config.SESSION_DIR):
        sessions = [f for f in os.listdir(Config.SESSION_DIR) if f.endswith('.session')]
    if sessions:
        print(f"PASS|Session文件|检测到{len(sessions)}个: {', '.join(sessions[:3])}")
    else:
        print(f"WARN|Session文件|未生成，请先运行 bash deploy/scripts/login_accounts.sh")

asyncio.run(main())
PYEOF

while IFS='|' read -r level name detail; do
    [ -z "$level" ] && continue
    check "$name" "$level" "$detail"
done < /tmp/check_db.txt

echo ""
echo "【5/6】Bot API连通性测试"
echo "─────────────────────────────────────────"

$PYTHON << 'PYEOF' > /tmp/check_bot.txt 2>&1
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TG_BOT_TOKEN","")
if not TOKEN or TOKEN.startswith("your_"):
    print("WARN|Bot Token有效性|未配置真实Token，跳过测试")
else:
    try:
        import httpx
        r = httpx.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=15)
        data = r.json()
        if data.get("ok"):
            bot = data["result"]
            print(f"PASS|Bot API连通性|@{bot.get('username','?')} (ID:{bot.get('id','?')})")
        else:
            print(f"FAIL|Bot API连通性|{data.get('description','未知错误')}")
    except Exception as e:
        print(f"FAIL|Bot API连通性|网络异常: {e}")

# 测试Telethon连通性（如果session存在）
import glob
sessions = glob.glob("data/sessions/*.session")
if sessions:
    try:
        import httpx
        r = httpx.get("https://mtp.telegram.org/api", timeout=5)
        print(f"PASS|Telegram MTProto网络|可连通 (HTTP {r.status_code})")
    except Exception as e:
        print(f"WARN|Telegram MTProto网络|服务器可能被墙，需确认：{str(e)[:50]}")
PYEOF

while IFS='|' read -r level name detail; do
    [ -z "$level" ] && continue
    check "$name" "$level" "$detail"
done < /tmp/check_bot.txt

echo ""
echo "【6/6】进程与定时任务"
echo "─────────────────────────────────────────"

# 检查进程
if [ -f "/etc/systemd/system/tg-search-bot.service" ]; then
    if systemctl is-active --quiet tg-search-bot; then
        check "Systemd服务" "PASS" "运行中 (PID: $(systemctl show -p MainPID tg-search-bot | cut -d= -f2))"
    else
        check "Systemd服务" "WARN" "未运行，执行 systemctl start tg-search-bot"
    fi
elif [ -n "$(grep docker /proc/1/cgroup 2>/dev/null)" ]; then
    check "运行环境" "PASS" "Docker容器模式"
else
    check "进程守护" "WARN" "未检测到Systemd服务或Docker容器"
fi

# 检查crontab
if command -v crontab &> /dev/null; then
    CRONS=$(crontab -l 2>/dev/null | grep -c "tg-search\|backup.sh\|recharge.sh" || echo 0)
    if [ "$CRONS" -gt 0 ]; then
        check "定时任务" "PASS" "已配置${CRONS}条"
    else
        check "定时任务" "WARN" "未配置，建议启用备份定时任务"
    fi
fi

# 输出日志文件检查
LOG_COUNT=$(find logs -name "*.log" 2>/dev/null | wc -l)
if [ "$LOG_COUNT" -gt 0 ]; then
    LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)
    LOG_LINES=$(wc -l < "$LATEST_LOG" 2>/dev/null || echo 0)
    check "日志系统" "PASS" "$LOG_COUNT个文件，最新: $(basename $LATEST_LOG) (${LOG_LINES}行)"
else
    check "日志系统" "WARN" "暂无日志（Bot启动后自动生成）"
fi

# ============================================================
# 汇总
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                       自检结果汇总                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  总计项: %-3d   ✅ 通过: %-3d   ⚠️ 警告: %-3d   ❌ 失败: %-3d ║\n" $TOTAL $PASS $WARN $FAIL
echo "╚══════════════════════════════════════════════════════════════╝"

if [ $FAIL -eq 0 ]; then
    if [ $WARN -eq 0 ]; then
        echo -e "\n\033[32m✅ 部署完美！所有检查通过，可以启动Bot服务\033[0m"
        echo ""
        echo "下一步命令:"
        echo "  宝塔:   systemctl start tg-search-bot && journalctl -u tg-search-bot -f"
        echo "  Docker: docker compose up -d && docker compose logs -f"
    else
        echo -e "\n\033[33m⚠️  基本通过，有$WARN项警告（部分为可选功能，不影响第1步上线）\033[0m"
        echo ""
        echo "建议处理完警告后启动，或直接启动验证第1步功能："
        echo "  宝塔:   systemctl start tg-search-bot"
        echo "  Docker: docker compose up -d"
    fi
else
    echo -e "\n\033[31m❌ 有$FAIL项失败，请先修复后再启动服务\033[0m"
    echo ""
    echo "快速修复命令参考:"
    echo "  安装依赖: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
    echo "  生成密钥: bash deploy/scripts/generate_secrets.sh"
    echo "  生成配置: cp .env.production .env 然后编辑填入"
    echo "  创建目录: mkdir -p data/sessions data/backups logs && chmod -R 755 data logs"
    echo "  登录账号: bash deploy/scripts/login_accounts.sh"
fi

exit 0
