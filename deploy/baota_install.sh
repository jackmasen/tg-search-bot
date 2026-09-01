#!/bin/bash
# ============================================================
# TG Search Bot v1.0.5 - BT Panel One-Click Deployment Script
# Auto detect → Auto fix → Auto install → Auto start
# ============================================================
set -e

BOT_DIR="/www/wwwroot/tg-search-bot"
VENV_DIR="$BOT_DIR/venv"
LOG_DIR="$BOT_DIR/logs"
LOG_FILE="$LOG_DIR/install_$(date +%Y%m%d_%H%M%S).log"
BT_NGINX_DIR="/www/server/panel/vhost/nginx"
PYTHON_BIN=""
PIP_BIN=""
PORT=8001

mkdir -p "$LOG_DIR"

log() {
    local msg="[$(date '+%H:%M:%S')] $*"
    echo -e "\033[32m$msg\033[0m"
    echo "$msg" >> "$LOG_FILE"
}

warn() {
    echo -e "\033[33m⚠️  $*\033[0m"
    echo "WARNING: $*" >> "$LOG_FILE"
}

error_exit() {
    echo -e "\033[31mERROR: $1\033[0m"
    echo "ERROR: $1" >> "$LOG_FILE"
    exit 1
}

# ============================================================
# Step 1: Auto detect Python 3.11
# ============================================================
log "=== Step 1: Detecting Python 3.11 ==="

detect_python() {
    for p in /usr/local/python3.11/bin/python3.11 \
             /usr/local/python3.11/bin/python \
             /usr/bin/python3.11 \
             /usr/bin/python3 \
             python3.11 python3; do
        if command -v "$p" &>/dev/null || [ -x "$p" ]; then
            local ver=$("$p" --version 2>&1 || echo "")
            if [[ "$ver" == *"3.11"* ]]; then
                echo "$p"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN=$(detect_python) || error_exit "Python 3.11 not found. Install it first: apt install python3.11 python3.11-venv python3.11-dev"
log "Python 3.11 found: $PYTHON_BIN"

# ============================================================
# Step 2: Auto fix venv (create or rebuild)
# ============================================================
log "=== Step 2: Fixing virtual environment ==="

fix_venv() {
    if [ -d "$VENV_DIR" ]; then
        local is_broken=false
        [ ! -f "$VENV_DIR/bin/pip" ] && is_broken=true
        [ -f "$VENV_DIR/bin/pip" ] && ! "$VENV_DIR/bin/pip" --version &>/dev/null && is_broken=true
        if [ "$is_broken" = true ]; then
            log "Broken venv detected, rebuilding..."
            rm -rf "$VENV_DIR"
        fi
    fi

    log "Creating virtual environment at $VENV_DIR ..."
    $PYTHON_BIN -m venv "$VENV_DIR"

    if [ ! -f "$VENV_DIR/bin/pip" ] || ! "$VENV_DIR/bin/pip" --version &>/dev/null; then
        log "venv pip broken, rebuilding with ensurepip..."
        rm -rf "$VENV_DIR"
        $PYTHON_BIN -m venv "$VENV_DIR"
        "$VENV_DIR/bin/python" -m ensurepip --upgrade 2>/dev/null || true
        if [ ! -f "$VENV_DIR/bin/pip" ] || ! "$VENV_DIR/bin/pip" --version &>/dev/null; then
            # Last resort: use system pip3.11 to bootstrap
            local sys_pip="/usr/local/python3.11/bin/pip"
            [ ! -f "$sys_pip" ] && sys_pip="$(command -v pip3.11 2>/dev/null || echo "")"
            if [ -n "$sys_pip" ] && [ -f "$sys_pip" ]; then
                log "Bootstrapping pip via system pip3.11..."
                "$sys_pip" install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple &>/dev/null || true
                # Create a launcher script in venv (unquoted heredoc so $PYTHON_BIN expands)
                cat > "$VENV_DIR/bin/pip" << PIP_EOF
#!/bin/sh
exec $PYTHON_BIN -m pip "\$@"
PIP_EOF
                chmod +x "$VENV_DIR/bin/pip"
            else
                error_exit "Cannot bootstrap pip. Please install python3.11-pip manually."
            fi
        fi
    fi

    PIP_BIN="$VENV_DIR/bin/pip"
    log "pip ready: $PIP_BIN"
}

fix_venv

# ============================================================
# Step 3: Auto fix requirements.txt encoding
# ============================================================
log "=== Step 3: Fixing requirements.txt encoding ==="

if [ -f "$BOT_DIR/requirements.txt" ]; then
    if head -c3 "$BOT_DIR/requirements.txt" | od -An -tx1 2>/dev/null | grep -q "efbbbf"; then
        log "Removing BOM from requirements.txt..."
        sed -i '1s/^\xEF\xBB\xBF//' "$BOT_DIR/requirements.txt"
    fi
    sed -i 's/\r$//' "$BOT_DIR/requirements.txt"
    log "requirements.txt encoding fixed"
fi

# ============================================================
# Step 4: Auto install Python dependencies
# ============================================================
log "=== Step 4: Installing Python dependencies ==="

if [ ! -f "$BOT_DIR/requirements.txt" ]; then
    error_exit "requirements.txt not found at $BOT_DIR/"
fi

log "Installing packages (this may take a few minutes)..."
"$PIP_BIN" install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || true
"$PIP_BIN" install -r "$BOT_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || {
    warn "Some packages failed to install, trying individually..."
    while IFS= read -r line; do
        pkg=$(echo "$line" | sed 's/[>=<].*//' | tr -d ' ')
        [ -z "$pkg" ] && continue
        "$PIP_BIN" install "$line" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || warn "Failed to install $pkg"
    done < "$BOT_DIR/requirements.txt"
}

# ============================================================
# Step 5: Auto verify core packages
# ============================================================
log "=== Step 5: Verifying core packages ==="

VERIFY_CMD='import fastapi, uvicorn, telethon, aiosqlite, jieba, loguru, dotenv; print("Core packages OK")'
if "$VENV_DIR/bin/python" -c "$VERIFY_CMD"; then
    log "Core packages verified successfully"
else
    warn "Some core packages failed, attempting individual installs..."
    for pkg in fastapi telethon aiosqlite jieba loguru dotenv uvicorn; do
        if ! "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null; then
            log "Missing: $pkg — installing..."
            "$PIP_BIN" install "$pkg" -i https://pypi.tuna.tsinghua.edu.cn/simple 2>>"$LOG_FILE" || warn "Failed to install $pkg"
        fi
    done
    "$VENV_DIR/bin/python" -c "$VERIFY_CMD" || error_exit "Core package verification failed"
fi

# ============================================================
# Step 6: Auto check .env configuration
# ============================================================
log "=== Step 6: Checking .env configuration ==="

if [ ! -f "$BOT_DIR/.env" ] || [ ! -s "$BOT_DIR/.env" ]; then
    if [ -f "$BOT_DIR/.env.example" ]; then
        cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
        log "Created .env from .env.example"
    fi
fi

if grep -q "YOUR_BOT_TOKEN_HERE" "$BOT_DIR/.env" 2>/dev/null; then
    warn "⚠️  TG_BOT_TOKEN is not configured! Edit .env before starting."
    log "Run: vim $BOT_DIR/.env"
fi

if grep -q "YOUR_API_ID_HERE" "$BOT_DIR/.env" 2>/dev/null; then
    warn "⚠️  TELETHON_API_IDS is not configured!"
fi

# ============================================================
# Step 7: Auto create Systemd service
# ============================================================
log "=== Step 7: Creating Systemd service ==="

SERVICE_FILE="/etc/systemd/system/tg-search-bot.service"

cat > "$SERVICE_FILE" << 'SVCEOF'
[Unit]
Description=TG Search Bot Service v1.0.5
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
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SVCEOF

ADMIN_SERVICE_FILE="/etc/systemd/system/tg-search-admin.service"

cat > "$ADMIN_SERVICE_FILE" << 'SVCEOF'
[Unit]
Description=TG Search Admin Panel (FastAPI + Uvicorn) v1.0.5
After=network.target tg-search-bot.service
Wants=tg-search-bot.service

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/tg-search-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/www/wwwroot/tg-search-bot/venv/bin/python -u server.py
Restart=always
RestartSec=5
StandardOutput=append:/www/wwwroot/tg-search-bot/logs/admin_stdout.log
StandardError=append:/www/wwwroot/tg-search-bot/logs/admin_stderr.log
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
log "Systemd services created: tg-search-bot.service + tg-search-admin.service"

# ============================================================
# Step 8: Auto start services
# ============================================================
log "=== Step 8: Starting TG Search Bot + Admin Panel ==="

systemctl restart tg-search-bot
systemctl restart tg-search-admin
sleep 3

if systemctl is-active --quiet tg-search-bot; then
    log "✅ TG Search Bot is running!"
else
    warn "Bot service failed to start, checking logs..."
    systemctl status tg-search-bot --no-pager | tail -20
fi

if systemctl is-active --quiet tg-search-admin; then
    log "✅ Admin Panel is running!"
else
    warn "Admin service failed to start, checking logs..."
    systemctl status tg-search-admin --no-pager | tail -20
fi

log "   Service:  tg-search-bot (Bot polling)"
log "   Admin:    tg-search-admin (FastAPI + Uvicorn :$PORT)"
log "   Port:     $PORT"
log "   Admin:    http://YOUR_SERVER_IP:$PORT/admin"
log "   Logs:     tail -f $BOT_DIR/logs/stderr.log"
log "   Admin:    tail -f $BOT_DIR/logs/admin_stderr.log"

# ============================================================
# Step 9: Nginx reverse proxy (BT Panel)
# ============================================================
log "=== Step 9: Nginx reverse proxy configuration ==="

check_bt_nginx() {
    if [ -d "$BT_NGINX_DIR" ] && [ -w "$BT_NGINX_DIR" ]; then
        return 0
    fi
    return 1
}

if check_bt_nginx; then
    # Check if any reverse proxy already exists for port $PORT
    local_proxy_found=false
    for conf in "$BT_NGINX_DIR"/*.conf; do
        if grep -q "127.0.0.1:$PORT" "$conf" 2>/dev/null; then
            local_proxy_found=true
            break
        fi
    done

    if [ "$local_proxy_found" = false ]; then
        warn "⚠️  Nginx reverse proxy not found!"
        log "BT Panel detected. Please configure reverse proxy manually:"
        log "  BT Panel → Website → Your Site → Reverse Proxy → Add"
        log "  Proxy Name: tg_search_bot"
        log "  Target URL: http://127.0.0.1:$PORT"
        log "  Send Domain: \$host"
        log ""
        log "  Custom headers to add:"
        log "    Host \$host"
        log "    X-Real-IP \$remote_addr"
        log "    X-Forwarded-For \$proxy_add_x_forwarded_for"
        log "    X-Forwarded-Proto \$scheme"
        log "    Upgrade \$http_upgrade"
        log "    Connection \"upgrade\""
        log "  Timeouts: 300s each"
    else
        log "Nginx reverse proxy already configured"
    fi
else
    warn "⚠️  BT Panel Nginx directory not found at $BT_NGINX_DIR"
    log "Please configure Nginx reverse proxy manually:"
    log "  Add to your Nginx site config:"
    log ""
    log "  location / {"
    log "      proxy_pass http://127.0.0.1:$PORT;"
    log "      proxy_http_version 1.1;"
    log "      proxy_set_header Host \$host;"
    log "      proxy_set_header X-Real-IP \$remote_addr;"
    log "      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;"
    log "      proxy_set_header X-Forwarded-Proto \$scheme;"
    log "      proxy_set_header Upgrade \$http_upgrade;"
    log "      proxy_set_header Connection \"upgrade\";"
    log "      proxy_read_timeout 300s;"
    log "      proxy_send_timeout 300s;"
    log "  }"
fi

# ============================================================
# Step 10: Firewall check
# ============================================================
log "=== Step 10: Firewall check ==="

if command -v ufw &>/dev/null; then
    ufw status 2>/dev/null | grep -q "$PORT" || {
        warn "⚠️  Port $PORT not open in UFW firewall"
        log "Run: ufw allow $PORT"
    }
fi

if command -v firewall-cmd &>/dev/null; then
    firewall-cmd --query-port=$PORT/tcp 2>/dev/null || {
        warn "⚠️  Port $PORT not open in firewalld"
        log "Run: firewall-cmd --add-port=$PORT/tcp --permanent && firewall-cmd --reload"
    }
fi

# ============================================================
# Done
# ============================================================
log ""
log "============================================================"
log "  TG Search Bot v1.0.5 Installation Complete!"
log "============================================================"
log ""
log "  Service Status:"
systemctl is-active tg-search-bot
log ""
log "  Quick Links:"
log "    Admin Panel:  http://YOUR_SERVER_IP:$PORT/admin"
log "    Logs:         tail -f $BOT_DIR/logs/stderr.log"
log ""
log "  Next Steps:"
log "    1. cp .env.example .env && 只填 BOT_TOKEN + HD_WALLET_MNEMONIC"
log "    2. 后台添加采集账号: http://YOUR_SERVER_IP:$PORT/admin → 系统配置 → 采集账号池"
log "    3. 账号保存后自动加载,无需重启服务"
log "    4. 宝塔面板配置 Nginx 反代 (127.0.0.1:$PORT)"
log "    5. 申请 SSL 证书"
log ""
log "  Installation log: $LOG_FILE"
log ""
