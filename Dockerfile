FROM python:3.9-slim

# 设置元数据
LABEL maintainer="your-email@example.com"
LABEL description="TVBox Source Manager with FileBrowser"
LABEL version="1.0"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY cnb_tvbox_tools.py .

# 下载并安装FileBrowser
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        ARCH="arm64"; \
    elif [ "$ARCH" = "armv7l" ]; then \
        ARCH="armv7"; \
    fi && \
    wget -O filebrowser.tar.gz "https://github.com/filebrowser/filebrowser/releases/latest/download/linux-${ARCH}-filebrowser.tar.gz" && \
    tar -xzf filebrowser.tar.gz && \
    chmod +x filebrowser && \
    mv filebrowser /usr/local/bin/ && \
    rm filebrowser.tar.gz

# 创建数据目录和配置目录
RUN mkdir -p /data && \
    mkdir -p /app/config

# 复制FileBrowser配置文件
COPY config/filebrowser.json /app/config/

# 创建启动脚本
RUN echo '#!/bin/bash\n\
\n\
echo "==================================="\n\
echo "    TVBox源管理容器启动中..."\n\
echo "==================================="\n\
\n\
# 检查数据目录\n\
if [ ! -d "/data" ]; then\n\
    echo "创建数据目录 /data"\n\
    mkdir -p /data\n\
fi\n\
\n\
# 初始化FileBrowser数据库（如果不存在）\n\
if [ ! -f "/data/filebrowser.db" ]; then\n\
    echo "初始化FileBrowser配置..."\n\
    filebrowser config init --database=/data/filebrowser.db\n\
    filebrowser config set --database=/data/filebrowser.db \\\n\
        --address=0.0.0.0 \\\n\
        --port=27677 \\\n\
        --baseurl="" \\\n\
        --root=/data \\\n\
        --auth.method=json\n\
    \n\
    # 设置管理员用户\n\
    filebrowser users add --database=/data/filebrowser.db \\\n\
        admin admin \\\n\
        --perm.admin\n\
    \n\
    echo "FileBrowser配置完成"\n\
fi\n\
\n\
# 运行源下载程序\n\
echo "开始下载TVBox源..."\n\
cd /app\n\
python cnb_tvbox_tools.py\n\
\n\
# 启动FileBrowser（后台运行）\n\
echo "启动FileBrowser服务..."\n\
filebrowser --database=/data/filebrowser.db --config=/app/config/filebrowser.json &\n\
\n\
echo "==================================="\n\
echo "    服务启动完成！"\n\
echo "FileBrowser访问地址: http://localhost:27677"\n\
echo "用户名: admin, 密码: admin"\n\
echo "数据目录: /data"\n\
echo "==================================="\n\
\n\
# 健康检查脚本（每30秒运行一次）\n\
while true; do\n\
    # 检查FileBrowser进程是否运行\n\
    if ! pgrep -f "filebrowser" > /dev/null; then\n\
        echo "$(date): FileBrowser进程异常，尝试重启..."\n\
        filebrowser --database=/data/filebrowser.db --config=/app/config/filebrowser.json &\n\
    fi\n\
    sleep 30\n\
done' > /app/start.sh && chmod +x /app/start.sh

# 暴露FileBrowser端口
EXPOSE 27677

# 设置环境变量默认值
ENV DATA_DIR=/data
ENV TIMEOUT=30
ENV JAR_SUFFIX=jar
ENV SITE_DOWN=true
ENV SOURCE_URLS=""

# 设置数据卷
VOLUME ["/data"]

# 设置启动命令
CMD ["/app/start.sh"]
