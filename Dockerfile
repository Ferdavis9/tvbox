# 基础镜像：Python 3.9 slim
FROM python:3.9-slim

# 维护者信息
LABEL maintainer="your-name <your-email>"

# 设置中国时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 关键：补充系统依赖（解决requests-html/pyppeteer运行依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    wget \
    ca-certificates \
    curl \
    unzip \
    # Pyppeteer/Chromium依赖库
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    # 编译依赖（解决部分包编译失败）
    build-essential \
    python3-dev \
    # 直接安装系统Chromium（避免pyppeteer手动下载）
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 配置Pyppeteer使用系统Chromium（跳过自动下载）
ENV PYPPETEER_SKIP_CHROMIUM_DOWNLOAD=1
ENV PYPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# 创建工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 升级pip + 安装Python依赖（指定国内源，避免超时）
RUN pip install --upgrade pip --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用文件
COPY tvbox_tools.py .
COPY start.sh .

# 赋予启动脚本执行权限
RUN chmod +x /app/start.sh

# 暴露Filebrowser端口
EXPOSE 27677

# 启动命令
CMD ["/app/start.sh"]
