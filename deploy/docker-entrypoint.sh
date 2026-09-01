#!/bin/bash
# ============================================================
# Docker入口脚本 - 启动前准备和健康检查
# ============================================================

set -e

echo "=========================================="
echo " TG搜索机器人 Docker容器启动中..."
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 检查.env是否存在，没有则从.example复制并提示
if [ ! -f "/app/.env" ]; then
    if [ -f "/app/.env.example" ]; then
        echo "[WARN] 未找到.env文件，已从.env.example复制"
        echo "       请编辑并填入真实配置后重启容器"
        cp /app/.env.example /app/.env
    fi
fi

# 2. 环境变量注入优先（兼容docker-compose environment: 配置）
# 如果通过环境变量传入了配置，自动写入.env
ENV_VARS=(
    "TG_BOT_TOKEN"
    "TELETHON_API_IDS"
    "TELETHON_API_HASHS"
    "TELETHON_PHONES"
    "SESSION_DIR"
    "DB_PATH"
    "MAX_CHANNELS_PER_ACCOUNT"
    "JOIN_INTERVAL_SECONDS"
    "MAX_JOIN_PER_DAY"
    "SEARCH_RESULT_LIMIT"
    "FREE_SEARCH_DAILY_LIMIT"
    "LOG_DIR"
    "LOG_LEVEL"
    "TRONGRID_API_KEY"
    "HD_WALLET_MNEMONIC"
    "SESSION_SECRET"
    "CRYPTO_SECRET"
    "ADMIN_TG_IDS"
)

for VAR in "${ENV_VARS[@]}"; do
    VALUE="${!VAR}"
    if [ -n "$VALUE" ] && [ -f "/app/.env" ]; then
        # 已存在则替换，不存在则追加
        if grep -q "^${VAR}=" /app/.env; then
            sed -i "s|^${VAR}=.*|${VAR}=${VALUE}|g" /app/.env
        else
            echo "${VAR}=${VALUE}" >> /app/.env
        fi
    fi
done

# 3. 确保目录存在和权限正确
mkdir -p /app/data/sessions
mkdir -p /app/data/backups
mkdir -p /app/logs

# 检查data目录可写
if [ ! -w "/app/data" ]; then
    echo "[ERROR] /app/data 目录不可写，请检查volume挂载权限"
    echo "        建议: docker run -v /your/host/path:/app/data:rw ..."
    exit 1
fi

# 4. 生成默认安全密钥（如果未配置）
if [ -f "/app/.env" ]; then
    if ! grep -q "SESSION_SECRET" /app/.env || grep -q "SESSION_SECRET=$" /app/.env; then
        SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
        if grep -q "SESSION_SECRET" /app/.env; then
            sed -i "s|^SESSION_SECRET=.*|SESSION_SECRET=${SECRET}|g" /app/.env
        else
            echo "" >> /app/.env
            echo "# 自动生成的安全密钥" >> /app/.env
            echo "SESSION_SECRET=${SECRET}" >> /app/.env
        fi
        echo "[INFO] 自动生成 SESSION_SECRET (首次启动)"
    fi
    if ! grep -q "CRYPTO_SECRET" /app/.env || grep -q "CRYPTO_SECRET=$" /app/.env; then
        SECRET=$(python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")
        if grep -q "CRYPTO_SECRET" /app/.env; then
            sed -i "s|^CRYPTO_SECRET=.*|CRYPTO_SECRET=${SECRET}|g" /app/.env
        else
            echo "CRYPTO_SECRET=${SECRET}" >> /app/.env
        fi
        echo "[INFO] 自动生成 CRYPTO_SECRET (首次启动)"
    fi
fi

# 5. 执行配置校验（不退出，只打印警告）
echo ""
echo "[INFO] 运行配置校验..."
python -c "
import sys
try:
    from app.config import Config
    Config.validate()
    print('[OK] 配置校验通过')
except ValueError as e:
    print(f'[WARN] 配置未完善（首次启动正常）: {e}')
    print('       请配置好 .env 或 docker-compose environment 后重启')
" || true

# 6. 首次启动提示
IS_FIRST=false
if [ ! -f "/app/data/.initialized" ]; then
    IS_FIRST=true
    echo ""
    echo "=========================================="
    echo " 首次启动指南："
    echo " 1. 填写 .env 中的 TG_BOT_TOKEN 和 Telethon账号"
    echo " 2. 需要手动登录采集账号生成session文件："
    echo "    docker exec -it tg-search-bot bash scripts/login_accounts.sh"
    echo " 3. 然后重启容器：docker restart tg-search-bot"
    echo "=========================================="
    touch /app/data/.initialized
fi

echo ""
echo "[INFO] 启动主进程: $@"
echo "=========================================="

# 7. 执行CMD命令
exec "$@"
