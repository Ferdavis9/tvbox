# 基础镜像：Python 3.9 slim
FROM python:3.9-slim

# 维护者信息
LABEL maintainer="your-name <your-email>"

# 设置中国时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 下载并安装Filebrowser（适配amd64架构，其他架构需替换下载链接）
RUN wget https://github.com/filebrowser/filebrowser/releases/download/v2.23.0/linux-amd64-filebrowser.tar.gz \
    && tar -zxvf linux-amd64-filebrowser.tar.gz \
    && mv filebrowser /usr/local/bin/ \
    && chmod +x /usr/local/bin/filebrowser \
    && rm -rf linux-amd64-filebrowser.tar.gz LICENSE README.md

# 创建工作目录
WORKDIR /app

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用文件
COPY tvbox_tools.py .
COPY start.sh .

# 赋予启动脚本执行权限
RUN chmod +x /app/start.sh

# 暴露Filebrowser端口
EXPOSE 27677

# 启动命令
CMD ["/app/start.sh"]
