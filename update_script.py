#!/usr/bin/env python3
import os
import sys
import asyncio
from tvbox_tools import GetSrc

def main():
    # 从环境变量获取配置
    tvbox_url = os.getenv('TVBOX_URL', '')
    tvbox_repo = os.getenv('TVBOX_REPO', 'tvbox_data')
    tvbox_mirror = int(os.getenv('TVBOX_MIRROR', '4'))
    tvbox_num = int(os.getenv('TVBOX_NUM', '10'))
    tvbox_site_down = os.getenv('TVBOX_SITE_DOWN', 'true').lower() == 'true'
    tvbox_jar_suffix = os.getenv('TVBOX_JAR_SUFFIX', 'jar')
    
    if not tvbox_url:
        print("错误: TVBOX_URL 环境变量未设置")
        return
    
    print(f"开始更新TVBox数据...")
    print(f"URL: {tvbox_url}")
    print(f"存储目录: {tvbox_repo}")
    print(f"镜像: {tvbox_mirror}")
    print(f"数量: {tvbox_num}")
    print(f"下载站点文件: {tvbox_site_down}")
    print(f"JAR后缀: {tvbox_jar_suffix}")
    
    try:
        # 修改GetSrc类，移除Git相关功能
        class LocalGetSrc(GetSrc):
            def __init__(self, *args, **kwargs):
                # 移除token和username参数
                kwargs.pop('token', None)
                kwargs.pop('username', None)
                super().__init__(*args, **kwargs)
                # 修改repo路径为绝对路径
                self.repo = f"/data/{self.repo}"
                # 修改cnb_slot为本地文件路径
                self.cnb_slot = f"/{self.repo}"
            
            def git_clone(self):
                """重写git_clone方法，只创建本地目录"""
                if not os.path.exists(self.repo):
                    os.makedirs(self.repo, exist_ok=True)
                    print(f"创建本地目录: {self.repo}")
                else:
                    print(f"目录已存在: {self.repo}")
            
            def get_local_repo(self):
                """重写get_local_repo方法，返回None"""
                return None
            
            def reset_commit(self, repo):
                """重写reset_commit方法，不做任何操作"""
                pass
            
            def git_push(self, repo):
                """重写git_push方法，不做任何操作"""
                print("数据已保存到本地目录，跳过Git推送")
        
        # 创建实例并运行
        get_src = LocalGetSrc(
            url=tvbox_url,
            repo=tvbox_repo,
            mirror=tvbox_mirror,
            num=tvbox_num,
            site_down=tvbox_site_down,
            jar_suffix=tvbox_jar_suffix
        )
        
        get_src.run()
        
        print("TVBox数据更新完成!")
        print(f"文件保存在: /data/{tvbox_repo}")
        print(f"可通过Filebrowser访问: http://localhost:27677")
        
    except Exception as e:
        print(f"更新过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
