#!/bin/bash

# 设置环境变量
TVBOX_URL=${TVBOX_URL:-""}
UPDATE_INTERVAL=${UPDATE_INTERVAL:-96}
TVBOX_REPO=${TVBOX_REPO:-"tvbox_data"}
TVBOX_MIRROR=${TVBOX_MIRROR:-4}
TVBOX_NUM=${TVBOX_NUM:-10}
TVBOX_SITE_DOWN=${TVBOX_SITE_DOWN:-true}
TVBOX_JAR_SUFFIX=${TVBOX_JAR_SUFFIX:-"jar"}

# 检查必要的环境变量
if [ -z "$TVBOX_URL" ]; then
    echo "错误: 必须设置 TVBOX_URL 环境变量"
    exit 1
fi

# 创建数据目录
mkdir -p /data/$TVBOX_REPO

# 配置Filebrowser
filebrowser config init -d /config/filebrowser.db
filebrowser users add admin admin --perm.admin -d /config/filebrowser.db
filebrowser config set --baseurl "/" -d /config/filebrowser.db
filebrowser config set --port 27677 -d /config/filebrowser.db
filebrowser config set --root /data -d /config/filebrowser.db

# 设置定时任务
echo "设置定时任务，每 ${UPDATE_INTERVAL} 小时更新一次"
echo "0 */${UPDATE_INTERVAL} * * * /usr/local/bin/python3 /app/update_script.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tvbox-update
chmod 0644 /etc/cron.d/tvbox-update
crontab /etc/cron.d/tvbox-update

# 首次运行更新脚本
echo "首次运行更新脚本..."
python3 /app/update_script.py

# 启动cron服务
service cron start

# 启动Filebrowser
echo "Filebrowser 服务启动在端口 27677"
echo "数据目录: /data"
filebrowser -d /config/filebrowser.db
