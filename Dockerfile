# 基础镜像：Python 3.9 轻量版
FROM python:3.9-slim

# 维护者信息（可选）
LABEL maintainer="tvbox-docker"

# 设置环境变量（适配Chrome和Python）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
    TZ=Asia/Shanghai

# 安装系统依赖（Chrome、Filebrowser、Cron等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    python3-dev \
    wget \
    curl \
    unzip \
    chromium-browser \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 安装Filebrowser（文件管理工具，暴露27677端口）
RUN wget -q https://github.com/filebrowser/filebrowser/releases/download/v2.27.0/linux-amd64-filebrowser.tar.gz \
    && tar -zxf linux-amd64-filebrowser.tar.gz -C /usr/local/bin/ \
    && rm -f linux-amd64-filebrowser.tar.gz \
    && chmod +x /usr/local/bin/filebrowser

# 创建工作目录
WORKDIR /app

# 复制脚本和依赖文件
COPY tvbox_tools.py .
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 配置Cron定时任务（每天凌晨3点执行下载脚本）
RUN echo "0 3 * * * python /app/tvbox_tools.py >> /app/download.log 2>&1" >> /etc/crontab \
    && chmod 644 /etc/crontab

# 复制启动脚本
COPY start.sh .
RUN chmod +x start.sh

# 暴露Filebrowser端口
EXPOSE 27677

# 数据卷（可选，持久化存储下载的文件）
VOLUME ["/app/tvbox_files"]

# 启动容器时执行的命令
CMD ["/app/start.sh"]
