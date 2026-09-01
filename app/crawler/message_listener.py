"""
新消息实时监听器
监听已加入频道的实时新消息，增量入库
"""
import hashlib
from datetime import datetime
from telethon import events
from loguru import logger
from app.crawler.account_pool import account_pool
from app.database import get_db


class MessageListener:
    """实时消息监听器"""

    async def start_listening(self):
        """为每个账号客户端注册新消息监听"""
        for idx, client in enumerate(account_pool.clients):
            client.add_event_handler(
                self._on_new_message,
                events.NewMessage(),
            )
            logger.info(f"账号 {idx+1} 新消息监听已启动")

    async def _on_new_message(self, event):
        """新消息回调：入库+更新FTS索引"""
        try:
            msg = event.message
            if not msg.text:
                return

            # 通过chat_id反查频道
            chat_id = event.chat_id
            async with get_db() as db:
                cursor = await db.execute(
                    "SELECT id FROM channels WHERE tg_channel_id=?",
                    (chat_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    return

                channel_id = row["id"]
                content_hash = hashlib.md5(msg.text.encode()).hexdigest()

                await db.execute(
                    """INSERT OR IGNORE INTO messages
                    (channel_id, tg_msg_id, content, msg_date, content_hash)
                    VALUES (?,?,?,?,?)""",
                    (channel_id, msg.id, msg.text, msg.date, content_hash),
                )
                await db.commit()

        except Exception as e:
            logger.error(f"处理新消息失败: {e}")


# 全局实例
message_listener = MessageListener()
