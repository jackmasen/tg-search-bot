# Telegram Search Bot (tg-search-bot)

🤖 Telegram 多账号搜索机器人系统，支持群消息搜索、关键词过滤、多账号管理、广告过滤等功能。

**当前版本：v1.0.12**

## 📋 功能特性

- ✅ 多账号管理（小号管理）
- ✅ Telegram 群消息搜索
- ✅ 关键词过滤与匹配
- ✅ 代理管理（支持 HTTP/HTTPS/SOCKS5）
- ✅ 订阅节点模式
- ✅ 广告过滤
- ✅ 钱包管理（HD钱包）
- ✅ 定时任务与自动备份
- ✅ Web 管理后台（FastAPI + Uvicorn）
- ✅ 运维监控页面

## 🚀 快速部署

### 宝塔环境一键部署

```bash
# 1. 上传源码到服务器
scp -r tg-search-bot/* root@您的服务器IP:/www/wwwroot/tg-search-bot/

# 2. SSH 登录服务器，执行一键部署
cd /www/wwwroot/tg-search-bot
bash deploy/oneclick.sh

# 3. 编辑配置
vim .env
# 填入 TG_BOT_TOKEN 和 HD_WALLET_MNEMONIC

# 4. 启动服务
systemctl start tg-search-bot
systemctl start tg-search-admin

# 5. 配置 Nginx 反代 + SSL（宝塔面板操作）
```

详细部署教程见：[宝塔部署教程_v1.0.12.md](./宝塔部署教程_v1.0.12.md)

### 手动部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
vim .env  # 填入必要配置

# 3. 启动服务
python main.py
```

## 📁 项目结构

```
tg-search-bot/
├── app/                    # 核心应用代码
│   ├── admin/              # 管理后台路由
│   ├── bot/                # Bot 核心逻辑
│   ├── crawler/            # 爬虫模块
│   ├── search/             # 搜索模块
│   ├── wallet/             # 钱包模块
│   └── server.py           # FastAPI Admin 服务
├── deploy/                 # 部署脚本
│   ├── baota_install.sh    # 宝塔一键部署
│   ├── oneclick.sh         # 通用一键部署
│   └── scripts/            # 辅助脚本
├── tests/                  # 测试文件
├── data/                   # 数据目录（sessions, databases）
├── logs/                   # 日志目录
├── .env.example            # 环境变量模板
└── requirements.txt        # Python 依赖
```

## 🔧 技术栈

- **后端**：FastAPI + Uvicorn
- **Telegram**：Telethon
- **数据库**：SQLite + JSON
- **部署**：Systemd + Nginx
- **爬虫**：Playwright（可选）

## 📝 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `TG_BOT_TOKEN` | Bot Token（从 @BotFather 获取） | ✅ |
| `HD_WALLET_MNEMONIC` | HD 钱包助记词 | ✅ |
| `SESSION_SECRET` | Session 密钥（自动生成） | ⚠️ |
| `CRYPTO_SECRET` | 加密密钥（自动生成） | ⚠️ |

详细配置见：[.env.example](./.env.example)

## 🔒 安全说明

- ⚠️ **严禁**将 `.env` 文件提交到 Git
- ⚠️ **严禁**将 `data/sessions/` 目录提交到 Git
- ⚠️ **严禁**在公开仓库分享助记词
- ✅ 本项目已配置 `.gitignore` 排除敏感文件

## 📄 许可证

MIT License

## 🙏 致谢

- [Telethon](https://github.com/LonamiWebs/Telethon)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
