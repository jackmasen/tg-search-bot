"""
AI 模块数据库迁移
"""
from loguru import logger


# AI 功能所需的建表 SQL
AI_SCHEMA_SQL = """
-- AI API 配置存储（通过 system_settings 管理，此处仅做说明）
-- AI 配置键：AI_PROVIDER, AI_API_BASE, AI_API_KEY, AI_MODEL, AI_MAX_TOKENS, AI_TEMPERATURE, ...

-- AI 搜索日志表
CREATE TABLE IF NOT EXISTS ai_search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER,
    model_name TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_logs_user ON ai_search_logs(tg_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_logs_date ON ai_search_logs(DATE(created_at));
"""


# AI 默认配置数据（首次启动时插入）
AI_DEFAULT_SETTINGS = [
    ("AI_PROVIDER", "deepseek", "str", 0, "AI模型提供商", "deepseek/openai/custom"),
    ("AI_API_BASE", "https://api.deepseek.com", "str", 0, "AI API Base URL", "OpenAI兼容接口地址"),
    ("AI_API_KEY", "", "str", 1, "AI API Key", "从 DeepSeek/OpenAI 平台获取"),
    ("AI_MODEL", "deepseek-chat", "str", 0, "默认AI模型", "deepseek-chat / deepseek-coder / gpt-4o"),
    ("AI_MAX_TOKENS", "1024", "int", 0, "单次最大Token数", "输出最大Token限制"),
    ("AI_TEMPERATURE", "0.7", "float", 0, "温度参数", "创造性程度，0-2，越高越有创意"),
    ("AI_KEYWORD_EXPAND", "1", "bool", 0, "启用关键词扩展", "搜索时自动扩展相关关键词"),
    ("AI_SUMMARIZE_RESULTS", "1", "bool", 0, "启用结果AI总结", "搜索结果自动生成摘要"),
    ("AI_FREE_DAILY_LIMIT", "3", "int", 0, "免费用户每日AI次数", "0表示不限"),
]


async def init_ai_schema():
    """初始化 AI 模块数据库表"""
    try:
        from app.database import get_db
        async with get_db() as db:
            await db.executescript(AI_SCHEMA_SQL)

            # 插入默认 AI 配置（如果不存在）
            for key, value, vtype, encrypted, desc, hint in AI_DEFAULT_SETTINGS:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, value, vtype, encrypted, hint),
                )
            await db.commit()
            logger.info("AI模块数据库初始化完成")
    except Exception as e:
        logger.warning(f"AI模块数据库初始化失败: {e}")
