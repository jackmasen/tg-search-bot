"""
数据库初始化与连接管理
SQLite + WAL模式 + FTS5全文索引
"""
import os
from contextlib import asynccontextmanager
import aiosqlite
from app.config import Config


# 数据库建表SQL（首次启动自动执行）
SCHEMA_SQL = """
-- 频道表
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_channel_id BIGINT UNIQUE,           -- TG频道内部ID
    username TEXT,                          -- 频道用户名（公开频道的@xxx）
    title TEXT,                             -- 频道标题
    member_count INTEGER DEFAULT 0,          -- 成员数
    last_crawled_at TIMESTAMP,              -- 最后采集时间
    crawl_status TEXT DEFAULT 'pending',     -- pending/joined/listening/error
    assigned_account TEXT,                  -- 分配的采集账号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息表（原始内容）
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    tg_msg_id BIGINT NOT NULL,              -- TG消息ID
    content TEXT,                           -- 消息文本内容
    msg_date TIMESTAMP,                     -- 消息发布时间
    content_hash TEXT,                      -- 内容hash，用于去重
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id),
    UNIQUE(channel_id, tg_msg_id)            -- 同频道同消息ID唯一
);

-- FTS5全文索引虚拟表（外部内容表，关联messages）
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content_rowid=rowid,
    content='messages',
    tokenize='unicode61'                    -- 内置分词，中文后续用jieba预处理
);

-- 触发器：messages插入后同步到FTS索引
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

-- 索引
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(msg_date DESC);
CREATE INDEX IF NOT EXISTS idx_channels_username ON channels(username);
CREATE INDEX IF NOT EXISTS idx_channels_status ON channels(crawl_status);

-- 版本记录表（用于版本更新与回滚追踪）
CREATE TABLE IF NOT EXISTS app_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,                  -- 版本号 如 1.0.0
    commit_hash TEXT,                       -- Git提交hash
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',           -- active/rolled_back
    rollback_to TEXT,                       -- 回滚到的版本
    notes TEXT                              -- 更新说明
);

-- 备份记录表
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_path TEXT NOT NULL,              -- 备份文件路径
    backup_type TEXT,                        -- auto/manual/pre_update
    file_size INTEGER,                       -- 文件大小（字节）
    version_before TEXT,                     -- 备份时的版本号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'available',        -- available/restored/corrupted
    notes TEXT                              -- 备注
);

-- ========== 第2步：钱包与广告模块 ==========

-- 用户表（含USDT余额）
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id BIGINT UNIQUE NOT NULL,       -- TG用户ID
    username TEXT,                            -- TG用户名
    wallet_balance_usdt REAL DEFAULT 0.0,    -- USDT余额
    role TEXT DEFAULT 'user',                 -- user/advertiser/admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户钱包地址（每个用户独立收款地址）
CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chain TEXT NOT NULL,                      -- trc20/bsc/erc20
    hd_index INTEGER,                         -- HD钱包派生索引（BIP44第5段），同一助记词+索引=唯一地址
    address TEXT NOT NULL,                    -- 收款地址
    private_key_encrypted TEXT,               -- 加密的私钥（或留空，运营方统一用TronLink管理）
    derivation_path TEXT,                     -- 完整派生路径，例如 m/44'/195'/0'/0/5
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, chain),
    UNIQUE(chain, hd_index)                   -- 同一条链上一个HD索引只能被用一次，绝对不能重复分配
);

-- 充值订单表
CREATE TABLE IF NOT EXISTS recharge_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_no TEXT UNIQUE NOT NULL,            -- 订单号
    chain TEXT NOT NULL,                      -- trc20/bsc/erc20
    address TEXT NOT NULL,                    -- 收款地址
    amount_usdt REAL NOT NULL,               -- 应充金额
    tx_hash TEXT,                             -- 链上交易hash
    status TEXT DEFAULT 'pending',            -- pending/confirmed/failed
    confirmations INTEGER DEFAULT 0,         -- 区块确认数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 交易流水表
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,                       -- recharge/ad_charge/build_fee/subscribe/refund
    amount REAL NOT NULL,                     -- 正数=入账 负数=出账
    balance_after REAL,                       -- 操作后余额
    related_id INTEGER,                       -- 关联的订单/广告/订阅ID
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 广告主表
CREATE TABLE IF NOT EXISTS advertisers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',             -- active/suspended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id)
);

-- 广告投放计划
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advertiser_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,                    -- 关联的搜索关键词
    title TEXT,                               -- 广告标题
    description TEXT,                         -- 广告描述
    target_channel TEXT,                      -- 目标频道/群组@username
    target_url TEXT,                          -- 点击跳转链接
    category TEXT DEFAULT '推广',              -- 广告分类
    member_count INTEGER DEFAULT 10000,        -- 成员数
    billing_type TEXT DEFAULT 'cpc',          -- cpc/cpm
    cpc_price REAL DEFAULT 0.05,             -- 单次点击费用
    cpm_price REAL DEFAULT 1.0,               -- 千次曝光费用
    daily_budget REAL DEFAULT 10.0,           -- 每日预算
    daily_spent REAL DEFAULT 0.0,             -- 今日已花费
    status TEXT DEFAULT 'pending',            -- pending/active/paused/ended
    display_order INTEGER DEFAULT 0,          -- 展示顺序（数值越小越靠前）
    is_featured INTEGER DEFAULT 0,             -- 是否首页推荐
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(id)
);

-- 广告曝光日志
CREATE TABLE IF NOT EXISTS ad_impressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    searcher_tg_id BIGINT,                   -- 搜索者TG ID
    position INTEGER,                         -- 展示位置（1=置顶）
    is_click INTEGER DEFAULT 0,               -- 是否点击
    cost REAL NOT NULL,                       -- 本次费用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES ad_campaigns(id)
);

-- 广告模板库
CREATE TABLE IF NOT EXISTS ad_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                       -- 模板名称
    category TEXT,                            -- 频道推广/产品推广/活动推广
    title_template TEXT,                      -- 标题模板
    desc_template TEXT,                       -- 描述模板
    example_text TEXT,                        -- 示例文案
    is_recommended INTEGER DEFAULT 0,         -- 是否推荐
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 热门关键词表（后台配置，显示在机器人首页）
CREATE TABLE IF NOT EXISTS hot_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,              -- 关键词
    category TEXT,                              -- 分类：加密/AI/Web3/DeFi/NFT 等
    display_order INTEGER DEFAULT 0,           -- 展示顺序
    is_custom INTEGER DEFAULT 1,               -- 1=后台自定义 0=系统默认
    is_active INTEGER DEFAULT 1,               -- 是否启用
    click_count INTEGER DEFAULT 0,             -- 点击次数（统计用）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 系统默认关键词分类表
CREATE TABLE IF NOT EXISTS hot_keyword_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,                  -- 分类名称
    icon TEXT,                                  -- 图标 emoji
    sort_order INTEGER DEFAULT 0,              -- 分类排序
    is_active INTEGER DEFAULT 1
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_users_tg ON users(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_wallets_address ON wallets(address);
CREATE INDEX IF NOT EXISTS idx_orders_status ON recharge_orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_address ON recharge_orders(address, status);
CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_keyword ON ad_campaigns(keyword, status);
CREATE INDEX IF NOT EXISTS idx_impressions_campaign ON ad_impressions(campaign_id, created_at DESC);

-- 搜索日志表（用于免费用户每日搜索次数限制）
CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_search_logs_user ON search_logs(tg_user_id, created_at DESC);

-- 系统配置表（后台可修改的配置项，非密钥类）
-- 规则：
--   1. 仅存储非密钥类配置；密钥类必须保留在 .env 中
--   2. 启动优先级：DB 配置 > .env 配置 > 代码默认值
--   3. 敏感字段（如 API Hash / Token）写入前用 CRYPTO_SECRET AES 加密
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,           -- 配置键名（例如 TG_BOT_TOKEN / TELETHON_API_IDS / DEFAULT_CPC_PRICE）
    setting_value TEXT,                         -- 配置值（字符串存储，复杂类型 JSON 序列化）
    value_type TEXT DEFAULT 'str',              -- 数据类型: str/int/float/bool/list_int/list_str/json
    is_encrypted INTEGER DEFAULT 0,             -- 是否加密存储（API密钥、Token 类设1）
    description TEXT,                           -- 配置说明（显示在后台）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    """初始化数据库：建表+开启WAL+优化参数+字段迁移"""
    # 确保目录存在
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)

    async with aiosqlite.connect(Config.DB_PATH) as db:
        # 开启WAL模式（提升并发读写性能）
        await db.execute("PRAGMA journal_mode=WAL")
        # 开启同步正常模式（性能与安全平衡）
        await db.execute("PRAGMA synchronous=NORMAL")
        # 缓存大小 20MB
        await db.execute("PRAGMA cache_size=-20000")
        # 执行建表
        await db.executescript(SCHEMA_SQL)

        # ===== 表结构升级迁移（从旧版本升级到新版本时自动补字段）=====
        # wallets表补 hd_index、derivation_path 字段（老库升级用）
        async with db.execute("PRAGMA table_info(wallets)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "hd_index" not in cols:
            await db.execute("ALTER TABLE wallets ADD COLUMN hd_index INTEGER")
        if "derivation_path" not in cols:
            await db.execute("ALTER TABLE wallets ADD COLUMN derivation_path TEXT")

        # recharge_orders表补 actual_amount_usdt（实际转账金额，可能和应充金额略有不同）
        async with db.execute("PRAGMA table_info(recharge_orders)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "actual_amount_usdt" not in cols:
            await db.execute("ALTER TABLE recharge_orders ADD COLUMN actual_amount_usdt REAL")
        # users表补 role 以外的预留字段（未来扩展）
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "is_advertiser" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN is_advertiser INTEGER DEFAULT 0")
        if "subscription_expires_at" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN subscription_expires_at TIMESTAMP")
        if "inviter_id" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN inviter_id INTEGER")
            await db.execute("ALTER TABLE users ADD COLUMN invite_code TEXT")
            await db.execute("ALTER TABLE users ADD COLUMN invited_count INTEGER DEFAULT 0")

        # ad_campaigns表补 display_order 和 is_featured 字段
        async with db.execute("PRAGMA table_info(ad_campaigns)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "display_order" not in cols:
            await db.execute("ALTER TABLE ad_campaigns ADD COLUMN display_order INTEGER DEFAULT 0")
        if "is_featured" not in cols:
            await db.execute("ALTER TABLE ad_campaigns ADD COLUMN is_featured INTEGER DEFAULT 0")
        if "category" not in cols:
            await db.execute("ALTER TABLE ad_campaigns ADD COLUMN category TEXT DEFAULT '推广'")
        if "member_count" not in cols:
            await db.execute("ALTER TABLE ad_campaigns ADD COLUMN member_count INTEGER DEFAULT 10000")
        if "updated_at" not in cols:
            # 注意：SQLite 部分版本不允许 ADD COLUMN 带 CURRENT_TIMESTAMP 默认值，
            # 因此先加空列，历史记录回填当前时间；代码层 update/set 操作会显式维护 updated_at
            await db.execute("ALTER TABLE ad_campaigns ADD COLUMN updated_at TIMESTAMP")
            await db.execute("UPDATE ad_campaigns SET updated_at=COALESCE(created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")

        # 初始化默认热门关键词分类
        default_categories = [
            ("加密货币", "💰", 1),
            ("AI人工智能", "🤖", 2),
            ("Web3/DeFi", "🌐", 3),
            ("NFT/元宇宙", "🎨", 4),
            ("量化交易", "📈", 5),
            ("空投/薅羊毛", "🎁", 6),
            ("编程开发", "💻", 7),
            ("科技前沿", "🚀", 8),
        ]
        for name, icon, order in default_categories:
            await db.execute(
                "INSERT OR IGNORE INTO hot_keyword_categories (name, icon, sort_order, is_active) VALUES (?,?,?,1)",
                (name, icon, order)
            )

        # 初始化默认热门关键词（系统级，不可删除）
        default_keywords = [
            # 加密货币
            ("比特币", "加密货币", 0),
            ("以太坊", "加密货币", 0),
            ("USDT", "加密货币", 0),
            ("Solana", "加密货币", 0),
            ("BNB", "加密货币", 0),
            # AI
            ("GPT", "AI人工智能", 0),
            ("人工智能", "AI人工智能", 0),
            ("LLM", "AI人工智能", 0),
            ("机器学习", "AI人工智能", 0),
            ("深度学习", "AI人工智能", 0),
            # Web3
            ("Web3", "Web3/DeFi", 0),
            ("DeFi", "Web3/DeFi", 0),
            ("质押挖矿", "Web3/DeFi", 0),
            ("Uniswap", "Web3/DeFi", 0),
            # 量化
            ("量化", "量化交易", 0),
            ("K线", "量化交易", 0),
            ("技术分析", "量化交易", 0),
            ("趋势交易", "量化交易", 0),
            # 空投
            ("空投", "空投/薅羊毛", 0),
            ("白嫖", "空投/薅羊毛", 0),
            ("测试网", "空投/薅羊毛", 0),
            ("任务平台", "空投/薅羊毛", 0),
            # 编程
            ("Python", "编程开发", 0),
            ("FastAPI", "编程开发", 0),
            ("Solidity", "编程开发", 0),
            ("Rust", "编程开发", 0),
        ]
        for kw, cat, order in default_keywords:
            await db.execute(
                "INSERT OR IGNORE INTO hot_keywords (keyword, category, display_order, is_custom, is_active) VALUES (?,?,?,0,1)",
                (kw, cat, order)
            )

        await db.commit()


@asynccontextmanager
async def get_db():
    """获取数据库连接（供其他模块使用，支持 async with）"""
    db = await aiosqlite.connect(Config.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
    finally:
        await db.close()
