FROM python:3.9-slim

# 设置中国时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制Python脚本和依赖文件
COPY tvbox_tools.py .
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 下载并安装Filebrowser
RUN wget https://github.com/filebrowser/filebrowser/releases/download/v2.23.0/linux-amd64-filebrowser.tar.gz \
    && tar -xzf linux-amd64-filebrowser.tar.gz \
    && mv filebrowser /usr/local/bin/ \
    && chmod +x /usr/local/bin/filebrowser \
    && rm linux-amd64-filebrowser.tar.gz

# 创建数据目录和配置文件
RUN mkdir -p /data /config

# 创建启动脚本
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 创建定时任务脚本
COPY update_script.py .
RUN chmod +x update_script.py

# 暴露Filebrowser端口
EXPOSE 27677

# 设置环境变量默认值
ENV TVBOX_URL=""
ENV UPDATE_INTERVAL=96
ENV TVBOX_REPO="tvbox_data"
ENV TVBOX_MIRROR=4
ENV TVBOX_NUM=10
ENV TVBOX_SITE_DOWN=true
ENV TVBOX_JAR_SUFFIX="jar"

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]
