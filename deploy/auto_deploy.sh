#!/bin/bash
# ============================================================
# TG搜索机器人 - 一键全自动部署脚本
# 功能：检测环境 → 自动修复 → 自动安装 → 自动启动（一键到底）
# 适用系统：CentOS 7+/Ubuntu 20.04+/Debian 10+
# 要求：把整个 tg-search-bot 源码解压到服务器任意目录后执行此脚本
# 执行方式：bash deploy/auto_deploy.sh  （在项目根目录执行）
#  或: bash auto_deploy.sh  （在项目根目录执行）
# ============================================================

set -e

# ============ 颜色 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============ 项目配置 ============
PROJECT_NAME="tg-search-bot"
DEPLOY_DIR="/www/wwwroot/${PROJECT_NAME}"
PYTHON_REQUIRED="3.11"
PYTHON_SRC_URL="https://registry.npmmirror.com/-/binary/python/3.11.9/Python-3.11.9.tgz"

# 自动检测脚本所在目录，向上寻找项目根
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/requirements.txt" ] && [ -f "${SCRIPT_DIR}/main.py" ]; then
    SOURCE_DIR="${SCRIPT_DIR}"
elif [ -f "${SCRIPT_DIR}/../requirements.txt" ] && [ -f "${SCRIPT_DIR}/../main.py" ]; then
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"
else
    SOURCE_DIR="${SCRIPT_DIR}"
fi

# 日志文件
LOG_FILE="${SOURCE_DIR}/auto_deploy_$(date +%Y%m%d_%H%M%S).log"

# 函数定义
log_info()    { echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$LOG_FILE"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
log_error()   { echo -e "${RED}[ERR ]${NC} $*" | tee -a "$LOG_FILE"; }
log_step()    { echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${MAGENTA}[$(date +%H:%M:%S)]${NC} $*"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
log_progress(){ echo -e "${BLUE}▶${NC} $*"; }

# ============ Banner ============
echo -e "${BLUE}
╔══════════════════════════════════════════════════════════════╗
║       TG搜索机器人 v1.0.4  一键全自动部署脚本               ║
║       One-Click Auto Deploy Script                          ║
║                                                              ║
║       自动检测源码位置 + 自动部署到 /www/wwwroot/tg-search-bot ║
╚══════════════════════════════════════════════════════════════╝
${NC}"

# 记录开始时间
START_TIME=$(date +%s)

# 初始化日志
mkdir -p "$(dirname "$LOG_FILE")"
echo "" > "$LOG_FILE"
log_info "部署开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
log_info "源码目录: ${SOURCE_DIR}"

# ============ 0. 环境预检查 ============
log_step "0. 环境预检查"

if [ "$(id -u)" != "0" ]; then
    log_error "必须以 root 用户执行此脚本 (sudo bash auto_deploy.sh)"
    exit 1
fi
log_info "✅ 当前为 root 用户"

# 检测 OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    log_error "无法检测操作系统"
    exit 1
fi
log_info "✅ 操作系统: ${OS} ${OS_VERSION}"

# 检测 CPU 架构
ARCH=$(uname -m)
log_info "✅ CPU 架构: ${ARCH}"

# ============ 1. 验证源码目录 ============
log_step "1. 验证源码目录"

if [ ! -f "${SOURCE_DIR}/main.py" ] || [ ! -f "${SOURCE_DIR}/requirements.txt" ]; then
    log_error "源码目录 ${SOURCE_DIR} 中找不到 main.py 和 requirements.txt"
    log_error "请在项目根目录执行此脚本，例如: bash deploy/auto_deploy.sh"
    exit 1
fi

log_info "✅ 源码目录验证通过: ${SOURCE_DIR}"
log_progress "项目文件数: $(find ${SOURCE_DIR} -type f | wc -l)"

# 显示关键文件
log_progress "关键文件:"
ls -la "${SOURCE_DIR}/main.py" "${SOURCE_DIR}/requirements.txt" "${SOURCE_DIR}/deploy/auto_deploy.sh" 2>/dev/null || true

# ============ 2. 复制到部署目录 ============
log_step "2. 复制到部署目录 ${DEPLOY_DIR}"

# 如果 DEPLOY_DIR 已存在且是运行中的服务，先停止
if [ -f "/etc/systemd/system/${PROJECT_NAME}.service" ]; then
    systemctl stop "${PROJECT_NAME}" 2>/dev/null || true
    log_progress "已停止旧的服务进程"
fi

# 备份旧的 .env
if [ -f "${DEPLOY_DIR}/.env" ]; then
    cp "${DEPLOY_DIR}/.env" "${DEPLOY_DIR}/.env.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    log_progress "已备份旧的 .env"
fi

# 创建目标目录
mkdir -p "${DEPLOY_DIR}"

# 复制源码（排除临时文件、__pycache__、venv）
log_progress "正在复制源码（使用 rsync 增量复制）..."
if command -v rsync &>/dev/null; then
    rsync -a --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='data/' \
        --exclude='logs/' \
        --exclude='venv/' \
        --exclude='.env' \
        --exclude='*.log' \
        --exclude='_test_*' \
        --exclude='_tmp_*' \
        "${SOURCE_DIR}/" "${DEPLOY_DIR}/"
else
    # 退回 cp
    cd "${SOURCE_DIR}"
    cp -r ./* "${DEPLOY_DIR}/" 2>/dev/null || true
    cp -r ./.env.* "${DEPLOY_DIR}/" 2>/dev/null || true
fi

# 恢复 data 和 logs 目录（如果存在旧数据）
if [ -d "${DEPLOY_DIR}/data" ]; then
    log_progress "保留旧的 data 目录（用户数据）"
else
    mkdir -p "${DEPLOY_DIR}/data"
fi

if [ -d "${DEPLOY_DIR}/logs" ]; then
    log_progress "保留旧的 logs 目录"
else
    mkdir -p "${DEPLOY_DIR}/logs"
fi

log_info "✅ 源码已复制到 ${DEPLOY_DIR}"
log_progress "文件数: $(find ${DEPLOY_DIR} -type f | wc -l)"

# ============ 3. 创建必要目录 ============
log_step "3. 创建工作目录"
mkdir -p "${DEPLOY_DIR}/data/backups" "${DEPLOY_DIR}/data/sessions" "${DEPLOY_DIR}/logs"
log_info "✅ data/ logs/ backups/ sessions/ 目录已创建"

# ============ 4. 安装系统依赖 ============
log_step "4. 安装系统依赖"

install_deps_debian() {
    log_progress "使用 apt 安装依赖..."
    apt-get update -y >> "$LOG_FILE" 2>&1 || true
    apt-get install -y \
        git build-essential libffi-dev libssl-dev libbz2-dev \
        libzlib-dev liblzma-dev libsqlite3-dev libreadline-dev \
        libgdbm-dev libgdbm-compat-dev libncurses-dev tk-dev \
        xz-utils wget curl unzip zip pkg-config libpq-dev \
        redis-server nginx >> "$LOG_FILE" 2>&1
}

install_deps_centos() {
    log_progress "使用 yum 安装依赖..."
    yum install -y epel-release >> "$LOG_FILE" 2>&1 || true
    yum install -y \
        git gcc gcc-c++ make libffi-devel openssl-devel bzip2-devel \
        zlib-devel xz-devel sqlite-devel readline-devel tk-devel \
        gdbm-devel ncurses-devel xz-devel wget curl unzip zip \
        postgresql-devel nginx >> "$LOG_FILE" 2>&1
}

case "$OS" in
    debian|ubuntu)
        install_deps_debian
        ;;
    centos|rhel|rocky|almalinux)
        install_deps_centos
        ;;
    *)
        log_warn "未识别的系统 ${OS}，尝试 apt-get 安装"
        install_deps_debian 2>/dev/null || install_deps_centos 2>/dev/null || log_error "依赖安装失败"
        ;;
esac

log_info "✅ 系统依赖已安装"

# ============ 5. Python 3.11 检查与安装 ============
log_step "5. Python 3.11 检查与安装"

PYTHON_BIN=""

# 5.1 尝试找系统已有的 python3.11
for p in python3.11 python3; do
    if command -v "$p" &>/dev/null; then
        VER=$("$p" --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$(command -v "$p")"
            log_info "✅ 检测到已有 Python ${VER} (${PYTHON_BIN})"
            break
        fi
    fi
done

# 5.2 如果没找到，编译安装
if [ -z "$PYTHON_BIN" ]; then
    log_warn "未检测到 Python 3.10+，开始自动编译安装..."

    PY_INSTALL_DIR="/usr/local/python311"

    if [ -f "${PY_INSTALL_DIR}/bin/python3.11" ]; then
        PYTHON_BIN="${PY_INSTALL_DIR}/bin/python3.11"
        log_info "✅ 已存在预编译的 Python 3.11"
    else
        cd /tmp
        if [ ! -f "Python-3.11.9.tgz" ]; then
            log_progress "下载 Python 3.11.9..."
            wget -q "${PYTHON_SRC_URL}" -O Python-3.11.9.tgz 2>>"$LOG_FILE"
        fi
        log_progress "解压..."
        tar -xzf Python-3.11.9.tgz 2>>"$LOG_FILE"
        cd Python-3.11.9
        log_progress "配置编译（这步约 1-2 分钟）..."
        ./configure --prefix="${PY_INSTALL_DIR}" --enable-optimizations --with-ssl \
            >> "$LOG_FILE" 2>&1
        log_progress "编译（这步约 3-5 分钟，请勿关闭窗口）..."
        make -j$(nproc) >> "$LOG_FILE" 2>&1
        log_progress "安装..."
        make altinstall >> "$LOG_FILE" 2>&1
        cd /tmp
        rm -rf Python-3.11.9 Python-3.11.9.tgz
    fi

    # 软链
    ln -sf "${PY_INSTALL_DIR}/bin/python3.11" /usr/local/bin/python3.11 2>/dev/null || true
    PYTHON_BIN="${PY_INSTALL_DIR}/bin/python3.11"
fi

log_info "✅ Python 可执行文件: ${PYTHON_BIN}"

# ============ 6. 创建 venv + 安装 pip 依赖 ============
log_step "6. 创建 venv 虚拟环境"

if [ -d "${DEPLOY_DIR}/venv" ]; then
    log_warn "检测到已有 venv，清理后重建..."
    rm -rf "${DEPLOY_DIR}/venv"
fi

"${PYTHON_BIN}" -m venv "${DEPLOY_DIR}/venv"
log_info "✅ venv 已创建: ${DEPLOY_DIR}/venv"

# 激活
source "${DEPLOY_DIR}/venv/bin/activate"
VENV_PYTHON="${DEPLOY_DIR}/venv/bin/python"
VENV_PIP="${DEPLOY_DIR}/venv/bin/pip"

log_step "7. 安装 Python 依赖包"

# 升级 pip
log_progress "升级 pip/setuptools..."
"${VENV_PIP}" install --upgrade pip setuptools wheel \
    -i https://pypi.tuna.tsinghua.edu.cn/simple >> "$LOG_FILE" 2>&1

# 安装 requirements
if [ -f "${DEPLOY_DIR}/requirements.txt" ]; then
    log_progress "从 requirements.txt 安装依赖（使用清华镜像加速）..."
    "${VENV_PIP}" install -r "${DEPLOY_DIR}/requirements.txt" \
        -i https://pypi.tuna.tsinghua.edu.cn/simple >> "$LOG_FILE" 2>&1
    log_info "✅ 依赖已安装"
else
    log_error "找不到 requirements.txt"
    exit 1
fi

# 验证依赖
DEP_CHECK=$("${VENV_PYTHON}" -c "import fastapi, telethon, aiosqlite, jieba; print('OK')" 2>&1)
if [ "$DEP_CHECK" = "OK" ]; then
    log_info "✅ 依赖验证通过 (fastapi/telethon/aiosqlite/jieba)"
else
    log_error "依赖验证失败: ${DEP_CHECK}"
    exit 1
fi

# 验证项目模块
MOD_CHECK=$("${VENV_PYTHON}" -c "import sys; sys.path.insert(0,'.'); from app.config import Config; print('OK')" 2>&1)
if [ "$MOD_CHECK" = "OK" ]; then
    log_info "✅ 项目模块验证通过"
else
    log_warn "项目模块验证: ${MOD_CHECK} (可能 .env 未配，不影响框架启动)"
fi

deactivate

# ============ 8. 创建 .env ============
log_step "8. 初始化 .env 配置"

if [ -f "${DEPLOY_DIR}/.env" ] && grep -q "SESSION_SECRET=.\{10\}" "${DEPLOY_DIR}/.env" 2>/dev/null; then
    log_warn ".env 已存在且有内容，保留原有配置"
else
    if [ -f "${DEPLOY_DIR}/.env.bak."* ]; then
        # 从备份恢复
        BACKUP_FILE=$(ls -t "${DEPLOY_DIR}/.env.bak."* 2>/dev/null | head -1)
        if [ -n "$BACKUP_FILE" ]; then
            cp "$BACKUP_FILE" "${DEPLOY_DIR}/.env"
            log_info "✅ 已从备份恢复 .env"
        fi
    elif [ -f "${DEPLOY_DIR}/.env.production" ]; then
        cp "${DEPLOY_DIR}/.env.production" "${DEPLOY_DIR}/.env"
        log_info "✅ 已从 .env.production 复制"
    elif [ -f "${DEPLOY_DIR}/.env.example" ]; then
        cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"
        log_info "✅ 已从 .env.example 复制"
    else
        touch "${DEPLOY_DIR}/.env"
        log_warn "未找到模板文件，创建了空的 .env"
    fi

    # 生成随机密钥（如果留空）
    if ! grep -q "^SESSION_SECRET=.\{10\}" "${DEPLOY_DIR}/.env" 2>/dev/null; then
        NEW_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import os; print(os.urandom(32).hex())")
        sed -i "s/^SESSION_SECRET=$/SESSION_SECRET=${NEW_SECRET}/" "${DEPLOY_DIR}/.env" 2>/dev/null || \
            echo "SESSION_SECRET=${NEW_SECRET}" >> "${DEPLOY_DIR}/.env"
        log_progress "自动生成 SESSION_SECRET"
    fi

    if ! grep -q "^CRYPTO_SECRET=.\{10\}" "${DEPLOY_DIR}/.env" 2>/dev/null; then
        NEW_SECRET2=$(openssl rand -hex 32 2>/dev/null || python3 -c "import os; print(os.urandom(32).hex())")
        sed -i "s/^CRYPTO_SECRET=$/CRYPTO_SECRET=${NEW_SECRET2}/" "${DEPLOY_DIR}/.env" 2>/dev/null || \
            echo "CRYPTO_SECRET=${NEW_SECRET2}" >> "${DEPLOY_DIR}/.env"
        log_progress "自动生成 CRYPTO_SECRET"
    fi
fi

# 修正权限
chmod 600 "${DEPLOY_DIR}/.env" 2>/dev/null || true
log_info "✅ .env 已准备好"

# ============ 9. 写 Systemd 服务 ============
log_step "9. 创建 Systemd 服务"

cat > "/etc/systemd/system/${PROJECT_NAME}.service" << 'SVC'
[Unit]
Description=TG Search Bot Service v1.0.4
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/tg-search-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/www/wwwroot/tg-search-bot/venv/bin/python -u main.py
Restart=always
RestartSec=5
StandardOutput=append:/www/wwwroot/tg-search-bot/logs/stdout.log
StandardError=append:/www/wwwroot/tg-search-bot/logs/stderr.log

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable "${PROJECT_NAME}"
log_info "✅ Systemd 服务已创建并启用开机自启"

# ============ 10. Nginx 配置（如果装了 Nginx） ============
log_step "10. Nginx 反代配置"

if command -v nginx &>/dev/null; then
    NGINX_CONF="/etc/nginx/conf.d/${PROJECT_NAME}.conf"
    cat > "${NGINX_CONF}" << 'NGINX'
server {
    listen 80;
    server_name _;
    
    # 反代到 127.0.0.1:8001
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINX
    # 调整 worker_connections
    if grep -q "worker_connections" /etc/nginx/nginx.conf 2>/dev/null; then
        sed -i 's/worker_connections  512;/worker_connections  4096;/' /etc/nginx/nginx.conf
        log_progress "已调大 worker_connections 到 4096"
    fi
    nginx -t >> "$LOG_FILE" 2>&1 && nginx -s reload 2>/dev/null || log_warn "Nginx 重载失败（不影响部署）"
    log_info "✅ Nginx 反代配置已生效（监听 80 端口 → 反代 8000）"
else
    log_warn "未检测到 Nginx，跳过反代配置（宝塔装 Nginx 后会自动提示）"
fi

# ============ 11. 写定时任务 ============
log_step "11. 配置定时任务"

cat > "${DEPLOY_DIR}/deploy/cron_setup.sh" << 'CRON'
#!/bin/bash
# 自动配置 crontab 定时任务
DEPLOY_DIR="/www/wwwroot/tg-search-bot"
LOG_DIR="${DEPLOY_DIR}/logs"

# 移除旧的 tg-search 相关任务
crontab -l 2>/dev/null | grep -v "tg-search" > /tmp/crontab_new 2>/dev/null || true

# 1. 每日 03:00 备份
echo "0 3 * * * cd ${DEPLOY_DIR} && bash deploy/scripts/manual_backup.sh >> ${LOG_DIR}/cron_backup.log 2>&1 # tg-search:backup" >> /tmp/crontab_new

# 2. 每 5 分钟充值对账
echo "*/5 * * * * cd ${DEPLOY_DIR} && source venv/bin/activate && python -c \"import asyncio; from app.wallet.wallet_manager import WalletManager; async def m(): print(await WalletManager().scan_deposits_and_credit()); asyncio.run(m())\" >> ${LOG_DIR}/cron_recharge.log 2>&1 # tg-search:recharge" >> /tmp/crontab_new

# 3. 每周一 04:00 清理日志
echo "0 4 * * 1 cd ${DEPLOY_DIR}/logs && find . -name '*.log' -mtime +14 -delete 2>/dev/null || true # tg-search:log_cleanup" >> /tmp/crontab_new

crontab /tmp/crontab_new
echo "✅ 定时任务已配置"
CRON
chmod +x "${DEPLOY_DIR}/deploy/cron_setup.sh"
bash "${DEPLOY_DIR}/deploy/cron_setup.sh"
log_info "✅ 3 条定时任务已配置（备份 / 对账 / 日志清理）"

# ============ 12. 启动服务 ============
log_step "12. 启动服务并验证"

# 如果已有旧的运行，先停
systemctl stop "${PROJECT_NAME}" 2>/dev/null || true
sleep 1

systemctl start "${PROJECT_NAME}"
sleep 3

# 检查状态
if systemctl is-active --quiet "${PROJECT_NAME}"; then
    log_info "✅ 服务已启动并保持运行"
else
    log_error "服务启动失败！查看日志："
    echo ""
    echo "    tail -n 50 ${DEPLOY_DIR}/logs/stderr.log"
    echo "    journalctl -u ${PROJECT_NAME} -n 50 --no-pager"
    echo ""
    # 输出最近错误
    if [ -f "${DEPLOY_DIR}/logs/stderr.log" ]; then
        echo "--- stderr.log 最近 20 行 ---"
        tail -n 20 "${DEPLOY_DIR}/logs/stderr.log"
    fi
    exit 1
fi

# 测试 API 响应
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/admin/settings/describe 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
    log_info "✅ API 响应正常 (HTTP ${HTTP_CODE})"
else
    log_warn "API 响应异常 (HTTP ${HTTP_CODE})，不影响后台访问"
fi

# ============ 13. 安全收尾 ============
log_step "13. 安全收尾"

# 清历史（防泄露助记词）
clear
history -c 2>/dev/null || true
rm -f /root/.bash_history 2>/dev/null || true

# ============ 14. 最终报告 ============
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MIN=$((DURATION / 60))
SEC=$((DURATION % 60))

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="<服务器IP>"

echo ""
echo -e "${GREEN}
╔══════════════════════════════════════════════════════════════╗
║                   🎉 部署完成 🎉                              ║
╠══════════════════════════════════════════════════════════════╣
║  ⏱ 耗时: ${MIN}分${SEC}秒                                    ║
║                                                              ║
║  🔗 后台地址:                                                ║
║     本机直连:  http://127.0.0.1:8001/admin                    ║
║     服务器IP:  http://${SERVER_IP}:8001/admin                ║
║     Nginx:     http://${SERVER_IP}/admin（已配置反代）        ║
║                                                              ║
║  👤 默认账号:  admin                                         ║
║  🔑 默认密码:  demo123456  (请立即在后台修改！)              ║
║                                                              ║
║  ⚠️  必须手工完成的操作（1 步）：                             ║
║  ① 后台 ⚙️ 系统配置 补全所有配置（含 HD 助记词）              ║
║                                                              ║
║  💡  可选操作（按需配置）：                                   ║
║  · 🐢 小号管理: 后台「小号/代理管理」→ 新增小号              ║
║    支持三步向导: 发送验证码 → 验证登录 → 配置保存            ║
║                                                              ║
║  📁 项目目录: ${DEPLOY_DIR}
║  📋 部署日志: ${LOG_FILE}
╚══════════════════════════════════════════════════════════════╝
${NC}"

log_info "部署日志已保存: ${LOG_FILE}"
log_info "部署完成！"
