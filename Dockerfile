# ============================================================
# TG搜索机器人 - Dockerfile
# 基础镜像: Python 3.11 Slim (轻量级)
# 构建: docker build -t tg-search-bot:latest .
# 运行: 推荐使用 docker-compose up -d
# ============================================================

FROM python:3.11-slim

# 设置构建参数和环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (SQLite编译选项需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    libsqlite3-dev \
    build-essential \
    # 编译Python内置sqlite3支持FTS5可选，debian自带sqlite3已支持
    sqlite3 \
    # 清理缓存减少镜像体积
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 先复制依赖列表（利用Docker缓存）
COPY requirements.txt .

# 安装Python依赖 (使用清华镜像加速国内构建)
RUN pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 验证关键包安装
RUN python -c "import telethon; import telegram; import aiosqlite; import jieba; import loguru; print('依赖校验OK')"

# 复制应用代码
COPY app/ ./app/
COPY main.py .
COPY .env.example ./.env.example

# 创建数据和日志目录挂载点
RUN mkdir -p /app/data/sessions \
    /app/data/backups \
    /app/logs \
    /app/scripts

# 设置启动入口（通过entrypoint脚本做启动前检查）
COPY deploy/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 健康检查：通过日志文件活跃时间判断
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "
import os, time, sys
log_dir = '/app/logs'
if not os.path.exists(log_dir):
    sys.exit(1)
files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
if not files:
    sys.exit(0)  # 启动初期无日志正常
latest = max(os.path.getmtime(os.path.join(log_dir, f)) for f in files)
# 5分钟内有日志更新认为健康
if time.time() - latest > 300:
    sys.exit(1)
sys.exit(0)
"

# 声明数据卷
VOLUME ["/app/data", "/app/logs"]

# 默认启动命令
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "main.py"]
