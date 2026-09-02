"""
AI 模型配置管理器
管理 AI API 池和搜索日志
支持多 API 配置 + 自动故障切换
"""
import json
from typing import Any, Dict, List, Optional
from loguru import logger
from app.database import get_db
from app.admin.system_settings_manager import (
    encode_value, decode_value, _encrypt, _decrypt,
)


AI_SETTING_GROUPS = [
    {
        "group_key": "ai",
        "group_name": "AI 智能搜索",
        "icon": "🤖",
        "items": [
            {
                "key": "AI_PROVIDER",
                "type": "str",
                "label": "AI 提供商",
                "placeholder": "deepseek",
                "sensitive": False,
                "hint": "deepseek / openai / custom，自定义时请同时设置 AI_API_BASE",
                "in_env": True,
            },
            {
                "key": "AI_API_BASE",
                "type": "str",
                "label": "默认 API Base URL",
                "placeholder": "https://api.deepseek.com",
                "sensitive": False,
                "hint": "OpenAI 兼容接口地址（多 API 池场景下，各接口 Base 在 AI_API_KEYS 中单独配置）",
                "in_env": True,
            },
            {
                "key": "AI_MODEL",
                "type": "str",
                "label": "默认模型名称",
                "placeholder": "deepseek-chat",
                "sensitive": False,
                "hint": "如 deepseek-chat、gpt-4o、gpt-4o-mini 等（各接口模型可在 AI_API_KEYS 中单独配置）",
                "in_env": True,
            },
            {
                "key": "AI_MAX_TOKENS",
                "type": "int",
                "label": "单次最大 Token 数",
                "placeholder": "1024",
                "sensitive": False,
                "default": 1024,
                "hint": "AI 输出最大 Token 限制，越大内容越长但成本越高",
                "in_env": True,
            },
            {
                "key": "AI_TEMPERATURE",
                "type": "float",
                "label": "温度参数（创造性 0-2）",
                "placeholder": "0.7",
                "sensitive": False,
                "default": 0.7,
                "hint": "越低越准确，越高越有创意。搜索场景建议 0.3-0.7",
                "in_env": True,
            },
            {
                "key": "AI_KEYWORD_EXPAND",
                "type": "bool",
                "label": "启用关键词自动扩展",
                "sensitive": False,
                "default": True,
                "hint": "搜索时 AI 自动扩展相关关键词，提升搜索结果覆盖率",
                "in_env": True,
            },
            {
                "key": "AI_SUMMARIZE_RESULTS",
                "type": "bool",
                "label": "启用结果 AI 摘要",
                "sensitive": False,
                "default": True,
                "hint": "搜索结果生成 AI 智能摘要，帮助用户快速获取关键信息",
                "in_env": True,
            },
            {
                "key": "AI_FREE_DAILY_LIMIT",
                "type": "int",
                "label": "免费用户每日 AI 次数（0=不限）",
                "placeholder": "3",
                "sensitive": False,
                "default": 3,
                "hint": "免费用户每天可使用 AI 搜索的次数，0 表示不限制",
                "in_env": True,
            },
            {
                "key": "AI_SEARCH_SYSTEM_PROMPT",
                "type": "str",
                "label": "搜索场景系统提示词",
                "sensitive": False,
                "default": "",
                "hint": "自定义 AI 在搜索场景下的角色描述",
                "in_env": True,
                "textarea": True,
            },
        ],
    },
]

AI_SENSITIVE_KEYS = {"AI_API_KEY"}


def get_ai_settings() -> List[Dict[str, Any]]:
    return AI_SETTING_GROUPS


def is_ai_key_sensitive(key: str) -> bool:
    return key in AI_SENSITIVE_KEYS


async def get_ai_config() -> Dict[str, Any]:
    """从数据库加载 AI 配置，包括多 API 池 (AI_API_KEYS)"""
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
    """批量保存 AI 配置（不含 AI_API_KEYS，该字段由专用接口管理）"""
    saved = []
    errors = []
    for k, v in payload.items():
        if not k.startswith("AI_") or k == "AI_API_KEYS":
            continue
        try:
            await save_ai_setting(k, v)
            saved.append(k)
        except Exception as e:
            errors.append(f"{k}: {str(e)}")
    return {"saved": saved, "errors": errors}


# ============ 多 API 池管理 ============

async def get_ai_api_keys() -> List[dict]:
    """获取 API 池配置（解密后的列表）"""
    try:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT setting_value, is_encrypted FROM system_settings WHERE setting_key = 'AI_API_KEYS'"
            )
            row = await cursor.fetchone()
            if not row or not row["setting_value"]:
                return []
            val = row["setting_value"]
            if row["is_encrypted"]:
                try:
                    from app.config import Config
                    crypto_secret = Config.CRYPTO_SECRET or "fallback_no_secret_2024"
                    val = _decrypt(val, crypto_secret)
                except Exception:
                    pass
            return json.loads(val)
    except Exception as e:
        logger.warning(f"获取 API 池失败: {e}")
        return []


async def save_ai_api_keys(keys: List[dict]) -> Dict[str, Any]:
    """保存 API 池配置（加密存储）"""
    from app.config import Config
    crypto_secret = Config.CRYPTO_SECRET or "fallback_no_secret_2024"
    encoded = _encrypt(json.dumps(keys, ensure_ascii=False), crypto_secret)
    try:
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
                ("AI_API_KEYS", encoded, "json", 1, "AI多API池配置"),
            )
            await db.commit()
        return {"ok": True}
    except Exception as e:
        logger.error(f"保存 API 池失败: {e}")
        return {"ok": False, "error": str(e)}


async def add_ai_api_key(item: dict) -> Dict[str, Any]:
    """向 API 池添加一个新接口"""
    keys = await get_ai_api_keys()
    # 自动分配 priority（取当前最大 + 1）
    max_priority = max((k.get("priority", 0) for k in keys), default=0)
    item.setdefault("priority", max_priority + 1)
    item.setdefault("enabled", True)
    item.setdefault("name", f"接口{len(keys) + 1}")
    keys.append(item)
    return await save_ai_api_keys(keys)


async def update_ai_api_key(index: int, item: dict) -> Dict[str, Any]:
    """更新 API 池中指定索引的接口"""
    keys = await get_ai_api_keys()
    if 0 <= index < len(keys):
        keys[index].update(item)
        return await save_ai_api_keys(keys)
    return {"ok": False, "error": "索引越界"}


async def delete_ai_api_key(index: int) -> Dict[str, Any]:
    """删除 API 池中指定索引的接口"""
    keys = await get_ai_api_keys()
    if 0 <= index < len(keys):
        removed = keys.pop(index)
        return await save_ai_api_keys(keys)
    return {"ok": False, "error": "索引越界"}


async def toggle_ai_api_key(index: int, enabled: bool) -> Dict[str, Any]:
    """启用/禁用 API 池中指定索引的接口"""
    keys = await get_ai_api_keys()
    if 0 <= index < len(keys):
        keys[index]["enabled"] = enabled
        return await save_ai_api_keys(keys)
    return {"ok": False, "error": "索引越界"}


# ============ 统计 ============

async def get_ai_search_stats(limit: int = 30) -> List[Dict[str, Any]]:
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
