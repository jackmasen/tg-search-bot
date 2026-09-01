#!/bin/bash
# ============================================================
# 脚本：手动创建数据库备份
# 宝塔: cd /www/wwwroot/tg-search-bot && source venv/bin/activate && bash scripts/manual_backup.sh "备份说明"
# Docker: docker compose run backup  或  docker compose exec bot bash scripts/manual_backup.sh "备注"
# ============================================================

set -e

BACKUP_NOTE="${1:-手动备份}"

echo "=========================================="
echo " 创建备份: $BACKUP_NOTE"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

$PYTHON << PYEOF
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

async def main():
    from app.admin.backup_manager import backup_manager
    
    print("执行 WAL Checkpoint...")
    result = await backup_manager.create_backup('manual', "$BACKUP_NOTE")
    
    if result["success"]:
        print(f"\n✅ 备份成功!")
        print(f"   备份ID: {result['backup_id']}")
        print(f"   文件路径: {result['file_path']}")
        print(f"   文件大小: {result.get('file_size_mb', 0):.2f} MB")
        print(f"   备份说明: {result['note']}")
    else:
        print(f"\n❌ 备份失败: {result.get('error')}")
        sys.exit(1)

asyncio.run(main())
PYEOF

echo ""
echo "当前备份列表:"
$PYTHON << 'PYEOF'
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
async def main():
    from app.admin.backup_manager import backup_manager
    backups = await backup_manager.list_backups(limit=5)
    if backups:
        print(f"{'ID':<40} {'时间':<20} {'大小':<10} {'说明'}")
        print("-" * 80)
        for b in backups:
            print(f"{b['id']:<40} {b['created_at']:<20} {b.get('file_size_mb',0):<10.2f} {b.get('note','')}")
asyncio.run(main())
PYEOF
