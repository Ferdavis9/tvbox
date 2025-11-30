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
import subprocess
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
    def __init__(self, url=None, num=10, timeout=3, jar_suffix=None, site_down=True):
        # 核心配置：本地存储目录（Docker容器内固定路径）
        self.root_dir = "/app/tvbox_files"
        self.jar_suffix = jar_suffix if jar_suffix else 'jar'
        self.site_down = site_down  # 是否下载site里的文件到本地
        self.num = int(num)
        self.sep = os.path.sep
        self.url = url.replace(' ', '').replace('，', ',') if url else url
        self.timeout = timeout
        self.target = 'tvbox.json'  # 默认输出json文件名
        self.headers = {"user-agent": "okhttp/3.15 Html5Plus/1.0 (Immersed/23.92157)"}
        self.s = requests.Session()
        self.size_tolerance = 15  # 线路文件大小误差在15以内认为是同一个

        # 请求重试配置
        retries = Retry(total=3, backoff_factor=1)
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))

        # 定义 drpy2 文件列表
        self.drpy2 = False
        self.drpy2_files = [
            "cat.js", "crypto-js.js", "drpy2.min.js", "http.js", "jquery.min.js",
            "jsencrypt.js", "log.js", "pako.min.js", "similarity.js", "uri.min.js",
            "cheerio.min.js", "deep.parse.js", "gbk.js", "jinja.js", "json5.js",
            "node-rsa.js", "script.js", "spider.js", "模板.js", "quark.min.js"
        ]

        # 创建本地存储目录（确保目录存在）
        self._create_storage_dirs()

    def _create_storage_dirs(self):
        """创建所有必要的存储目录"""
        dirs = [
            self.root_dir,
            os.path.join(self.root_dir, "jar"),
            os.path.join(self.root_dir, "ext"),
            os.path.join(self.root_dir, "api"),
            os.path.join(self.root_dir, "api/drpy2")
        ]
        for dir_path in dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"创建目录：{dir_path}")

    async def download_drpy2_files(self):
        """异步下载 drpy2 文件到 api/drpy2 目录"""
        api_drpy2_dir = os.path.join(self.root_dir, "api/drpy2")
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            for filename in self.drpy2_files:
                local_path = os.path.join(api_drpy2_dir, filename)
                if os.path.exists(local_path):
                    continue
                # drpy2 文件源地址（保持原逻辑）
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
                                print(f"drpy2文件下载成功: {filename}")
                                return True
                        except Exception as e:
                            if attempt < retries - 1:
                                await asyncio.sleep(1)
                            else:
                                print(f"drpy2文件下载失败: {filename}, 错误: {e}")
                                return False

                tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def file_hash(self, filepath):
        """计算文件SHA256哈希"""
        with open(filepath, 'rb') as f:
            file_contents = f.read()
            return hashlib.sha256(file_contents).hexdigest()

    def remove_duplicates(self, folder_path):
        """移除重复文件（保留核心逻辑）"""
        folder_path = Path(folder_path)
        jar_folder = os.path.join(folder_path, "jar")
        excludes = {'.json', '.git', 'jar', '.idea', 'ext', '.DS_Store', '.md'}
        files_info = {}

        # 统一jar文件后缀
        self.rename_jar_suffix(jar_folder)

        # 收集文件信息
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix not in excludes:
                file_size = file_path.stat().st_size
                file_hash = self.file_hash(file_path)
                files_info[file_path.name] = {'path': str(file_path), 'size': file_size, 'hash': file_hash}

        # 去重逻辑
        keep_files = []
        for file_name, info in sorted(files_info.items(), key=lambda item: item[1]['size']):
            if not keep_files or abs(info['size'] - files_info[keep_files[-1]]['size']) > self.size_tolerance:
                keep_files.append(file_name)
            else:
                os.remove(info['path'])
                self.remove_jar_file(jar_folder, file_name.replace('.txt', f'.{self.jar_suffix}'))

        keep_files.sort()
        return keep_files

    def rename_jar_suffix(self, jar_folder):
        """统一jar文件后缀"""
        if not os.path.exists(jar_folder):
            return
        for root, dirs, files in os.walk(jar_folder):
            for file in files:
                old_file = os.path.join(root, file)
                new_file = os.path.join(root, os.path.splitext(file)[0] + f'.{self.jar_suffix}')
                os.rename(old_file, new_file)

    def remove_jar_file(self, jar_folder, file_name):
        """删除指定jar文件"""
        jar_file_path = os.path.join(jar_folder, file_name)
        if os.path.isfile(jar_file_path):
            os.remove(jar_file_path)

    def remove_emojis(self, text):
        """移除表情符号和特殊字符"""
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
        text = text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚', '').strip()
        return emoji_pattern.sub('', text)

    def json_compatible(self, str):
        """JSON格式兼容处理"""
        res = str.replace('//"', '"').replace('//{', '{').replace('key:', '"key":').replace('name:', '"name":')
        res = res.replace('type:', '"type":').replace('api:', '"api":').replace('searchable:', '"searchable":')
        res = res.replace('quickSearch:', '"quickSearch":').replace('filterable:', '"filterable":').strip()
        return res

    def ghproxy(self, str):
        """代理链接替换（保留原逻辑）"""
        u = 'https://github.moeyy.xyz/'
        res = str.replace('https://ghproxy.net/', u).replace('https://ghproxy.com/', u)
        res = res.replace('https://gh-proxy.com/', u).replace('https://mirror.ghproxy.com/', u)
        res = res.replace('https://gh.xxooo.cf/', u).replace('https://ghp.ci/', u).replace('https://gitdl.cn/', u)
        return res

    def picparse(self, url):
        """解析base64编码的内容"""
        r = self.s.get(url, headers=self.headers, timeout=self.timeout, verify=False)
        pattern = r'([A-Za-z0-9+/]+={0,2})'
        matches = re.findall(pattern, r.text)
        decoded_data = base64.b64decode(matches[-1])
        text = decoded_data.decode('utf-8')
        return text

    async def js_render(self, url):
        """JS渲染页面（适配Docker Chrome环境）"""
        timeout = self.timeout * 4
        if timeout > 15:
            timeout = 15
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-setuid-sandbox',
            '--headless=new'  # Chrome 112+ 推荐参数
        ]
        from requests_html import AsyncHTMLSession

        session = AsyncHTMLSession(browser_args=browser_args)
        try:
            r = await session.get(
                f'http://lige.unaux.com/?url={url}',
                headers=self.headers,
                timeout=timeout,
                verify=False,
            )
            await r.html.arender(timeout=timeout)
            return r.html
        finally:
            await session.close()

    async def site_file_down(self, files, url):
        """下载ext/jar/api文件（去掉仓库链接替换）"""
        ext_dir = os.path.join(self.root_dir, "ext")
        jar_dir = os.path.join(self.root_dir, "jar")
        api_dir = os.path.join(self.root_dir, "api")
        api_drpy2_dir = os.path.join(self.root_dir, "api/drpy2")

        # 确保目录存在
        for directory in [ext_dir, jar_dir, api_dir, api_drpy2_dir]:
            os.makedirs(directory, exist_ok=True)

        file = files[0]
        file2 = files[1] if len(files) > 1 else ''

        # 读取api.json
        with open(file, 'r', encoding='utf-8') as f:
            try:
                api_data = commentjson.load(f)
                sites = api_data["sites"]
                print(f"总站点数: {len(sites)}")
            except Exception as e:
                print(f"解析 {file} 失败: {e}")
                return

        # 异步下载
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            for site in sites:
                for field in ["ext", "jar", "api"]:
                    if field in site:
                        value = site[field]
                        if isinstance(value, str):
                            clean_value = value.split(';')[0].rstrip('?')
                            # 过滤无效文件类型
                            if field == "ext" and not clean_value.endswith((".js", ".txt", ".json")):
                                continue
                            elif field == "api":
                                if os.path.basename(clean_value).lower() in ["drpy2.min.js", "quark.min.js"]:
                                    self.drpy2 = True
                                    continue  # 不替换链接，保持原生
                                if not clean_value.endswith(".py"):
                                    continue

                            # 构造下载链接和本地路径
                            filename = os.path.basename(clean_value)
                            if './' in value:
                                path = os.path.dirname(url)
                                json_url = value.replace('./', f'{path}/')
                            else:
                                json_url = urljoin(url, value)
                            local_path = os.path.join(os.path.join(self.root_dir, field), filename)

                            async def download_task(json_url=json_url, local_path=local_path, filename=filename):
                                retries = 3
                                for attempt in range(retries):
                                    try:
                                        async with session.get(json_url) as response:
                                            response.raise_for_status()
                                            if os.path.exists(local_path):
                                                print(f"{filename} 已存在，跳过")
                                                return True
                                            content = await response.read()
                                            with open(local_path, "wb") as f:
                                                f.write(content)
                                            print(f"{field}文件下载成功: {filename}")
                                            return True
                                    except Exception as e:
                                        if attempt < retries - 1:
                                            await asyncio.sleep(1)
                                        else:
                                            print(f"{field}文件下载失败: {filename}, 错误: {e}")
                                            return False

                            tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # 写回更新后的数据（不修改文件内的链接）
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=4, ensure_ascii=False)

        if file2 and os.path.basename(file2):
            with open(file2, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, indent=4, ensure_ascii=False)

    def get_jar(self, name, url, text):
        """下载jar文件（去掉仓库链接替换）"""
        jar_dir = os.path.join(self.root_dir, "jar")
        os.makedirs(jar_dir, exist_ok=True)
        
        name = f'{name}.{self.jar_suffix}'
        pattern = r'\"spider\":(\s)?\"([^,]+)\"'
        matches = re.search(pattern, text)
        jar_url = None
        try:
            jar_url = matches.group(2).replace('./', f'{url}/').split(';')[0]
            jar_url = jar_url.split('"spider":"')[-1]
            if name == f'tvbox.{self.jar_suffix}':
                name = f"{jar_url.split('/')[-1]}"
            print(f'jar下载地址: {jar_url}')
            
            timeout = self.timeout * 4
            if timeout > 15:
                timeout = 15
            r = self.s.get(jar_url, timeout=timeout, verify=False)
            if r.status_code != 200:
                raise Exception(f'status_code: {r.status_code}')
            
            local_path = os.path.join(jar_dir, name)
            with open(local_path, 'wb') as f:
                f.write(r.content)
            print(f'jar文件下载成功: {name}')
        except Exception as e:
            print(f'【jar下载失败】{name}, 地址: {jar_url}, 错误: {e}')
        return text  # 不替换text中的jar路径，保持原生

    async def download(self, url, name, filename, cang=True):
        """下载单线路文件"""
        # 检查文件是否已存在
        file_list = []
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                file_list.append(file)
        if filename in file_list:
            print(f'{filename} 已存在，无需重复下载')
            return
        
        if 'agit.ai' in url:
            print(f'下载异常：agit.ai链接失效')
            return

        try:
            path = os.path.dirname(url)
            r = self.s.get(url, headers=self.headers, allow_redirects=True, timeout=self.timeout, verify=False)
            if r.status_code == 200:
                print(f"开始下载线路【{name}】: {url}")
                # 处理JS渲染和base64解析
                if 'searchable' not in r.text:
                    html = await self.js_render(url)
                    if hasattr(html, 'text') and html.text:
                        r_text = html.text
                    else:
                        r_text = self.picparse(url)
                        if 'searchable' not in r_text:
                            raise Exception("内容无searchable字段，下载失败")
                        r_text = self.get_jar(name, url, r_text)
                else:
                    r_text = r.text

                # 内容处理
                try:
                    if r_text.startswith(u'\ufeff'):
                        r_text = r_text.encode('utf-8')[3:].decode('utf-8')
                    r_text = self.ghproxy(r_text.replace('./', f'{path}/'))
                    r_text = self.get_jar(name, url, r_text)
                except Exception as e:
                    print(f"线路【{name}】内容处理失败: {e}")
                    return

                # 保存文件
                local_path = os.path.join(self.root_dir, filename)
                with open(local_path, 'w+', encoding='utf-8') as f:
                    f.write(r_text)
                pipes.add(name)
                print(f"线路【{name}】下载成功，保存路径: {local_path}")

                # 下载关联的ext/jar/api文件
                try:
                    if self.site_down:
                        await self.site_file_down([local_path], url)
                except Exception as e:
                    print(f"线路【{name}】关联文件下载失败: {e}")
        except Exception as e:
            print(f"线路【{name}】下载错误: {e}")

    async def down(self, data, s_name):
        """下载单仓文件"""
        newJson = {}
        global items
        items = []
        urls = data.get("urls") if data.get("urls") else data.get("sites")
        
        for u in urls:
            name = u.get("name").strip()
            name = self.remove_emojis(name)
            url = u.get("url")
            url = self.ghproxy(url)
            filename = f'{name}.txt'
            
            if name in pipes:
                print(f"线路【{name}】已存在，无需重复下载")
                continue
            await self.download(url, name, filename)
        
        # 生成单仓json（保存到本地）
        newJson['urls'] = items
        newJson = pprint.pformat(newJson, width=200)
        print(f'开始写入单仓文件: {s_name}')
        local_path = os.path.join(self.root_dir, s_name)
        with open(local_path, 'w+', encoding='utf-8') as f:
            content = str(newJson).replace("'", '"')
            f.write(json.loads(json.dumps(content, indent=4, ensure_ascii=False)))

    def all(self):
        """生成所有线路的汇总all.json"""
        newJson = {}
        items = []
        files = self.remove_duplicates(self.root_dir)
        
        for file in files:
            if file.endswith('.txt'):
                item = {}
                item['name'] = file.split('.txt')[0]
                item['local_path'] = os.path.join(self.root_dir, file)  # 本地路径，方便查看
                items.append(item)
        
        newJson['urls'] = items
        newJson = pprint.pformat(newJson, width=200)
        print(f'开始写入汇总文件: all.json')
        local_path = os.path.join(self.root_dir, 'all.json')
        with open(local_path, 'w+', encoding='utf-8') as f:
            content = str(newJson).replace("'", '"')
            f.write(json.loads(json.dumps(content, indent=4, ensure_ascii=False)))

    async def batch_handle_online_interface(self):
        """批量处理在线接口"""
        print(f'--------- 开始处理在线接口 ----------')
        if not self.url:
            print("错误：未指定下载链接（TVBOX_URL环境变量为空）")
            return
        
        urls = self.url.split(',')
        for url in urls:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            signame_value = query_params.get('signame', [''])[0]
            item = url.split('?&signame=')
            self.current_url = item[0] if len(item) > 1 else url
            self.signame = signame_value if signame_value else None
            print(f'当前处理接口: {self.current_url}')
            await self.storeHouse()
        
        # 清理空目录
        await self.clean_directories()

    async def clean_directories(self):
        """清理空目录"""
        dirs = [
            os.path.join(self.root_dir, "api"),
            os.path.join(self.root_dir, "ext"),
            os.path.join(self.root_dir, "api/drpy2")
        ]
        for dir_path in dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                if not os.listdir(dir_path):
                    shutil.rmtree(dir_path)
                    print(f"清理空目录: {dir_path}")

    async def storeHouse(self):
        """处理单接口（线路/单仓/多仓）"""
        await self.download_drpy2_files()

        try:
            # 解析接口内容
            res = self.s.get(self.current_url, headers=self.headers, verify=False, timeout=self.timeout).content.decode('utf8')
            if '404 Not Found' in res:
                print(f'{self.current_url} 请求异常（404）')
                return
        except Exception as e:
            if 'Read timed out' in str(e) or 'nodename nor servname provided' in str(e):
                print(f'{self.current_url} 请求异常：{e}')
                return
            # 尝试JS渲染
            html = await self.js_render(self.current_url)
            res = html.text if hasattr(html, 'text') else ''
            if not res:
                res = self.picparse(self.current_url)
                if not res:
                    print(f'{self.current_url} 无法获取内容')
                    return

        # 处理线路文件（含searchable字段）
        if 'searchable' in str(res):
            filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
            path = os.path.dirname(self.current_url)
            print(f"处理线路文件: {filename}")
            try:
                local_path = os.path.join(self.root_dir, filename)
                target_path = os.path.join(self.root_dir, self.target)
                
                # 内容处理
                r_text = self.ghproxy(res.replace('./', f'{path}/'))
                r_text = self.get_jar(filename.split('.txt')[0], self.current_url, r_text)
                r_text = self.json_compatible(r_text)
                
                # 保存文件
                with open(local_path, 'w+', encoding='utf-8') as f, open(target_path, 'w+', encoding='utf-8') as f2:
                    f.write(r_text)
                    f2.write(r_text)
                
                # 下载关联文件
                if self.site_down:
                    await self.site_file_down([local_path, target_path], self.current_url)
            except Exception as e:
                print(f"线路文件处理失败: {e}")
            return

        # JSON格式兼容处理
        res = self.json_compatible(res)
        # 移除注释
        datas = ''
        for d in res.splitlines():
            if d.find(" //") != -1 or d.find("// ") != -1 or d.find(",//") != -1 or d.startswith("//"):
                d = d.split(" //", maxsplit=1)[0]
                d = d.split("// ", maxsplit=1)[0]
                d = d.split(",//", maxsplit=1)[0]
                d = d.split("//", maxsplit=1)[0]
            datas = '\n'.join([datas, d])
        
        # BOM头处理
        datas = datas.replace('\n', '').strip()
        if datas.startswith(u'\ufeff'):
            try:
                datas = datas.encode('utf-8')[3:].decode('utf-8')
            except:
                datas = datas.encode('utf-8')[4:].decode('utf-8')

        # 处理多仓（含storeHouse字段）
        if 'storeHouse' in datas:
            try:
                res = json.loads(datas)
            except Exception as e:
                print(f"多仓JSON解析失败: {e}")
                return
            
            srcs = res.get("storeHouse")
            if not srcs:
                print("未找到storeHouse字段")
                return
            
            i = 1
            for s in srcs:
                if i > self.num:
                    break
                i += 1
                s_name = s.get("sourceName")
                s_name = self.remove_emojis(s_name) + '.json'
                s_url = s.get("sourceUrl")
                print(f"处理多仓【{s_name}】: {s_url}")
                
                # 检查链接有效性
                try:
                    check = self.s.get(s_url, headers=self.headers, timeout=5, verify=False)
                    if check.status_code >= 400:
                        print(f"多仓链接无效（{check.status_code}）: {s_url}")
                        continue
                except Exception as e:
                    print(f"多仓链接无法访问: {e}")
                    continue
                
                # 下载并解析多仓内容
                try:
                    data = self.s.get(s_url, headers=self.headers).content.decode('utf-8')
                    # 移除注释
                    datas = ''
                    for d in data.splitlines():
                        if d.find(" //") != -1 or d.find("// ") != -1 or d.find(",//") != -1 or d.startswith("//"):
                            d = d.split(" //", maxsplit=1)[0]
                            d = d.split("// ", maxsplit=1)[0]
                            d = d.split(",//", maxsplit=1)[0]
                            d = d.split("//", maxsplit=1)[0]
                        datas = '\n'.join([datas, d])
                    
                    # BOM头处理
                    if datas.lstrip().startswith(u'\ufeff'):
                        datas = datas.encode('utf-8')[1:].decode('utf-8')
                    
                    await self.down(json.loads(datas), s_name)
                except Exception as e:
                    print(f"多仓【{s_name}】处理失败: {e}")
        
            # 生成总仓json
            newJson = {"storeHouse": [{"sourceName": s.split('.json')[0], "sourceUrl": os.path.join(self.root_dir, s)} for s in os.listdir(self.root_dir) if s.endswith('.json') and s != self.target]}
            newJson = pprint.pformat(newJson, width=200)
            target_path = os.path.join(self.root_dir, self.target)
            with open(target_path, 'w+', encoding='utf-8') as f:
                f.write(json.dumps(json.loads(str(newJson).replace("'", '"')), sort_keys=True, indent=4, ensure_ascii=False))
        
        # 处理单仓
        else:
            try:
                res = json.loads(datas)
            except Exception as e:
                if 'domainnameisinvalid' in datas:
                    print(f'域名无效: {self.current_url}')
                    return
                # 尝试JS渲染
                html = await self.js_render(self.current_url)
                res = html.text.replace(' ', '').replace("'", '"') if hasattr(html, 'text') else ''
                if not res:
                    res = self.picparse(self.current_url).replace(' ', '').replace("'", '"')
                try:
                    res = json.loads(res)
                except Exception as e:
                    print(f"单仓JSON解析失败: {e}")
                    return
            
            s_name = self.target
            print(f"处理单仓【{s_name}】: {self.current_url}")
            try:
                await self.down(res, s_name)
            except Exception as e:
                if 'searchable' in str(res):
                    filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
                    print(f"处理单仓线路: {filename}")
                    await self.download(self.current_url, filename.split('.txt')[0], filename, cang=False)

    def run(self):
        """主运行入口"""
        start_time = time.time()
        print(f"开始执行TVBox源下载任务，存储目录: {self.root_dir}")
        
        # 批量处理接口
        asyncio.run(self.batch_handle_online_interface())
        
        # 生成汇总文件
        self.all()
        
        end_time = time.time()
        print(f'\n本次任务完成！耗时: {end_time - start_time:.2f} 秒')
        print(f'文件存储路径: {self.root_dir}')
        print(f'可通过Filebrowser访问: http://容器IP:27677')


if __name__ == '__main__':
    # 从环境变量读取配置（优先级：环境变量 > 默认值）
    TVBOX_URL = os.getenv('TVBOX_URL', 'https://tvbox.catvod.com/xs/api.json?signame=xs')  # 核心：TVBox源接口URL
    TVBOX_UPDATE_INTERVAL = os.getenv('TVBOX_UPDATE_INTERVAL', '')  # 仅用于启动脚本读取，脚本内不使用
    SITE_DOWN = os.getenv('SITE_DOWN', 'True').lower() == 'true'  # 是否下载关联文件
    NUM = int(os.getenv('TVBOX_NUM', 10))  # 多仓最大下载数量
    TIMEOUT = int(os.getenv('TVBOX_TIMEOUT', 3))  # 请求超时时间
    JAR_SUFFIX = os.getenv('TVBOX_JAR_SUFFIX', 'jar')  # jar文件后缀
    
    # 启动单次下载任务
    GetSrc(
        url=TVBOX_URL,
        num=NUM,
        timeout=TIMEOUT,
        jar_suffix=JAR_SUFFIX,
        site_down=SITE_DOWN
    ).run()
