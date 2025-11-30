# -*- coding: utf-8 -*-
# !/usr/bin/env python3
from requests_html import HTMLSession
import pprint
import random
import string
import time
import hashlib
import json
import re
import base64
import requests
import asyncio
import aiohttp
from requests.adapters import HTTPAdapter, Retry
import os
import ssl
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urljoin
import commentjson

ssl._create_default_https_context = ssl._create_unverified_context
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

global pipes
pipes = set()

class GetSrc:
    def __init__(self, username=None, token=None, url=None, repo=None, num=10, target=None, timeout=3, signame=None, mirror=None, jar_suffix=None, site_down=True):
        self.jar_suffix = jar_suffix if jar_suffix else 'jar'
        self.site_down = site_down
        self.mirror = int(str(mirror).strip()) if mirror else 1
        self.mirror_proxy = 'https://ghp.ci/https://raw.githubusercontent.com'
        self.num = int(num)
        self.sep = os.path.sep
        self.username = username
        self.token = token
        self.timeout = timeout
        self.url = url.replace(' ','').replace('，',',') if url else url
        self.repo = repo if repo else 'tvbox'
        self.target = f'{target.split(".json")[0]}.json' if target else 'tvbox.json'
        self.headers = {"user-agent": "okhttp/3.15 Html5Plus/1.0 (Immersed/23.92157)"}
        self.s = requests.Session()
        self.signame = signame
        retries = Retry(total=3, backoff_factor=1)
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))
        self.size_tolerance = 15
        self.main_branch = 'main'
        self.slot = f'{self.mirror_proxy}/{self.username}/{self.repo}/{self.main_branch}'
        self.cnb_slot = f'/{self.repo}'  # 修改为本地路径

        # 其他初始化代码保持不变...
        self.gh1 = [
            'https://ghp.ci/https://raw.githubusercontent.com',
            'https://gh.xxooo.cf/https://raw.githubusercontent.com',
            'https://ghproxy.net/https://raw.githubusercontent.com',
            'https://github.moeyy.xyz/https://raw.githubusercontent.com',
            'https://gh-proxy.com/https://raw.githubusercontent.com',
            'https://ghproxy.cc/https://raw.githubusercontent.com',
            'https://raw.yzuu.cf',
            'https://raw.nuaa.cf',
            'https://raw.kkgithub.com',
            'https://mirror.ghproxy.com/https://raw.githubusercontent.com',
            'https://gh.llkk.cc/https://raw.githubusercontent.com',
            'https://gh.ddlc.top/https://raw.githubusercontent.com',
            'https://gh-proxy.llyke.com/https://raw.githubusercontent.com',
            'https://slink.ltd',
            'https://cors.zme.ink',
            'https://git.886.be'
        ]
        
        self.drpy2 = False
        self.drpy2_files = [
            "cat.js", "crypto-js.js", "drpy2.min.js", "http.js", "jquery.min.js",
            "jsencrypt.js", "log.js", "pako.min.js", "similarity.js", "uri.min.js",
            "cheerio.min.js", "deep.parse.js", "gbk.js", "jinja.js", "json5.js",
            "node-rsa.js", "script.js", "spider.js", "模板.js", "quark.min.js"
        ]

    def git_clone(self):
        """创建本地目录"""
        if not os.path.exists(self.repo):
            os.makedirs(self.repo, exist_ok=True)
            print(f"创建本地目录: {self.repo}")
        else:
            print(f"目录已存在: {self.repo}")

    def get_local_repo(self):
        """返回None，不进行Git操作"""
        return None

    def reset_commit(self, repo):
        """空实现"""
        pass

    def git_push(self, repo):
        """空实现"""
        print("数据已保存到本地目录")

    # 其他方法保持不变...
    async def download_drpy2_files(self):
        """异步下载 drpy2 文件"""
        api_drpy2_dir = os.path.join(self.repo, "api/drpy2")
        if not os.path.exists(api_drpy2_dir):
            os.makedirs(api_drpy2_dir)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            for filename in self.drpy2_files:
                local_path = os.path.join(api_drpy2_dir, filename)
                if os.path.exists(local_path):
                    continue
                json_url = f"https://github.moeyy.xyz/https://raw.githubusercontent.com/fish2018/lib/main/js/dr_py/{filename}"

                async def download_task(json_url=json_url, local_path=local_path, filename=filename):
                    retries = 3
                    for attempt in range(retries):
                        try:
                            async with session.get(json_url) as response:
                                response.raise_for_status()
                                content = await response.read()
                                with open(local_path, "wb") as f:
                                    f.write(content)
                                return True
                        except Exception as e:
                            if attempt < retries - 1:
                                await asyncio.sleep(1)
                            else:
                                print(f"下载 {json_url} 失败")
                                return False
                tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def file_hash(self, filepath):
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def remove_duplicates(self, folder_path):
        """去重逻辑保持不变..."""
        folder_path = Path(folder_path)
        jar_folder = f'{folder_path}/jar'
        excludes = {'.json', '.git', 'jar', '.idea', 'ext', '.DS_Store', '.md'}
        files_info = {}

        self.rename_jar_suffix(jar_folder)

        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix not in excludes:
                file_size = file_path.stat().st_size
                file_hash = self.file_hash(file_path)
                files_info[file_path.name] = {'path': str(file_path), 'size': file_size, 'hash': file_hash}

        keep_files = []
        for file_name, info in sorted(files_info.items(), key=lambda item: item[1]['size']):
            if not keep_files or abs(info['size'] - files_info[keep_files[-1]]['size']) > self.size_tolerance:
                keep_files.append(file_name)
            else:
                os.remove(info['path'])
                self.remove_jar_file(jar_folder, file_name.replace('.txt', f'.{self.jar_suffix}'))

        keep_files.sort()
        return keep_files

    # 其他方法实现保持不变...
    def rename_jar_suffix(self, jar_folder):
        for root, dirs, files in os.walk(jar_folder):
            for file in files:
                old_file = os.path.join(root, file)
                new_file = os.path.join(root, os.path.splitext(file)[0] + f'.{self.jar_suffix}')
                os.rename(old_file, new_file)

    def remove_jar_file(self, jar_folder, file_name):
        jar_file_path = os.path.join(jar_folder, file_name)
        if os.path.isfile(jar_file_path):
            os.remove(jar_file_path)

    def remove_emojis(self, text):
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"
                                   u"\U0001F300-\U0001F5FF"
                                   u"\U0001F680-\U0001F6FF"
                                   u"\U0001F1E0-\U0001F1FF"
                                   "\U00002500-\U00002BEF"
                                   "\U00010000-\U0010ffff"
                                   "\u200d"
                                   "\u20E3"
                                   "\ufe0f"
                                   "]+", flags=re.UNICODE)
        text = text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚','').strip()
        return emoji_pattern.sub('', text)

    def json_compatible(self, str):
        res = str.replace('//"', '"').replace('//{', '{').replace('key:', '"key":').replace('name:', '"name":').replace('type:', '"type":').replace('api:','"api":').replace('searchable:', '"searchable":').replace('quickSearch:', '"quickSearch":').replace('filterable:','"filterable":').strip()
        return res

    def ghproxy(self, str):
        u = 'https://github.moeyy.xyz/'
        res = str.replace('https://ghproxy.net/', u).replace('https://ghproxy.com/', u).replace('https://gh-proxy.com/',u).replace('https://mirror.ghproxy.com/',u).replace('https://gh.xxooo.cf/',u).replace('https://ghp.ci/',u).replace('https://gitdl.cn/',u)
        return res

    # 其他方法实现...
    # 由于代码长度限制，这里只展示关键修改部分，完整实现需要包含原脚本的所有方法

    def run(self):
        start_time = time.time()
        self.git_clone()
        asyncio.run(self.batch_handle_online_interface())
        repo = self.get_local_repo()
        self.all()
        self.mirror_proxy2new()
        self.git_push(repo)
        end_time = time.time()
        print(f'耗时: {end_time - start_time} 秒')
        print(f'数据已保存到: {self.repo}')
        print(f'主配置文件: {self.repo}/all.json')
        print(f'目标配置文件: {self.repo}/{self.target}')

if __name__ == '__main__':
    # 测试代码
    url = 'https://tvbox.catvod.com/xs/api.json?signame=xs'
    site_down = True
    GetSrc(url=url, repo='tvbox_data', mirror=4, num=10, site_down=site_down).run()
