"""
TG搜索机器人 - 主启动入口
启动流程：初始化DB → 加载DB配置覆盖.env → 初始化账号池 → 启动Bot → 启动监听
"""
import asyncio
import sys
import os
from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import Config
from app.database import init_db
from app.crawler.account_pool import account_pool
from app.crawler.message_listener import message_listener
from app.bot.handlers import (
    start_command,
    help_command,
    stats_command,
    add_channel_command,
    search_handler,
    wallet_command,
    recharge_command,
    check_recharge_command,
    advertise_command,
    create_ad_command,
    my_ads_command,
    ad_templates_command,
    ad_stats_command,
    ai_search_command,
    ai_command,
    kw_callback_handler,
)


async def _load_config_from_db():
    """从数据库加载配置并覆盖内存 Config（DB > .env）"""
    try:
        from app.database import get_db
        from app.admin.system_settings_manager import load_all_settings_from_db
        async with get_db() as db:
            db_vals = await load_all_settings_from_db(db)
            if db_vals:
                Config.apply_overrides(db_vals)
                logger.info(f"已从数据库加载配置，生效项: {list(db_vals.keys())}")
    except Exception as e:
        logger.warning(f"数据库配置加载失败（使用 .env 配置）: {e}")


# 日志配置
def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - {message}",
    )
    logger.add(
        f"{Config.LOG_DIR}/bot_{{time}}.log",
        rotation="10 MB",
        retention="30 days",
        level=Config.LOG_LEVEL,
        encoding="utf-8",
    )
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - {message}",
    )
    logger.add(
        f"{Config.LOG_DIR}/bot_{{time}}.log",
        rotation="10 MB",
        retention="30 days",
        level=Config.LOG_LEVEL,
        encoding="utf-8",
    )


async def post_init(app: Application):
    """Bot启动后的初始化（在事件循环中执行）"""
    logger.info("加载数据库配置...")
    await _load_config_from_db()

    logger.info("初始化数据库...")
    await init_db()

    logger.info("初始化采集账号池...")
    await account_pool.initialize()

    logger.info("启动实时消息监听...")
    await message_listener.start_listening()

    logger.success("TG搜索机器人启动完成！")


def main():
    """主入口"""
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    setup_logging()

    # 校验配置
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置错误:\n{e}")
        logger.error("请复制 .env.example 为 .env 并填写真实配置")
        sys.exit(1)

    logger.info(f"启动 TG搜索机器人 v{Config.APP_VERSION}")
    logger.info(f"Bot Token: {'已配置 ✓' if Config.BOT_TOKEN else '未配置（将从数据库加载）'}")

    # 提前加载DB配置（在构建Application之前，确保BOT_TOKEN已就位）
    logger.info("提前加载数据库配置...")
    asyncio.run(_load_config_from_db())
    logger.info(f"Bot Token: {'已配置 ✓' if Config.BOT_TOKEN else '仍未配置，将尝试启动'}")

    # 创建Bot应用
    application = Application.builder().token(Config.BOT_TOKEN).post_init(post_init).build()

    # 注册命令
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("add", add_channel_command))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("recharge", recharge_command))
    application.add_handler(CommandHandler("checkrecharge", check_recharge_command))
    application.add_handler(CommandHandler("advertise", advertise_command))
    application.add_handler(CommandHandler("createad", create_ad_command))
    application.add_handler(CommandHandler("myads", my_ads_command))
    application.add_handler(CommandHandler("adtemplates", ad_templates_command))
    application.add_handler(CommandHandler("adstats", ad_stats_command))
    application.add_handler(CommandHandler("aisearch", ai_search_command))
    application.add_handler(CommandHandler("ai", ai_command))

    # 注册回调查询处理
    application.add_handler(CallbackQueryHandler(kw_callback_handler))

    # 注册文本搜索（非命令消息）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    # 启动Bot（polling模式）
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
