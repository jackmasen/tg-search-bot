#!/bin/bash
set -e
cd /www/wwwroot/tg-search-bot

echo "===== 1. 配置 Git Safe Directory ====="
git config --global --add safe.directory /www/wwwroot/tg-search-bot
git remote add origin https://github.com/jackmasen/tg-search-bot.git 2>/dev/null || true
echo "Git 配置完成"

echo ""
echo "===== 2. 拉取最新代码 ====="
git fetch origin main
git pull origin main --force
echo "代码已更新"

echo ""
echo "===== 3. 检查 TELETHON 配置 ====="
sqlite3 data/tg_search.db "SELECT key, length(value) as len FROM system_settings WHERE key IN ('TELETHON_API_IDS','TELETHON_API_HASHS','TELETHON_PHONES');"

echo ""
echo "===== 4. 调用 fix_telethon_config 修复配置 ====="
TOKEN=$(curl -s -X POST http://127.0.0.1:8001/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
  curl -s -X POST "http://127.0.0.1:8001/api/admin/ops/fix_telethon_config?session_id=$TOKEN" \
    -H "Content-Type: application/json" | python3 -m json.tool
  echo "修复完成"
else
  echo "自动登录失败，请手动在后台点击【🔧 修复账号池配置】"
fi

echo ""
echo "===== 5. 重启服务 ====="
systemctl restart tg-search-admin tg-search-bot
sleep 3
systemctl is-active tg-search-admin tg-search-bot
echo ""
echo "===== 6. Bot 最近日志 ====="
journalctl -u tg-search-bot --no-pager -n 15

echo ""
echo "===== 完成 ====="
echo "如果 Bot 显示 active，说明修复成功。"
echo "请在浏览器打开后台：http://186.244.251.12:8001/admin"
echo "点击【系统升级维护】→【运维工具】，验证三个按钮是否正常。"
