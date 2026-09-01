"""
第2步本地测试：USDT钱包 + 广告系统
验证完整变现链路
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, get_db
from app.wallet.wallet_manager import wallet_manager
from app.advertising.ad_manager import ad_manager
from app.search.indexer import searcher
from app.admin.backup_manager import backup_manager


MOCK_CHANNELS = [
    {"tg_channel_id": 100001, "username": "crypto_news", "title": "加密货币资讯", "member_count": 50000},
    {"tg_channel_id": 100002, "username": "defi_daily", "title": "DeFi日报", "member_count": 30000},
    {"tg_channel_id": 100003, "username": "airdrop_hub", "title": "空投中心", "member_count": 80000},
    {"tg_channel_id": 100004, "username": "trading_signals", "title": "交易信号站", "member_count": 120000},
    {"tg_channel_id": 100005, "username": "nft_market", "title": "NFT市场观察", "member_count": 25000},
]

MOCK_MESSAGES = [
    (1, 1001, "比特币今日突破6万美元，机构资金持续流入BTC ETF产品", "2026-08-15 10:30:00"),
    (1, 1002, "以太坊2.0升级进展顺利，ETH质押量创新高，DeFi生态TVL重回500亿", "2026-08-15 14:20:00"),
    (1, 1003, "Solana生态爆发，SOL价格一周翻倍", "2026-08-16 09:15:00"),
    (1, 1004, "美国SEC批准比特币现货ETF", "2026-08-16 16:45:00"),
    (2, 2001, "Uniswap V4即将上线，hooks机制改变DEX交易模式", "2026-08-15 11:00:00"),
    (2, 2002, "Aave V3总借贷量突破100亿，GHO稳定币表现抢眼", "2026-08-15 18:30:00"),
    (2, 2003, "Curve战争升级，veCRV持有者参与治理争夺", "2026-08-16 10:00:00"),
    (3, 3001, "LayerZero空投确认，ZRO代币下周上线", "2026-08-15 12:00:00"),
    (3, 3002, "zkSync Era确认发币，ZK代币空投查询页面已开放", "2026-08-15 19:00:00"),
    (3, 3003, "Scroll生态空投即将到来，交互教程发布", "2026-08-16 14:00:00"),
    (4, 4001, "BTC支撑位58000，阻力位62000，多头信号", "2026-08-15 13:00:00"),
    (4, 4002, "ETH/BTC汇率触底反弹，DeFi蓝筹代币补涨", "2026-08-15 20:00:00"),
    (5, 5001, "BAYC地板价回到20ETH，蓝筹NFT成交量回升", "2026-08-15 15:00:00"),
    (5, 5002, "Pudgy Penguins宣布进军实体零售，NFT IP商业化加速", "2026-08-16 11:30:00"),
]

# 模拟TG用户ID
TEST_USER_1 = 88800001  # 广告主张三
TEST_USER_2 = 88800002  # 搜索用户李四


async def setup_data():
    """初始化数据库和测试数据"""
    print("\n" + "=" * 60)
    print("初始化：数据库+Mock数据+广告模板")
    print("=" * 60)

    # 清理旧数据库
    db_path = "./data/tg_search.db"
    for suffix in ["", "-wal", "-shm"]:
        full_path = db_path + suffix
        if os.path.exists(full_path):
            os.remove(full_path)

    await init_db()
    print("✓ 数据库初始化完成")

    # 插入频道和消息
    import hashlib
    async with get_db() as db:
        for ch in MOCK_CHANNELS:
            await db.execute(
                "INSERT OR IGNORE INTO channels (tg_channel_id, username, title, member_count, crawl_status) VALUES (?,?,?,?, 'joined')",
                (ch["tg_channel_id"], ch["username"], ch["title"], ch["member_count"]),
            )
        for msg in MOCK_MESSAGES:
            content_hash = hashlib.md5(msg[2].encode()).hexdigest()
            await db.execute(
                "INSERT OR IGNORE INTO messages (channel_id, tg_msg_id, content, msg_date, content_hash) VALUES (?,?,?,?,?)",
                (msg[0], msg[1], msg[2], msg[3], content_hash),
            )
        await db.commit()
    print(f"✓ 插入 {len(MOCK_CHANNELS)} 频道 + {len(MOCK_MESSAGES)} 消息")

    # 初始化广告模板
    await ad_manager.init_templates()
    print("✓ 广告模板库初始化")

    return True


async def test_wallet_recharge():
    """测试1：用户注册+充值地址+模拟到账"""
    print("\n" + "=" * 60)
    print("测试1：钱包充值流程")
    print("=" * 60)

    # 用户注册
    user = await wallet_manager.get_or_create_user(TEST_USER_1, "advertiser_zhang")
    print(f"✓ 用户注册: ID={user['id']} TG={user['tg_user_id']} 余额={user['wallet_balance_usdt']}U")

    # 获取充值地址
    wallet = await wallet_manager.get_recharge_address(TEST_USER_1, "trc20")
    print(f"✓ 充值地址生成: {wallet['address']}")

    # 创建充值订单
    order = await wallet_manager.create_recharge_order(TEST_USER_1, 100.0, "trc20")
    print(f"✓ 充值订单: {order['order_no']} 金额={order['amount']}U")

    # 模拟到账（直接调用确认方法）
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM recharge_orders WHERE order_no=?", (order["order_no"],))
        order_row = dict(await cursor.fetchone())

    await wallet_manager._confirm_recharge(order_row, "0x_mock_tx_hash_12345")
    print(f"✓ 模拟到账确认: +100U")

    # 验证余额
    balance = await wallet_manager.get_balance(TEST_USER_1)
    print(f"✓ 当前余额: {balance}U")
    assert balance == 100.0, f"余额应为100U，实际{balance}U"

    # 查询交易记录
    txs = await wallet_manager.get_transaction_history(TEST_USER_1)
    print(f"✓ 交易记录: {len(txs)}条")
    assert len(txs) == 1

    return True


async def test_create_ad():
    """测试2：创建广告计划"""
    print("\n" + "=" * 60)
    print("测试2：广告计划创建")
    print("=" * 60)

    # 成为广告主
    await ad_manager.become_advertiser(TEST_USER_1)
    print("✓ 成为广告主")

    # 创建广告计划1：比特币关键词
    result1 = await ad_manager.create_campaign(TEST_USER_1, {
        "keyword": "比特币",
        "title": "📣 币圈资讯站 - 最全BTC行情",
        "description": "专注比特币行情分析，5万人已加入",
        "target_channel": "@crypto_premium",
        "billing_type": "cpc",
        "cpc_price": 0.05,
        "daily_budget": 10.0,
    })
    print(f"✓ 广告计划1创建: ID={result1['campaign_id']} 关键词=比特币")

    # 创建广告计划2：空投关键词
    result2 = await ad_manager.create_campaign(TEST_USER_1, {
        "keyword": "空投",
        "title": "🎁 最新空投汇总站",
        "description": "每日更新空投信息，错过等一年",
        "target_channel": "@airdrop_list",
        "billing_type": "cpm",
        "cpm_price": 1.0,
        "daily_budget": 5.0,
    })
    print(f"✓ 广告计划2创建: ID={result2['campaign_id']} 关键词=空投")

    # 查看广告列表
    campaigns = await ad_manager.list_campaigns(TEST_USER_1)
    print(f"✓ 广告主计划数: {len(campaigns)}")
    assert len(campaigns) == 2

    return True


async def test_search_with_ads():
    """测试3：搜索+广告展示+扣费"""
    print("\n" + "=" * 60)
    print("测试3：搜索时广告展示与扣费")
    print("=" * 60)

    # 搜索"比特币"（应触发广告1）
    print("\n--- 搜索'比特币' ---")
    results = await searcher.search("比特币")
    ads = await ad_manager.get_ads_for_keyword("比特币")
    print(f"  搜索结果: {len(results)}条")
    print(f"  匹配广告: {len(ads)}条")
    if ads:
        print(f"  广告标题: {ads[0]['title']}")
        print(f"  目标频道: {ads[0]['target_channel']}")

        # 记录曝光（CPC模式曝光不扣费）
        imp_result = await ad_manager.record_impression(ads[0]["id"], TEST_USER_2, is_click=False)
        print(f"  曝光记录: cost={imp_result['cost']}U（CPC曝光不扣费）")

        # 记录点击（CPC模式点击扣费）
        click_result = await ad_manager.record_impression(ads[0]["id"], TEST_USER_2, is_click=True)
        print(f"  点击记录: cost={click_result['cost']}U（扣0.05U）")
        assert click_result["cost"] == 0.05

    # 搜索"空投"（应触发广告2，CPM模式）
    print("\n--- 搜索'空投' ---")
    ads2 = await ad_manager.get_ads_for_keyword("空投")
    print(f"  匹配广告: {len(ads2)}条")
    if ads2:
        # CPM模式每次曝光都扣费
        imp_result = await ad_manager.record_impression(ads2[0]["id"], TEST_USER_2, is_click=False)
        print(f"  曝光记录: cost={imp_result['cost']:.4f}U（CPM每次曝光扣0.001U）")
        assert imp_result["cost"] == 0.001

    # 验证余额扣减
    balance = await wallet_manager.get_balance(TEST_USER_1)
    print(f"\n✓ 广告主余额: {balance:.4f}U（100 - 0.05 - 0.001 = 99.949）")
    assert abs(balance - 99.949) < 0.01

    return True


async def test_ad_stats():
    """测试4：广告数据统计"""
    print("\n" + "=" * 60)
    print("测试4：广告数据统计")
    print("=" * 60)

    campaigns = await ad_manager.list_campaigns(TEST_USER_1)
    for c in campaigns:
        stats = await ad_manager.get_campaign_stats(c["id"])
        print(f"  广告ID={c['id']} | {c['keyword']}")
        print(f"    曝光: {stats['total_impressions']}")
        print(f"    点击: {stats['total_clicks']}")
        print(f"    CTR: {stats['ctr']:.1f}%")
        print(f"    总花费: {stats['total_cost']:.4f}U")

    return True


async def test_insufficient_balance():
    """测试5：余额不足创建广告"""
    print("\n" + "=" * 60)
    print("测试5：余额不足检查")
    print("=" * 60)

    # 新用户没有充值
    await wallet_manager.get_or_create_user(TEST_USER_2, "user_li")
    # 先成为广告主
    await ad_manager.become_advertiser(TEST_USER_2)
    balance = await wallet_manager.get_balance(TEST_USER_2)
    print(f"✓ 用户2余额: {balance}U（未充值）")

    # 尝试创建广告（应因余额不足失败）
    result = await ad_manager.create_campaign(TEST_USER_2, {
        "keyword": "test",
        "target_channel": "@test",
    })
    print(f"✓ 创建广告结果: {result['success']}")
    print(f"  错误信息: {result.get('error', '')}")
    assert not result["success"]
    assert "余额不足" in result.get("error", "")

    return True


async def test_ad_templates():
    """测试6：广告模板库"""
    print("\n" + "=" * 60)
    print("测试6：广告模板库")
    print("=" * 60)

    templates = await ad_manager.list_templates()
    print(f"✓ 模板数量: {len(templates)}")
    for t in templates:
        rec = "⭐" if t["is_recommended"] else ""
        print(f"  {t['name']} {rec} | {t['category']}")
        print(f"    示例: {t['example_text'][:40]}...")

    assert len(templates) >= 3
    return True


async def test_backup_with_ads():
    """测试7：备份包含广告数据"""
    print("\n" + "=" * 60)
    print("测试7：备份与回滚（含广告数据）")
    print("=" * 60)

    # 创建备份
    backup = await backup_manager.create_backup(backup_type="manual", notes="含广告数据测试备份")
    print(f"✓ 备份创建: ID={backup['backup_id']} 大小={backup['file_size']/1024:.1f}KB")

    # 插入额外数据
    async with get_db() as db:
        await db.execute(
            "INSERT INTO ad_campaigns (advertiser_id, keyword, target_channel, billing_type, daily_budget, daily_spent, status) VALUES (1, 'test_extra', '@test', 'cpc', 5, 0, 'active')"
        )
        await db.commit()

    cursor_count = await ad_manager.list_campaigns(TEST_USER_1)
    print(f"  插入额外广告后计划数: {len(cursor_count)}")

    # 回滚
    restore = await backup_manager.restore_backup(backup["backup_id"])
    print(f"✓ 回滚成功: {restore['success']}")

    # 验证额外数据被清除
    campaigns = await ad_manager.list_campaigns(TEST_USER_1)
    print(f"  回滚后计划数: {len(campaigns)}（应恢复为2）")
    assert len(campaigns) == 2

    return True


async def main():
    print("╔" + "═" * 58 + "╗")
    print("║" + " TG搜索系统 - 第2步本地测试 ".center(50) + "║")
    print("║" + " USDT钱包 + 广告系统 ".center(50) + "║")
    print("╚" + "═" * 58 + "╝")

    results = []
    results.append(("初始化数据", await setup_data()))
    results.append(("钱包充值流程", await test_wallet_recharge()))
    results.append(("创建广告计划", await test_create_ad()))
    results.append(("搜索+广告展示+扣费", await test_search_with_ads()))
    results.append(("广告数据统计", await test_ad_stats()))
    results.append(("余额不足检查", await test_insufficient_balance()))
    results.append(("广告模板库", await test_ad_templates()))
    results.append(("备份与回滚", await test_backup_with_ads()))

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
        print("🎉 第2步全部测试通过！变现链路可跑通。")
        print("\n完整闭环验证：")
        print("  用户注册 → 充值USDT → 成为广告主")
        print("  → 创建广告 → 用户搜索 → 广告展示")
        print("  → 按CPC/CPM扣费 → 余额扣减 → 流水记录")
    else:
        print("⚠️ 有测试失败")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
