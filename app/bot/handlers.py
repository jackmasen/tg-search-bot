"""
Bot命令处理器（第1步+第2步）
搜索 + USDT充值 + 广告合作 + AI智能搜索
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

    ad_limit = Config.FEATURED_AD_LIMIT
    featured_channels = await ad_manager.get_featured_channels(ad_limit)

    hot_keywords_by_cat = await ad_manager.get_hot_keywords_by_category()

    keyboard_rows = []
    keyboard_rows.append([InlineKeyboardButton("🔍 直接搜索", callback_data="hint_search")])

    # 置顶推广频道按钮（最多显示3个）
    for idx, ch in enumerate(featured_channels[:3], 1):
        title = ch.get('title', '') or ch.get('username', '未知频道')
        username = ch.get('username', '')
        if username:
            cb = f"channel_{username}"
        else:
            cb = f"channel_{ch.get('id', 0)}"
        rank_emoji = "🥇" if idx == 1 else ("🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}")
        keyboard_rows.append([InlineKeyboardButton(f"{rank_emoji} {title}", callback_data=cb)])

    keyboard_rows.append([
        InlineKeyboardButton("💰 我的钱包", callback_data="wallet"),
        InlineKeyboardButton("📢 广告合作", callback_data="advertise"),
    ])
    keyboard_rows.append([InlineKeyboardButton("📊 数据统计", callback_data="stats")])

    # 热门关键词 - 构建文字提示
    kw_lines = []
    kw_limit = Config.HOT_KEYWORD_PER_CATEGORY_LIMIT
    for cat_name, cat_data in hot_keywords_by_cat.items():
        icon = cat_data.get("icon", "🔍")
        keywords = cat_data.get("keywords", [])
        if keywords:
            kw_list = [f"`{kw['keyword']}`" for kw in keywords[:kw_limit]]
            kw_lines.append(f"{icon} **{cat_name}**：{', '.join(kw_list)}")
    if not kw_lines:
        default_kw = ["比特币", "以太坊", "AI", "空投", "Python", "FastAPI"]
        kw_lines.append(f"🚀 **默认热门**：{', '.join(f'`{k}`' for k in default_kw)}")

    welcome = (
        f"👋 欢迎 **{user.first_name}**！\n\n"
        "🔍 **TG搜索Pro机器人**\n"
        "精准搜索TG频道/群组/消息内容\n\n"
        f"📋 每日免费搜索：{Config.FREE_SEARCH_DAILY_LIMIT} 次\n\n"
    )

    if featured_channels:
        welcome += "📣 **今日置顶推荐**\n点击按钮直达频道：\n\n"

    welcome += "\n".join(kw_lines) + "\n\n"
    welcome += "**使用方法：**\n"
    welcome += "• 直接发送关键词搜索\n"
    welcome += "• 点击置顶按钮访问推荐频道\n"
    welcome += "• /wallet 查看钱包余额\n"
    welcome += "• /advertise 广告合作\n"

    reply_markup = InlineKeyboardMarkup(keyboard_rows)
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


# ============ AI 智能搜索 ============
_user_ai_count: dict = {}


async def ai_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/aisearch 命令 - AI 智能搜索"""
    if not context.args:
        await update.message.reply_text(
            "🤖 **AI 智能搜索**\n\n"
            "用法：`/aisearch 你的问题`\n\n"
            "示例：\n"
            "• `/aisearch 最近有什么热门频道`\n"
            "• `/aisearch 帮我总结比特币相关内容`\n\n"
            "AI 会自动扩展关键词并生成智能摘要"
        )
        return

    keyword = " ".join(context.args).strip()
    if len(keyword) < 2:
        await update.message.reply_text("⚠️ 请输入至少2个字符的问题")
        return

    user_id = update.effective_user.id
    today = date.today()
    ai_stat = _user_ai_count.get(user_id, {"count": 0, "date": today})
    if ai_stat["date"] != today:
        ai_stat = {"count": 0, "date": today}

    free_limit = Config.AI_FREE_DAILY_LIMIT
    if free_limit > 0 and ai_stat["count"] >= free_limit:
        await update.message.reply_text(
            f"⚠️ 今日 AI 搜索次数已用完（{free_limit}次）\n"
            "明日重置或联系管理员开通更多次数"
        )
        return

    thinking_msg = await update.message.reply_text(f"🤖 AI 正在分析：`{keyword}` ...")

    try:
        from app.ai.model_service import ai_service
        from app.ai.settings_manager import record_ai_usage

        if not ai_service.is_configured():
            await thinking_msg.edit_text(
                "⚠️ AI 搜索功能尚未配置\n"
                "请联系管理员在后台配置 AI API Key"
            )
            return

        # 构建上下文：先用传统搜索获取结果
        search_results = await searcher.search(keyword)
        context_text = ""
        if search_results:
            for i, item in enumerate(search_results[:10], 1):
                channel = item.get("channel_title") or item.get("channel_username") or "未知"
                excerpt = item.get("excerpt") or ""
                date_str = item.get("msg_date", "")[:10] if item.get("msg_date") else ""
                context_text += f"{i}. [{channel}] {date_str}\n   {excerpt}\n\n"

        # AI 智能搜索
        if context_text and Config.AI_SUMMARIZE_RESULTS:
            result = await ai_service.smart_search(keyword, search_results)
        else:
            result = await ai_service.chat(keyword, context_text)

        content = result.get("content", "AI 未返回内容")
        model_name = result.get("model", "unknown")
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)

        # 记录用量
        try:
            await record_ai_usage(user_id, model_name, input_tokens, output_tokens)
        except Exception:
            pass

        ai_stat["count"] += 1
        _user_ai_count[user_id] = ai_stat

        # 截断过长内容
        if len(content) > 2000:
            content = content[:1997] + "..."

        remaining = free_limit - ai_stat["count"] if free_limit > 0 else "∞"
        reply_text = (
            f"🤖 **AI 搜索结果**\n\n"
            f"💬 问题：`{keyword}`\n\n"
            f"{content}\n\n"
            f"──\n"
            f"模型：{model_name} | "
            f"消耗：{input_tokens + output_tokens} tokens | "
            f"剩余 AI 次数：{remaining}"
        )
        await thinking_msg.edit_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"AI 搜索失败: {e}")
        await thinking_msg.edit_text(f"❌ AI 搜索出错：{str(e)[:200]}")


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ai 命令 - AI 对话"""
    if not context.args:
        await update.message.reply_text(
            "🤖 **AI 对话助手**\n\n"
            "用法：`/ai 你的问题`\n\n"
            "AI 可以回答各类问题，结合知识库内容\n\n"
            "示例：\n"
            "• `/ai 今天有什么新闻`\n"
            "• `/ai 什么是区块链`\n"
            "• `/ai 帮我写一段Python代码`"
        )
        return

    question = " ".join(context.args).strip()
    if len(question) < 2:
        await update.message.reply_text("⚠️ 请输入至少2个字符的问题")
        return

    user_id = update.effective_user.id
    today = date.today()
    ai_stat = _user_ai_count.get(user_id, {"count": 0, "date": today})
    if ai_stat["date"] != today:
        ai_stat = {"count": 0, "date": today}

    free_limit = Config.AI_FREE_DAILY_LIMIT
    if free_limit > 0 and ai_stat["count"] >= free_limit:
        await update.message.reply_text(
            f"⚠️ 今日 AI 次数已用完（{free_limit}次）\n明日重置"
        )
        return

    thinking_msg = await update.message.reply_text(f"🤖 AI 思考中：`{question}` ...")

    try:
        from app.ai.model_service import ai_service
        from app.ai.settings_manager import record_ai_usage

        if not ai_service.is_configured():
            await thinking_msg.edit_text(
                "⚠️ AI 功能尚未配置\n"
                "请联系管理员配置 AI API Key"
            )
            return

        # 用知识库内容作为上下文
        search_results = await searcher.search(question[:30])
        context_text = ""
        if search_results:
            for i, item in enumerate(search_results[:5], 1):
                channel = item.get("channel_title") or item.get("channel_username") or "未知"
                excerpt = item.get("excerpt") or ""
                context_text += f"{i}. [{channel}] {excerpt}\n"

        result = await ai_service.chat(question, context_text)
        content = result.get("content", "AI 未返回内容")
        model_name = result.get("model", "unknown")
        pool_used = result.get("pool_used", "")
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)

        try:
            await record_ai_usage(user_id, model_name, input_tokens, output_tokens)
        except Exception:
            pass

        ai_stat["count"] += 1
        _user_ai_count[user_id] = ai_stat

        if len(content) > 2000:
            content = content[:1997] + "..."

        remaining = free_limit - ai_stat["count"] if free_limit > 0 else "∞"
        pool_label = f"接口：{pool_used} | " if pool_used else ""
        reply_text = (
            f"🤖 **AI 回答**\n\n"
            f"💬 {question}\n\n"
            f"{content}\n\n"
            f"──\n"
            f"模型：{model_name} | {pool_label}消耗：{input_tokens + output_tokens} tokens | 剩余：{remaining}"
        )
        await thinking_msg.edit_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"AI 对话失败: {e}")
        await thinking_msg.edit_text(f"❌ AI 出错：{str(e)[:200]}")
