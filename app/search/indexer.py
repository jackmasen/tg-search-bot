"""
搜索索引器
FTS5全文检索 + BM25排序 + 结果格式化
"""
import jieba
from loguru import logger
from app.database import get_db
from app.config import Config


class Searcher:
    """关键词搜索器"""

    @staticmethod
    def _preprocess_keyword(keyword: str) -> str:
        """
        中文关键词预处理：jieba分词 + FTS5查询语法转义
        例如：比特币行情 → 比特币 行情
        """
        # 过滤FTS5特殊字符
        keyword = keyword.replace('"', "").replace("*", "").replace("'", "")
        # jieba分词
        words = jieba.cut_for_search(keyword)
        # 组装FTS5查询：词之间用OR连接，提升召回率
        tokens = [w for w in words if len(w.strip()) > 0]
        if not tokens:
            return f'"{keyword}"'
        # 用 OR 组合
        query = " OR ".join(f'"{w}"' for w in tokens)
        return query

    async def search(self, keyword: str, limit: int = None) -> list:
        """
        执行搜索
        策略：FTS5全文检索 + LIKE后备，取并集去重
        返回: [{channel_title, username, excerpt, score, msg_date}]
        """
        if limit is None:
            limit = Config.SEARCH_RESULT_LIMIT

        fts_query = self._preprocess_keyword(keyword)
        like_pattern = f"%{keyword}%"
        logger.debug(f"关键词 '{keyword}' → FTS查询: {fts_query} | LIKE: {like_pattern}")

        async with get_db() as db:
            # 第一优先：FTS5全文检索
            cursor = await db.execute(
                """
                SELECT
                    m.id AS msg_id,
                    c.title AS channel_title,
                    c.username AS channel_username,
                    snippet(messages_fts, 0, '【', '】', '...', 20) AS excerpt,
                    bm25(messages_fts) AS score,
                    m.msg_date
                FROM messages_fts
                JOIN messages m ON m.id = messages_fts.rowid
                JOIN channels c ON c.id = m.channel_id
                WHERE messages_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_query, limit),
            )
            fts_rows = await cursor.fetchall()
            fts_ids = {row["msg_id"] for row in fts_rows}

            # 第二优先：LIKE后备（补全FTS5中文分词未命中的）
            remaining = limit - len(fts_rows)
            if remaining > 0:
                cursor = await db.execute(
                    """
                    SELECT
                        m.id AS msg_id,
                        c.title AS channel_title,
                        c.username AS channel_username,
                        substr(m.content, 1, 200) AS excerpt,
                        999.0 AS score,
                        m.msg_date
                    FROM messages m
                    JOIN channels c ON c.id = m.channel_id
                    WHERE m.content LIKE ?
                    ORDER BY m.msg_date DESC
                    LIMIT ?
                    """,
                    (like_pattern, remaining),
                )
                like_rows = await cursor.fetchall()
                # 去重：排除FTS5已命中的
                like_rows = [r for r in like_rows if r["msg_id"] not in fts_ids]
            else:
                like_rows = []

            # 合并结果
            results = [dict(row) for row in fts_rows] + [dict(row) for row in like_rows]
            logger.info(f"搜索 '{keyword}' 命中 {len(results)} 条 (FTS5:{len(fts_rows)} + LIKE:{len(like_rows)})")
            return results

    async def get_channel_count(self) -> int:
        """获取已采集频道数"""
        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) AS cnt FROM channels")
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_message_count(self) -> int:
        """获取已索引消息总数"""
        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) AS cnt FROM messages")
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


# 全局实例
searcher = Searcher()
