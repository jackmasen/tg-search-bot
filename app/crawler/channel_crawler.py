"""
频道采集器
负责加入频道、拉取历史消息、入库
"""
import hashlib
import asyncio
from datetime import datetime
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, ChannelPrivateError
from loguru import logger
from app.crawler.account_pool import account_pool
from app.database import get_db


class ChannelCrawler:
    """频道采集器"""

    async def add_channel(self, username: str, title: str = "", tg_channel_id: int = None):
        """新增频道到数据库"""
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO channels (username, title, tg_channel_id, crawl_status) VALUES (?,?,?, 'pending')",
                (username.lstrip("@"), title, tg_channel_id),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_pending_channels(self, limit: int = 50):
        """获取待采集的频道列表"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT id, username, title FROM channels WHERE crawl_status='pending' LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def join_and_crawl(self, channel_id: int, username: str):
        """加入频道并拉取历史消息"""
        account_index, client = await account_pool.get_available_account()

        try:
            # 加入公开频道
            if not username.startswith("@"):
                username = "@" + username

            await client(JoinChannelRequest(username))
            await account_pool.record_join(account_index)
            logger.info(f"账号 {account_index+1} 已加入频道 {username}")

            # 更新频道状态
            async with get_db() as db:
                await db.execute(
                    "UPDATE channels SET crawl_status='joined', assigned_account=?, last_crawled_at=? WHERE id=?",
                    (f"account_{account_index+1}", datetime.now(), channel_id),
                )
                await db.commit()

            # 拉取历史消息
            await self._fetch_history(client, channel_id, username)

        except FloodWaitError as e:
            await account_pool.handle_flood_wait(account_index, e.seconds)
        except ChannelPrivateError:
            logger.warning(f"频道 {username} 是私密频道，需邀请链接")
            async with get_db() as db:
                await db.execute(
                    "UPDATE channels SET crawl_status='error' WHERE id=?",
                    (channel_id,),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"加入频道 {username} 失败: {e}")

    async def _fetch_history(self, client, channel_id: int, username: str):
        """拉取频道历史消息（分页拉取，最多500条）"""
        try:
            entity = await client.get_entity(username)
            limit = 500  # 单频道历史拉取上限
            batch_size = 100

            messages = await client.get_messages(entity, limit=limit)
            count = 0
            async with get_db() as db:
                for msg in messages:
                    if not msg.text:
                        continue  # 跳过非文本消息
                    content_hash = hashlib.md5(msg.text.encode()).hexdigest()
                    try:
                        await db.execute(
                            """INSERT OR IGNORE INTO messages
                            (channel_id, tg_msg_id, content, msg_date, content_hash)
                            VALUES (?,?,?,?,?)""",
                            (channel_id, msg.id, msg.text, msg.date, content_hash),
                        )
                        count += 1
                    except Exception:
                        continue
                await db.commit()

            logger.success(f"频道 {username} 历史消息入库: {count} 条")
        except Exception as e:
            logger.error(f"拉取频道 {username} 历史失败: {e}")

    async def crawl_batch(self, batch_size: int = 20):
        """批量采集待处理频道（供定时任务调用）"""
        channels = await self.get_pending_channels(batch_size)
        if not channels:
            logger.info("无待采集频道")
            return

        logger.info(f"开始批量采集: {len(channels)} 个频道")
        for ch in channels:
            await self.join_and_crawl(ch["id"], ch["username"])
            # 频道间间隔
            await asyncio.sleep(5)


# 全局实例
channel_crawler = ChannelCrawler()
