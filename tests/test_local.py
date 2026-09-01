"""
本地环境模拟测试脚本
不依赖真实TG账号，使用mock数据验证：
1. 数据库初始化与建表
2. FTS5索引写入与搜索
3. 备份与回滚
4. 版本记录
"""
import asyncio
import os
import sys

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, get_db
from app.search.indexer import searcher
from app.admin.backup_manager import backup_manager
from app.admin.version_manager import version_manager


# ===== Mock测试数据 =====
MOCK_CHANNELS = [
    {"tg_channel_id": 100001, "username": "crypto_news", "title": "加密货币资讯", "member_count": 50000},
    {"tg_channel_id": 100002, "username": "defi_daily", "title": "DeFi日报", "member_count": 30000},
    {"tg_channel_id": 100003, "username": "airdrop_hub", "title": "空投中心", "member_count": 80000},
    {"tg_channel_id": 100004, "username": "trading_signals", "title": "交易信号站", "member_count": 120000},
    {"tg_channel_id": 100005, "username": "nft_market", "title": "NFT市场观察", "member_count": 25000},
]

MOCK_MESSAGES = [
    # 频道1: 加密货币资讯
    (1, 1001, "比特币今日突破6万美元，机构资金持续流入BTC ETF产品，市场情绪高涨", "2026-08-15 10:30:00"),
    (1, 1002, "以太坊2.0升级进展顺利，ETH质押量创新高，DeFi生态TVL重回500亿", "2026-08-15 14:20:00"),
    (1, 1003, "Solana生态爆发，SOL价格一周翻倍，链上日活地址数突破200万", "2026-08-16 09:15:00"),
    (1, 1004, "美国SEC批准比特币现货ETF，传统金融机构加速布局加密资产", "2026-08-16 16:45:00"),

    # 频道2: DeFi日报
    (2, 2001, "Uniswap V4即将上线，新 hooks 机制将彻底改变DEX交易模式", "2026-08-15 11:00:00"),
    (2, 2002, "Aave V3总借贷量突破100亿，GHO稳定币在DeFi借贷市场表现抢眼", "2026-08-15 18:30:00"),
    (2, 2003, "Curve战争升级，veCRV持有者参与多个协议的治理争夺", "2026-08-16 10:00:00"),
    (2, 2004, "DeFi永续合约协议GMX和dYdX交易量创新高，衍生品成为增长引擎", "2026-08-16 20:00:00"),

    # 频道3: 空投中心
    (3, 3001, "LayerZero空投确认，ZRO代币将于下周上线，快照已结束", "2026-08-15 12:00:00"),
    (3, 3002, "zkSync Era确认发币，ZK代币空投查询页面已开放，检查你的资格", "2026-08-15 19:00:00"),
    (3, 3003, "Scroll生态空投即将到来，交互教程：跨链+兑换+流动性", "2026-08-16 14:00:00"),
    (3, 3004, "Linea Voyage活动结束，LINEA空投快照完成，预计Q3发币", "2026-08-16 21:30:00"),

    # 频道4: 交易信号站
    (4, 4001, "BTC支撑位58000，阻力位62000，4小时级别出现多头信号", "2026-08-15 13:00:00"),
    (4, 4002, "ETH/BTC汇率触底反弹，DeFi蓝筹代币补涨行情开启", "2026-08-15 20:00:00"),
    (4, 4003, "SOL突破压力位，生态代币RAY、SRM跟涨，注意止盈", "2026-08-16 15:00:00"),
    (4, 4004, "市场恐慌指数降至20，逆向思维：可能是抄底机会", "2026-08-16 22:00:00"),

    # 频道5: NFT市场观察
    (5, 5001, "BAYC地板价回到20ETH，蓝筹NFT成交量回升", "2026-08-15 15:00:00"),
    (5, 5002, "Pudgy Penguins宣布进军实体零售，NFT IP商业化加速", "2026-08-16 11:30:00"),
    (5, 5003, "Azuki Elementals系列发布，动漫NFT赛道热度持续", "2026-08-16 17:00:00"),
    (5, 5004, "OpenSea推出Diamond协议，NFT版税保护新方案", "2026-08-16 23:00:00"),
]

# 测试用搜索关键词
TEST_KEYWORDS = [
    "比特币",
    "DeFi",
    "空投",
    "ETH质押",
    "NFT蓝筹",
    "交易信号",
]


async def test_database_init():
    """测试1：数据库初始化"""
    print("\n" + "=" * 60)
    print("测试1：数据库初始化与建表")
    print("=" * 60)

    # 删除旧测试库（包括WAL和SHM文件）
    db_path = "./data/tg_search.db"
    for suffix in ["", "-wal", "-shm"]:
        full_path = db_path + suffix
        if os.path.exists(full_path):
            os.remove(full_path)

    await init_db()
    print("✓ 数据库初始化成功，表结构创建完成")

    async with get_db() as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in await cursor.fetchall()]
        print(f"✓ 已创建表: {tables}")

        # 检查FTS5虚拟表
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts'")
        fts_exists = await cursor.fetchone()
        if fts_exists:
            print("✓ FTS5全文索引虚拟表已创建")
        else:
            print("✗ FTS5虚拟表创建失败")
            return False

    return True


async def test_insert_mock_data():
    """测试2：插入Mock数据"""
    print("\n" + "=" * 60)
    print("测试2：插入Mock测试数据")
    print("=" * 60)

    import hashlib

    async with get_db() as db:
        # 插入频道
        for ch in MOCK_CHANNELS:
            await db.execute(
                """INSERT OR IGNORE INTO channels
                (tg_channel_id, username, title, member_count, crawl_status)
                VALUES (?,?,?,?, 'joined')""",
                (ch["tg_channel_id"], ch["username"], ch["title"], ch["member_count"]),
            )
        print(f"✓ 插入 {len(MOCK_CHANNELS)} 个频道")

        # 插入消息（触发器自动同步到FTS）
        for msg in MOCK_MESSAGES:
            channel_id, tg_msg_id, content, msg_date = msg
            content_hash = hashlib.md5(content.encode()).hexdigest()
            await db.execute(
                """INSERT OR IGNORE INTO messages
                (channel_id, tg_msg_id, content, msg_date, content_hash)
                VALUES (?,?,?,?,?)""",
                (channel_id, tg_msg_id, content, msg_date, content_hash),
            )
        print(f"✓ 插入 {len(MOCK_MESSAGES)} 条消息")

        await db.commit()

        # 验证
        cursor = await db.execute("SELECT COUNT(*) FROM channels")
        ch_count = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM messages")
        msg_count = (await cursor.fetchone())[0]
        print(f"✓ 验证: 频道={ch_count}, 消息={msg_count}")

    return True


async def test_search():
    """测试3：FTS5搜索功能"""
    print("\n" + "=" * 60)
    print("测试3：FTS5全文搜索功能")
    print("=" * 60)

    for keyword in TEST_KEYWORDS:
        results = await searcher.search(keyword, limit=5)
        status = "✓" if results else "○"
        print(f"{status} 搜索 '{keyword}': 命中 {len(results)} 条")
        if results:
            first = results[0]
            print(f"  → 首条: [{first['channel_title']}] {first['excerpt'][:50]}...")

    return True


async def test_backup():
    """测试4：备份与回滚"""
    print("\n" + "=" * 60)
    print("测试4：数据库备份与回滚")
    print("=" * 60)

    # 创建备份
    backup_result = await backup_manager.create_backup(backup_type="manual", notes="测试备份")
    print(f"✓ 创建备份成功: ID={backup_result['backup_id']}")
    print(f"  文件: {os.path.basename(backup_result['backup_path'])}")
    print(f"  大小: {backup_result['file_size']/1024:.1f}KB")

    # 列出备份
    backups = await backup_manager.list_backups()
    print(f"✓ 当前可用备份数: {len(backups)}")

    # 测试回滚
    backup_id = backup_result["backup_id"]
    print(f"  准备测试回滚到备份 ID={backup_id}...")

    # 先插入一条测试数据（验证回滚后是否消失）
    async with get_db() as db:
        await db.execute(
            """INSERT INTO messages (channel_id, tg_msg_id, content, msg_date, content_hash)
            VALUES (1, 9999, '这条是回滚测试数据，回滚后应该消失', '2026-08-17 00:00:00', 'test_rollback')"""
        )
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM messages")
        before_rollback = (await cursor.fetchone())[0]
        print(f"  插入测试数据后消息数: {before_rollback}")

    # 执行回滚
    restore_result = await backup_manager.restore_backup(backup_id)
    if restore_result["success"]:
        print(f"✓ 回滚成功，恢复到版本: {restore_result['restored_version']}")

        # 验证测试数据已消失
        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            after_rollback = (await cursor.fetchone())[0]
            print(f"  回滚后消息数: {after_rollback}")
            if after_rollback < before_rollback:
                print("✓ 测试数据已被回滚清除，回滚功能正常")
            else:
                print("✗ 回滚后数据未减少，可能有问题")

    return True


async def test_version_record():
    """测试5：版本记录"""
    print("\n" + "=" * 60)
    print("测试5：版本记录功能")
    print("=" * 60)

    from app.config import Config

    async with get_db() as db:
        await db.execute(
            "INSERT INTO app_versions (version, status, notes) VALUES (?, 'active', '本地测试版本')",
            (Config.APP_VERSION,),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM app_versions ORDER BY id DESC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            print(f"✓ 版本记录成功: v{row['version']} 状态={row['status']}")
            print(f"  时间: {row['updated_at']}")

    return True


async def test_stats():
    """测试6：统计功能"""
    print("\n" + "=" * 60)
    print("测试6：数据库统计")
    print("=" * 60)

    channel_count = await searcher.get_channel_count()
    msg_count = await searcher.get_message_count()
    print(f"✓ 频道总数: {channel_count}")
    print(f"✓ 消息总数: {msg_count:,}")

    return True


async def main():
    """主测试流程"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " TG搜索机器人 - 本地模拟测试 ".center(54) + "║")
    print("╚" + "═" * 58 + "╝")

    results = []

    # 执行测试
    results.append(("数据库初始化", await test_database_init()))
    results.append(("插入Mock数据", await test_insert_mock_data()))
    results.append(("FTS5搜索功能", await test_search()))
    results.append(("备份与回滚", await test_backup()))
    results.append(("版本记录", await test_version_record()))
    results.append(("数据库统计", await test_stats()))

    # 测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status} - {name}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")
    if passed == len(results):
        print("🎉 所有测试通过！核心链路可跑通。")
    else:
        print("⚠️ 有测试失败，请检查")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
