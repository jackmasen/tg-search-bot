"""
Bot命令处理器（第1步+第2步）
搜索 + USDT充值 + 广告合作
"""
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from app.search.indexer import searcher
from app.wallet.wallet_manager import wallet_manager
from app.advertising.ad_manager import ad_manager
from app.database import get_db
from app.config import Config


# 用户每日搜索计数
_user_search_count: dict = {}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 命令"""
    user = update.effective_user
    # 自动注册用户
    await wallet_manager.get_or_create_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("🔍 直接搜索", callback_data="hint_search")],
        [
            InlineKeyboardButton("💰 我的钱包", callback_data="wallet"),
            InlineKeyboardButton("📢 广告合作", callback_data="advertise"),
        ],
        [InlineKeyboardButton("📊 数据统计", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        f"👋 欢迎 {user.first_name}！\n\n"
        "🔍 **TG搜索机器人**\n"
        "免费搜索TG频道/群组/消息内容\n\n"
        "**使用方法：**\n"
        "• 直接发送关键词即可搜索\n"
        "• /wallet 查看钱包余额\n"
        "• /advertise 广告合作\n\n"
        f"📋 每日免费搜索：{Config.FREE_SEARCH_DAILY_LIMIT} 次"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help 命令"""
    help_text = (
        "**使用帮助**\n\n"
        "🔍 搜索：直接发送关键词\n"
        "💰 /wallet - 查看钱包余额\n"
        "💸 /recharge 金额 - USDT充值\n"
        "📢 /advertise - 广告合作\n"
        "📋 /myads - 我的广告计划\n"
        "📊 /stats - 数据库统计\n"
        "➕ /add @频道 - 添加频道到采集"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats 命令"""
    channel_count = await searcher.get_channel_count()
    msg_count = await searcher.get_message_count()
    stats_text = (
        "📊 **数据库统计**\n\n"
        f"频道数：{channel_count}\n"
        f"消息数：{msg_count:,}\n"
    )
    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/add 命令"""
    if not context.args:
        await update.message.reply_text("用法：/add @频道用户名")
        return

    username = context.args[0].lstrip("@")
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO channels (username, title, crawl_status) VALUES (?,?, 'pending')",
            (username, username),
        )
        await db.commit()
    await update.message.reply_text(f"✅ 频道 @{username} 已加入采集队列")


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/wallet 命令：查看钱包余额和交易记录"""
    user = update.effective_user
    await wallet_manager.get_or_create_user(user.id, user.username)

    balance = await wallet_manager.get_balance(user.id)
    transactions = await wallet_manager.get_transaction_history(user.id, limit=5)

    text = (
        "💰 **我的钱包**\n\n"
        f"USDT余额：**{balance:.2f} U**\n\n"
    )

    if transactions:
        text += "**最近交易记录：**\n"
        for tx in transactions:
            amount = tx["amount"]
            sign = "+" if amount > 0 else ""
            type_map = {
                "recharge": "充值",
                "ad_charge": "广告扣费",
                "build_fee": "建站费",
                "subscribe": "订阅",
                "refund": "退款",
            }
            type_name = type_map.get(tx["type"], tx["type"])
            text += f"  {sign}{amount:.2f}U | {type_name} | {tx['description'][:20]}\n"
    else:
        text += "暂无交易记录\n"

    text += f"\n💸 /recharge 金额 - 充值USDT"
    await update.message.reply_text(text, parse_mode="Markdown")


async def recharge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/recharge 命令：创建充值订单"""
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "用法：/recharge 金额\n"
            "示例：/recharge 10\n"
            "（将生成TRC20地址，转账USDT到该地址）"
        )
        return

    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("金额必须是正数")
        return

    # 创建充值订单
    order = await wallet_manager.create_recharge_order(user.id, amount, chain="trc20")

    text = (
        "💸 **USDT充值订单**\n\n"
        f"订单号：`{order['order_no']}`\n"
        f"充值金额：**{order['amount']} U**\n"
        f"链路：TRC20（推荐，gas低）\n\n"
        f"📥 收款地址：\n`{order['address']}`\n\n"
        "⚠️ 请使用TRC20网络转账USDT到以上地址\n"
        "到账后自动入账（需12个区块确认）\n\n"
        f"查询到账：/checkrecharge {order['order_no']}"
    )

    keyboard = [[InlineKeyboardButton("📋 复制地址", callback_data=f"copy_addr_{order['address']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def check_recharge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/checkrecharge 命令：查询充值到账状态"""
    if not context.args:
        await update.message.reply_text("用法：/checkrecharge 订单号")
        return

    order_no = context.args[0]
    result = await wallet_manager.check_recharge_status(order_no)

    status_map = {
        "pending": "⏳ 等待到账中",
        "confirmed": "✅ 已到账",
        "failed": "❌ 充值失败",
        "not_found": "❌ 订单不存在",
    }
    status_text = status_map.get(result["status"], result["status"])

    text = f"📋 订单 `{order_no}`\n状态：{status_text}"
    if result["status"] == "confirmed":
        text += f"\n到账金额：{result['amount']} U"

    await update.message.reply_text(text, parse_mode="Markdown")


async def advertise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/advertise 命令：广告合作入口"""
    user = update.effective_user
    await ad_manager.become_advertiser(user.id)
    balance = await wallet_manager.get_balance(user.id)

    text = (
        "📢 **广告合作**\n\n"
        f"您的USDT余额：**{balance:.2f} U**\n\n"
        "**广告形式：**\n"
        "用户搜索关键词时，您的广告展示在结果顶部\n\n"
        "**计费方式：**\n"
        "• CPC按点击：0.05U/次起\n"
        "• CPM按曝光：1.0U/千次起\n\n"
        "**操作命令：**\n"
        "• /createad - 创建广告计划\n"
        "• /myads - 查看我的广告\n"
        "• /adtemplates - 广告模板\n"
        "• /adstats - 广告数据\n\n"
        "💡 余额不足时请先 /recharge 充值"
    )

    if balance < 1.0:
        text += f"\n\n⚠️ 余额不足（<1U），请先充值"

    await update.message.reply_text(text, parse_mode="Markdown")


async def create_ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/createad 命令：创建广告计划（交互式或参数式）"""
    user = update.effective_user
    balance = await wallet_manager.get_balance(user.id)

    if balance < 1.0:
        await update.message.reply_text(
            f"⚠️ 余额不足（{balance:.2f}U），创建广告至少需要1U\n"
            "请先 /recharge 充值"
        )
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "**创建广告计划**\n\n"
            "用法：\n"
            "`/createad 关键词 频道用户名`\n\n"
            "示例：\n"
            "`/createad 比特币 @my_crypto_channel`\n\n"
            "将使用默认CPC计费：0.05U/次点击，日预算10U\n"
            "创建后可用 /myads 修改详细设置",
            parse_mode="Markdown",
        )
        return

    keyword = context.args[0]
    target_channel = context.args[1]

    campaign_data = {
        "keyword": keyword,
        "title": f"📣 广告-{keyword}",
        "description": f"搜索'{keyword}'相关内容，关注{target_channel}",
        "target_channel": target_channel,
        "target_url": "",
        "billing_type": "cpc",
        "cpc_price": 0.05,
        "cpm_price": 1.0,
        "daily_budget": 10.0,
    }

    result = await ad_manager.create_campaign(user.id, campaign_data)
    if result["success"]:
        await update.message.reply_text(
            f"✅ 广告计划创建成功！\n"
            f"广告ID：{result['campaign_id']}\n"
            f"关键词：{keyword}\n"
            f"目标频道：{target_channel}\n"
            f"计费：CPC 0.05U/次点击\n"
            f"日预算：10U\n\n"
            f"用户搜索'{keyword}'时将展示您的广告"
        )
    else:
        await update.message.reply_text(f"❌ 创建失败：{result.get('error', '未知错误')}")


async def my_ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/myads 命令：查看我的广告计划"""
    user = update.effective_user
    campaigns = await ad_manager.list_campaigns(user.id)

    if not campaigns:
        await update.message.reply_text("暂无广告计划\n用 /createad 创建")
        return

    text = "📋 **我的广告计划**\n\n"
    for c in campaigns:
        status_emoji = {"active": "▶️", "paused": "⏸️", "ended": "⏹️", "pending": "⏳"}.get(c["status"], "❓")
        text += (
            f"{status_emoji} ID:{c['id']} | {c['keyword']}\n"
            f"   频道：{c['target_channel']}\n"
            f"   计费：{c['billing_type'].upper()} | 日预算：{c['daily_budget']}U\n"
            f"   今日花费：{c['daily_spent']:.2f}U\n\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def ad_templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/adtemplates 命令：查看广告模板"""
    templates = await ad_manager.list_templates()

    if not templates:
        await update.message.reply_text("暂无模板")
        return

    text = "📝 **广告模板库**\n\n"
    for t in templates:
        recommend = " ⭐推荐" if t["is_recommended"] else ""
        text += (
            f"**{t['name']}**{recommend}\n"
            f"分类：{t['category']}\n"
            f"模板：{t['title_template']}\n"
            f"示例：{t['example_text'][:50]}...\n\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def ad_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/adstats 命令：查看广告数据"""
    user = update.effective_user
    campaigns = await ad_manager.list_campaigns(user.id)

    if not campaigns:
        await update.message.reply_text("暂无广告计划")
        return

    text = "📊 **广告数据统计**\n\n"
    for c in campaigns[:5]:
        stats = await ad_manager.get_campaign_stats(c["id"])
        text += (
            f"**ID:{c['id']} | {c['keyword']}**\n"
            f"  曝光：{stats['total_impressions']}\n"
            f"  点击：{stats['total_clicks']}\n"
            f"  CTR：{stats['ctr']:.1f}%\n"
            f"  总花费：{stats['total_cost']:.2f}U\n\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    核心搜索处理：关键词搜索 + 广告位插入
    """
    keyword = update.message.text.strip()
    user_id = update.effective_user.id

    # 检查每日搜索次数
    today = date.today()
    user_stat = _user_search_count.get(user_id, {"count": 0, "date": today})
    if user_stat["date"] != today:
        user_stat = {"count": 0, "date": today}

    if user_stat["count"] >= Config.FREE_SEARCH_DAILY_LIMIT:
        await update.message.reply_text(
            f"⚠️ 今日免费搜索已用完（{Config.FREE_SEARCH_DAILY_LIMIT}次）\n"
            "明日重置或开通VIP"
        )
        return

    if len(keyword) < 2:
        await update.message.reply_text("关键词太短，请输入至少2个字符")
        return

    searching_msg = await update.message.reply_text(f"🔍 正在搜索 '{keyword}'...")

    # 执行搜索
    results = await searcher.search(keyword)

    # 获取匹配广告
    ads = await ad_manager.get_ads_for_keyword(keyword, limit=2)

    # 记录广告曝光
    for ad in ads:
        await ad_manager.record_impression(ad["id"], user_id, is_click=False, position=1)

    user_stat["count"] += 1
    _user_search_count[user_id] = user_stat

    await searching_msg.delete()

    if not results and not ads:
        await update.message.reply_text(f"❌ 未找到 '{keyword}' 相关内容")
        return

    reply_text = f"🔎 搜索 '{keyword}' - 命中 {len(results)} 条\n\n"

    # 广告位插入头部
    if ads:
        reply_text += "━━━━ 广告 ━━━━\n"
        for ad in ads:
            reply_text += (
                f"📢 **{ad['title']}**\n"
                f"   {ad['description']}\n"
                f"   👉 {ad['target_channel']}\n\n"
            )
        reply_text += "━━━━━━━━━━━\n\n"

    # 搜索结果
    for i, item in enumerate(results[:8], 1):
        excerpt = item["excerpt"] or "（无预览）"
        channel = item["channel_title"] or item["channel_username"] or "未知"
        username = item["channel_username"] or ""
        date_str = item["msg_date"][:10] if item["msg_date"] else ""

        reply_text += f"{i}. **{channel}**\n   {excerpt}\n   📅 {date_str}"
        if username:
            reply_text += f"  | @{username}"
        reply_text += "\n\n"

    remaining = Config.FREE_SEARCH_DAILY_LIMIT - user_stat["count"]
    reply_text += f"\n💡 剩余搜索：{remaining}/{Config.FREE_SEARCH_DAILY_LIMIT}"

    await update.message.reply_text(reply_text, parse_mode="Markdown", disable_web_page_preview=True)
