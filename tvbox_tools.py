# -*- coding: utf-8 -*-
# !/usr/bin/env python3
import os
import json
import asyncio
import aiohttp
import requests
import random
import string
import re
import hashlib
import base64
import time
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urljoin
import commentjson

# 禁用SSL警告
import ssl
import urllib3
from urllib3.exceptions import InsecureRequestWarning
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(InsecureRequestWarning)

class TVBoxSourceManager:
    def __init__(self, base_dir="/data", timeout=30, jar_suffix="jar", site_down=True):
        self.base_dir = base_dir
        self.jar_suffix = jar_suffix
        self.site_down = site_down
        self.timeout = timeout
        self.sep = os.path.sep
        
        # 创建必要的目录
        self.create_directories()
        
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive"
        }
        
        # 创建会话
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update(self.headers)
        
        # 设置重试策略
        from requests.adapters import HTTPAdapter, Retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.s.mount("http://", adapter)
        self.s.mount("https://", adapter)
        
        self.size_tolerance = 15
        
        # drpy2 文件列表
        self.drpy2_files = [
            "cat.js", "crypto-js.js", "drpy2.min.js", "http.js", "jquery.min.js",
            "jsencrypt.js", "log.js", "pako.min.js", "similarity.js", "uri.min.js",
            "cheerio.min.js", "deep.parse.js", "gbk.js", "jinja.js", "json5.js",
            "node-rsa.js", "script.js", "spider.js", "模板.js", "quark.min.js"
        ]

    def create_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.base_dir,
            f"{self.base_dir}/ext",
            f"{self.base_dir}/jar", 
            f"{self.base_dir}/api",
            f"{self.base_dir}/api/drpy2"
        ]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")

    def remove_emojis(self, text):
        """移除表情符号和特殊字符"""
        if not text:
            return ""
            
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
        text = str(text)
        text = text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚','').strip()
        return emoji_pattern.sub('', text)

    def json_compatible(self, text):
        """JSON兼容性处理"""
        if not text:
            return ""
            
        replacements = {
            '//"': '"',
            '//{': '{',
            'key:': '"key":',
            'name:': '"name":',
            'type:': '"type":',
            'api:': '"api":',
            'searchable:': '"searchable":',
            'quickSearch:': '"quickSearch":',
            'filterable:': '"filterable":'
        }
        
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
            
        return result.strip()

    def file_hash(self, filepath):
        """计算文件哈希"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""

    async def download_drpy2_files(self):
        """下载drpy2文件"""
        print("开始下载drpy2支持文件...")
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            for filename in self.drpy2_files:
                local_path = f"{self.base_dir}/api/drpy2/{filename}"
                if os.path.exists(local_path):
                    continue
                    
                json_url = f"https://raw.githubusercontent.com/fish2018/lib/main/js/dr_py/{filename}"

                async def download_task(json_url=json_url, local_path=local_path, filename=filename):
                    retries = 3
                    for attempt in range(retries):
                        try:
                            async with session.get(json_url) as response:
                                response.raise_for_status()
                                content = await response.read()
                                with open(local_path, "wb") as f:
                                    f.write(content)
                                print(f"✓ 下载成功: {filename}")
                                return True
                        except Exception as e:
                            print(f"✗ 下载 {filename} 失败 (尝试 {attempt + 1}/{retries}): {e}")
                            if attempt < retries - 1:
                                await asyncio.sleep(1)
                            else:
                                print(f"✗ 下载 {filename} 最终失败")
                                return False

                tasks.append(download_task())

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                print(f"drpy2文件下载完成: {success_count}/{len(tasks)} 个文件下载成功")
            else:
                print("所有drpy2文件已存在，无需下载")

    async def download_site_files(self, file_path, source_url):
        """下载站点相关的文件"""
        if not self.site_down:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                api_data = commentjson.loads(content)
                sites = api_data.get("sites", [])
        except Exception as e:
            print(f"解析文件失败: {e}")
            return

        if not sites:
            return

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            downloaded_files = 0
            
            for site in sites:
                # 处理ext文件
                if "ext" in site and isinstance(site["ext"], str):
                    ext_value = site["ext"].split(';')[0].rstrip('?')
                    if ext_value.endswith((".js", ".txt", ".json")):
                        filename = os.path.basename(ext_value)
                        json_url = urljoin(source_url, ext_value)
                        local_path = f"{self.base_dir}/ext/{filename}"
                        
                        async def download_ext(json_url=json_url, local_path=local_path, filename=filename):
                            try:
                                async with session.get(json_url) as response:
                                    if response.status == 200:
                                        content = await response.read()
                                        with open(local_path, "wb") as f:
                                            f.write(content)
                                        # 更新路径为本地路径
                                        site["ext"] = f"./ext/{filename}"
                                        print(f"✓ 下载ext文件: {filename}")
                                        return True
                            except Exception as e:
                                print(f"✗ 下载ext文件失败 {filename}: {e}")
                            return False
                        
                        tasks.append(download_ext())

                # 处理api文件（Python文件）
                if "api" in site and isinstance(site["api"], str):
                    api_value = site["api"].split(';')[0].rstrip('?')
                    if api_value.endswith(".py"):
                        filename = os.path.basename(api_value)
                        json_url = urljoin(source_url, api_value)
                        local_path = f"{self.base_dir}/api/{filename}"
                        
                        async def download_api(json_url=json_url, local_path=local_path, filename=filename):
                            try:
                                async with session.get(json_url) as response:
                                    if response.status == 200:
                                        content = await response.read()
                                        with open(local_path, "wb") as f:
                                            f.write(content)
                                        site["api"] = f"./api/{filename}"
                                        print(f"✓ 下载api文件: {filename}")
                                        return True
                            except Exception as e:
                                print(f"✗ 下载api文件失败 {filename}: {e}")
                            return False
                        
                        tasks.append(download_api())

            if tasks:
                print(f"开始下载 {len(tasks)} 个站点文件")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                downloaded_files = sum(1 for r in results if r is True)
                
                # 保存更新后的数据
                if downloaded_files > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(api_data, f, indent=4, ensure_ascii=False)
                    print(f"站点文件下载完成: {downloaded_files}/{len(tasks)} 个文件下载成功")
            else:
                print("没有找到需要下载的站点文件")

    async def download_source(self, url, name=None):
        """下载单个源"""
        if not name:
            name = f"source_{int(time.time())}_{random.randint(1000, 9999)}"
        
        clean_name = self.remove_emojis(name)
        filename = f"{clean_name}.json"
        file_path = f"{self.base_dir}/{filename}"
        
        print(f"\n开始下载源: {name}")
        print(f"URL: {url}")
        
        try:
            # 下载主文件
            response = self.s.get(url, timeout=self.timeout)
            if response.status_code != 200:
                print(f"✗ 下载失败，状态码: {response.status_code}")
                return False

            content = response.text
            
            # 尝试处理base64编码的内容
            if 'searchable' not in content and len(content) < 1000:
                try:
                    matches = re.findall(r'([A-Za-z0-9+/]+={0,2})', content)
                    if matches:
                        decoded_data = base64.b64decode(matches[-1])
                        content = decoded_data.decode('utf-8')
                        print("✓ 检测到Base64编码内容，已解码")
                except:
                    pass

            # JSON兼容性处理
            content = self.json_compatible(content)
            
            # 验证是否为有效的JSON
            try:
                json.loads(content)
            except:
                print("✗ 内容不是有效的JSON格式")
                return False
            
            # 保存主文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ 源文件保存成功: {filename}")
            
            # 下载相关的站点文件
            await self.download_site_files(file_path, url)
            
            return True
            
        except Exception as e:
            print(f"✗ 下载源失败: {e}")
            return False

    async def process_urls(self, urls):
        """处理所有URL"""
        print(f"\n开始处理 {len(urls)} 个URL")
        print("=" * 50)
        
        # 下载drpy2支持文件
        await self.download_drpy2_files()
        
        success_count = 0
        for i, url_config in enumerate(urls, 1):
            if isinstance(url_config, dict):
                url = url_config.get('url', '')
                name = url_config.get('name', f'源{i}')
            else
