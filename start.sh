#!/bin/bash

# 设置环境变量
INTERVAL=${UPDATE_INTERVAL:-96}
URL=${TVBOX_URL:-""}
REPO=${TVBOX_REPO:-"tvbox"}
NUM=${TVBOX_NUM:-10}
TARGET=${TVBOX_TARGET:-"tvbox.json"}
TIMEOUT=${TVBOX_TIMEOUT:-3}
JAR_SUFFIX=${TVBOX_JAR_SUFFIX:-"jar"}
SITE_DOWN=${TVBOX_SITE_DOWN:-"true"}

# 检查必要环境变量
if [ -z "$URL" ]; then
    echo "错误: 必须设置 TVBOX_URL 环境变量"
    exit 1
fi

# 设置工作目录到数据卷
cd /data

# 更新函数
update_tvbox() {
    echo "$(date): 开始更新TVBox源..."
    TVBOX_URL="$URL" \
    TVBOX_REPO="$REPO" \
    TVBOX_NUM="$NUM" \
    TVBOX_TARGET="$TARGET" \
    TVBOX_TIMEOUT="$TIMEOUT" \
    TVBOX_JAR_SUFFIX="$JAR_SUFFIX" \
    TVBOX_SITE_DOWN="$SITE_DOWN" \
    python3 /app/tvbox_tools.py
    echo "$(date): TVBox源更新完成"
}

# 首次更新
update_tvbox

# 启动FileBrowser（后台运行）
echo "启动FileBrowser服务在端口27677..."
filebrowser --port 27677 --address 0.0.0.0 --root /data/tvbox --noauth &

# 定时更新循环
while true; do
    echo "等待 $INTERVAL 小时后再次更新..."
    sleep $(($INTERVAL * 3600))
    update_tvbox
done
