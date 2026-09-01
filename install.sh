#!/bin/bash
# TG Search Bot v1.0.5 - Auto Install Script
# Self-healing: auto detect → auto fix → auto install → auto start
set -e

BOT_DIR="/www/wwwroot/tg-search-bot"
VENV_DIR="$BOT_DIR/venv"
LOG_FILE="$BOT_DIR/logs/install_$(date +%Y%m%d_%H%M%S).log"
PYTHON_BIN=""
PIP_BIN=""

mkdir -p "$BOT_DIR/logs"

log() {
    local msg="[$(date '+%H:%M:%S')] $*"
    echo -e "\033[32m$msg\033[0m"
    echo "$msg" >> "$LOG_FILE"
}

warn() {
    echo -e "\033[33m$*\033[0m"
}

error_exit() {
    echo -e "\033[31mERROR: $1\033[0m"
    exit 1
}

# ============================================================
# Step 1: Auto detect Python 3.11
# ============================================================
log "=== Step 1: Detecting Python 3.11 ==="

detect_python() {
    local py_paths=(
        /usr/local/python3.11/bin/python3.11
        /usr/local/python3.11/bin/python
        /usr/bin/python3.11
        /usr/bin/python3
        python3.11
        python3
    )
    for p in "${py_paths[@]}"; do
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

PYTHON_BIN=$(detect_python) || error_exit "Python 3.11 not found. Install it with: apt install python3.11 python3.11-venv python3.11-dev"
log "Python found: $PYTHON_BIN ($(python3.11 --version 2>/dev/null || $PYTHON_BIN --version 2>/dev/null))"

# ============================================================
# Step 2: Auto fix venv (create or rebuild)
# ============================================================
log "=== Step 2: Fixing Python virtual environment ==="

fix_venv() {
    # Remove broken venv
    if [ -d "$VENV_DIR" ]; then
        local is_broken=false
        if [ ! -f "$VENV_DIR/bin/pip" ]; then is_broken=true; fi
        if [ -f "$VENV_DIR/bin/pip" ] && ! "$VENV_DIR/bin/pip" --version &>/dev/null; then is_broken=true; fi
        if [ "$is_broken" = true ]; then
            log "Broken venv detected, rebuilding..."
            rm -rf "$VENV_DIR"
        fi
    fi

    # Create venv
    log "Creating virtual environment at $VENV_DIR ..."
    $PYTHON_BIN -m venv "$VENV_DIR"

    # Check pip works; rebuild via ensurepip if broken
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
# Step 3: Auto fix requirements.txt encoding (BOM removal)
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

# Create log dir early (may not exist yet)
mkdir -p "$BOT_DIR/logs"

# Get base requirements path
if [ -f "$BOT_DIR/requirements.txt" ]; then
    REQ_FILE="$BOT_DIR/requirements.txt"
    log "Using: $REQ_FILE"
else
    error_exit "requirements.txt not found at $BOT_DIR/"
fi

# Install
log "Installing packages (this may take a few minutes)..."
"$PIP_BIN" install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || true
"$PIP_BIN" install -r "$REQ_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || {
    warn "Some packages failed to install. Checking what's missing..."
    # Try installing one by one to find broken ones
    while IFS= read -r line; do
        pkg=$(echo "$line" | sed 's/[>=<].*//' | tr -d ' ')
        [ -z "$pkg" ] && continue
        "$PIP_BIN" install "$line" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>>"$LOG_FILE" || log "Warning: failed to install $pkg"
    done < "$REQ_FILE"
}

# ============================================================
# Step 5: Auto verify core packages
# ============================================================
log "=== Step 5: Verifying core packages ==="

VERIFY_CMD='import fastapi, uvicorn, telethon, aiosqlite, jieba, loguru, dotenv; print("Core packages OK")'
if "$VENV_DIR/bin/python" -c "$VERIFY_CMD"; then
    log "Core packages verified successfully"
else
    warn "Some core packages failed verification, checking which ones..."
    for pkg in fastapi telethon aiosqlite jieba loguru dotenv uvicorn; do
        if ! "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null; then
            log "Missing: $pkg — attempting install..."
            "$PIP_BIN" install "$pkg" -i https://pypi.tuna.tsinghua.edu.cn/simple 2>>"$LOG_FILE" || warn "Failed to install $pkg"
        fi
    done
    "$VENV_DIR/bin/python" -c "$VERIFY_CMD" || error_exit "Core package verification failed"
fi

# ============================================================
# Step 6: Auto check .env and create if missing
# ============================================================
log "=== Step 6: Checking .env configuration ==="

if [ ! -f "$BOT_DIR/.env" ] || [ ! -s "$BOT_DIR/.env" ]; then
    if [ -f "$BOT_DIR/.env.example" ]; then
        cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
        log "Created .env from .env.example — please edit it and fill in your credentials"
    fi
fi

if grep -q "YOUR_BOT_TOKEN_HERE" "$BOT_DIR/.env" 2>/dev/null; then
    warn "⚠️  TG_BOT_TOKEN is not configured! Edit .env before starting the service."
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
mkdir -p "$BOT_DIR/logs"

cat > "$SERVICE_FILE" << 'SVCEOF'
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
# Step 8: Auto start and verify service
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

log "   Service: tg-search-bot (Bot polling)"
log "   Admin:   tg-search-admin (FastAPI + Uvicorn :8001)"
log "   Logs:    tail -f $BOT_DIR/logs/stderr.log"
log "   Admin:   tail -f $BOT_DIR/logs/admin_stderr.log"

log "=== Installation complete ==="
log "Next steps:"
log "  1. cp .env.example .env && 只填 BOT_TOKEN + HD_WALLET_MNEMONIC"
log "  2. 后台添加采集账号: http://YOUR_IP:8001/admin → 系统配置 → 采集账号池"
log "  3. 账号保存后自动加载,无需重启服务"
