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
import chardet

ssl._create_default_https_context = ssl._create_unverified_context
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

global pipes
pipes = set()

class GetSrc:
    def __init__(self, url=None, repo=None, num=10, target=None, timeout=3, signame=None, jar_suffix=None, site_down=True):
        self.jar_suffix = jar_suffix if jar_suffix else 'jar'
        self.site_down = site_down  # 是否下载site里的文件到本地
        self.num = int(num)
        self.sep = os.path.sep
        self.timeout = timeout
        self.url = url.replace(' ','').replace('，',',') if url else url
        self.repo = repo if repo else 'tvbox'
        self.target = f'{target.split(".json")[0]}.json' if target else 'tvbox.json'
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        self.s = requests.Session()
        # 增加重试机制
        retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))
        self.signame = signame
        self.size_tolerance = 15  # 线路文件大小误差在15以内认为是同一个
        
        # 定义 drpy2 文件列表
        self.drpy2 = False
        self.drpy2_files = [
            "cat.js", "crypto-js.js", "drpy2.min.js", "http.js", "jquery.min.js",
            "jsencrypt.js", "log.js", "pako.min.js", "similarity.js", "uri.min.js",
            "cheerio.min.js", "deep.parse.js", "gbk.js", "jinja.js", "json5.js",
            "node-rsa.js", "script.js", "spider.js", "模板.js", "quark.min.js"
        ]

    def detect_encoding(self, content):
        """自动检测编码"""
        try:
            result = chardet.detect(content)
            encoding = result['encoding']
            confidence = result['confidence']
            if encoding and confidence > 0.7:
                return encoding
        except:
            pass
        return 'utf-8'

    async def download_drpy2_files(self):
        """
        异步下载 drpy2 文件到 self.repo/api/drpy2
        """
        # 创建 drpy2 目录
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
                json_url = f"https://gh-proxy.org/https://raw.githubusercontent.com/fish2018/lib/main/js/dr_py/{filename}"

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
                                print(f"下载 {json_url} 最终失败")
                                return False

                tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def file_hash(self, filepath):
        with open(filepath, 'rb') as f:
            file_contents = f.read()
            return hashlib.sha256(file_contents).hexdigest()

    def remove_duplicates(self, folder_path):
        folder_path = Path(folder_path)
        jar_folder = f'{folder_path}/jar'
        excludes = {'.json', '.git', 'jar', '.idea', 'ext', '.DS_Store', '.md'}
        files_info = {}

        # 把jar目录下所有文件后缀都改成新的self.jar_suffix
        self.rename_jar_suffix(jar_folder)

        # 存储文件名、大小和哈希值
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix not in excludes:
                file_size = file_path.stat().st_size
                file_hash = self.file_hash(file_path)
                files_info[file_path.name] = {'path': str(file_path), 'size': file_size, 'hash': file_hash}

        # 保留的文件列表
        keep_files = []
        # 按文件大小排序，然后按顺序处理
        for file_name, info in sorted(files_info.items(), key=lambda item: item[1]['size']):
            if not keep_files or abs(info['size'] - files_info[keep_files[-1]]['size']) > self.size_tolerance:
                keep_files.append(file_name)
            else:
                # 如果当前文件大小在容忍范围内，删除当前文件和对应的jar文件
                os.remove(info['path'])
                self.remove_jar_file(jar_folder, file_name.replace('.txt', f'.{self.jar_suffix}'))

        keep_files.sort()
        return keep_files

    def rename_jar_suffix(self, jar_folder):
        if not os.path.exists(jar_folder):
            return
        # 遍历目录中的所有文件和子目录
        for root, dirs, files in os.walk(jar_folder):
            for file in files:
                # 构造完整的文件路径
                old_file = os.path.join(root, file)
                # 构造新的文件名，去除原有的后缀，加上 self.jar_suffix
                new_file = os.path.join(root, os.path.splitext(file)[0] + f'.{self.jar_suffix}')
                try:
                    # 重命名文件
                    os.rename(old_file, new_file)
                except Exception as e:
                    pass

    def remove_jar_file(self, jar_folder, file_name):
        # 构建jar文件的路径
        jar_file_path = os.path.join(jar_folder, file_name)
        # 如果jar文件存在，则删除它
        if os.path.isfile(jar_file_path):
            os.remove(jar_file_path)

    def remove_emojis(self, text):
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   "\U00002500-\U00002BEF"  # chinese char
                                   "\U00010000-\U0010ffff"
                                   "\u200d"  # zero width joiner
                                   "\u20E3"  # combining enclosing keycap
                                   "\ufe0f"  # VARIATION SELECTOR-16
                                   "]+", flags=re.UNICODE)
        text = text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚','').strip()
        return emoji_pattern.sub('', text)

    def json_compatible(self, str):
        # 兼容错误json
        res = str.replace('//"', '"').replace('//{', '{').replace('key:', '"key":').replace('name:', '"name":').replace('type:', '"type":').replace('api:','"api":').replace('searchable:', '"searchable":').replace('quickSearch:', '"quickSearch":').replace('filterable:','"filterable":').strip()
        return res

    def ghproxy(self, str):
        u = 'https://github.moeyy.xyz/'
        res = str.replace('https://ghproxy.net/', u).replace('https://ghproxy.com/', u).replace('https://gh-proxy.com/',u).replace('https://mirror.ghproxy.com/',u).replace('https://gh.xxooo.cf/',u).replace('https://ghp.ci/',u).replace('https://gitdl.cn/',u)
        return res

    def picparse(self, url):
        try:
            r = self.s.get(url, headers=self.headers, timeout=self.timeout, verify=False)
            pattern = r'([A-Za-z0-9+/]+={0,2})'
            matches = re.findall(pattern, r.text)
            if matches:
                decoded_data = base64.b64decode(matches[-1])
                text = decoded_data.decode('utf-8')
                return text
        except Exception as e:
            print(f"图片解析失败: {e}")
        return ""

    async def js_render(self, url):
        """获取 JS 渲染页面源代码"""
        timeout = self.timeout * 4
        if timeout > 15:
            timeout = 15
        
        try:
            from requests_html import AsyncHTMLSession
            
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-setuid-sandbox',
            ]
            
            session = AsyncHTMLSession(browser_args=browser_args)
            try:
                # 使用更稳定的代理服务
                proxy_url = f'https://r.jina.ai/{url}'
                r = await session.get(
                    proxy_url,
                    headers=self.headers,
                    timeout=timeout,
                    verify=False,
                )
                # 等待页面加载完成
                await asyncio.sleep(2)
                return r.html
            except Exception as e:
                print(f"JS渲染失败: {e}")
                # 备用方案：直接返回空内容
                from requests_html import HTML
                return HTML(html="")
            finally:
                await session.close()
        except Exception as e:
            print(f"JS渲染初始化失败: {e}")
            from requests_html import HTML
            return HTML(html="")

    async def site_file_down(self, files, url):
        """
        异步函数，用于同时下载和更新 ext、jar 和 api 文件。
        """
        # 设置 ext、jar 和 api 的保存目录
        ext_dir = f"{self.repo}/ext"
        jar_dir = f"{self.repo}/jar"
        api_dir = f"{self.repo}/api"
        api_drpy2_dir = f"{self.repo}/api/drpy2"
        for directory in [ext_dir, jar_dir, api_dir, api_drpy2_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # 获取文件路径并读取 api.json
        file = files[0]
        file2 = files[1] if len(files) > 1 else ''

        try:
            with open(file, 'r', encoding='utf-8') as f:
                api_data = commentjson.load(f)
                sites = api_data["sites"]
                print(f"总站点数: {len(sites)}")
        except Exception as e:
            print(f"解析 {file} 失败: {e}")
            return

        # 使用 aiohttp 创建会话并收集下载任务
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=60, connect=15)
        ) as session:
            tasks = []
            for site in sites:
                for field in ["ext", "jar", "api"]:
                    repo_dir_name = field
                    if field in site:
                        value = site[field]
                        if isinstance(value, str):
                            clean_value = value.split(';')[0].rstrip('?')
                            if field == "ext":
                                if not clean_value.endswith((".js", ".txt", ".json")):
                                    continue
                            elif field == "api":
                                if os.path.basename(clean_value).lower() in ["drpy2.min.js","quark.min.js"]:
                                    self.drpy2 = True
                                    site[field] = f"./api/drpy2/{os.path.basename(clean_value).lower()}"
                                    continue
                                if not clean_value.endswith(".py"):
                                    continue

                            # 默认下载逻辑
                            filename = os.path.basename(clean_value)
                            if './' in value:
                                path = os.path.dirname(url)
                                json_url = value.replace('./', f'{path}/')
                            else:
                                json_url = urljoin(url, value)
                            local_path = os.path.join(f"{self.repo}/{repo_dir_name}", filename)

                            async def download_task(site=site, json_url=json_url, local_path=local_path,
                                                    filename=filename, field=field, repo_dir_name=repo_dir_name):
                                retries = 3
                                for attempt in range(retries):
                                    try:
                                        async with session.get(json_url) as response:
                                            response.raise_for_status()
                                            if os.path.exists(local_path):
                                                site[field] = f'./{repo_dir_name}/{filename}'
                                                return True
                                            content = await response.read()
                                            with open(local_path, "wb") as f:
                                                f.write(content)
                                            site[field] = f'./{repo_dir_name}/{filename}'
                                            return True
                                    except Exception as e:
                                        if attempt < retries - 1:
                                            await asyncio.sleep(1)
                                        else:
                                            return False

                            tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # 将更新后的数据写回文件
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, indent=4, ensure_ascii=False)

            if file2 and os.path.basename(file2):
                with open(file2, 'w', encoding='utf-8') as f:
                    json.dump(api_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"写入文件失败: {e}")

    def get_jar(self, name, url, text):
        if not os.path.exists(f'{self.repo}/jar'):
            os.makedirs(f'{self.repo}/jar')
        name = f'{name}.{self.jar_suffix}'
        pattern = r'\"spider\":(\s)?\"([^,]+)\"'
        matches = re.search(pattern, text)
        try:
            jar = matches.group(2).replace('./', f'{url}/').split(';')[0]
            jar = jar.split('"spider":"')[-1]
            if name==f'{self.repo}.{self.jar_suffix}':
                name = f"{jar.split('/')[-1]}"
            print('jar地址: ', jar)
            timeout = self.timeout * 4
            if timeout > 15:
                timeout = 15
            r = self.s.get(jar, timeout=timeout, verify=False)
            if r.status_code != 200:
                raise Exception(f'jar下载失败, status_code:{r.status_code}')
            with open(f'{self.repo}/jar/{name}', 'wb') as f:
                f.write(r.content)
            jar = f'./jar/{name}'
            text = text.replace(matches.group(2), jar)
        except Exception as e:
            print(f'【jar下载失败】{name} jar地址: {jar} error:{e}')
        return text

    async def download(self, url, name, filename, cang=True):
        file_list = []
        for root, dirs, files in os.walk(self.repo):
            for file in files:
                file_list.append(file)
        if filename in file_list:
            print(f'{filename}：已经存在，无需重复下载')
            return
        if 'agit.ai' in url:
            print(f'下载异常：agit.ai失效')
            return
        
        # 下载单线路
        item = {}
        try:
            path = os.path.dirname(url)
            r = self.s.get(url, headers=self.headers, allow_redirects=True, timeout=self.timeout, verify=False)
            if r.status_code == 200:
                print("开始下载【线路】{}: {}".format(name, url))
                
                # 自动检测编码
                encoding = self.detect_encoding(r.content)
                try:
                    content = r.content.decode(encoding)
                except:
                    content = r.content.decode('utf-8', errors='ignore')
                
                if 'searchable' not in content:
                    html = await self.js_render(url)
                    if html and html.text:
                        content = html.text
                    else:
                        pic_content = self.picparse(url)
                        if pic_content and 'searchable' in pic_content:
                            content = self.get_jar(name, url, pic_content)
                            with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f:
                                f.write(content)
                                return
                
                if 'searchable' not in content:
                    raise Exception("内容中未找到searchable字段")
                    
                with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f:
                    try:
                        if content.startswith(u'\ufeff'):
                            content = content.encode('utf-8')[3:].decode('utf-8')
                        content = content.replace('./', f'{path}/')
                    except:
                        pass

                    content = self.ghproxy(content)
                    content = self.get_jar(name, url, content)
                    f.write(content)
                    pipes.add(name)
                    
                try:
                    if self.site_down:
                        await self.site_file_down([f'{self.repo}{self.sep}{filename}'], url)
                except Exception as e:
                    print(f'下载ext中的json失败: {e}')
                    
        except Exception as e:
            print(f"【线路】{name}: {url} 下载错误：{e}")
            
        # 单仓时写入item
        if os.path.exists(f'{self.repo}{self.sep}{filename}') and cang:
            item['name'] = name
            item['url'] = f'./{filename}'
            items.append(item)

    async def down(self, data, s_name):
        '''下载单仓'''
        newJson = {}
        global items
        items = []
        urls = data.get("urls") if data.get("urls") else data.get("sites")
        for u in urls:
            name = u.get("name", "").strip()
            if not name:
                continue
            name = self.remove_emojis(name)
            url = u.get("url")
            if not url:
                continue
            url = self.ghproxy(url)
            filename = '{}.txt'.format(name)
            if name in pipes:
                print(f"【线路】{name} 已存在，无需重复下载")
                continue
            await self.download(url, name, filename)
        newJson['urls'] = items
        newJson = pprint.pformat(newJson, width=200)
        print(f'开始写入单仓{s_name}')
        with open(f'{self.repo}{self.sep}{s_name}', 'w+', encoding='utf-8') as f:
            content = str(newJson).replace("'", '"')
            f.write(json.loads(json.dumps(content, indent=4, ensure_ascii=False)))

    def all(self):
        # 整合所有文件到all.json
        newJson = {}
        items = []
        files = self.remove_duplicates(self.repo)
        for file in files:
            item = {}
            item['name'] = file.split('.txt')[0]
            item['url'] = f'./{file}'
            items.append(item)
        newJson['urls'] = items
        newJson = pprint.pformat(newJson, width=200)
        print(f'开始写入all.json')
        with open(f'{self.repo}{self.sep}all.json', 'w+', encoding='utf-8') as f:
            content = str(newJson).replace("'", '"')
            f.write(json.loads(json.dumps(content, indent=4, ensure_ascii=False)))

    async def batch_handle_online_interface(self):
        # 下载线路，处理多url场景
        print(f'--------- 开始私有化在线接口 ----------')
        urls = self.url.split(',')
        for url in urls:
            # 解析URL
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            signame_value = query_params.get('signame', [''])[0]
            item = url.split('?&signame=')
            self.url = item[0]
            self.signame = signame_value if signame_value else None
            print(f'当前url: {self.url}')
            await self.storeHouse()
        await self.clean_directories()

    async def clean_directories(self):
        # Step 1: 删除 api/drpy2 目录（如果 self.drpy2 为假）
        if not self.drpy2:
            drpy2_path = f"{self.repo}/api/drpy2"
            if os.path.exists(drpy2_path):
                await asyncio.to_thread(shutil.rmtree, drpy2_path)

        # Step 2: 检查并删除空的 api 和 ext 目录
        directories = [f"{self.repo}/api", f"{self.repo}/ext"]
        for dir_path in directories:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                if not os.listdir(dir_path):  # 目录为空
                    await asyncio.to_thread(shutil.rmtree, dir_path)

    async def storeHouse(self):
        '''生成多仓json文件'''
        await self.download_drpy2_files()

        newJson = {}
        items = []

        # 解析最初链接
        try:
            res = self.s.get(self.url, headers=self.headers, verify=False, timeout=self.timeout)
            # 自动检测编码
            encoding = self.detect_encoding(res.content)
            try:
                res_text = res.content.decode(encoding)
            except:
                res_text = res.content.decode('utf-8', errors='ignore')
                
            if '404 Not Found' in res_text:
                print(f'{self.url} 请求异常')
                return
        except Exception as e:
            print(f"直接请求失败: {e}")
            try:
                html = await self.js_render(self.url)
                if html and html.text:
                    res_text = html.text.replace(' ', '').replace("'", '"')
                else:
                    res_text = self.picparse(self.url).replace(' ', '').replace("'", '"')
            except Exception as js_e:
                print(f"备用方案也失败: {js_e}")
                return

        # 线路
        if 'searchable' in str(res_text):
            filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
            path = os.path.dirname(self.url)
            print("【线路】 {}: {}".format(self.repo, self.url))
            try:
                with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f, open(
                        f'{self.repo}{self.sep}{self.target}', 'w+', encoding='utf-8') as f2:
                    content = self.ghproxy(res_text.replace('./', f'{path}/'))
                    content = self.get_jar(filename.split('.txt')[0], self.url, content)
                    # json容错处理
                    content = self.json_compatible(content)
                    f.write(content)
                    f2.write(content)
            except Exception as e:
                print(f"写入文件失败: {e}")
            try:
                if self.site_down:
                    await self.site_file_down([f'{self.repo}{self.sep}{filename}',f'{self.repo}{self.sep}{self.target}'], self.url)
            except Exception as e:
                print(f"下载site文件失败: {e}")
            return

        # json容错处理
        res_text = self.json_compatible(res_text)
        # 移除注释
        datas = ''
        for d in res_text.splitlines():
            if d.find(" //") != -1 or d.find("// ") != -1 or d.find(",//") != -1 or d.startswith("//"):
                d = d.split(" //", maxsplit=1)[0]
                d = d.split("// ", maxsplit=1)[0]
                d = d.split(",//", maxsplit=1)[0]
                d = d.split("//", maxsplit=1)[0]
            datas = '\n'.join([datas, d])
        # 容错处理，便于json解析
        datas = datas.replace('\n', '')
        res_text = datas.replace(' ', '').replace("'", '"').replace('\n', '')
        if datas.startswith(u'\ufeff'):
            try:
                res_text = datas.encode('utf-8')[3:].decode('utf-8').replace(' ', '').replace("'", '"').replace('\n', '')
            except Exception as e:
                res_text = datas.encode('utf-8')[4:].decode('utf-8').replace(' ', '').replace("'", '"').replace('\n', '')

        # 多仓
        elif 'storeHouse' in datas:
            try:
                res_data = json.loads(str(res_text))
                srcs = res_data.get("storeHouse") if res_data.get("storeHouse") else None
                if srcs:
                    i = 1
                    for s in srcs:
                        if i > self.num:
                            break
                        i += 1
                        item = {}
                        s_name = s.get("sourceName")
                        if not s_name:
                            continue
                        s_name = self.remove_emojis(s_name)
                        s_name = f'{s_name}.json'
                        s_url = s.get("sourceUrl")
                        if not s_url:
                            continue
                        print("【多仓】 {}: {}".format(s_name, s_url))
                        try:
                            if self.s.get(s_url, headers=self.headers).status_code >= 400:
                                continue
                        except Exception as e:
                            print('地址无法响应: ',e)
                            continue
                        try:
                            s_res = self.s.get(s_url, headers=self.headers)
                            encoding = self.detect_encoding(s_res.content)
                            try:
                                data_content = s_res.content.decode(encoding)
                            except:
                                data_content = s_res.content.decode('utf-8', errors='ignore')
                        except Exception as e:
                            print(f"获取子仓数据失败: {e}")
                            continue

                        datas = ''
                        for d in data_content.splitlines():
                            if d.find(" //") != -1 or d.find("// ") != -1 or d.find(",//") != -1 or d.startswith("//"):
                                d = d.split(" //", maxsplit=1)[0]
                                d = d.split("// ", maxsplit=1)[0]
                                d = d.split(",//", maxmaxsplit=1)[0]
                                d = d.split("//", maxsplit=1)[0]
                            datas = '\n'.join([datas, d])

                        try:
                            if datas.lstrip().startswith(u'\ufeff'):
                                datas = datas.encode('utf-8')[1:]
                            await self.down(json.loads(datas), s_name)
                        except Exception as e:
                            print(f"处理子仓数据失败: {e}")
                        item['sourceName'] = s_name.split('.json')[0]
                        item['sourceUrl'] = f'./{s_name}'
                        items.append(item)
                    newJson["storeHouse"] = items
                    newJson = pprint.pformat(newJson, width=200)
                    with open(f'{self.repo}{self.sep}{self.target}', 'w+', encoding='utf-8') as f:
                        print(f"开始写入{self.target}")
                        f.write(json.dumps(json.loads(str(newJson).replace("'", '"')), sort_keys=True, indent=4, ensure_ascii=False))
            except Exception as e:
                print(f"处理多仓数据失败: {e}")
        # 单仓
        else:
            try:
                res_data = json.loads(str(res_text))
            except Exception as e:
                if 'domainnameisinvalid' in res_text:
                    print(f'该域名无效，请提供正常可用接口')
                    return
                try:
                    html = await self.js_render(self.url)
                    if html and html.text:
                        res_text = html.text.replace(' ', '').replace("'", '"')
                    else:
                        res_text = self.picparse(self.url).replace(' ', '').replace("'", '"')
                    res_data = json.loads(str(res_text))
                except Exception as e:
                    print(f"解析单仓数据失败: {e}")
                    return
            s_name = self.target
            s_url = self.url
            print("【单仓】 {}: {}".format(s_name, s_url))
            try:
                await self.down(res_data, s_name)
            except Exception as e:
                print(f"处理单仓失败: {e}")
                if 'searchable' in str(res_text):
                    filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
                    print("【线路】 {}: {}".format(filename, self.url))
                    try:
                        await self.download(self.url, filename.split('.txt')[0], filename, cang=False)
                    except Exception as e:
                        print('下载异常', e)

    def run(self):
        start_time = time.time()
        # 创建repo目录
        if not os.path.exists(self.repo):
            os.makedirs(self.repo)
        
        asyncio.run(self.batch_handle_online_interface())
        self.all()
        end_time = time.time()
        print(f'耗时: {end_time - start_time} 秒')
        print(f'文件已保存到本地目录: {self.repo}')

def main():
    # 从环境变量获取配置
    url = os.getenv('TVBOX_URL', '')
    repo = os.getenv('TVBOX_REPO', 'tvbox')
    num = int(os.getenv('TVBOX_NUM', '10'))
    target = os.getenv('TVBOX_TARGET', 'tvbox.json')
    timeout = int(os.getenv('TVBOX_TIMEOUT', '10'))  # 增加默认超时时间
    jar_suffix = os.getenv('TVBOX_JAR_SUFFIX', 'jar')
    site_down = os.getenv('TVBOX_SITE_DOWN', 'true').lower() == 'true'
    
    if not url:
        print("错误: 请设置 TVBOX_URL 环境变量")
        return
    
    print(f"开始处理TVBox源: {url}")
    GetSrc(
        url=url,
        repo=repo,
        num=num,
        target=target,
        timeout=timeout,
        jar_suffix=jar_suffix,
        site_down=site_down
    ).run()

if __name__ == '__main__':
    main()
