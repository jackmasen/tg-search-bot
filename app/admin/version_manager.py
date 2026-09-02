"""
版本更新管理器
- 检查新版本
- 一键更新（先备份→拉取→重启）
- 回滚到指定版本
"""
import os
import subprocess
import asyncio
from datetime import datetime
from loguru import logger
from app.config import Config
from app.database import get_db
from app.admin.backup_manager import backup_manager


class VersionManager:
    """版本管理器"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    async def get_current_version(self) -> str:
        """获取当前版本号"""
        return Config.APP_VERSION

    async def check_update(self) -> dict:
        """
        检查是否有新版本
        通过git fetch + 比较commit实现
        返回: {has_update, latest_commit, current_commit, new_files}
        """
        if not Config.VERSION_REPO_URL:
            return {"has_update": False, "reason": "未配置Git仓库地址"}
        self._ensure_git_safe()
        try:
            # git fetch（不合并）
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.project_root,
                capture_output=True,
                timeout=60,
            )

            # 比较本地与远程
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..origin/main"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            behind_count = int(result.stdout.strip()) if result.stdout.strip() else 0

            # 获取远程最新commit信息
            result = subprocess.run(
                ["git", "log", "origin/main", "-1", "--format=%H|%s|%ci"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            latest_info = result.stdout.strip().split("|") if result.stdout.strip() else []

            return {
                "has_update": behind_count > 0,
                "current_version": Config.APP_VERSION,
                "behind_commits": behind_count,
                "latest_commit": latest_info[0] if len(latest_info) > 0 else "",
                "latest_message": latest_info[1] if len(latest_info) > 1 else "",
                "latest_date": latest_info[2] if len(latest_info) > 2 else "",
            }
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            return {"has_update": False, "reason": str(e)}

    async def perform_update(self, auto_rollback: bool = True) -> dict:
        """
        执行更新
        流程：备份 → 记录当前版本 → git pull → 记录新版本 → 失败则回滚
        返回: {success, old_version, new_version, backup_id}
        """
        # 1. 更新前自动备份
        logger.info("更新前自动备份数据库...")
        backup_result = await backup_manager.create_backup(
            backup_type="pre_update",
            notes=f"更新前自动备份，旧版本 {Config.APP_VERSION}"
        )
        backup_id = backup_result["backup_id"]
        old_version = Config.APP_VERSION

        # 2. 记录旧版本
        async with get_db() as db:
            await db.execute(
                """INSERT INTO app_versions (version, status, notes) VALUES (?, 'active', ?)""",
                (old_version, f"更新前版本"),
            )
            await db.commit()

        # 3. 执行git pull（自动处理本地未提交修改）
        self._ensure_git_safe()
        try:
            # 先 stash 本地未提交的修改
            subprocess.run(
                ["git", "stash", "push", "-m", f"pre_update_stash_{datetime.now().strftime('%Y%m%d%H%M%S')}"],
                cwd=self.project_root,
                capture_output=True,
                timeout=30,
            )

            result = subprocess.run(
                ["git", "pull", "--autostash", "origin", "main"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                # pull 失败，尝试硬重置到远端
                logger.warning("git pull 失败，尝试 git reset --hard origin/main...")
                reset_result = subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if reset_result.returncode != 0:
                    logger.error(f"git reset 也失败: {reset_result.stderr}")
                    if auto_rollback:
                        await self._auto_rollback(backup_id, "git pull失败")
                    return {"success": False, "error": result.stderr, "backup_id": backup_id}

            # 4. 安装新依赖
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # 5. 读取新版本号
            new_version = self._read_version_from_file()

            # 6. 记录新版本
            async with get_db() as db:
                # 旧版本标记为已替换
                await db.execute(
                    "UPDATE app_versions SET status='replaced' WHERE version=? AND status='active'",
                    (old_version,),
                )
                # 插入新版本记录
                await db.execute(
                    """INSERT INTO app_versions (version, status, notes) VALUES (?, 'active', '更新成功')""",
                    (new_version,),
                )
                await db.commit()

            logger.success(f"更新成功: {old_version} → {new_version}")
            return {
                "success": True,
                "old_version": old_version,
                "new_version": new_version,
                "backup_id": backup_id,
                "need_restart": True,
            }

        except Exception as e:
            logger.error(f"更新过程异常: {e}")
            if auto_rollback:
                await self._auto_rollback(backup_id, str(e))
            return {"success": False, "error": str(e), "backup_id": backup_id}

    async def _auto_rollback(self, backup_id: int, reason: str):
        """更新失败后自动回滚"""
        logger.warning(f"更新失败，自动回滚到备份 {backup_id}，原因：{reason}")
        try:
            result = await backup_manager.restore_backup(backup_id)
            # 记录回滚
            async with get_db() as db:
                await db.execute(
                    """UPDATE app_versions SET status='rolled_back', rollback_to=?, notes=?
                    WHERE version=?""",
                    (Config.APP_VERSION, f"自动回滚: {reason}", Config.APP_VERSION),
                )
                await db.commit()
            logger.success("自动回滚完成")
        except Exception as e:
            logger.error(f"自动回滚失败: {e}，需要手动恢复备份 {backup_id}")

    def _ensure_git_safe(self):
        """确保 git 认为当前目录是安全的（解决 root 用户 git 报错）"""
        subprocess.run(
            ["git", "config", "--global", "--add", "safe.directory", self.project_root],
            capture_output=True,
        )

    def _read_version_from_file(self) -> str:
        """从config.py读取最新版本号"""
        try:
            # 重新加载config模块读取版本
            import importlib
            import app.config
            importlib.reload(app.config)
            return app.config.Config.APP_VERSION
        except Exception:
            return Config.APP_VERSION

    async def get_version_history(self, limit: int = 10) -> list:
        """获取版本更新历史"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT version, commit_hash, updated_at, status, rollback_to, notes
                FROM app_versions ORDER BY updated_at DESC LIMIT ?""",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# 全局实例
version_manager = VersionManager()
