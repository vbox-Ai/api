# coding=utf-8
# 熊猫福利 - API聚合源（vbox修复版）
import sys
import requests
import re
import json
from urllib.parse import quote, unquote, urljoin
sys.path.append('..')
from base.spider import Spider as BaseSpider

xurl = "https://www.5r88x.com/home.html"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
api_url = 'https://spiderscloudcn2.51111666.com'

class Spider(BaseSpider):
    """
    vbox 福利蜘蛛修复说明：
    1. 类继承修复：避免 Spider 名字遮蔽基类
    2. localProxy 兼容 iOS 端 JSON 字符串参数格式
    3. playerContent 的 m3u8 走本地代理
    4. detailContent 的 vod_id 不能为空
    5. getName 返回有意义的名称
    """

    def getName(self):
        return "熊猫"

    def init(self, extend=""):
        self.serverMap = self.getServerMap()
        self.session = requests.Session()
        self.session.headers.update(headerx)

    # ==================== 服务器线路配置 ====================

    def getServerMap(self):
        """从getDataInit接口动态获取视频服务器线路配置(macVodLinkMap)"""
        try:
            data = {"name": "John", "age": 31, "city": "New York"}
            res = requests.post(api_url + '/getDataInit', headers=headerx, json=data, timeout=10)
            res.encoding = "utf-8"
            json_dict = json.loads(res.text)
            return json_dict["data"].get("macVodLinkMap", {})
        except:
            # 接口获取失败时使用备用硬编码配置
            return {
                "10": {"LINK_1": "https://xcdn10.uedugtgt.com", "LINK_2": "https://s10.dqsldz.com", "LINK_3": "https://7wzx9.com"},
                "11": {"LINK_1": "https://xcdn11.uedugtgt.com", "LINK_2": "https://xcdn11.uedugtgt.com", "LINK_3": "https://xm101.com"},
                "12": {"LINK_1": "https://xcdn12.zgnzcyw.com", "LINK_2": "https://s12.lzaotw.com", "LINK_3": "https://xm131.com"},
                "13": {"LINK_1": "https://xcdn13.sxyjspsc.com", "LINK_2": "https://s13.lzaotw.com", "LINK_3": "https://xm141.com"},
                "14": {"LINK_1": "https://xcdn14.chahewl.com", "LINK_2": "https://s14.getehu.com", "LINK_3": "https://eu3.xm141.com"},
                "15": {"LINK_1": "https://xcdn15.hzyhzy6.com", "LINK_2": "https://s15.getehu.com", "LINK_3": "https://eu4.9997f.com"},
                "16": {"LINK_1": "https://ok16.hzx8188.com", "LINK_2": "https://s16.hdbjzs.com", "LINK_3": "https://s16.hdbjzs.com"},
                "17": {"LINK_1": "https://17bb.zgnzcyw.com", "LINK_2": "https://s17.izxih.com", "LINK_3": "https://s17.izxih.com"},
                "18": {"LINK_1": "https://18bb.sxyjspsc.com", "LINK_2": "https://s18.hdbjzs.com", "LINK_3": "https://s18.hdbjzs.com"},
            }

    def isVideoFormat(self, url):
        return url and ('.m3u8' in url or '.mp4' in url)

    def manualVideoCheck(self):
        return False

    # ==================== 首页 ====================

    def homeContent(self, filter=False):
        data = {"name": "John", "age": 31, "city": "New York"}
        res = requests.post(api_url + '/getDataInit', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        menu0ListMap = json_dict["data"]["menu0ListMap"]
        result = {}
        result['class'] = []
        for item in menu0ListMap:
            if item['typeName'] in ("传媒", "视频", "电影"):
                for item1 in item['menu2List']:
                    result['class'].append({'type_id': item1['typeId2'], 'type_name': item1['typeName2']})
        return result

    def homeVideoContent(self):
        videos = []
        try:
            data = {
                "command": "WEB_GET_INFO",
                "pageNumber": 1,
                "RecordsPage": 20,
                "typeId": "24",
                "typeMid": "1",
                "languageType": "CN",
                "content": ""
            }
            res = requests.post(api_url + '/forward', headers=headerx, json=data)
            res.encoding = "utf-8"
            json_dict = json.loads(res.text)
            menu0ListMap = json_dict["data"]["resultList"]
            for item in menu0ListMap:
                name1 = item['vod_name'].replace("yy8ycom", "")
                pattern = r'(.*?)-(.*?)-\d+\s+'
                name = re.sub(pattern, '', name1)
                vid = item['id']
                pic = item['vod_pic']
                sid = item['vod_server_id']
                video = {
                    "vod_id": str(vid) + '#' + str(sid),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ''
                }
                videos.append(video)
            result = {'list': videos}
            return result
        except:
            pass
        return {'list': []}

    # ==================== 分类 ====================

    def categoryContent(self, cid, pg=1, filter=False, extend=None):
        result = {}
        videos = []
        if not pg:
            pg = 1

        try:
            data = {
                "command": "WEB_GET_INFO",
                "pageNumber": pg,
                "RecordsPage": 20,
                "typeId": cid,
                "typeMid": "1",
                "languageType": "CN",
                "content": ""
            }
            res = requests.post(api_url + '/forward', headers=headerx, json=data)
            res.encoding = "utf-8"
            json_dict = json.loads(res.text)
            menu0ListMap = json_dict["data"]["resultList"]
            for item in menu0ListMap:
                name1 = item['vod_name'].replace("yy8ycom", "")
                pattern = r'(.*?)-(.*?)-\d+\s+'
                name = re.sub(pattern, '', name1)
                vid = item['id']
                pic = item['vod_pic']
                sid = item['vod_server_id']
                video = {
                    "vod_id": str(vid) + '#' + str(sid),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ''
                }
                videos.append(video)
        except:
            pass

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    # ==================== 详情 ====================

    def detailContent(self, ids):
        did = ids[0]
        cid, svid = did.split("#")
        videos = []
        result = {}
        data = {
            "command": "WEB_GET_INFO_DETAIL",
            "type_Mid": "1",
            "id": cid,
            "languageType": "CN"
        }
        res = requests.post(api_url + '/forward', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        vod_url_path = json_dict['data']["result"]["vod_url"]
        vod_name = json_dict['data']["result"].get("vod_name", "")
        vod_pic = json_dict['data']["result"].get("vod_pic", "")

        # 确保serverMap已加载
        if not hasattr(self, 'serverMap') or not self.serverMap:
            self.serverMap = self.getServerMap()

        # 根据vod_server_id动态获取视频服务器地址
        server_info = self.serverMap.get(str(svid), {})
        link1 = server_info.get("LINK_1", "")
        link2 = server_info.get("LINK_2", "")
        link3 = server_info.get("LINK_3", "")

        # 构建多线路播放地址(国内线路1/国内线路2/海外线路)
        play_froms = []
        play_urls = []

        if link1:
            play_froms.append("国内线路1")
            play_urls.append("播放$" + link1 + vod_url_path)
        if link2 and link2 != link1:
            play_froms.append("国内线路2")
            play_urls.append("播放$" + link2 + vod_url_path)
        if link3 and link3 != link1 and link3 != link2:
            play_froms.append("海外线路")
            play_urls.append("播放$" + link3 + vod_url_path)

        # 如果没有匹配到服务器配置，兜底直接使用vod_url
        if not play_froms:
            play_froms.append("直链播放")
            play_urls.append("播放$" + vod_url_path)

        videos.append({
            "vod_id": did,
            "vod_name": vod_name or did,
            "vod_pic": vod_pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "$$$".join(play_froms),
            "vod_play_url": "$$$".join(play_urls)
        })

        result['list'] = videos
        return result

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags=None):
        """
        vbox修复：m3u8 链接走本地代理，header 用 dict 格式
        """
        if not id:
            return {"parse": 1, "url": "", "header": {}}

        # 已经是直链 m3u8/mp4
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            if '.m3u8' in id:
                # m3u8 走本地代理（支持广告清洗、防盗链）
                proxy_url = self._build_proxy_url('m3u8', id, '')
                return {"parse": 0, "url": proxy_url, "header": headerx.copy()}
            else:
                return {"parse": 0, "url": id, "header": headerx.copy()}

        # 兜底：需要解析
        return {"parse": 1, "url": id, "header": headerx.copy()}

    # ==================== 搜索 ====================

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []
        if not page:
            page = 1

        data = {
            "command": "WEB_GET_INFO",
            "pageNumber": page,
            "RecordsPage": 20,
            "typeId": "0",
            "typeMid": "1",
            "languageType": "CN",
            "content": key,
            "type": "1"
        }
        res = requests.post(api_url + '/forward', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        menu0ListMap = json_dict["data"]["resultList"]
        for item in menu0ListMap:
            name = item['vod_name'].replace("yy8ycom", "")
            vid = item['id']
            pic = item['vod_pic']
            sid = item['vod_server_id']

            video = {
                "vod_id": str(vid) + '#' + str(sid),
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": ''
            }
            videos.append(video)

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick=False):
        return self.searchContentPage(key, quick, 1)

    # ==================== 本地代理 ====================

    def _build_proxy_url(self, ptype, url, referer):
        """构建本地代理 URL（vbox 基类 getProxyUrl）"""
        try:
            if hasattr(self, 'getProxyUrl'):
                base = self.getProxyUrl()
                if '?' not in base:
                    base += '?do=py'
                return (base + '&type=' + ptype +
                        '&url=' + quote(url, safe='') +
                        '&referer=' + quote(referer or '', safe=''))
        except:
            pass
        return url

    def _parse_params(self, params):
        """
        vbox 修复：兼容三种参数格式
        1. dict 字典
        2. JSON 字符串（iOS 端 WelfarePythonSpiderService 传入）
        3. URL query string
        """
        if isinstance(params, dict):
            return params
        if isinstance(params, str):
            # 尝试 JSON 解析
            try:
                d = json.loads(params)
                if isinstance(d, dict):
                    return d
            except:
                pass
            # 尝试 query string 解析
            result = {}
            if '?' in params:
                qs = params.split('?', 1)[1]
            else:
                qs = params
            for pair in qs.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    result[k] = unquote(v)
            return result
        return {}

    def localProxy(self, params):
        """
        本地代理：m3u8 代理、ts 代理、media 代理
        vbox 修复：兼容 iOS JSON 字符串参数
        """
        try:
            p = self._parse_params(params)
            ptype = p.get('type') or p.get('action') or p.get('do', '')
            url = p.get('url', '')
            referer = p.get('referer', '')

            if not url or not url.startswith('http'):
                return [404, 'text/plain', b'']

            if ptype == 'm3u8':
                return self._proxy_m3u8(url, referer)
            elif ptype == 'ts':
                return self._proxy_ts(url, referer)
            elif ptype == 'media' or ptype == 'mp4':
                return self._proxy_media(url, referer)

            return [404, 'text/plain', b'']
        except Exception as e:
            print(f"[xiongmao] localProxy error: {e}")
            return [500, 'text/plain', b'error']

    def _proxy_m3u8(self, url, referer):
        """代理 m3u8 文件"""
        try:
            h = headerx.copy()
            if referer:
                h['Referer'] = referer
            r = self.session.get(url, headers=h, timeout=15)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'']
            text = r.text
            # 处理相对路径
            base_url = url.rsplit('/', 1)[0] + '/'
            out_lines = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    # 处理 EXT-X-KEY 的 URI
                    if line.startswith('#EXT-X-KEY:') and 'URI=' in line:
                        line = re.sub(
                            r'URI="([^"]+)"',
                            lambda m: 'URI="' + urljoin(base_url, m.group(1)) + '"',
                            line
                        )
                    out_lines.append(line)
                elif not line.startswith('http'):
                    # 相对路径补全
                    out_lines.append(urljoin(base_url, line))
                else:
                    out_lines.append(line)
            content = '\n'.join(out_lines) + '\n'
            return [200, 'application/vnd.apple.mpegurl', content.encode('utf-8')]
        except Exception as e:
            print(f"[xiongmao] proxy_m3u8 error: {e}")
            return [500, 'text/plain', b'']

    def _proxy_ts(self, url, referer):
        """代理 ts 分片"""
        return self._proxy_media(url, referer)

    def _proxy_media(self, url, referer):
        """代理媒体文件（透传）"""
        try:
            h = headerx.copy()
            if referer:
                h['Referer'] = referer
            r = self.session.get(url, headers=h, timeout=30, stream=True)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'']
            content_type = r.headers.get('Content-Type', 'application/octet-stream')
            return [200, content_type, r.content]
        except Exception as e:
            print(f"[xiongmao] proxy_media error: {e}")
            return [500, 'text/plain', b'']
