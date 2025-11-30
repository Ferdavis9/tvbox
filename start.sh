#!/bin/bash
set -e

# 读取环境变量（更新间隔，单位：小时；默认96小时）
UPDATE_INTERVAL_HOURS=${TVBOX_UPDATE_INTERVAL:-96}
# 转换为秒（小时×3600）
UPDATE_INTERVAL_SECONDS=$((UPDATE_INTERVAL_HOURS * 3600))

echo "======================================="
echo "TVBox文件下载服务启动"
echo "---------------------------------------"
echo "当前配置："
echo "TVBox源接口URL: $TVBOX_URL"
echo "自动更新间隔: $UPDATE_INTERVAL_HOURS 小时（$UPDATE_INTERVAL_SECONDS 秒）"
echo "是否下载关联文件（jar/ext/api）: $SITE_DOWN"
echo "Filebrowser访问地址: http://容器IP:27677（用户名：admin，密码：admin）"
echo "======================================="

# 启动Filebrowser（后台运行）
echo "启动Filebrowser服务..."
filebrowser -r /app/tvbox_files -p 27677 -u admin -P admin &

# 循环执行下载任务
while true; do
    echo -e "\n======================================="
    echo "开始执行TVBox源下载/更新任务（$(date +'%Y-%m-%d %H:%M:%S')）"
    echo "======================================="
    
    # 执行Python脚本，输出日志到download.log
    python /app/cnb_tvbox_tools.py >> /app/download.log 2>&1
    
    echo -e "\n======================================="
    echo "本次任务完成！下次更新时间：$(date -d "$UPDATE_INTERVAL_HOURS hours" +'%Y-%m-%d %H:%M:%S')"
    echo "======================================="
    
    # 休眠指定间隔时间
    sleep $UPDATE_INTERVAL_SECONDS
done
