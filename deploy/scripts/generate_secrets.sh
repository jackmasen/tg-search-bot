#!/bin/bash
# ============================================================
# 密钥一键生成工具（离线执行，不联网）
# 生成内容：
#   1. SESSION_SECRET - 32位HEX会话密钥
#   2. CRYPTO_SECRET  - 32字节BASE64加密密钥
#   3. HD钱包助记词（可选，第2步用）
# ============================================================

set -e

echo "=========================================="
echo " 🔐  TG搜索机器人 - 密钥生成工具"
echo "=========================================="
echo ""

# 检查python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] 未检测到Python，请先安装Python 3.8+"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)

# 检查项目目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ============================================================
# 1. 生成基础密钥
# ============================================================
echo "【1/3】生成安全密钥..."
SESSION_SECRET=$($PYTHON -c "import secrets; print(secrets.token_hex(32))")
CRYPTO_SECRET=$($PYTHON -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")
echo "  ✅ SESSION_SECRET: $SESSION_SECRET"
echo "  ✅ CRYPTO_SECRET : $CRYPTO_SECRET"
echo ""

# ============================================================
# 2. 生成HD钱包助记词（第2步用）
# ============================================================
MNEMONIC=""
read -p "【2/3】是否同时生成TRON HD钱包助记词？(y/N) " gen_wallet
if [[ "$gen_wallet" =~ ^[Yy]$ ]]; then
    echo "  正在生成TRX助记词..."
    # 先检查hdwallet是否已安装
    if ! $PYTHON -c "import hdwallet" 2>/dev/null; then
        echo "  [INFO] 安装hdwallet依赖..."
        $PYTHON -m pip install hdwallet --quiet
    fi
    MNEMONIC=$($PYTHON << 'PYEOF'
from hdwallet import HDWallet
from hdwallet.symbols import TRX
w = HDWallet(symbol=TRX)
w.from_mnemonic(language="english", strength=128)  # 12词
print(w.mnemonic())
PYEOF
)
    echo "  ✅ 助记词已生成（12个英文单词，空格分隔）"
    echo "  ⚠️  请离线复制保存到安全的地方！！！"
    echo "     助记词: $MNEMONIC"
    echo ""
    # 展示第一个地址给用户验证
    FIRST_ADDR=$($PYTHON -c "
from hdwallet import HDWallet
from hdwallet.symbols import TRX
w = HDWallet(symbol=TRX)
w.from_mnemonic('$MNEMONIC')
w.from_path(\"m/44'/195'/0'/0/0\")
print(w.address())
")
    echo "     首个充值地址(索引0): $FIRST_ADDR"
    echo ""
fi

# ============================================================
# 3. 写入.env文件
# ============================================================
echo "【3/3】写入配置文件..."

ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "  检测到现有 .env 文件，已备份为 .env.bak.$(date +%s)"
    cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%s)"
else
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
    echo "  从 .env.example 复制生成 .env 文件"
fi

# 写入SESSION_SECRET
if grep -q "^SESSION_SECRET=" "$ENV_FILE"; then
    sed -i "s|^SESSION_SECRET=.*|SESSION_SECRET=${SESSION_SECRET}|g" "$ENV_FILE"
else
    echo "" >> "$ENV_FILE"
    echo "# 部署脚本生成的安全密钥" >> "$ENV_FILE"
    echo "SESSION_SECRET=${SESSION_SECRET}" >> "$ENV_FILE"
fi

# 写入CRYPTO_SECRET
if grep -q "^CRYPTO_SECRET=" "$ENV_FILE"; then
    sed -i "s|^CRYPTO_SECRET=.*|CRYPTO_SECRET=${CRYPTO_SECRET}|g" "$ENV_FILE"
else
    echo "CRYPTO_SECRET=${CRYPTO_SECRET}" >> "$ENV_FILE"
fi

# 写入助记词（如果有）
if [ -n "$MNEMONIC" ]; then
    if grep -q "^HD_WALLET_MNEMONIC=" "$ENV_FILE"; then
        sed -i "s|^HD_WALLET_MNEMONIC=.*|HD_WALLET_MNEMONIC=${MNEMONIC}|g" "$ENV_FILE"
    else
        echo "" >> "$ENV_FILE"
        echo "# TRON HD钱包助记词" >> "$ENV_FILE"
        echo "HD_WALLET_MNEMONIC=${MNEMONIC}" >> "$ENV_FILE"
    fi
fi

echo ""
echo "=========================================="
echo " ✅ 密钥生成完成！"
echo "    配置文件: $ENV_FILE"
echo "=========================================="
echo ""
echo "📋 接下来还需要手动填入 .env 中的配置:"
echo "   1. TG_BOT_TOKEN       - @BotFather 获取"
echo "   2. TELETHON_API_IDS   - my.telegram.org 获取"
echo "   3. TELETHON_API_HASHS - 同上"
echo "   4. TELETHON_PHONES    - 采集账号手机号列表"
echo "   5. ADMIN_TG_IDS       - 你的TG用户ID (搜 @userinfobot 获取)"
echo ""
echo "📌 下一步命令:"
if [ -f "venv/bin/python" ]; then
    echo "   source venv/bin/activate"
fi
echo "   bash deploy/scripts/login_accounts.sh  # 登录采集账号"
echo ""
echo "⚠️  最后提醒: 请把HD钱包助记词离线抄写或加密备份，"
echo "             .env 文件权限设为 600 (chmod 600 .env)"
