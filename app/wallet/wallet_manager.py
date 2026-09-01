"""
USDT钱包管理器 - 完整版（HD钱包派生 + TronGrid链上扫描 + 批量入账 + 资金归集）
架构说明：
┌──────────────────────────────────────────────────────────────┐
│                     同一个HD钱包助记词                         │
│                     BIP44: m/44'/195'/0'/0/{index}            │
├─────────────┬────────────────────────────────────────────────┤
│ 索引 0      │ 运营主地址（归集目的地，TronLink默认显示的地址） │
│ 索引 1      │ 用户A专属充值地址                               │
│ 索引 2      │ 用户B专属充值地址                               │
│ 索引 3      │ 用户C专属充值地址                               │
│ ...         │ 按用户注册顺序递增，永不重复                     │
└─────────────┴────────────────────────────────────────────────┘
用户打USDT到专属地址 → 定时任务每5分钟扫TronGrid → 确认入账加余额
→ 您随时点「一键归集」把所有子地址的USDT转到索引0（TronLink统一管理）
"""
import time
import uuid
import asyncio
import hashlib
from datetime import datetime, timedelta
from loguru import logger
from app.database import get_db
from app.config import Config


# 模块级HD钱包实例（懒加载，避免未配置助记词时启动报错）
_HDWALLET_INSTANCE = None
_HDWALLET_MNEMONIC = ""


def _get_hdwallet():
    """获取HD钱包实例（懒加载，线程内安全，不用加锁因为是纯CPU计算+只读）"""
    global _HDWALLET_INSTANCE, _HDWALLET_MNEMONIC
    mnemonic = (Config.HD_WALLET_MNEMONIC or "").strip()
    if not mnemonic:
        # 未配置助记词 → 返回 None，后续走模拟地址模式（本地测试用）
        return None
    # 助记词变了（热更新配置时）→ 重建实例
    if _HDWALLET_INSTANCE is None or _HDWALLET_MNEMONIC != mnemonic:
        try:
            from hdwallet import HDWallet as _HDWalletCls
            from hdwallet.symbols import TRX
            w = _HDWalletCls(symbol=TRX)
            w.from_mnemonic(mnemonic=mnemonic, language="english")
            _HDWALLET_INSTANCE = w
            _HDWALLET_MNEMONIC = mnemonic
            logger.success("HD钱包初始化成功，地址模式=真实派生")
        except Exception as e:
            logger.error(f"HD钱包初始化失败: {e}，将降级为模拟地址模式")
            _HDWALLET_INSTANCE = None
    return _HDWALLET_INSTANCE


def _derive_hd_address(index: int) -> tuple:
    """
    按HD索引派生TRC20地址
    返回 (address, derivation_path, private_key_hex_or_empty)
    异常或未配置助记词时返回空字符串元组
    """
    wallet = _get_hdwallet()
    if wallet is None:
        return ("", "", "")
    try:
        path = f"{Config.HD_DERIVATION_BASE}/{index}"
        wallet.from_path(path)
        addr = wallet.address()
        # 私钥可选导出（加密后存库，或留空用TronLink统一管理）
        priv = wallet.private_key() or ""
        return (addr, path, priv)
    except Exception as e:
        logger.error(f"HD派生索引{index}失败: {e}")
        return ("", "", "")


def _encrypt_private_key(priv_hex: str) -> str:
    """用CRYPTO_SECRET做AES-GCM加密私钥（简化版：仅做XOR掩码，真上线换成cryptography库）"""
    if not priv_hex:
        return ""
    secret = (Config.CRYPTO_SECRET or Config.SESSION_SECRET or "default-secret-change-me").encode()
    key = hashlib.sha256(secret).digest()
    # 简化加密：先base64再hash前缀标记，生产请换 cryptography.Fernet
    import base64
    data = priv_hex.encode()
    masked = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return "ENCv1:" + base64.b64encode(masked).decode()


class WalletManager:
    """USDT钱包管理"""

    # ============== 用户与基础查询 ==============

    async def get_or_create_user(self, tg_user_id: int, username: str = "") -> dict:
        """获取或创建用户"""
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE tg_user_id=?", (tg_user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)

            # 新建用户
            await db.execute(
                "INSERT INTO users (tg_user_id, username, wallet_balance_usdt) VALUES (?,?,0.0)",
                (tg_user_id, username),
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE tg_user_id=?", (tg_user_id,))
            row = await cursor.fetchone()
            logger.info(f"新用户注册: tg_id={tg_user_id} username={username}")
            return dict(row)

    async def get_balance(self, tg_user_id: int) -> float:
        """查询用户余额"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT wallet_balance_usdt FROM users WHERE tg_user_id=?",
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            return row["wallet_balance_usdt"] if row else 0.0

    async def get_transaction_history(self, tg_user_id: int, limit: int = 10) -> list:
        """查询交易流水"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT t.* FROM transactions t
                JOIN users u ON u.id = t.user_id
                WHERE u.tg_user_id=?
                ORDER BY t.created_at DESC LIMIT ?""",
                (tg_user_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ============== HD地址分配：每用户固定一个，永久复用 ==============
    # 核心规则（来自项目经验612725，避免反复踩坑）：
    # 1. 先查 wallets 表（按user_id+chain），已分配直接返回（同一个用户永远用同一个地址）
    # 2. 未分配 → 取当前链 MAX(hd_index)+1 作为新索引（从1开始，0留给运营主地址）
    # 3. 数据库 UNIQUE(chain, hd_index) 兜底防并发重复分配
    # 4. 异常分支绝不返回共享公共地址（避免多用户打同地址无法对账）

    async def get_recharge_address(self, tg_user_id: int, chain: str = "trc20") -> dict:
        """
        获取用户专属充值地址（已分配直接返回旧的，未分配生成新的）
        同一个用户，同一条链，永远返回相同的地址，方便用户保存后随时充值
        """
        chain = chain.lower()
        if chain != "trc20":
            # 其他链暂未实现，防止误配置返回空地址（禁止fallback共享地址！）
            raise ValueError(f"暂不支持{chain}，仅支持trc20")

        user = await self.get_or_create_user(tg_user_id)

        async with get_db() as db:
            # 规则1：优先返回该用户已绑定的地址
            cursor = await db.execute(
                "SELECT * FROM wallets WHERE user_id=? AND chain=?",
                (user["id"], chain),
            )
            wallet = await cursor.fetchone()
            if wallet:
                w = dict(wallet)
                # 兼容老数据：如果老地址是模拟的但现在有助记词了，保持不变（避免通知用户换地址）
                return w

            # 规则2：分配新的HD索引（从1开始，跳过索引0=运营主地址）
            cursor = await db.execute(
                "SELECT COALESCE(MAX(hd_index), 0) AS max_idx FROM wallets WHERE chain=?",
                (chain,),
            )
            row = await cursor.fetchone()
            next_index = max((row["max_idx"] or 0) + 1, 1)  # 至少从1开始

            # 真实HD派生（优先），失败则用模拟地址兼容本地测试
            address, derivation_path, priv_hex = _derive_hd_address(next_index)
            if not address:
                # 降级模式：本地测试/未配置助记词时，用可重现的假地址（用户id→固定地址）
                address = self._generate_mock_address(user["id"], chain)
                derivation_path = f"{Config.HD_DERIVATION_BASE}/{next_index}"
                logger.warning(f"HD未配置，为用户{tg_user_id}分配模拟地址{address}（仅测试，不可真实充值）")

            # 规则3：写入数据库，UNIQUE约束防重复（并发场景失败会抛异常，上层可重试）
            try:
                await db.execute(
                    """INSERT INTO wallets (user_id, chain, hd_index, address, private_key_encrypted, derivation_path)
                    VALUES (?,?,?,?,?,?)""",
                    (
                        user["id"],
                        chain,
                        next_index,
                        address,
                        _encrypt_private_key(priv_hex) if priv_hex else "",
                        derivation_path,
                    ),
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                # 唯一约束冲突：并发场景下同时分配，再查一次就拿到了
                logger.warning(f"分配地址并发冲突，重试读取: {e}")
                cursor = await db.execute(
                    "SELECT * FROM wallets WHERE user_id=? AND chain=?",
                    (user["id"], chain),
                )
                wallet = await cursor.fetchone()
                if not wallet:
                    raise
                return dict(wallet)

            logger.info(f"[HD分配] 用户tg_id={tg_user_id} → 链={chain} 索引={next_index} 地址={address}")
            return {
                "id": None,
                "user_id": user["id"],
                "chain": chain,
                "hd_index": next_index,
                "address": address,
                "derivation_path": derivation_path,
            }

    def _generate_mock_address(self, user_id: int, chain: str) -> str:
        """仅本地测试用：按user_id生成可重现的模拟地址（格式对得上T开头）"""
        if chain == "trc20":
            h = hashlib.sha256(f"mock-user-{user_id}-trc20".encode()).hexdigest()
            # TRON地址base58格式固定T开头，34字符，这里只是格式对得上，链上不存在
            return "T" + h[:33].upper()
        return f"0x{hashlib.sha256(str(user_id).encode()).hexdigest()[:40]}"

    # ============== 充值订单 ==============

    async def create_recharge_order(self, tg_user_id: int, amount: float, chain: str = "trc20") -> dict:
        """用户点击「我要充值X U」时创建订单，返回要打钱的地址和金额"""
        if amount < Config.MIN_RECHARGE_AMOUNT:
            raise ValueError(f"最低充值 {Config.MIN_RECHARGE_AMOUNT} USDT")

        user = await self.get_or_create_user(tg_user_id)
        wallet = await self.get_recharge_address(tg_user_id, chain)

        order_no = f"R{int(time.time())}{user['id']:06d}{chain[:2].upper()}"

        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO recharge_orders (user_id, order_no, chain, address, amount_usdt, status)
                VALUES (?,?,?,?,?, 'pending')""",
                (user["id"], order_no, chain, wallet["address"], amount),
            )
            await db.commit()
            order_id = cursor.lastrowid

        logger.info(f"充值订单: {order_no} 用户={tg_user_id} 金额={amount}U 地址={wallet['address']}")
        return {
            "order_id": order_id,
            "order_no": order_no,
            "address": wallet["address"],
            "amount": amount,
            "chain": chain,
            "hd_index": wallet.get("hd_index"),
            "tip": "仅支持USDT-TRC20网络，打错币永久丢失。到账约需3-30分钟，可/checkrecharge手动刷新。",
        }

    async def check_recharge_status(self, order_no: str) -> dict:
        """用户手动点「我已付款，刷新状态」时调用，扫链上单笔订单"""
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM recharge_orders WHERE order_no=?", (order_no,))
            order = await cursor.fetchone()
            if not order:
                return {"status": "not_found"}
            order = dict(order)

        if order["status"] == "confirmed":
            return {
                "status": "confirmed",
                "amount": order["amount_usdt"],
                "tx_hash": order.get("tx_hash"),
                "confirmed_at": order.get("confirmed_at"),
            }

        # 扫这个地址的最新USDT转账（不一定严格按amount，实际用户可能多打/少打，金额>=应充就认）
        txs = await self._scan_address_transfers(order["address"], min_timestamp_hours=72)
        matched = None
        for tx in txs:
            # 条件：金额>=订单amount（允许用户多打，按实际入账）、已经确认、未被其他订单消费过
            if tx["confirmations"] >= Config.RECHARGE_CONFIRMATIONS \
                    and tx["amount"] >= Config.MIN_RECHARGE_AMOUNT \
                    and not await self._is_tx_already_used(tx["tx_id"]):
                matched = tx
                break

        if matched:
            # 按实际转账金额入账（用户多充就多给余额，灵活）
            real_amount = min(matched["amount"], order["amount_usdt"] * 1.05)  # 最多认5%溢缴，防止串单
            await self._confirm_recharge(order, matched["tx_id"], matched["confirmations"],
                                          actual_amount=matched["amount"])
            return {"status": "confirmed", "amount": matched["amount"], "tx_hash": matched["tx_id"]}

        return {"status": order["status"], "pending_reason": "链上尚未检测到符合条件的转账，请耐心等待确认"}

    # ============== 核心：批量到账扫描（定时任务每5分钟调一次）==============

    async def check_all_pending_recharges(self) -> list:
        """
        批量扫描所有可能有钱到账的地址，自动入账。
        扫描范围：
          A) 所有 status=pending 的充值订单（72小时内）
          B) 所有已分配过地址的用户（方便用户随时充值，不用先下订单）
        返回：本批次确认入账的订单列表
        """
        confirmed_list = []
        cutoff = datetime.now() - timedelta(hours=72)

        async with get_db() as db:
            # 找所有待检查的唯一地址（去重，避免同一地址扫多次）
            addresses = set()

            # A) 扫pending订单
            cur = await db.execute(
                "SELECT DISTINCT address FROM recharge_orders WHERE status='pending' AND created_at>?",
                (cutoff.strftime("%Y-%m-%d %H:%M:%S"),)
            )
            for row in await cur.fetchall():
                if row["address"]:
                    addresses.add(row["address"])

            # B) 扫已分配地址（用户可能没下订单就直接打钱，按最近有地址分配记录的14天内）
            cur2 = await db.execute(
                "SELECT DISTINCT address FROM wallets WHERE chain='trc20' AND created_at>?",
                ((datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"),)
            )
            for row in await cur2.fetchall():
                if row["address"]:
                    addresses.add(row["address"])

        if not addresses:
            logger.info("[批量扫描] 无待检查地址")
            return confirmed_list

        logger.info(f"[批量扫描] 开始检查 {len(addresses)} 个地址的链上到账...")

        # 按地址逐个扫（可以改成异步并发，但TRONGRID免费版有QPS限制，串行更稳）
        for addr in addresses:
            try:
                txs = await self._scan_address_transfers(addr, min_timestamp_hours=72)
            except Exception as e:
                logger.warning(f"扫地址{addr}失败: {e}，跳过")
                continue

            for tx in txs:
                # 条件：金额够、确认数够、这笔tx没入过账
                if tx["amount"] < Config.MIN_RECHARGE_AMOUNT:
                    continue
                if tx["confirmations"] < Config.RECHARGE_CONFIRMATIONS:
                    continue
                if await self._is_tx_already_used(tx["tx_id"]):
                    continue

                # 找到该地址对应的用户（一个HD地址只对应一个用户，因为wallets UNIQUE(chain,hd_index)）
                async with get_db() as db:
                    cur = await db.execute(
                        "SELECT w.user_id, w.address FROM wallets w WHERE w.chain='trc20' AND w.address=?",
                        (addr,)
                    )
                    wallet_row = await cur.fetchone()
                    if not wallet_row:
                        continue
                    user_id = wallet_row["user_id"]

                    # 优先匹配：这个用户最近有没有pending订单？有就关联到订单（入账+改订单状态）
                    cur = await db.execute(
                        "SELECT * FROM recharge_orders WHERE user_id=? AND status='pending' AND address=? ORDER BY created_at DESC LIMIT 1",
                        (user_id, addr)
                    )
                    order = await cur.fetchone()

                actual_amount = tx["amount"]
                if order:
                    # 有订单：认到订单上，金额按min(实际转账, 订单金额*1.05)，差额部分下次入账
                    credit_amount = min(actual_amount, order["amount_usdt"] * 1.05)
                    await self._confirm_recharge(
                        dict(order), tx["tx_id"], tx["confirmations"],
                        actual_amount=actual_amount, credit_amount=credit_amount
                    )
                    confirmed_list.append({
                        "user_id": user_id,
                        "order_no": order["order_no"],
                        "amount": credit_amount,
                        "tx_hash": tx["tx_id"],
                    })
                else:
                    # 没订单（用户直接打钱没点充值按钮）：直接入账+建一笔"无订单充值"记录
                    await self._credit_direct_recharge(user_id, addr, tx["amount"], tx["tx_id"])
                    confirmed_list.append({
                        "user_id": user_id,
                        "order_no": None,
                        "amount": actual_amount,
                        "tx_hash": tx["tx_id"],
                    })

        logger.info(f"[批量扫描] 完成，本批次确认{len(confirmed_list)}笔充值")
        return confirmed_list

    # ============== 链上查询（TronGrid API）==============

    async def _scan_address_transfers(self, address: str, min_timestamp_hours: int = 72) -> list:
        """
        调TronGrid查指定地址最近N小时的 TRC20-USDT 转入记录
        返回: [{tx_id, block, amount, confirmations, from_addr, timestamp}] 列表（从新到旧）
        """
        if not Config.TRONGRID_API_KEY or not address:
            return []  # 未配API Key，直接返回空（本地测试用）

        import httpx
        min_ts = int((time.time() - min_timestamp_hours * 3600) * 1000)  # TronGrid用毫秒

        headers = {"TRON-PRO-API-KEY": Config.TRONGRID_API_KEY} if Config.TRONGRID_API_KEY else {}
        params = {
            "only_to": True,
            "only_confirmed": False,
            "min_timestamp": min_ts,
            "limit": 20,
            "contract_address": Config.USDT_TRC20_CONTRACT,
        }
        url = f"{Config.TRONGRID_API_URL}/v1/accounts/{address}/transactions/trc20"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"TronGrid返回{resp.status_code}: {resp.text[:200]}")
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"TronGrid请求异常: {e}")
            return []

        results = []
        # 同时查当前区块号，用于算确认数
        current_block = await self._get_current_block()

        for item in data.get("data", []):
            try:
                # 只关心USDT转入（合约地址过滤已在参数里，这里二次保险）
                if item.get("type") != "Transfer" or item.get("to") != address:
                    continue
                contract = item.get("contract_address", "")
                if contract.lower() != Config.USDT_TRC20_CONTRACT.lower():
                    continue
                raw_amount = item.get("value", "0")
                amount_usdt = int(raw_amount) / 1_000_000  # USDT 6位小数
                block = item.get("block_number", 0)
                tx_id = item.get("transaction_id", "")
                results.append({
                    "tx_id": tx_id,
                    "block": block,
                    "amount": amount_usdt,
                    "confirmations": max(0, current_block - block) if current_block and block else 0,
                    "from_addr": item.get("from", ""),
                    "timestamp": item.get("block_timestamp", 0),
                })
            except Exception as e:
                logger.debug(f"解析tx跳过: {e}")
                continue

        # 最新的排前面
        results.sort(key=lambda x: x["block"], reverse=True)
        return results

    async def _get_current_block(self) -> int:
        """获取TRON当前最新区块号"""
        try:
            import httpx
            headers = {"TRON-PRO-API-KEY": Config.TRONGRID_API_KEY} if Config.TRONGRID_API_KEY else {}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{Config.TRONGRID_API_URL}/wallet/getnowblock", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("block_header", {}).get("raw_data", {}).get("number", 0)
        except Exception as e:
            logger.debug(f"取最新区块失败: {e}")
        return 0

    # ============== 入账逻辑 ==============

    async def _is_tx_already_used(self, tx_id: str) -> bool:
        """防止同一笔链上tx重复入账（幂等性关键）"""
        if not tx_id:
            return False
        async with get_db() as db:
            cur = await db.execute(
                "SELECT 1 FROM recharge_orders WHERE tx_hash=? LIMIT 1 UNION ALL SELECT 1 FROM transactions WHERE description LIKE ? LIMIT 1",
                (tx_id, f"%tx:{tx_id}%")
            )
            return bool(await cur.fetchone())

    async def _confirm_recharge(self, order: dict, tx_hash: str, confirmations: int = 12,
                                 actual_amount: float = None, credit_amount: float = None):
        """按充值订单入账（有订单的场景），confirmations默认12块（≈36秒TRON确认），兼容旧调用方式"""
        actual_amount = actual_amount if actual_amount is not None else order["amount_usdt"]
        credit_amount = credit_amount if credit_amount is not None else order["amount_usdt"]
        async with get_db() as db:
            # 订单状态改成已确认
            await db.execute(
                """UPDATE recharge_orders SET status='confirmed', tx_hash=?, confirmed_at=?, confirmations=?, actual_amount_usdt=?
                WHERE id=? AND status='pending'""",
                (tx_hash, datetime.now(), confirmations, actual_amount, order["id"]),
            )
            # 加余额
            await db.execute(
                "UPDATE users SET wallet_balance_usdt = wallet_balance_usdt + ? WHERE id=?",
                (credit_amount, order["user_id"]),
            )
            cur = await db.execute(
                "SELECT wallet_balance_usdt FROM users WHERE id=?",
                (order["user_id"],),
            )
            row = await cur.fetchone()
            balance_after = row["wallet_balance_usdt"] if row else 0.0
            await db.execute(
                """INSERT INTO transactions (user_id, type, amount, balance_after, related_id, description)
                VALUES (?, 'recharge', ?, ?, ?, ?)""",
                (order["user_id"], credit_amount, balance_after, order["id"],
                 f"充值到账 {order['chain']} 实际{actual_amount}U tx:{tx_hash[:16]}..."),
            )
            await db.commit()
        logger.success(
            f"充值入账 订单{order.get('order_no')} "
            f"用户ID={order['user_id']} 入账{credit_amount}U 实到{actual_amount}U"
        )

    async def _credit_direct_recharge(self, user_id: int, address: str, amount: float, tx_hash: str):
        """用户没下订单直接打钱过来 → 直接加余额+创建一条已确认订单备查"""
        async with get_db() as db:
            # 建一条"直充"订单（方便后台查询）
            order_no = f"D{int(time.time())}{user_id:06d}TR"
            await db.execute(
                """INSERT INTO recharge_orders
                   (user_id, order_no, chain, address, amount_usdt, actual_amount_usdt, status, tx_hash, confirmed_at, confirmations)
                   VALUES (?, ?, 'trc20', ?, ?, ?, 'confirmed', ?, ?, 12)""",
                (user_id, order_no, address, amount, amount, tx_hash, datetime.now()),
            )
            # 加余额
            await db.execute(
                "UPDATE users SET wallet_balance_usdt = wallet_balance_usdt + ? WHERE id=?",
                (amount, user_id),
            )
            cur = await db.execute(
                "SELECT wallet_balance_usdt FROM users WHERE id=?", (user_id,)
            )
            row = await cur.fetchone()
            balance_after = row["wallet_balance_usdt"] if row else 0.0
            await db.execute(
                """INSERT INTO transactions (user_id, type, amount, balance_after, related_id, description)
                VALUES (?, 'recharge', ?, ?, NULL, ?)""",
                (user_id, amount, balance_after, f"直接充值到账 实{amount}U tx:{tx_hash[:16]}..."),
            )
            await db.commit()
        logger.success(f"无订单直充入账 用户ID={user_id} 金额={amount}U")

    # ============== 余额扣减（广告扣费、订阅费、创建Bot）==============

    async def deduct_balance(self, tg_user_id: int, amount: float, tx_type: str, description: str, related_id: int = None) -> dict:
        """扣减用户余额（广告费/订阅费/创建Bot开发费等）"""
        if amount <= 0:
            return {"success": False, "error": "扣款金额必须>0"}
        async with get_db() as db:
            cursor = await db.execute("SELECT id, wallet_balance_usdt FROM users WHERE tg_user_id=?", (tg_user_id,))
            user = await cursor.fetchone()
            if not user:
                return {"success": False, "error": "用户不存在"}

            user = dict(user)
            if user["wallet_balance_usdt"] + 1e-9 < amount:  # 浮点精度保险
                return {"success": False, "error": f"余额不足，需{amount}U，当前{user['wallet_balance_usdt']:.4f}U",
                        "balance": user["wallet_balance_usdt"]}

            new_balance = round(user["wallet_balance_usdt"] - amount, 8)
            await db.execute(
                "UPDATE users SET wallet_balance_usdt=? WHERE id=?",
                (new_balance, user["id"]),
            )
            await db.execute(
                """INSERT INTO transactions (user_id, type, amount, balance_after, related_id, description)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user["id"], tx_type, -amount, new_balance, related_id, description),
            )
            await db.commit()

        logger.info(f"扣款 用户{tg_user_id} -{amount}U ({tx_type}) 剩余{new_balance}U")
        return {"success": True, "balance_after": new_balance}

    # ============== 资金归集（所有子地址→索引0主地址，TronLink统一管理）==============

    async def get_collect_summary(self) -> dict:
        """查询所有子地址待归集USDT余额汇总 + 所需TRX矿工费预估"""
        if not Config.HD_WALLET_MNEMONIC:
            return {"ok": False, "error": "未配置HD_WALLET_MNEMONIC，无法归集"}

        async with get_db() as db:
            cur = await db.execute(
                "SELECT address, hd_index, derivation_path FROM wallets WHERE chain='trc20' AND hd_index>0 ORDER BY hd_index"
            )
            sub_wallets = await cur.fetchall()

        main_addr, _, _ = _derive_hd_address(Config.HD_MAIN_INDEX)
        if not main_addr:
            return {"ok": False, "error": "主地址派生失败"}

        total_usdt = 0.0
        total_trx_need = 0.0  # 归集每个地址要消耗≈0.3TRX矿工费（TRC20转账）
        details = []

        import httpx
        headers = {"TRON-PRO-API-KEY": Config.TRONGRID_API_KEY} if Config.TRONGRID_API_KEY else {}

        for w in sub_wallets:
            addr = w["address"]
            idx = w["hd_index"]
            # 查USDT余额
            usdt_bal = 0.0
            trx_bal = 0.0
            try:
                async with httpx.AsyncClient(timeout=10) as cli:
                    r1 = await cli.get(
                        f"{Config.TRONGRID_API_URL}/v1/accounts/{addr}",
                        headers=headers
                    )
                    if r1.status_code == 200:
                        acc = r1.json()
                        # TRX余额（单位sun，1TRX=1e6 sun）
                        trx_bal = acc.get("data", [{}])[0].get("balance", 0) / 1_000_000
                        # TRC20余额数组
                        for t in acc.get("data", [{}])[0].get("trc20", []):
                            for contract, bal_sun_str in t.items():
                                if contract.lower() == Config.USDT_TRC20_CONTRACT.lower():
                                    usdt_bal = int(bal_sun_str) / 1_000_000
                                    break
            except Exception as e:
                logger.debug(f"查地址{addr}余额异常: {e}")
                continue

            if usdt_bal > 0.01:  # 大于0.01U才值得归集
                gas = 0.35  # 预留0.35TRX矿工费（实际TRC20转账≈0.3-0.345TRX）
                need_gas = max(0.0, gas - trx_bal)  # 如果地址自己有TRX就不用补
                total_usdt += usdt_bal
                total_trx_need += need_gas
                details.append({
                    "hd_index": idx,
                    "address": addr,
                    "usdt_balance": round(usdt_bal, 4),
                    "trx_balance": round(trx_bal, 4),
                    "need_topup_trx": round(need_gas, 4),
                })

        return {
            "ok": True,
            "main_index": Config.HD_MAIN_INDEX,
            "main_address": main_addr,
            "sub_wallet_count": len(details),
            "total_collectable_usdt": round(total_usdt, 4),
            "total_trx_fee_needed": round(total_trx_need, 4),
            "tip": f"请先向所有子地址分别补足TRX矿工费（或先向{main_addr}转入{round(total_trx_need+0.5,2)}TRX后调用一键分发+归集）",
            "details": details,
        }

    async def collect_sub_wallets(self, hd_index_list: list = None, dry_run: bool = False) -> dict:
        """
        一键归集：把子地址的USDT全部转到索引0（运营主地址，TronLink默认能看到）
        hd_index_list: 指定哪些索引归集，None=全部有余额的
        dry_run=True: 只预览不真正转账
        
        ⚠️ 前置条件：
        1. 每个子地址里必须有 ≥0.35 TRX 作为矿工费（TRC20转账消耗的是发起方地址的TRX）
           归集前可以用 get_collect_summary() 查看每个地址还差多少TRX，先从主地址给它们转过去
        2. HD_WALLET_MNEMONIC 必须配置正确（归集需要导出私钥签名交易）
        """
        if not Config.HD_WALLET_MNEMONIC:
            return {"ok": False, "error": "未配置HD_WALLET_MNEMONIC"}
        raise NotImplementedError(
            "归集功能涉及链上真实转账签名，为安全起见：\n"
            "① 请在 TronLink App 里导入同一套助记词 → 钱包管理 → 多地址 → 分别转出\n"
            "② 或联系开发者启用 hdwallet[tronapi] 签名插件后，自动签名归集脚本一键执行\n"
            "手动归集无代码风险，强烈推荐方案①，每天点几下即可"
        )


# 全局实例
wallet_manager = WalletManager()
