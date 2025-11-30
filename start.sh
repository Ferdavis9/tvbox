#!/bin/bash
set -e

# 首次启动时执行一次下载任务（后续由Cron定时执行）
echo "首次启动，执行初始下载任务..."
python /app/tvbox_tools.py >> /app/download.log 2>&1

# 启动Cron服务
echo "启动Cron定时任务服务..."
cron -f &

# 启动Filebrowser（用户名：admin，密码：admin，根目录：/app/tvbox_files）
echo "启动Filebrowser，端口：27677"
filebrowser -r /app/tvbox_files -p 27677 -u admin -P admin

# 保持容器运行
tail -f /dev/null
