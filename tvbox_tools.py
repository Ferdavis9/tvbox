# -*- coding: utf-8 -*-
#!/usr/bin/env python3
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

# 禁用SSL验证和警告
ssl._create_default_https_context = ssl._create_unverified_context
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

global pipes
pipes = set()

class GetSrc:
    def __init__(self, username=None, token=None, url=None, repo=None, num=10, target=None, timeout=3, signame=None, mirror=None, jar_suffix=None, site_down=True):
        # 核心配置：容器内存储目录（固定为/tvbox_data，方便Filebrowser暴露）
        self.repo = repo if repo else '/tvbox_data'
        self.jar_suffix = jar_suffix if jar_suffix else 'jar'
        self.site_down = site_down  # 是否下载site里的文件到本地
        self.mirror = int(str(mirror).strip()) if mirror else 1
        self.mirror_proxy = 'https://ghp.ci/https://raw.githubusercontent.com'
        self.num = int(num)
        self.sep = os.path.sep
        self.username = username  # 保留但无实际作用（无需推送仓库）
        self.token = token        # 保留但无实际作用
        self.timeout = timeout
        self.url = url.replace(' ','').replace('，',',').strip() if url else url
        self.target = f'{target.split(".json")[0]}.json' if target else 'tvbox.json'
        self.headers = {"user-agent": "okhttp/3.15 Html5Plus/1.0 (Immersed/23.92157)"}
        self.s = requests.Session()
        self.signame = signame
        # 请求重试配置
        retries = Retry(total=3, backoff_factor=1)
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))
        self.size_tolerance = 15  # 线路文件大小误差在15以内认为是同一个
        self.main_branch = 'main'
        
        # 移除cnb.cool相关配置（无需推送仓库），改为本地路径
        self.slot = f'/tvbox_data'
        self.cnb_slot = f'/tvbox_data'

        # GitHub镜像代理列表（保留用于替换链接）
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
        self.gh2 = [
            "https://fastly.jsdelivr.net/gh",
            "https://jsd.onmicrosoft.cn/gh",
            "https://gcore.jsdelivr.net/gh",
            "https://cdn.jsdmirror.com/gh",
            "https://cdn.jsdmirror.cn/gh",
            "https://jsd.proxy.aks.moe/gh",
            "https://jsdelivr.b-cdn.net/gh",
            "https://jsdelivr.pai233.top/gh"
        ]

        # drpy2 文件列表
        self.drpy2 = False
        self.drpy2_files = [
            "cat.js", "crypto-js.js", "drpy2.min.js", "http.js", "jquery.min.js",
            "jsencrypt.js", "log.js", "pako.min.js", "similarity.js", "uri.min.js",
            "cheerio.min.js", "deep.parse.js", "gbk.js", "jinja.js", "json5.js",
            "node-rsa.js", "script.js", "spider.js", "模板.js", "quark.min.js"
        ]

    async def download_drpy2_files(self):
        """异步下载 drpy2 文件到 self.repo/api/drpy2"""
        api_drpy2_dir = os.path.join(self.repo, "api/drpy2")
        if not os.path.exists(api_drpy2_dir):
            os.makedirs(api_drpy2_dir)
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
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
                                print(f"下载 {filename} 最终失败: {e}")
                                return False

                tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def file_hash(self, filepath):
        """计算文件SHA256哈希"""
        if not os.path.exists(filepath):
            return ""
        with open(filepath, 'rb') as f:
            file_contents = f.read()
            return hashlib.sha256(file_contents).hexdigest()

    def remove_duplicates(self, folder_path):
        """去重线路文件，保留唯一文件"""
        folder_path = Path(folder_path)
        jar_folder = f'{folder_path}/jar'
        excludes = {'.json', '.git', 'jar', '.idea', 'ext', '.DS_Store', '.md'}
        files_info = {}

        # 重命名jar目录文件后缀
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
                # 删除重复文件
                os.remove(info['path'])
                self.remove_jar_file(jar_folder, file_name.replace('.txt', f'{self.jar_suffix}'))

        keep_files.sort()
        return keep_files

    def rename_jar_suffix(self, jar_folder):
        """重命名jar目录下所有文件后缀为self.jar_suffix"""
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
        """移除文本中的emoji和特殊字符"""
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # 表情
                                   u"\U0001F300-\U0001F5FF"  # 符号
                                   u"\U0001F680-\U0001F6FF"  # 交通
                                   u"\U0001F1E0-\U0001F1FF"  # 国旗
                                   "\U00002500-\U00002BEF"  # 中文
                                   "\U00010000-\U0010ffff"
                                   "\u200d"
                                   "\u20E3"
                                   "\ufe0f"
                                   "]+", flags=re.UNICODE)
        text = text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚','').strip()
        return emoji_pattern.sub('', text)

    def json_compatible(self, str_data):
        """修复JSON格式兼容性问题"""
        res = str_data.replace('//"', '"').replace('//{', '{')
        res = res.replace('key:', '"key":').replace('name:', '"name":')
        res = res.replace('type:', '"type":').replace('api:','"api":')
        res = res.replace('searchable:', '"searchable":').replace('quickSearch:', '"quickSearch":')
        res = res.replace('filterable:','"filterable":').strip()
        return res

    def ghproxy(self, str_data):
        """统一GitHub代理链接"""
        u = 'https://github.moeyy.xyz/'
        res = str_data.replace('https://ghproxy.net/', u)
        res = res.replace('https://ghproxy.com/', u).replace('https://gh-proxy.com/',u)
        res = res.replace('https://mirror.ghproxy.com/',u).replace('https://gh.xxooo.cf/',u)
        res = res.replace('https://ghp.ci/',u).replace('https://gitdl.cn/',u)
        return res

    def picparse(self, url):
        """解析图片中的base64编码内容"""
        r = self.s.get(url, headers=self.headers, timeout=self.timeout, verify=False)
        pattern = r'([A-Za-z0-9+/]+={0,2})'
        matches = re.findall(pattern, r.text)
        decoded_data = base64.b64decode(matches[-1])
        text = decoded_data.decode('utf-8')
        return text

    async def js_render(self, url):
        """JS渲染页面获取内容"""
        timeout = self.timeout * 4
        if timeout > 15:
            timeout = 15
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-setuid-sandbox',
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
        """异步下载site中的ext/jar/api文件到本地"""
        ext_dir = f"{self.repo}/ext"
        jar_dir = f"{self.repo}/jar"
        api_dir = f"{self.repo}/api"
        api_drpy2_dir = f"{self.repo}/api/drpy2"
        
        # 创建目录
        for directory in [ext_dir, jar_dir, api_dir, api_drpy2_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # 读取api.json
        file = files[0]
        file2 = files[1] if len(files) > 1 else ''
        try:
            with open(file, 'r', encoding='utf-8') as f:
                api_data = commentjson.load(f)
                sites = api_data["sites"]
        except Exception as e:
            print(f"解析 {file} 失败: {e}")
            return

        # 异步下载任务
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
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
                            # 过滤文件类型
                            if field == "ext" and not clean_value.endswith((".js", ".txt", ".json")):
                                continue
                            elif field == "api":
                                if os.path.basename(clean_value).lower() in ["drpy2.min.js","quark.min.js"]:
                                    self.drpy2 = True
                                    site[field] = f"{self.cnb_slot}/{api_drpy2_dir}/{os.path.basename(clean_value).lower()}"
                                    continue
                                if not clean_value.endswith(".py"):
                                    continue

                            # 构建下载URL和本地路径
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
                                                site[field] = f'{self.cnb_slot}/{repo_dir_name}/{filename}'
                                                return True
                                            content = await response.read()
                                            with open(local_path, "wb") as f:
                                                f.write(content)
                                            site[field] = f'{self.cnb_slot}/{repo_dir_name}/{filename}'
                                            return True
                                    except Exception as e:
                                        if attempt < retries - 1:
                                            await asyncio.sleep(1)
                                        else:
                                            print(f"下载 {json_url} 最终失败: {e}")
                                            return False

                            tasks.append(download_task())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # 写回更新后的数据
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=4, ensure_ascii=False)

        if file2 and os.path.basename(file2):
            with open(file2, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, indent=4, ensure_ascii=False)

    def get_jar(self, name, url, text):
        """下载jar文件并替换链接"""
        jar_dir = f'{self.repo}/jar'
        if not os.path.exists(jar_dir):
            os.makedirs(jar_dir)
        
        name = f'{name}.{self.jar_suffix}'
        pattern = r'\"spider\":(\s)?\"([^,]+)\"'
        matches = re.search(pattern, text)
        try:
            jar_url = matches.group(2).replace('./', f'{url}/').split(';')[0]
            jar_url = jar_url.split('"spider":"')[-1]
            if name == f'{self.repo}.{self.jar_suffix}':
                name = f"{jar_url.split('/')[-1]}"
            
            print(f'jar地址: {jar_url}')
            timeout = self.timeout * 4
            if timeout > 15:
                timeout = 15
            
            r = self.s.get(jar_url, timeout=timeout, verify=False)
            if r.status_code != 200:
                raise Exception(f'status_code:{r.status_code}')
            
            # 保存jar文件到本地
            jar_path = os.path.join(jar_dir, name)
            with open(jar_path, 'wb') as f:
                f.write(r.content)
            
            # 替换为本地路径
            local_jar_url = f'{self.cnb_slot}/jar/{name}'
            text = text.replace(matches.group(2), local_jar_url)
        except Exception as e:
            print(f'【jar下载失败】{name} jar地址: {jar_url} error:{e}')
        return text

    async def download(self, url, name, filename, cang=True):
        """下载单个线路文件"""
        file_list = []
        for root, dirs, files in os.walk(self.repo):
            file_list.extend(files)
        
        if filename in file_list:
            print(f'{filename}：已存在，跳过')
            return
        
        if 'agit.ai' in url:
            print(f'下载异常：agit.ai失效 - {url}')
            return

        item = {}
        try:
            path = os.path.dirname(url)
            r = self.s.get(url, headers=self.headers, allow_redirects=True, timeout=self.timeout, verify=False)
            if r.status_code == 200:
                print(f"开始下载【线路】{name}: {url}")
                # 处理非标准JSON内容
                if 'searchable' not in r.text:
                    # 尝试JS渲染
                    html = await self.js_render(url)
                    if not html or not html.text:
                        # 尝试解析图片base64
                        r_text = self.picparse(url)
                        if 'searchable' not in r_text:
                            raise Exception("未找到searchable字段")
                        r_text = self.get_jar(name, url, r_text)
                        with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f:
                            f.write(r_text)
                        return
                    r_text = html.text
                else:
                    r_text = r.text

                if 'searchable' not in r_text:
                    raise Exception("未找到searchable字段")

                # 处理文件编码和路径替换
                try:
                    if r.content.decode('utf8').startswith(u'\ufeff'):
                        str_data = r.content.decode('utf8').encode('utf-8')[3:].decode('utf-8')
                    else:
                        str_data = r.content.decode('utf-8').replace('./', f'{path}/')
                except:
                    str_data = r_text
                
                # 替换GitHub代理和jar链接
                str_data = self.ghproxy(str_data.replace('./', f'{path}/'))
                str_data = self.get_jar(name, url, str_data)

                # 保存文件
                with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f:
                    f.write(str_data)
                pipes.add(name)

                # 下载site中的文件
                if self.site_down:
                    await self.site_file_down([f'{self.repo}{self.sep}{filename}'], url)
        except Exception as e:
            print(f"【线路】{name}: {url} 下载错误：{e}")

        # 单仓写入（本地存储，无需推送）
        if os.path.exists(f'{self.repo}{self.sep}{filename}') and cang:
            item['name'] = name
            item['url'] = f'{self.cnb_slot}/{filename}'
            global items
            items.append(item)

    async def down(self, data, s_name):
        """下载单仓数据"""
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
                print(f"【线路】{name} 已存在，跳过")
                continue
            
            await self.download(url, name, filename)

        # 生成单仓JSON
        newJson['urls'] = items
        newJson_str = pprint.pformat(newJson, width=200)
        print(f'开始写入单仓 {s_name}')
        with open(f'{self.repo}{self.sep}{s_name}', 'w+', encoding='utf-8') as f:
            content = newJson_str.replace("'", '"')
            f.write(json.dumps(json.loads(content), indent=4, ensure_ascii=False))

    def all(self):
        """整合所有线路到all.json"""
        newJson = {}
        items = []
        files = self.remove_duplicates(self.repo)
        
        for file in files:
            item = {}
            item['name'] = file.split('.txt')[0]
            item['url'] = f'{self.cnb_slot}/{file}'
            items.append(item)
        
        newJson['urls'] = items
        newJson_str = pprint.pformat(newJson, width=200)
        print(f'开始写入all.json')
        with open(f'{self.repo}{self.sep}all.json', 'w+', encoding='utf-8') as f:
            content = newJson_str.replace("'", '"')
            f.write(json.dumps(json.loads(content), indent=4, ensure_ascii=False))

    async def batch_handle_online_interface(self):
        """批量处理在线接口"""
        print(f'--------- 开始处理在线接口 ----------')
        if not self.url:
            print("未配置TVBOX_URL环境变量，跳过下载")
            return
        
        urls = self.url.split(',')
        for url in urls:
            # 解析signame参数
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            signame_value = query_params.get('signame', [''])[0]
            self.signame = signame_value if signame_value else None
            self.url = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
            print(f'当前处理URL: {self.url}')
            await self.storeHouse()
        
        await self.clean_directories()

    async def clean_directories(self):
        """清理空目录和无用文件"""
        # 删除空的drpy2目录
        if not self.drpy2:
            drpy2_path = f"{self.repo}/api/drpy2"
            if os.path.exists(drpy2_path):
                shutil.rmtree(drpy2_path)

        # 清理空目录
        directories = [f"{self.repo}/api", f"{self.repo}/ext"]
        for dir_path in directories:
            if os.path.exists(dir_path) and os.path.isdir(dir_path) and not os.listdir(dir_path):
                shutil.rmtree(dir_path)

    async def storeHouse(self):
        """核心处理逻辑：下载并处理TVBox源"""
        # 创建存储目录
        if not os.path.exists(self.repo):
            os.makedirs(self.repo)
        
        # 下载drpy2基础文件
        await self.download_drpy2_files()

        # 读取在线接口内容
        try:
            res = self.s.get(self.url, headers=self.headers, verify=False, timeout=self.timeout).content.decode('utf8')
            if '404 Not Found' in res:
                print(f'{self.url} 请求异常（404）')
                return
        except Exception as e:
            print(f'请求 {self.url} 失败，尝试JS渲染: {e}')
            html = await self.js_render(self.url)
            res = html.text if html else ""
            if not res:
                res = self.picparse(self.url)
            res = res.replace(' ', '').replace("'", '"')

        # 处理单个线路文件（含searchable字段）
        if 'searchable' in str(res):
            filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
            path = os.path.dirname(self.url)
            print(f"【线路】 {filename}: {self.url}")
            
            try:
                res = self.ghproxy(res.replace('./', f'{path}/'))
                res = self.get_jar(filename.split('.txt')[0], self.url, res)
                res = self.json_compatible(res)
                
                # 保存文件
                with open(f'{self.repo}{self.sep}{filename}', 'w+', encoding='utf-8') as f, open(
                        f'{self.repo}{self.sep}{self.target}', 'w+', encoding='utf-8') as f2:
                    f.write(res)
                    f2.write(res)
                
                # 下载site文件
                if self.site_down:
                    await self.site_file_down([f'{self.repo}{self.sep}{filename}', f'{self.repo}{self.sep}{self.target}'], self.url)
            except Exception as e:
                print(f'保存线路文件失败: {e}')
            return

        # 清理JSON注释和格式
        res = self.json_compatible(res)
        datas = ''
        for d in res.splitlines():
            if "//" in d:
                d = d.split("//")[0]
            datas += d.strip()
        
        # 处理BOM头
        datas = datas.replace('\n', '').replace(' ', '').replace("'", '"')
        if datas.startswith(u'\ufeff'):
            datas = datas.encode('utf-8')[3:].decode('utf-8')

        # 处理多仓数据
        if 'storeHouse' in datas:
            try:
                res_json = json.loads(datas)
                srcs = res_json.get("storeHouse", [])
                if not srcs:
                    return
                
                newJson = {}
                items = []
                i = 1
                for s in srcs:
                    if i > self.num:
                        break
                    i += 1
                    
                    s_name = s.get("sourceName", "")
                    if not s_name:
                        continue
                    s_name = self.remove_emojis(s_name) + '.json'
                    s_url = s.get("sourceUrl")
                    if not s_url:
                        continue
                    
                    print(f"【多仓】 {s_name}: {s_url}")
                    
                    # 检查URL可用性
                    try:
                        if self.s.get(s_url, headers=self.headers, timeout=self.timeout).status_code >= 400:
                            continue
                    except Exception as e:
                        print(f'地址无法访问: {s_url} - {e}')
                        continue

                    # 读取并清理数据
                    try:
                        resp = self.s.get(s_url, headers=self.headers, timeout=self.timeout)
                        data = resp.content.decode('utf-8')
                        if data.startswith(u'\ufeff'):
                            data = data[1:]
                    except Exception as e:
                        print(f'读取多仓数据失败: {s_url} - {e}')
                        continue

                    # 清理注释
                    clean_data = ''
                    for d in data.splitlines():
                        if "//" in d:
                            d = d.split("//")[0]
                        clean_data += d.strip()

                    # 处理并下载
                    try:
                        await self.down(json.loads(clean_data), s_name)
                        item = {
                            'sourceName': s_name.split('.json')[0],
                            'sourceUrl': f'{self.cnb_slot}/{s_name}'
                        }
                        items.append(item)
                    except Exception as e:
                        print(f'处理多仓数据失败: {s_url} - {e}')
                        continue

                # 生成多仓JSON
                newJson["storeHouse"] = items
                newJson_str = pprint.pformat(newJson, width=200)
                with open(f'{self.repo}{self.sep}{self.target}', 'w+', encoding='utf-8') as f:
                    content = newJson_str.replace("'", '"')
                    f.write(json.dumps(json.loads(content), indent=4, ensure_ascii=False))
            except Exception as e:
                print(f'处理多仓数据异常: {e}')
        # 处理单仓数据
        else:
            try:
                res_json = json.loads(datas)
            except Exception as e:
                print(f'解析JSON失败，尝试JS渲染: {e}')
                html = await self.js_render(self.url)
                res = html.text if html else self.picparse(self.url)
                res = res.replace(' ', '').replace("'", '"')
                try:
                    res_json = json.loads(res)
                except Exception as e:
                    print(f'最终解析失败: {e}')
                    return

            s_name = self.target
            s_url = self.url
            print(f"【单仓】 {s_name}: {s_url}")
            
            try:
                await self.down(res_json, s_name)
            except Exception as e:
                print(f'处理单仓失败，尝试直接下载线路: {e}')
                if 'searchable' in str(res):
                    filename = self.signame + '.txt' if self.signame else f"{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
                    print(f"【线路】 {filename}: {self.url}")
                    await self.download(self.url, filename.split('.txt')[0], filename, cang=False)

    def mirror_init(self):
        """初始化镜像代理配置"""
        # gh1 类型（raw.githubusercontent.com代理）
        if self.mirror == 1:
            self.mirror_proxy = 'https://ghp.ci/https://raw.githubusercontent.com'
        elif self.mirror == 2:
            self.mirror_proxy = 'https://gh.xxooo.cf/https://raw.githubusercontent.com'
        elif self.mirror == 3:
            self.mirror_proxy = 'https://ghproxy.net/https://raw.githubusercontent.com'
        elif self.mirror == 4:
            self.mirror_proxy = 'https://github.moeyy.xyz/https://raw.githubusercontent.com'
        elif self.mirror == 5:
            self.mirror_proxy = 'https://gh-proxy.com/https://raw.githubusercontent.com'
        elif self.mirror == 6:
            self.mirror_proxy = 'https://ghproxy.cc/https://raw.githubusercontent.com'
        elif self.mirror == 7:
            self.mirror_proxy = 'https://raw.yzuu.cf'
        elif self.mirror == 8:
            self.mirror_proxy = 'https://raw.nuaa.cf'
        elif self.mirror == 9:
            self.mirror_proxy = 'https://raw.kkgithub.com'
        elif self.mirror == 10:
            self.mirror_proxy = 'https://gh.con.sh/https://raw.githubusercontent.com'
        elif self.mirror == 11:
            self.mirror_proxy = 'https://gh.llkk.cc/https://raw.githubusercontent.com'
        elif self.mirror == 12:
            self.mirror_proxy = 'https://gh.ddlc.top/https://raw.githubusercontent.com'
        elif self.mirror == 13:
            self.mirror_proxy = 'https://gh-proxy.llyke.com/https://raw.githubusercontent.com'

        # gh2 类型（jsdelivr代理）
        elif self.mirror == 21:
            self.mirror_proxy = "https://fastly.jsdelivr.net/gh"
        elif self.mirror == 22:
            self.mirror_proxy = "https://jsd.onmicrosoft.cn/gh"
        elif self.mirror == 23:
            self.mirror_proxy = "https://gcore.jsdelivr.net/gh"
        elif self.mirror == 24:
            self.mirror_proxy = "https://cdn.jsdmirror.com/gh"
        elif self.mirror == 25:
            self.mirror_proxy = "https://cdn.jsdmirror.cn/gh"
        elif self.mirror == 26:
            self.mirror_proxy = "https://jsd.proxy.aks.moe/gh"
        elif self.mirror == 27:
            self.mirror_proxy = "https://jsdelivr.b-cdn.net/gh"
        elif self.mirror == 28:
            self.mirror_proxy = "https://jsdelivr.pai233.top/gh"

        # 更新本地slot路径
        self.slot = f'/tvbox_data'
        self.cnb_slot = f'/tvbox_data'

    def mirror_proxy2new(self):
        """替换文件中的镜像代理链接为本地路径"""
        if self.mirror < 20:
            # 处理gh1类型代理
            patterns = [re.escape(proxy) for proxy in self.gh2]
            self.pattern = re.compile(r'({})/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(/.*)?'.format('|'.join(patterns)))
            
            for root, dirs, files in os.walk(self.repo):
                for file in files:
                    if file.endswith('.txt') or file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # 替换为本地路径
                        new_content = content
                        for proxy in self.gh1:
                            new_content = new_content.replace(proxy, self.mirror_proxy)
                        # 写入替换后的内容
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
        elif self.mirror > 20:
            # 处理gh2类型代理
            if self.jar_suffix not in ['html','js','css','json','txt']:
                return
            patterns = [re.escape(proxy) for proxy in self.gh1]
            self.pattern = re.compile(r'({})/(.+?)/(.+?)/(master|main)(/|/.*)'.format('|'.join(patterns)))
            
            for filename in os.listdir(self.repo):
                file_path = os.path.join(self.repo, filename)
                if os.path.isfile(file_path) and (filename.endswith('.txt') or filename.endswith('.json')):
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        new_content = content
                        for proxy in self.gh2:
                            new_content = new_content.replace(proxy, self.mirror_proxy)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)

    def run(self):
        """主执行函数"""
        start_time = time.time()
        # 初始化镜像代理
        self.mirror_init()
        # 异步处理在线接口
        asyncio.run(self.batch_handle_online_interface())
        # 生成all.json
        self.all()
        # 替换镜像代理链接
        self.mirror_proxy2new()
        # 输出结果
        end_time = time.time()
        print(f'处理完成，耗时: {end_time - start_time} 秒')
        print(f'文件存储路径: {self.repo}')
        print(f'Filebrowser访问地址: http://<容器IP>:27677')

if __name__ == '__main__':
    # 从环境变量读取配置
    import os
    TVBOX_URL = os.getenv('TVBOX_URL', '')
    TVBOX_MIRROR = int(os.getenv('TVBOX_MIRROR', 4))
    TVBOX_NUM = int(os.getenv('TVBOX_NUM', 10))
    TVBOX_SITE_DOWN = os.getenv('TVBOX_SITE_DOWN', 'true').lower() == 'true'
    
    # 执行核心逻辑
    GetSrc(
        url=TVBOX_URL,
        mirror=TVBOX_MIRROR,
        num=TVBOX_NUM,
        site_down=TVBOX_SITE_DOWN
    ).run()
