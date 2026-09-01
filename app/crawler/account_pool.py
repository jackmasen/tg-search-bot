"""
Telethon账号池管理
负责账号轮换、风控控制、会话复用
支持从数据库 crawler_accounts 表加载账号
"""
import asyncio
import os
import time
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from loguru import logger
from app.config import Config


class AccountPool:
    """账号池：管理多个Telethon客户端，轮换使用"""

    def __init__(self):
        self.clients: list[TelegramClient] = []
        self.account_stats: dict = {}  # 账号当日join次数统计
        self.last_join_time: dict = {}  # 账号上次join时间戳
        self.lock = asyncio.Lock()
        self._round_robin_index = 0
        self._db_loaded = False

    async def initialize(self):
        """初始化所有账号客户端（优先从DB加载，回退到环境变量）"""
        os.makedirs(Config.SESSION_DIR, exist_ok=True)

        # 尝试从数据库加载
        db_accounts = await self._load_accounts_from_db()
        if db_accounts:
            logger.info(f"从数据库加载到 {len(db_accounts)} 个采集账号")
            pool = db_accounts
            self._db_loaded = True
        else:
            # 回退到环境变量
            pool = Config.get_account_pool()
            logger.info(f"数据库无账号，回退到环境变量配置，共 {len(pool)} 个账号")

        await self._connect_clients(pool)

        logger.info(f"账号池就绪: {len(self.clients)} 个账号可用")

    async def reload_from_db(self):
        """从数据库重新加载账号池（后台添加账号后调用）"""
        os.makedirs(Config.SESSION_DIR, exist_ok=True)
        db_accounts = await self._load_accounts_from_db()
        if not db_accounts:
            logger.warning("数据库无账号，保持现有账号池不变")
            return False

        logger.info(f"从数据库重新加载 {len(db_accounts)} 个采集账号，正在重建连接...")
        await self._connect_clients(db_accounts)
        self._db_loaded = True
        return True

    async def _connect_clients(self, pool):
        """连接所有账号客户端"""
        old_clients = self.clients
        self.clients = []
        self.account_stats = {}
        self.last_join_time = {}
        self._round_robin_index = 0

        for i, acc in enumerate(pool):
            phone = acc.get("phone", f"account_{i+1}")
            session_name = acc.get("session_name", f"account_{i+1}")
            api_id = acc.get("api_id")
            api_hash = acc.get("api_hash")
            session_file = acc.get("session_file")

            if not api_id or not api_hash:
                logger.warning(f"账号 {phone} 缺少 api_id 或 api_hash，跳过")
                continue

            session_path = os.path.join(Config.SESSION_DIR, session_name)

            # 优先使用已保存的 session 文件
            if session_file:
                session_path = os.path.join(Config.SESSION_DIR, os.path.basename(session_file))

            proxy = None
            proxy_mode = acc.get("proxy_mode", "none")
            if proxy_mode and proxy_mode not in ("none", ""):
                proxy_host = acc.get("proxy_host")
                proxy_port = acc.get("proxy_port")
                if proxy_host and proxy_port:
                    try:
                        proxy_port = int(proxy_port)
                    except (ValueError, TypeError):
                        logger.warning(f"账号 {phone} 代理端口无效: {proxy_port}，跳过代理")
                        proxy_port = None
                if proxy_host and proxy_port:
                    proxy_protocol = acc.get("proxy_protocol", "socks5") or "socks5"
                    try:
                        import socks
                        if proxy_protocol == "socks5":
                            proxy = (socks.SOCKS5, proxy_host, proxy_port)
                        elif proxy_protocol in ("http", "http_connect"):
                            proxy = (socks.HTTP, proxy_host, proxy_port)
                        else:
                            proxy = (socks.SOCKS5, proxy_host, proxy_port)
                    except ImportError:
                        logger.warning(f"账号 {phone} 需要 socksio 库支持代理，请运行: pip install socksio")

            client = TelegramClient(
                session_path,
                api_id,
                api_hash,
                proxy=proxy,
            )
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    logger.warning(f"账号 {phone} 未授权，需先登录")
                    await client.disconnect()
                else:
                    logger.success(f"账号 {phone} 连接成功 (session: {session_name})")
                    self.clients.append(client)
                    self.account_stats[len(self.account_stats)] = {
                        "join_count_today": 0,
                        "date": datetime.now().date(),
                    }
                    self.last_join_time[len(self.last_join_time)] = 0
            except Exception as e:
                logger.error(f"账号 {phone} 连接失败: {e}")
                try:
                    await client.disconnect()
                except Exception:
                    pass

    async def _load_accounts_from_db(self):
        """从 crawler_accounts 表加载账号列表，关联 crawler_proxies"""
        try:
            from app.database import get_db
            async with get_db() as db:
                cur = await db.execute(
                    "SELECT a.id, a.phone, a.api_id, a.api_hash, a.session_file, "
                    "a.tg_user_id, a.tg_username, a.status, a.proxy_mode, a.proxy_protocol, "
                    "a.proxy_host, a.proxy_port, a.proxy_username, a.proxy_password, a.proxy_id, "
                    "p.name as proxy_name, p.proxy_host as proxy_host_src, p.proxy_port as proxy_port_src "
                    "FROM crawler_accounts a "
                    "LEFT JOIN crawler_proxies p ON a.proxy_id = p.id "
                    "WHERE a.status IN ('active', 'need_verify') "
                    "ORDER BY a.sort_order ASC, a.id ASC"
                )
                rows = await cur.fetchall()
                if not rows:
                    return []

                accounts = []
                for row in rows:
                    acc = dict(row)
                    session_name = f"account_{acc['id']}"
                    if acc.get("tg_username"):
                        session_name = f"account_{acc['tg_username']}"
                    elif acc.get("phone"):
                        session_name = f"account_{acc['phone']}"

                    # 优先使用独立代理，否则使用账号自带代理配置
                    proxy_host = acc.get("proxy_host_src") or acc.get("proxy_host")
                    proxy_port = acc.get("proxy_port_src") or acc.get("proxy_port")
                    proxy_mode = acc.get("proxy_mode", "system")
                    if proxy_mode == "custom" and proxy_host:
                        pass  # 使用独立代理
                    elif not proxy_host:
                        proxy_mode = "system"
                        proxy_port = None

                    accounts.append({
                        "id": acc["id"],
                        "phone": acc.get("phone", f"account_{acc['id']}"),
                        "api_id": acc.get("api_id"),
                        "api_hash": acc.get("api_hash"),
                        "session_name": session_name,
                        "session_file": acc.get("session_file"),
                        "tg_user_id": acc.get("tg_user_id"),
                        "tg_username": acc.get("tg_username"),
                        "status": acc.get("status", "active"),
                        "proxy_mode": proxy_mode,
                        "proxy_protocol": acc.get("proxy_protocol", "http"),
                        "proxy_host": proxy_host,
                        "proxy_port": proxy_port,
                        "proxy_username": acc.get("proxy_username") or acc.get("proxy_username"),
                        "proxy_password": acc.get("proxy_password"),
                        "proxy_name": acc.get("proxy_name"),
                    })
                return accounts
        except Exception as e:
            logger.warning(f"从数据库加载账号失败: {e}，回退到环境变量")
            return []

    async def get_available_account(self) -> tuple:
        """
        轮询获取可用账号
        返回: (account_index, client)
        筛选条件: 当日join未超限、间隔足够
        """
        async with self.lock:
            if not self.clients:
                logger.warning("账号池为空，请先添加采集账号")
                await asyncio.sleep(5)
                return await self.get_available_account()

            today = datetime.now().date()
            for _ in range(len(self.clients)):
                idx = self._round_robin_index % len(self.clients)
                self._round_robin_index += 1

                # 重置每日计数
                stats = self.account_stats.get(idx, {})
                if stats.get("date") != today:
                    self.account_stats[idx] = {"join_count_today": 0, "date": today}

                # 检查每日上限
                if self.account_stats[idx]["join_count_today"] >= Config.MAX_JOIN_PER_DAY:
                    continue

                # 检查间隔
                if time.time() - self.last_join_time.get(idx, 0) < Config.JOIN_INTERVAL_SECONDS:
                    continue

                return idx, self.clients[idx]

            # 全部不可用，等待
            logger.warning("所有账号均不可用，等待60秒后重试")
            await asyncio.sleep(60)
            return await self.get_available_account()

    async def record_join(self, account_index: int):
        """记录一次join操作，用于风控统计"""
        async with self.lock:
            if account_index not in self.account_stats:
                self.account_stats[account_index] = {"join_count_today": 0, "date": datetime.now().date()}
            self.account_stats[account_index]["join_count_today"] += 1
            self.last_join_time[account_index] = time.time()
            logger.debug(
                f"账号 {account_index+1} 今日join次数: "
                f"{self.account_stats[account_index]['join_count_today']}/{Config.MAX_JOIN_PER_DAY}"
            )

    async def handle_flood_wait(self, account_index: int, seconds: int):
        """处理FloodWait限频"""
        logger.warning(f"账号 {account_index+1} 触发限频，等待 {seconds} 秒")
        # 标记该账号今日不可用
        self.account_stats[account_index]["join_count_today"] = Config.MAX_JOIN_PER_DAY
        await asyncio.sleep(seconds + 5)

    async def disconnect_all(self):
        """关闭所有客户端"""
        for client in self.clients:
            await client.disconnect()
        logger.info("所有账号已断开")


# 全局账号池实例
account_pool = AccountPool()


async def get_all_accounts():
    """查询所有采集账号（供后台管理页面使用）"""
    from app.database import get_db
    try:
        async with get_db() as db:
            cur = await db.execute(
                "SELECT id, phone, api_id, api_hash, session_file, tg_user_id, tg_username, "
                "status, health_score, joined_channels, join_today, search_today, "
                "proxy_mode, proxy_host, proxy_port, created_at "
                "FROM crawler_accounts ORDER BY sort_order ASC, id ASC"
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"查询账号池失败: {e}")
        return []


async def add_crawler_account(phone: str, api_id: int, api_hash: str, proxy_mode: str = "system",
                               proxy_host: str = None, proxy_port: int = None) -> dict:
    """从后台添加/更新采集账号（upsert）"""
    from app.database import get_db
    try:
        async with get_db() as db:
            cur = await db.execute("SELECT id FROM crawler_accounts WHERE phone=?", (phone,))
            existing = cur.fetchone()
            if existing:
                await db.execute(
                    "UPDATE crawler_accounts SET api_id=?, api_hash=? WHERE phone=?",
                    (api_id, api_hash, phone)
                )
                logger.info(f"后台更新采集账号: {phone}")
                return {"ok": True, "phone": phone, "id": existing[0], "action": "updated"}
            else:
                cur2 = await db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM crawler_accounts")
                max_sort = cur2.fetchone()[0]
                await db.execute(
                    """INSERT INTO crawler_accounts
                       (phone, api_id, api_hash, status, health_score, sort_order, created_at)
                       VALUES (?, ?, ?, 'active', 100, ?, ?)""",
                    (phone, api_id, api_hash, max_sort + 1, datetime.now().isoformat())
                )
                logger.info(f"后台添加采集账号: {phone}")
                return {"ok": True, "phone": phone, "id": cur.lastrowid, "action": "inserted"}
    except Exception as e:
        logger.error(f"添加账号失败: {e}")
        return {"ok": False, "error": str(e)}


async def delete_crawler_account(account_id: int) -> dict:
    """从后台删除采集账号"""
    from app.database import get_db
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM crawler_accounts WHERE id=?", (account_id,))
            await db.commit()
            logger.info(f"后台删除采集账号 id={account_id}")
            return {"ok": True}
    except Exception as e:
        logger.error(f"删除账号失败: {e}")
        return {"ok": False, "error": str(e)}
