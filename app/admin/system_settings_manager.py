"""
系统配置管理器
- 从数据库 system_settings 表读写配置
- 敏感字段使用 CRYPTO_SECRET AES 加密存储
- 启动时用 DB 配置覆盖 .env 配置
"""
import json
import base64
import hashlib
import time as _time
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet
    _HAS_CRYPTO = True
except ImportError:  # 没有 cryptography 时降级到简单 base64 混淆
    _HAS_CRYPTO = False


# ---------- 配置项元数据：定义哪些配置能在后台改 ----------
# 分 5 个分组：机器人 / 采集账号 / 搜索采集 / 钱包广告 / 系统安全
# FORBIDDEN = 只能在 .env 写（安全硬约束，禁止入库）
FORBIDDEN_IN_DB = set()  # 已改为全部支持后台配置
# SENSITIVE = 可以入库，但必须加密存储（如 Bot Token、API Hash、助记词）
SENSITIVE_KEYS = {
    "TG_BOT_TOKEN",
    "TELETHON_API_HASHS",
    "TRONGRID_API_KEY",
    "SESSION_SECRET",
    "CRYPTO_SECRET",
    "HD_WALLET_MNEMONIC",
}

SETTING_GROUPS: List[Dict[str, Any]] = [
    {
        "group_key": "bot",
        "group_name": "机器人配置",
        "icon": "🤖",
        "items": [
            {
                "key": "TG_BOT_TOKEN",
                "type": "str",
                "label": "TG Bot Token",
                "placeholder": "123456:ABC-DEF...",
                "sensitive": True,
                "hint": "由 @BotFather 申请，格式『数字:字母串』",
                "in_env": True,
            },
            {
                "key": "ADMIN_TG_IDS",
                "type": "list_int",
                "label": "管理员 TG ID",
                "placeholder": "888999000,987654321",
                "sensitive": False,
                "hint": "英文逗号分隔，填入后该 ID 的 TG 用户即为管理员",
                "in_env": True,
            },
        ],
    },
    {
        "group_key": "crawler",
        "group_name": "采集账号池",
        "icon": "🎣",
        "items": [
            {
                "key": "DEFAULT_API_ID",
                "type": "int",
                "label": "默认 api_id（所有小号共用）",
                "placeholder": "12345678",
                "sensitive": False,
                "hint": "一套凭据可供所有小号使用。申请自 my.telegram.org → API development tools",
                "in_env": True,
            },
            {
                "key": "DEFAULT_API_HASH",
                "type": "str",
                "label": "默认 api_hash（所有小号共用）",
                "placeholder": "32位hash值",
                "sensitive": True,
                "hint": "加密存储。与默认 api_id 配对使用，添加小号时自动填充",
                "in_env": True,
            },
            {
                "key": "TELETHON_API_IDS",
                "type": "list_int",
                "label": "Telethon api_id（逗号分隔）",
                "placeholder": "123456,789012",
                "sensitive": False,
                "hint": "（旧版）数量必须与 api_hash、phone 一致",
                "in_env": True,
            },
            {
                "key": "TELETHON_API_HASHS",
                "type": "list_str",
                "label": "Telethon api_hash（逗号分隔）",
                "placeholder": "abc123xxx, yyy789zzz",
                "sensitive": True,
                "hint": "（旧版）加密存储，申请自 my.telegram.org",
                "in_env": True,
            },
            {
                "key": "TELETHON_PHONES",
                "type": "list_str",
                "label": "采集手机号（逗号分隔）",
                "placeholder": "+8613800001111,+8613800002222",
                "sensitive": False,
                "hint": "带国际区号，每个号对应上方一组 api_id/hash",
                "in_env": True,
            },
        ],
    },
    {
        "group_key": "search",
        "group_name": "搜索与采集风控",
        "icon": "🔍",
        "items": [
            {"key": "SEARCH_RESULT_LIMIT", "type": "int", "label": "单次搜索返回条数", "sensitive": False, "default": 20, "in_env": True},
            {"key": "FREE_SEARCH_DAILY_LIMIT", "type": "int", "label": "免费用户每日搜索次数（0=无限）", "sensitive": False, "default": 5, "in_env": True},
            {"key": "FEATURED_AD_LIMIT", "type": "int", "label": "首页推荐广告展示数量", "sensitive": False, "default": 10, "hint": "用户打开Bot首页时展示的推荐频道数量", "in_env": True},
            {"key": "HOT_KEYWORD_PER_CATEGORY_LIMIT", "type": "int", "label": "每个分类展示关键词数量", "sensitive": False, "default": 8, "hint": "Bot首页每个分类最多显示的关键词数", "in_env": True},
            {"key": "MAX_CHANNELS_PER_ACCOUNT", "type": "int", "label": "单账号最大订阅频道数（上限500）", "sensitive": False, "default": 450, "in_env": True},
            {"key": "JOIN_INTERVAL_SECONDS", "type": "int", "label": "每次 Join 间隔秒数", "sensitive": False, "default": 45, "in_env": True},
            {"key": "MAX_JOIN_PER_DAY", "type": "int", "label": "单账号每日最大 Join 次数", "sensitive": False, "default": 40, "in_env": True},
        ],
    },
    {
        "group_key": "wallet",
        "group_name": "钱包与广告定价",
        "icon": "💰",
        "items": [
            {
                "key": "TRONGRID_API_KEY",
                "type": "str",
                "label": "TronGrid API Key",
                "sensitive": True,
                "hint": "www.trongrid.io 免费申请，用于充值对账",
                "in_env": True,
            },
            {"key": "RECHARGE_CONFIRMATIONS", "type": "int", "label": "充值确认区块数", "sensitive": False, "default": 12, "in_env": True},
            {"key": "MIN_RECHARGE_AMOUNT", "type": "float", "label": "链上最低充值金额（USDT）", "sensitive": False, "default": 0.5, "in_env": True},
            {"key": "MIN_RECHARGE_USER", "type": "float", "label": "普通会员最低充值（USDT）", "sensitive": False, "default": 10, "in_env": True},
            {"key": "MIN_RECHARGE_ADVERTISER", "type": "float", "label": "广告主最低充值（USDT）", "sensitive": False, "default": 20, "in_env": True},
            {"key": "CUSTOM_BOT_SETUP_FEE_USDT", "type": "float", "label": "专属机器人开通费（USDT）", "sensitive": False, "default": 500, "in_env": True},
            {"key": "MONTHLY_SUBSCRIPTION_USDT", "type": "float", "label": "月度订阅（USDT）", "sensitive": False, "default": 99, "in_env": True},
            {"key": "QUARTERLY_SUBSCRIPTION_USDT", "type": "float", "label": "季度订阅（USDT）", "sensitive": False, "default": 267, "in_env": True},
            {"key": "YEARLY_SUBSCRIPTION_USDT", "type": "float", "label": "年度订阅（USDT）", "sensitive": False, "default": 950, "in_env": True},
            {"key": "DEFAULT_CPC_PRICE", "type": "float", "label": "默认 CPC 单价（USDT/点击）", "sensitive": False, "default": 0.01, "in_env": True},
            {"key": "DEFAULT_CPM_PRICE", "type": "float", "label": "默认 CPM 单价（USDT/千曝）", "sensitive": False, "default": 0.5, "in_env": True},
            {"key": "MIN_AD_BUDGET_USDT", "type": "float", "label": "广告最低预算（USDT）", "sensitive": False, "default": 1, "in_env": True},
            {"key": "MAX_DAILY_SPEND_USDT", "type": "float", "label": "每日最高消耗上限（0=不限）", "sensitive": False, "default": 0, "in_env": True},
        ],
    },
    {
        "group_key": "system",
        "group_name": "系统与安全",
        "icon": "⚙️",
        "items": [
            {
                "key": "ADMIN_USERNAME",
                "type": "str",
                "label": "管理员账号",
                "placeholder": "admin",
                "sensitive": False,
                "hint": "后台登录账号，修改后需要用新账号登录",
                "in_env": True,
            },
            {
                "key": "ADMIN_PASSWORD",
                "type": "str",
                "label": "管理员密码",
                "placeholder": "至少6位",
                "sensitive": True,
                "hint": "🔒 加密存储。修改后立即生效",
                "in_env": True,
            },
            {
                "key": "HD_WALLET_MNEMONIC",
                "type": "str",
                "label": "HD 钱包助记词",
                "placeholder": "word1 word2 word3 ... word12",
                "sensitive": True,
                "hint": "🔒 12 个英文单词，加密存储，不可导出。务必离线备份！",
                "in_env": True,
                "textarea": True,
            },
            {"key": "SESSION_DIR", "type": "str", "label": "采集账号会话目录", "sensitive": False, "default": "./data/sessions", "in_env": True},
            {"key": "DB_PATH", "type": "str", "label": "SQLite 数据库路径", "sensitive": False, "default": "./data/tg_search.db", "in_env": True},
            {"key": "LOG_DIR", "type": "str", "label": "日志目录", "sensitive": False, "default": "./logs", "in_env": True},
            {"key": "LOG_LEVEL", "type": "str", "label": "日志级别（DEBUG/INFO/WARNING/ERROR）", "sensitive": False, "default": "INFO", "in_env": True},
            {"key": "VERSION_REPO_URL", "type": "str", "label": "版本更新 Git 仓库（可选）", "sensitive": False, "default": "", "in_env": True},
        ],
    },
    {
        "group_key": "ai",
        "group_name": "AI 智能搜索",
        "icon": "🤖",
        "items": [
            {
                "key": "AI_PROVIDER",
                "type": "str",
                "label": "AI 模型提供商",
                "placeholder": "deepseek",
                "sensitive": False,
                "hint": "deepseek / openai / custom，自定义时请同时设置 AI_API_BASE",
                "in_env": True,
            },
            {
                "key": "AI_API_BASE",
                "type": "str",
                "label": "AI API Base URL",
                "placeholder": "https://api.deepseek.com",
                "sensitive": False,
                "hint": "OpenAI 兼容接口地址，如 https://api.deepseek.com 或 https://api.openai.com",
                "in_env": True,
            },
            {
                "key": "AI_API_KEY",
                "type": "str",
                "label": "AI API Key",
                "placeholder": "sk-xxxxxxxx",
                "sensitive": True,
                "hint": "🔒 从 DeepSeek/OpenAI 平台获取，加密存储。必须配置后才能使用 AI 搜索功能",
                "in_env": True,
            },
            {
                "key": "AI_MODEL",
                "type": "str",
                "label": "默认 AI 模型",
                "placeholder": "deepseek-chat",
                "sensitive": False,
                "hint": "支持的模型：deepseek-chat / deepseek-coder / gpt-4o / gpt-4o-mini 等",
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
                "label": "温度参数（创造性）",
                "placeholder": "0.7",
                "sensitive": False,
                "default": 0.7,
                "hint": "0-2 之间，越低越准确，越高越有创意。搜索场景建议 0.3-0.7",
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
        ],
    },
]


def _get_meta_by_key(key: str) -> Optional[Dict[str, Any]]:
    for g in SETTING_GROUPS:
        for it in g["items"]:
            if it["key"] == key:
                return it
    return None


def is_key_allowed(key: str) -> bool:
    return key not in FORBIDDEN_IN_DB


def is_key_sensitive(key: str) -> bool:
    return key in SENSITIVE_KEYS or (_get_meta_by_key(key) or {}).get("sensitive", False)


# ---------- 加解密 ----------
def _fernet_key(crypto_secret: str) -> bytes:
    if not crypto_secret:
        raise RuntimeError("CRYPTO_SECRET 为空，无法加密敏感配置")
    raw = hashlib.sha256(crypto_secret.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _encrypt(value: str, crypto_secret: str) -> str:
    if not value:
        return ""
    if _HAS_CRYPTO:
        f = Fernet(_fernet_key(crypto_secret))
        return "ENC:" + f.encrypt(value.encode()).decode()
    # 降级：简单混淆（仅当 cryptography 未安装时）
    return "B64:" + base64.b64encode(value.encode()).decode()


def _decrypt(value: str, crypto_secret: str) -> str:
    if not value:
        return ""
    if value.startswith("ENC:"):
        if not _HAS_CRYPTO:
            raise RuntimeError("cryptography 未安装，无法解密数据")
        f = Fernet(_fernet_key(crypto_secret))
        return f.decrypt(value[4:].encode()).decode()
    if value.startswith("B64:"):
        return base64.b64decode(value[4:].encode()).decode()
    return value


# ---------- 类型编码/解码 ----------
def encode_value(value: Any, value_type: str) -> str:
    if value_type in ("int", "float", "str", "bool"):
        return str(value) if value is not None else ""
    if value_type in ("list_int", "list_str"):
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(str(x) for x in value)
        return str(value)
    if value_type == "json":
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else ""


def decode_value(raw: str, value_type: str) -> Any:
    if raw is None or raw == "":
        if value_type in ("list_int", "list_str"):
            return []
        if value_type == "int":
            return 0
        if value_type == "float":
            return 0.0
        if value_type == "bool":
            return False
        if value_type == "json":
            return None
        return ""
    if value_type == "int":
        try:
            return int(raw)
        except ValueError:
            return 0
    if value_type == "float":
        try:
            return float(raw)
        except ValueError:
            return 0.0
    if value_type == "bool":
        return str(raw).lower() in ("1", "true", "yes", "on")
    if value_type == "list_int":
        res = []
        for x in str(raw).split(","):
            x = x.strip()
            if not x:
                continue
            try:
                res.append(int(x))
            except ValueError:
                pass
        return res
    if value_type == "list_str":
        return [x.strip() for x in str(raw).split(",") if x.strip()]
    if value_type == "json":
        try:
            return json.loads(raw)
        except Exception:
            return None
    return raw


# ---------- 读写 DB ----------
async def load_all_settings_from_db(db) -> Dict[str, Any]:
    """从 system_settings 加载所有配置（返回已解码的 dict）

    关键：CRYPTO_SECRET 本身不加密（value_type=str, is_encrypted=0），
    所以必须先单独取出它，再用于解密其他加密字段。
    """
    from app.config import Config as _C

    rows = await db.execute_fetchall(
        "SELECT setting_key, setting_value, value_type, is_encrypted FROM system_settings"
    )
    # 第一遍：先提取 CRYPTO_SECRET（它本身不加密，是解密的密钥）
    crypto_secret = _C.CRYPTO_SECRET or "fallback_no_secret_2024"
    for r in rows:
        if r["setting_key"] == "CRYPTO_SECRET" and not r["is_encrypted"]:
            v = decode_value(r["setting_value"] or "", r["value_type"])
            if v:
                crypto_secret = str(v)
            break

    out: Dict[str, Any] = {}
    for r in rows:
        key = r["setting_key"]
        if not is_key_allowed(key):
            continue
        raw = r["setting_value"] or ""
        if r["is_encrypted"] and raw:
            try:
                raw = _decrypt(raw, crypto_secret)
            except Exception:
                try:
                    raw = _decrypt(raw, "fallback_no_secret_2024")
                except Exception:
                    raw = ""
        out[key] = decode_value(raw, r["value_type"])
    return out


async def upsert_setting(db, key: str, value: Any) -> Dict[str, Any]:
    """保存单条配置（加密、编码、落库一体化）"""
    from app.config import Config as _C

    if not is_key_allowed(key):
        raise ValueError(f"[{key}] 为安全硬约束配置，禁止存入数据库，请在 .env 文件中配置")

    meta = _get_meta_by_key(key) or {}
    value_type = meta.get("type", "str")
    sensitive = is_key_sensitive(key)
    description = meta.get("hint", "") or meta.get("label", "")

    crypto_secret = _C.CRYPTO_SECRET or ""
    encoded = encode_value(value, value_type)
    if sensitive:
        if not crypto_secret:
            # 无加密密钥时降级为简单混淆，允许保存
            crypto_secret = "fallback_no_secret_2024"
        encoded = _encrypt(encoded, crypto_secret)

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
        (key, encoded, value_type, 1 if sensitive else 0, description),
    )
    await db.commit()
    return {"ok": True, "key": key}


async def reset_setting(db, key: str) -> Dict[str, Any]:
    """删除单条 DB 配置（回退到 .env 默认值）"""
    if not is_key_allowed(key):
        raise ValueError(f"[{key}] 为安全硬约束，只能在 .env 中修改，无法重置")
    await db.execute("DELETE FROM system_settings WHERE setting_key=?", (key,))
    await db.commit()
    return {"ok": True, "key": key}


async def bulk_save_settings(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    """批量保存（忽略安全硬约束字段）"""
    forbidden_hit = []
    saved = []
    errors = []
    for k, v in payload.items():
        if k in FORBIDDEN_IN_DB:
            forbidden_hit.append(k)
            continue
        try:
            await upsert_setting(db, k, v)
            saved.append(k)
        except Exception as e:
            errors.append(f"{k}: {str(e)}")
    return {"saved": saved, "forbidden": forbidden_hit, "errors": errors}


def merge_env_with_db(env_values: Dict[str, Any], db_values: Dict[str, Any]) -> Dict[str, Any]:
    """配置合并：DB 覆盖 .env（但安全硬约束只能从 .env 来，DB 存了也忽略）"""
    merged = dict(env_values)
    for k, v in db_values.items():
        if k in FORBIDDEN_IN_DB:
            continue
        merged[k] = v
    return merged
