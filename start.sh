#!/bin/bash
set -e

# 环境变量默认值
TVBOX_URL=${TVBOX_URL:-""}
UPDATE_INTERVAL=${UPDATE_INTERVAL:-345600}  # 默认96小时（345600秒）
TVBOX_MIRROR=${TVBOX_MIRROR:-4}
TVBOX_NUM=${TVBOX_NUM:-10}
TVBOX_SITE_DOWN=${TVBOX_SITE_DOWN:-true}

# 创建存储目录
mkdir -p /tvbox_data

# 启动Filebrowser（后台运行）
echo "启动Filebrowser，端口27677"
filebrowser -r /tvbox_data -a 0.0.0.0 -p 27677 -d /tvbox_data/filebrowser.db &

# 定时更新逻辑
echo "开始定时更新，间隔: $UPDATE_INTERVAL 秒"
while true; do
    echo "====================================="
    echo "开始执行TVBox源更新: $(date)"
    echo "TVBOX_URL: $TVBOX_URL"
    # 执行Python脚本
    python /app/tvbox_tools.py
    echo "更新完成，下次更新时间: $(date -d "+$UPDATE_INTERVAL seconds")"
    echo "====================================="
    # 休眠指定时间
    sleep $UPDATE_INTERVAL
done
