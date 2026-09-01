"""
数据库备份与回滚管理器
- 自动定时备份
- 更新前自动备份
- 一键回滚到指定备份
"""
import os
import shutil
import sqlite3
import asyncio
from datetime import datetime
from loguru import logger
from app.config import Config
from app.database import get_db


class BackupManager:
    """备份管理器"""

    def __init__(self):
        self.backup_dir = Config.BACKUP_DIR
        os.makedirs(self.backup_dir, exist_ok=True)

    async def create_backup(self, backup_type: str = "manual", notes: str = "") -> dict:
        """
        创建数据库备份
        backup_type: auto / manual / pre_update
        返回: {backup_path, file_size, backup_id}
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = Config.APP_VERSION
        backup_filename = f"backup_{version}_{timestamp}_{backup_type}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        # 记录备份前版本
        version_before = Config.APP_VERSION

        # 先执行WAL checkpoint，将WAL数据写入主数据库文件
        async with get_db() as db:
            await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            await db.commit()

        # 短暂等待确保文件写入完成
        await asyncio.sleep(0.5)

        # 直接复制数据库文件（避免sqlite3模块与aiosqlite的连接冲突）
        try:
            shutil.copy2(Config.DB_PATH, backup_path)
            file_size = os.path.getsize(backup_path)
            logger.success(f"数据库备份成功: {backup_filename} ({file_size/1024:.1f}KB)")
        except Exception as e:
            logger.error(f"备份失败: {e}")
            raise

        # 备份会话文件目录（可选，避免账号失效）
        sessions_dir = Config.SESSION_DIR
        if os.path.exists(sessions_dir):
            sessions_backup = os.path.join(self.backup_dir, f"sessions_{timestamp}")
            shutil.copytree(sessions_dir, sessions_backup, dirs_exist_ok=True)

        # 记录到数据库
        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO backups (backup_path, backup_type, file_size, version_before, notes)
                VALUES (?,?,?,?,?)""",
                (backup_path, backup_type, file_size, version_before, notes),
            )
            await db.commit()
            backup_id = cursor.lastrowid

        # 清理旧备份，只保留最近N份
        await self._cleanup_old_backups()

        return {
            "backup_id": backup_id,
            "backup_path": backup_path,
            "file_size": file_size,
            "version_before": version_before,
        }

    async def _cleanup_old_backups(self):
        """清理旧备份，保留最近 BACKUP_KEEP_COUNT 份"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT id, backup_path FROM backups
                WHERE status='available'
                ORDER BY created_at DESC
                LIMIT -1 OFFSET ?""",
                (Config.BACKUP_KEEP_COUNT,),
            )
            old_backups = await cursor.fetchall()

            for row in old_backups:
                # 删除备份文件
                if os.path.exists(row["backup_path"]):
                    os.remove(row["backup_path"])
                # 标记为已清理
                await db.execute(
                    "UPDATE backups SET status='cleaned' WHERE id=?",
                    (row["id"],),
                )
            await db.commit()

            if old_backups:
                logger.info(f"已清理 {len(old_backups)} 份旧备份")

    async def list_backups(self, limit: int = 20) -> list:
        """列出可用备份"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT id, backup_path, backup_type, file_size, version_before, created_at, status
                FROM backups WHERE status='available'
                ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def restore_backup(self, backup_id: int) -> dict:
        """
        回滚到指定备份
        流程：先备份当前 → 用旧备份覆盖当前 → 标记备份状态
        返回: {success, restored_from, new_backup_id}
        """
        # 1. 先备份当前数据库（回滚前的状态，防止误操作）
        pre_rollback = await self.create_backup(backup_type="pre_rollback", notes=f"回滚前自动备份，目标回滚到ID={backup_id}")

        # 2. 获取目标备份信息
        async with get_db() as db:
            cursor = await db.execute("SELECT backup_path, version_before FROM backups WHERE id=?", (backup_id,))
            target = await cursor.fetchone()
            if not target:
                raise ValueError(f"备份ID {backup_id} 不存在")
            target_path = target["backup_path"]
            target_version = target["version_before"]

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"备份文件不存在: {target_path}")

        # 3. 关闭数据库连接，覆盖文件
        # 注意：需要在无连接状态下操作
        await asyncio.sleep(2)  # 等待连接释放

        # 用备份覆盖当前数据库
        shutil.copy2(target_path, Config.DB_PATH)
        logger.success(f"数据库已回滚到备份 {backup_id}（版本 {target_version}）")

        # 4. 更新备份状态
        async with get_db() as db:
            await db.execute(
                "UPDATE backups SET status='restored' WHERE id=?",
                (backup_id,),
            )
            await db.commit()

        return {
            "success": True,
            "restored_from": backup_id,
            "restored_version": target_version,
            "new_backup_id": pre_rollback["backup_id"],
        }


# 全局实例
backup_manager = BackupManager()
