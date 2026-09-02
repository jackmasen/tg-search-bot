"""
配置管理模块
从环境变量读取所有配置，集中管理
"""
import os
from loguru import logger
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


def _safe_int(value, default=0):
    """安全转 int：占位符(如 your_xxx)/空值 返回 default，不抛异常"""
    if not value:
        return default
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def _safe_float(value, default=0.0):
    """安全转 float：占位符/空值 返回 default，不抛异常"""
    if not value:
        return default
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


def _parse_int_list(raw):
    """解析逗号分隔的整数列表，跳过非数字占位符"""
    result = []
    if not raw:
        return result
    for x in str(raw).split(","):
        x = x.strip()
        if not x:
            continue
        try:
            result.append(int(x))
        except ValueError:
            # 占位符(如 your_api_id_1)跳过，后续 validate() 会报告
            continue
    return result


def _parse_str_list(raw):
    """解析逗号分隔的字符串列表"""
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(",") if x.strip()]


class Config:
    """全局配置"""

    # ===== TG Bot =====
    BOT_TOKEN: str = os.getenv("TG_BOT_TOKEN", "")

    # ===== Telethon 账号池 =====
    API_IDS: list = _parse_int_list(os.getenv("TELETHON_API_IDS", ""))
    API_HASHES: list = _parse_str_list(os.getenv("TELETHON_API_HASHS", ""))
    PHONES: list = _parse_str_list(os.getenv("TELETHON_PHONES", ""))
    DEFAULT_API_ID: int = _safe_int(os.getenv("DEFAULT_API_ID", ""))
    DEFAULT_API_HASH: str = os.getenv("DEFAULT_API_HASH", "")
    SESSION_DIR: str = os.getenv("SESSION_DIR", "./data/sessions")

    # ===== 数据库 =====
    DB_PATH: str = os.getenv("DB_PATH", "./data/tg_search.db")

    # ===== 采集风控 =====
    MAX_CHANNELS_PER_ACCOUNT: int = _safe_int(os.getenv("MAX_CHANNELS_PER_ACCOUNT"), 450)
    JOIN_INTERVAL_SECONDS: int = _safe_int(os.getenv("JOIN_INTERVAL_SECONDS"), 45)
    MAX_JOIN_PER_DAY: int = _safe_int(os.getenv("MAX_JOIN_PER_DAY"), 40)

    # ===== 搜索 =====
    SEARCH_RESULT_LIMIT: int = _safe_int(os.getenv("SEARCH_RESULT_LIMIT"), 20)
    FREE_SEARCH_DAILY_LIMIT: int = _safe_int(os.getenv("FREE_SEARCH_DAILY_LIMIT"), 5)

    # ===== AI 智能搜索 =====
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "deepseek")
    AI_API_BASE: str = os.getenv("AI_API_BASE", "https://api.deepseek.com")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-chat")
    AI_MAX_TOKENS: int = _safe_int(os.getenv("AI_MAX_TOKENS"), 1024)
    AI_TEMPERATURE: float = _safe_float(os.getenv("AI_TEMPERATURE"), 0.7)
    AI_KEYWORD_EXPAND: bool = os.getenv("AI_KEYWORD_EXPAND", "1") in ("1", "true", "yes")
    AI_SUMMARIZE_RESULTS: bool = os.getenv("AI_SUMMARIZE_RESULTS", "1") in ("1", "true", "yes")
    AI_FREE_DAILY_LIMIT: int = _safe_int(os.getenv("AI_FREE_DAILY_LIMIT"), 3)

    # ===== 前端展示数量 =====
    FEATURED_AD_LIMIT: int = _safe_int(os.getenv("FEATURED_AD_LIMIT"), 10)
    HOT_KEYWORD_PER_CATEGORY_LIMIT: int = _safe_int(os.getenv("HOT_KEYWORD_PER_CATEGORY_LIMIT"), 8)

    # ===== 日志 =====
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ===== 钱包（USDT-TRC20 HD钱包）=====
    # HD钱包助记词（12/24词，空格分隔），从.env读取
    HD_WALLET_MNEMONIC: str = os.getenv("HD_WALLET_MNEMONIC", "")
    # BIP44基础路径：TRON是m/44'/195'/0'/0
    HD_DERIVATION_BASE: str = "m/44'/195'/0'/0"
    # 主地址归集索引（运营方TronLink里默认看到的就是索引0地址）
    HD_MAIN_INDEX: int = 0
    # TronGrid API Key（免费申请 https://www.trongrid.io/）
    TRONGRID_API_KEY: str = os.getenv("TRONGRID_API_KEY", "")
    TRONGRID_API_URL: str = "https://api.trongrid.io"
    # USDT-TRC20合约地址（主网固定值，勿改）
    USDT_TRC20_CONTRACT: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    # 充值确认区块数（TRON约3秒/块，12块≈36秒安全）
    RECHARGE_CONFIRMATIONS: int = _safe_int(os.getenv("RECHARGE_CONFIRMATIONS"), 12)
    # 最低充值金额USDT（低于此数的小额转账忽略，防止灰尘攻击）
    MIN_RECHARGE_AMOUNT: float = _safe_float(os.getenv("MIN_RECHARGE_AMOUNT"), 0.5)
    # 普通用户最低充值
    MIN_RECHARGE_USER: float = _safe_float(os.getenv("MIN_RECHARGE_USER"), 10)
    # 广告主最低充值
    MIN_RECHARGE_ADVERTISER: float = _safe_float(os.getenv("MIN_RECHARGE_ADVERTISER"), 20)
    # 业务定价
    CUSTOM_BOT_SETUP_FEE_USDT: float = _safe_float(os.getenv("CUSTOM_BOT_SETUP_FEE_USDT"), 500)
    MONTHLY_SUBSCRIPTION_USDT: float = _safe_float(os.getenv("MONTHLY_SUBSCRIPTION_USDT"), 99)
    QUARTERLY_SUBSCRIPTION_USDT: float = _safe_float(os.getenv("QUARTERLY_SUBSCRIPTION_USDT"), 267)
    YEARLY_SUBSCRIPTION_USDT: float = _safe_float(os.getenv("YEARLY_SUBSCRIPTION_USDT"), 950)

    # ===== 安全密钥 =====
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")
    CRYPTO_SECRET: str = os.getenv("CRYPTO_SECRET", "")

    # ===== 管理员 =====
    ADMIN_TG_IDS: list = _parse_int_list(os.getenv("ADMIN_TG_IDS", ""))

    # ===== 广告系统定价默认值 =====
    DEFAULT_CPC_PRICE: float = _safe_float(os.getenv("DEFAULT_CPC_PRICE"), 0.01)
    DEFAULT_CPM_PRICE: float = _safe_float(os.getenv("DEFAULT_CPM_PRICE"), 0.5)
    MIN_AD_BUDGET_USDT: float = _safe_float(os.getenv("MIN_AD_BUDGET_USDT"), 1)
    MAX_DAILY_SPEND_USDT: float = _safe_float(os.getenv("MAX_DAILY_SPEND_USDT"), 0)

    # ===== 版本与备份 =====
    APP_VERSION: str = "1.0.25"
    BACKUP_DIR: str = "./data/backups"
    BACKUP_KEEP_COUNT: int = 10  # 保留最近10份备份
    VERSION_REPO_URL: str = os.getenv("VERSION_REPO_URL", "")  # Git仓库地址，用于拉取更新

    @classmethod
    def apply_overrides(cls, overrides: dict):
        """应用 DB 配置覆盖（DB > .env > 默认值），安全硬约束字段会被忽略"""
        from app.admin.system_settings_manager import FORBIDDEN_IN_DB

        mapping = {
            "TG_BOT_TOKEN": "BOT_TOKEN",
            "TELETHON_API_IDS": "API_IDS",
            "TELETHON_API_HASHS": "API_HASHES",
            "TELETHON_PHONES": "PHONES",
            "DEFAULT_API_ID": "DEFAULT_API_ID",
            "DEFAULT_API_HASH": "DEFAULT_API_HASH",
            "SESSION_DIR": "SESSION_DIR",
            "DB_PATH": "DB_PATH",
            "MAX_CHANNELS_PER_ACCOUNT": "MAX_CHANNELS_PER_ACCOUNT",
            "JOIN_INTERVAL_SECONDS": "JOIN_INTERVAL_SECONDS",
            "MAX_JOIN_PER_DAY": "MAX_JOIN_PER_DAY",
            "SEARCH_RESULT_LIMIT": "SEARCH_RESULT_LIMIT",
            "FREE_SEARCH_DAILY_LIMIT": "FREE_SEARCH_DAILY_LIMIT",
            "FEATURED_AD_LIMIT": "FEATURED_AD_LIMIT",
            "HOT_KEYWORD_PER_CATEGORY_LIMIT": "HOT_KEYWORD_PER_CATEGORY_LIMIT",
            "HD_WALLET_MNEMONIC": "HD_WALLET_MNEMONIC",
            "TRONGRID_API_KEY": "TRONGRID_API_KEY",
            "RECHARGE_CONFIRMATIONS": "RECHARGE_CONFIRMATIONS",
            "MIN_RECHARGE_AMOUNT": "MIN_RECHARGE_AMOUNT",
            "MIN_RECHARGE_USER": "MIN_RECHARGE_USER",
            "MIN_RECHARGE_ADVERTISER": "MIN_RECHARGE_ADVERTISER",
            "CUSTOM_BOT_SETUP_FEE_USDT": "CUSTOM_BOT_SETUP_FEE_USDT",
            "MONTHLY_SUBSCRIPTION_USDT": "MONTHLY_SUBSCRIPTION_USDT",
            "QUARTERLY_SUBSCRIPTION_USDT": "QUARTERLY_SUBSCRIPTION_USDT",
            "YEARLY_SUBSCRIPTION_USDT": "YEARLY_SUBSCRIPTION_USDT",
            "DEFAULT_CPC_PRICE": "DEFAULT_CPC_PRICE",
            "DEFAULT_CPM_PRICE": "DEFAULT_CPM_PRICE",
            "MIN_AD_BUDGET_USDT": "MIN_AD_BUDGET_USDT",
            "MAX_DAILY_SPEND_USDT": "MAX_DAILY_SPEND_USDT",
            "SESSION_SECRET": "SESSION_SECRET",
            "CRYPTO_SECRET": "CRYPTO_SECRET",
            "ADMIN_TG_IDS": "ADMIN_TG_IDS",
            "LOG_DIR": "LOG_DIR",
            "LOG_LEVEL": "LOG_LEVEL",
            "VERSION_REPO_URL": "VERSION_REPO_URL",
        }
        applied = []
        ignored = []
        for env_key, value in overrides.items():
            if env_key in FORBIDDEN_IN_DB:
                ignored.append(env_key)
                continue
            if env_key not in mapping:
                continue
            attr = mapping[env_key]
            if not hasattr(cls, attr):
                continue
            if value is None or (isinstance(value, str) and value == ""):
                continue  # 空值不覆盖，继续用 .env
            setattr(cls, attr, value)
            applied.append(env_key)
        return {"applied": applied, "ignored": ignored}

    @classmethod
    def as_dict_for_db(cls) -> dict:
        """把当前生效配置转成 env_key -> value（后台表单展示用），敏感字段用占位符"""
        return {
            "TG_BOT_TOKEN": cls.BOT_TOKEN,
            "TELETHON_API_IDS": cls.API_IDS,
            "TELETHON_API_HASHS": cls.API_HASHES,
            "TELETHON_PHONES": cls.PHONES,
            "DEFAULT_API_ID": cls.DEFAULT_API_ID,
            "DEFAULT_API_HASH": cls.DEFAULT_API_HASH,
            "ADMIN_TG_IDS": cls.ADMIN_TG_IDS,
            "SESSION_DIR": cls.SESSION_DIR,
            "DB_PATH": cls.DB_PATH,
            "MAX_CHANNELS_PER_ACCOUNT": cls.MAX_CHANNELS_PER_ACCOUNT,
            "JOIN_INTERVAL_SECONDS": cls.JOIN_INTERVAL_SECONDS,
            "MAX_JOIN_PER_DAY": cls.MAX_JOIN_PER_DAY,
            "SEARCH_RESULT_LIMIT": cls.SEARCH_RESULT_LIMIT,
            "FREE_SEARCH_DAILY_LIMIT": cls.FREE_SEARCH_DAILY_LIMIT,
            "FEATURED_AD_LIMIT": cls.FEATURED_AD_LIMIT,
            "HOT_KEYWORD_PER_CATEGORY_LIMIT": cls.HOT_KEYWORD_PER_CATEGORY_LIMIT,
            "HD_WALLET_MNEMONIC": "******",  # 永远不回显
            "TRONGRID_API_KEY": cls.TRONGRID_API_KEY,
            "RECHARGE_CONFIRMATIONS": cls.RECHARGE_CONFIRMATIONS,
            "MIN_RECHARGE_AMOUNT": cls.MIN_RECHARGE_AMOUNT,
            "MIN_RECHARGE_USER": cls.MIN_RECHARGE_USER,
            "MIN_RECHARGE_ADVERTISER": cls.MIN_RECHARGE_ADVERTISER,
            "CUSTOM_BOT_SETUP_FEE_USDT": cls.CUSTOM_BOT_SETUP_FEE_USDT,
            "MONTHLY_SUBSCRIPTION_USDT": cls.MONTHLY_SUBSCRIPTION_USDT,
            "QUARTERLY_SUBSCRIPTION_USDT": cls.QUARTERLY_SUBSCRIPTION_USDT,
            "YEARLY_SUBSCRIPTION_USDT": cls.YEARLY_SUBSCRIPTION_USDT,
            "DEFAULT_CPC_PRICE": cls.DEFAULT_CPC_PRICE,
            "DEFAULT_CPM_PRICE": cls.DEFAULT_CPM_PRICE,
            "MIN_AD_BUDGET_USDT": cls.MIN_AD_BUDGET_USDT,
            "MAX_DAILY_SPEND_USDT": cls.MAX_DAILY_SPEND_USDT,
            "LOG_DIR": cls.LOG_DIR,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "VERSION_REPO_URL": cls.VERSION_REPO_URL,
            "AI_PROVIDER": cls.AI_PROVIDER,
            "AI_API_BASE": cls.AI_API_BASE,
            "AI_API_KEY": cls.AI_API_KEY,
            "AI_MODEL": cls.AI_MODEL,
            "AI_MAX_TOKENS": cls.AI_MAX_TOKENS,
            "AI_TEMPERATURE": cls.AI_TEMPERATURE,
            "AI_KEYWORD_EXPAND": cls.AI_KEYWORD_EXPAND,
            "AI_SUMMARIZE_RESULTS": cls.AI_SUMMARIZE_RESULTS,
            "AI_FREE_DAILY_LIMIT": cls.AI_FREE_DAILY_LIMIT,
        }

    @classmethod
    def validate(cls):
        """校验必填配置（BOT_TOKEN可从DB加载，仅警告不阻塞启动）"""
        errors = []
        warnings = []
        if not cls.BOT_TOKEN:
            warnings.append("TG_BOT_TOKEN 未配置（将在post_init从数据库加载；如数据库也无则Bot无法工作）")
        if not cls.API_IDS or not cls.API_HASHES or not cls.PHONES:
            warnings.append("TELETHON 账号池未配置（请在后台【系统配置】→【采集账号池】中填写，服务可先启动，添加账号后自动加载）")
        if len(cls.API_IDS) != len(cls.API_HASHES) or len(cls.API_IDS) != len(cls.PHONES):
            errors.append("TELETHON 账号池三组配置数量不一致")
        if errors:
            raise ValueError("配置校验失败:\n" + "\n".join(errors))
        for w in warnings:
            logger.warning(w)

    @classmethod
    def get_account_pool(cls):
        """返回账号池列表 [{api_id, api_hash, phone, session_name}]"""
        pool = []
        for i in range(len(cls.API_IDS)):
            pool.append({
                "api_id": cls.API_IDS[i],
                "api_hash": cls.API_HASHES[i],
                "phone": cls.PHONES[i],
                "session_name": f"account_{i+1}",
            })
        return pool
