FROM python:3.9-slim

# 设置中国时区
RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# 安装必要的系统依赖（包括chromium）
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 下载并安装 filebrowser
RUN wget https://github.com/filebrowser/filebrowser/releases/download/v2.23.0/linux-amd64-filebrowser.tar.gz && \
    tar -xzf linux-amd64-filebrowser.tar.gz && \
    mv filebrowser /usr/local/bin/ && \
    chmod +x /usr/local/bin/filebrowser && \
    rm linux-amd64-filebrowser.tar.gz

# 设置Chromium路径
ENV CHROMIUM_PATH /usr/bin/chromium

# 创建工作目录
WORKDIR /app

# 复制Python依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制主脚本
COPY tvbox_tools.py .

# 创建数据目录
RUN mkdir -p /data/tvbox

# 复制启动脚本
COPY start.sh .

# 设置启动脚本权限
RUN chmod +x start.sh

# 暴露FileBrowser端口
EXPOSE 27677

# 设置环境变量默认值
ENV UPDATE_INTERVAL=96
ENV TVBOX_URL=""
ENV TVBOX_REPO="tvbox"
ENV TVBOX_NUM=10
ENV TVBOX_TARGET="tvbox.json"
ENV TVBOX_TIMEOUT=10
ENV TVBOX_JAR_SUFFIX="jar"
ENV TVBOX_SITE_DOWN="true"

# 启动服务
CMD ["./start.sh"]
