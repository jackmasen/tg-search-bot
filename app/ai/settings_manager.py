"""
AI 模型配置管理器
管理 AI API 配置和搜索日志
"""
from typing import Any, Dict, List, Optional
from loguru import logger
from app.database import get_db
from app.admin.system_settings_manager import (
    encode_value, decode_value, _encrypt, _decrypt,
)


# AI 配置项元数据
AI_SETTING_GROUPS = [
    {
        "group_key": "ai",
        "group_name": "AI模型配置",
        "icon": "🤖",
        "items": [
            {
                "key": "AI_PROVIDER",
                "type": "str",
                "label": "AI 提供商",
                "placeholder": "deepseek",
                "sensitive": False,
                "hint": "deepseek / openai / custom，自定义填 custom",
                "in_env": True,
            },
            {
                "key": "AI_API_BASE",
                "type": "str",
                "label": "API Base URL",
                "placeholder": "https://api.deepseek.com",
                "sensitive": False,
                "hint": "OpenAI 兼容 API 端点（不含 /chat/completions）",
                "in_env": True,
            },
            {
                "key": "AI_API_KEY",
                "type": "str",
                "label": "API Key",
                "placeholder": "sk-xxx",
                "sensitive": True,
                "hint": "🔒 加密存储。DeepSeek: platform.deepseek.com 申请",
                "in_env": True,
            },
            {
                "key": "AI_MODEL",
                "type": "str",
                "label": "默认模型名称",
                "placeholder": "deepseek-chat",
                "sensitive": False,
                "hint": "如 deepseek-chat、deepseek-coder、gpt-4o、claude-3-5-sonnet 等",
                "in_env": True,
            },
            {
                "key": "AI_MAX_TOKENS",
                "type": "int",
                "label": "单次最大 Token 数",
                "placeholder": "1024",
                "sensitive": False,
                "default": 1024,
                "in_env": True,
            },
            {
                "key": "AI_TEMPERATURE",
                "type": "float",
                "label": "温度（创造性 0-2）",
                "placeholder": "0.7",
                "sensitive": False,
                "default": 0.7,
                "in_env": True,
            },
            {
                "key": "AI_KEYWORD_EXPAND",
                "type": "bool",
                "label": "启用关键词扩展",
                "sensitive": False,
                "default": True,
                "hint": "搜索时自动扩展关键词，提升命中率",
                "in_env": True,
            },
            {
                "key": "AI_SUMMARIZE_RESULTS",
                "type": "bool",
                "label": "启用搜索结果 AI 总结",
                "sensitive": False,
                "default": True,
                "in_env": True,
            },
            {
                "key": "AI_FREE_DAILY_LIMIT",
                "type": "int",
                "label": "免费用户每日 AI 使用次数（0=无限）",
                "placeholder": "3",
                "sensitive": False,
                "default": 3,
                "in_env": True,
            },
            {
                "key": "AI_SEARCH_SYSTEM_PROMPT",
                "type": "str",
                "label": "搜索场景系统提示词",
                "sensitive": False,
                "default": "",
                "hint": "自定义 AI 在搜索场景下的系统角色描述",
                "in_env": True,
                "textarea": True,
            },
        ],
    },
]


# 所有 AI 相关配置键（用于加密判断）
AI_SENSITIVE_KEYS = {"AI_API_KEY"}


def get_ai_settings() -> List[Dict[str, Any]]:
    """获取所有 AI 配置项元数据"""
    return AI_SETTING_GROUPS


def is_ai_key_sensitive(key: str) -> bool:
    return key in AI_SENSITIVE_KEYS


async def get_ai_config() -> Dict[str, Any]:
    """从数据库加载 AI 配置"""
    out: Dict[str, Any] = {}
    try:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT setting_key, setting_value, value_type, is_encrypted "
                "FROM system_settings WHERE setting_key LIKE 'AI_%'"
            )
            rows = await cursor.fetchall()
            for r in rows:
                key = r["setting_key"]
                val = r["setting_value"] or ""
                if r["is_encrypted"] and val:
                    try:
                        from app.config import Config
                        crypto_secret = Config.CRYPTO_SECRET or "fallback_no_secret_2024"
                        val = _decrypt(val, crypto_secret)
                    except Exception:
                        pass
                out[key] = decode_value(val, r["value_type"])
    except Exception as e:
        logger.warning(f"加载 AI 配置失败: {e}")
    return out


async def save_ai_setting(key: str, value: Any) -> Dict[str, Any]:
    """保存单条 AI 配置"""
    from app.config import Config
    crypto_secret = Config.CRYPTO_SECRET or "fallback_no_secret_2024"
    value_type = "str"
    for g in AI_SETTING_GROUPS:
        for it in g["items"]:
            if it["key"] == key:
                value_type = it.get("type", "str")
                break
    encoded = encode_value(value, value_type)
    sensitive = is_ai_key_sensitive(key)
    if sensitive and encoded:
        encoded = _encrypt(encoded, crypto_secret)
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value=excluded.setting_value,
                value_type=excluded.value_type,
                is_encrypted=excluded.is_encrypted,
                description=excluded.description,
                updated_at=CURRENT_TIMESTAMP
            """,
            (key, encoded, value_type, 1 if sensitive else 0, f"AI配置: {key}"),
        )
        await db.commit()
    return {"ok": True, "key": key}


async def batch_save_ai_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """批量保存 AI 配置"""
    saved = []
    errors = []
    for k, v in payload.items():
        if not k.startswith("AI_"):
            continue
        try:
            await save_ai_setting(k, v)
            saved.append(k)
        except Exception as e:
            errors.append(f"{k}: {str(e)}")
    return {"saved": saved, "errors": errors}


async def get_ai_search_stats(limit: int = 30) -> List[Dict[str, Any]]:
    """获取 AI 搜索使用统计"""
    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT model_name, COUNT(*) as times,
                       SUM(input_tokens) as total_input,
                       SUM(output_tokens) as total_output,
                       created_at
                FROM ai_search_logs
                GROUP BY model_name, DATE(created_at)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in await cursor.fetchall()]
    except Exception as e:
        logger.warning(f"获取 AI 统计失败: {e}")
        return []


async def get_today_ai_usage(user_id: int) -> int:
    """获取用户今天的 AI 使用次数"""
    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) as cnt FROM ai_search_logs
                WHERE tg_user_id = ? AND DATE(created_at) = DATE('now','localtime')
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
            return row["cnt"] if row else 0
    except Exception:
        return 0


async def record_ai_usage(user_id: int, model_name: str, input_tokens: int, output_tokens: int):
    """记录 AI 使用"""
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO ai_search_logs (tg_user_id, model_name, input_tokens, output_tokens, created_at)
                VALUES (?, ?, ?, ?, datetime('now','localtime'))
                """,
                (user_id, model_name, input_tokens, output_tokens),
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"记录 AI 使用失败: {e}")
