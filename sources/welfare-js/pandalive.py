# -*- coding: utf-8 -*-
"""
PandaLive 熊猫直播 — vbox 适配版
修复内容：
1. 继承 base.spider.Spider，使用 self.fetch() 走代理/自定义域名
2. vod_play_url 分隔符改为 $$$ (vbox 标准)
3. playerContent 正确解析多线路
4. 修复 lines 变量作用域 bug
5. header 返回 dict 格式
6. 第三方代理站 5721004.xyz 提供数据
"""
import sys
import json
import re
sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):

    def getName(self):
        return "PandaLive"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        self.host = "https://5721004.xyz"
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.base_headers = {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/plain, */*',
        }
        print("[PandaLive] 初始化成功")

    def homeContent(self, filter=False):
        classes = [{'type_id': 'pandalive', 'type_name': 'PandaTV'}]

        filters = {}
        if filter:
            filters = {
                "pandalive": [
                    {
                        "key": "type", "name": "类型",
                        "value": [
                            {"n": "全部", "v": "all"},
                            {"n": "19+", "v": "adult"},
                            {"n": "密码房", "v": "pw"},
                            {"n": "粉丝房", "v": "fan"}
                        ]
                    },
                    {
                        "key": "sort", "name": "排序",
                        "value": [
                            {"n": "观众量 ↓", "v": "user-desc"},
                            {"n": "热度 ↓", "v": "totalScoreCnt-desc"},
                            {"n": "关注量 ↓", "v": "bookmarkCnt-desc"}
                        ]
                    }
                ]
            }

        all_data = self._fetch_json_data()
        return {
            'class': classes,
            'list': all_data[:30],
            'filters': filters
        }

    def homeVideoContent(self):
        try:
            return {'list': self._fetch_json_data()[:20]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        try:
            all_list = self._fetch_json_data()
            filtered = all_list

            # 解析 extend（可能是 JSON 字符串或 dict）
            if isinstance(extend, str):
                try:
                    extend = json.loads(extend) if extend.strip().startswith('{') else {}
                except Exception:
                    extend = {}
            if not isinstance(extend, dict):
                extend = {}

            # 筛选
            f_type = extend.get('type', 'all')
            if f_type == 'adult':
                filtered = [v for v in filtered if v.get('_isAdult')]
            elif f_type == 'pw':
                filtered = [v for v in filtered if v.get('_isPw')]
            elif f_type == 'fan':
                filtered = [v for v in filtered if v.get('_type') == 'fan']

            # 排序
            sort_type = extend.get('sort', 'user-desc')
            if sort_type == 'user-desc':
                filtered.sort(key=lambda x: x.get('_user_count', 0), reverse=True)
            elif sort_type == 'totalScoreCnt-desc':
                filtered.sort(key=lambda x: x.get('_score', 0), reverse=True)
            elif sort_type == 'bookmarkCnt-desc':
                filtered.sort(key=lambda x: x.get('_bookmark', 0), reverse=True)

            # 分页
            pg = int(pg)
            limit = 30
            start = (pg - 1) * limit
            end = start + limit
            page_list = filtered[start:end] if start < len(filtered) else []

            return {
                'list': page_list,
                'page': pg,
                'pagecount': max((len(filtered) + limit - 1) // limit, 1),
                'limit': limit,
                'total': len(filtered)
            }
        except Exception as e:
            print(f"[PandaLive] categoryContent 错误: {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1}

    def _fetch_json_data(self):
        """从第三方代理站获取主播列表 JSON"""
        try:
            url = f"{self.host}/player/list.json"
            res = self.fetch(url, headers=self.base_headers)
            data = res.json()
            raw_list = data.get('list', [])

            processed = []
            for item in raw_list:
                user_id = item.get('userId', '')
                nick = item.get('userNick', '未知主播')
                title = item.get('title', '无标题')
                is_adult = item.get('isAdult', False)
                is_pw = item.get('isPw', False)
                v_type = item.get('type', '')

                processed.append({
                    'vod_id': f"live_{user_id}",
                    'vod_name': f"{nick}",
                    'vod_pic': item.get('thumbUrl', ''),
                    'vod_remarks': f"观众 {item.get('user', 0)}{'  19+' if is_adult else ''}",
                    'vod_content': title,
                    'vod_actor': user_id,
                    '_isAdult': is_adult,
                    '_isPw': is_pw,
                    '_type': v_type,
                    '_user_count': item.get('user', 0),
                    '_score': item.get('totalScoreCnt', 0),
                    '_bookmark': item.get('bookmarkCnt', 0)
                })
            return processed
        except Exception as e:
            print(f"[PandaLive] JSON 抓取失败: {e}")
            return []

    def _fetch_m3u_lines(self):
        """获取 M3U 播放列表，返回行列表"""
        try:
            url = f"{self.host}/player/list.m3u"
            res = self.fetch(url, headers=self.base_headers)
            return res.text.split('\n')
        except Exception as e:
            print(f"[PandaLive] M3U 抓取失败: {e}")
            return []

    def detailContent(self, ids):
        try:
            first_id = ids[0] if isinstance(ids, list) else ids
            user_id = first_id.replace("live_", "")
            stream_url = ""

            lines = self._fetch_m3u_lines()
            if lines:
                # 精确匹配: #EXTINF:0,主播ID,主播名称
                for i, line in enumerate(lines):
                    if f",{user_id}," in line and i + 1 < len(lines):
                        stream_url = lines[i + 1].strip()
                        break

                # 模糊匹配
                if not stream_url:
                    for i, line in enumerate(lines):
                        if user_id in line and i + 1 < len(lines):
                            stream_url = lines[i + 1].strip()
                            break

            # 代理服务器列表
            proxies = [
                "https://hubu.515355.xyz/proxy/?",
                "https://flank.515355.xyz/proxy/",
                "https://uae2.515355.xyz/proxy/",
                "https://pol.515355.xyz/proxy/",
                "https://f00.515355.xyz/proxy/",
                "https://ce2.515355.xyz/proxy/?",
            ]

            # 构建多线路播放 URL（vbox 标准 $$$ 分隔符）
            play_lines = []
            line_names = []

            if stream_url:
                play_lines.append(f"直播${stream_url}")
                line_names.append("直连")

            for i, p in enumerate(proxies, 1):
                if stream_url:
                    proxy_url = p + stream_url
                    play_lines.append(f"直播${proxy_url}")
                    line_names.append(f"代理{i}")

            if not play_lines:
                play_lines.append(f"直播$")
                line_names.append("无流")

            vod = {
                'vod_id': first_id,
                'vod_name': f"PandaTV - {user_id}",
                'vod_pic': '',
                'vod_content': f'主播: {user_id}',
                'vod_play_from': '$$$'.join(line_names),
                'vod_play_url': '$$$'.join(play_lines)
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"[PandaLive] detailContent 错误: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            all_v = self._fetch_json_data()
            key_l = key.lower()
            res = [v for v in all_v if key_l in v['vod_name'].lower() or key_l in v.get('vod_actor', '').lower()]
            return {'list': res[:50], 'page': int(pg)}
        except Exception:
            return {'list': [], 'page': int(pg)}

    def playerContent(self, flag, id, vipFlags=None):
        """
        播放解析：parse=0 表示直接返回 m3u8 流地址
        id 是 vod_play_url 中 $ 后面的 URL 部分
        """
        try:
            # id 已经是完整的流地址（直连或代理 URL）
            if id and (id.startswith('http://') or id.startswith('https://')):
                return {
                    'parse': 0,
                    'url': id,
                    'header': {
                        'User-Agent': self.ua,
                        'Referer': 'https://www.pandalive.co.kr/',
                        'Origin': 'https://www.pandalive.co.kr'
                    }
                }

            # 如果 id 为空或无效，尝试从 flag 重新获取
            user_id = flag.replace("live_", "") if flag else ""
            if user_id:
                lines = self._fetch_m3u_lines()
                if lines:
                    for i, line in enumerate(lines):
                        if f",{user_id}," in line and i + 1 < len(lines):
                            stream_url = lines[i + 1].strip()
                            if stream_url:
                                return {
                                    'parse': 0,
                                    'url': stream_url,
                                    'header': {
                                        'User-Agent': self.ua,
                                        'Referer': 'https://www.pandalive.co.kr/',
                                        'Origin': 'https://www.pandalive.co.kr'
                                    }
                                }
                            break

            return {
                'parse': 1,
                'url': 'https://www.pandalive.co.kr/',
                'header': {
                    'User-Agent': self.ua
                }
            }
        except Exception as e:
            print(f"[PandaLive] playerContent 错误: {e}")
            return {
                'parse': 1,
                'url': 'https://www.pandalive.co.kr/',
                'header': {'User-Agent': self.ua}
            }