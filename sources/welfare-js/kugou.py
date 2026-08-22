# -*- coding: utf-8 -*-
import re
import sys
import json
import time
import urllib.parse

from base.spider import Spider


class Spider(Spider):

    def __init__(self):
        self.name = "酷狗直播"
        self.host = "https://fanxing.kugou.com"
        self.api_host = "https://fxservice4.kugou.com"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://fanxing.kugou.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        # 缓存机制
        self.cache = {}
        self.cache_timeout = 300
        # 新增：直播间基础信息缓存 key:roomId
        self.room_info_cache = {}

    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def homeContent(self, filter):
        """首页分类"""
        result = {}
        classes = [
            {"type_id": "0", "type_name": "推荐"},
            {"type_id": "game", "type_name": "一起玩"},
            {"type_id": "music", "type_name": "音乐"},
            {"type_id": "dance", "type_name": "舞蹈"},
            {"type_id": "face", "type_name": "颜值"},
            {"type_id": "acg", "type_name": "酷次元"},
            {"type_id": "chinese", "type_name": "新秀"}
        ]
        result['class'] = classes
        return result

    def homeVideoContent(self):
        """首页推荐"""
        return self.categoryContent('0', '1', None, None)

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        videos = []
        page = int(pg or 1)
        limit = 50
        
        try:
            if tid == "0":
                videos = self._get_recommend_list(page, limit)
            elif tid == "game":
                videos = self._get_game_list(page, limit)
            elif tid == "music":
                videos = self._get_music_list(page, limit)
            elif tid == "dance":
                videos = self._get_dance_list(page, limit)
            elif tid == "face":
                videos = self._get_face_list(page, limit)
            elif tid == "acg":
                videos = self._get_acg_list(page, limit)
            elif tid == "chinese":
                videos = self._get_chinese_list(page, limit)
        except Exception as e:
            print(f"获取分类内容失败: {e}")
        
        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': limit,
            'total': 999999
        }

    def _save_room_cache(self, room_id, nickName, imgPath, cityName="", tagText="", viewerNum=0):
        """统一存入直播间缓存"""
        self.room_info_cache[str(room_id)] = {
            "roomId": str(room_id),
            "nickName": nickName,
            "imgPath": imgPath,
            "cityName": cityName,
            "tagText": tagText,
            "viewerNum": viewerNum
        }

    def _get_recommend_list(self, page, limit):
        """获取推荐列表"""
        videos = []
        api_url = f"{self.api_host}/mfanxing-home/h5/cdn/room/index/list"
        params = {
            "pid": "0",
            "kugouId": "0",
            "doubleLiveFirst": "1",
            "sysVersion": "0",
            "platform": "7",
            "device": "d5e6f3453f454395fb41be10305af348",
            "channel": "0",
            "version": "99999",
            "longitude": "0",
            "latitude": "0",
            "appid": "1010",
            "liveTypeFilter": "0",
            "isNew": "0",
            "entranceType": "0",
            "uiMode": "0",
            "page": page,
            "areaName": ""
        }
        
        resp = self.fetch(api_url, params=params, headers=self.header)
        data = resp.json()
        
        if data.get('code') == 0:
            room_list = data.get('data', {}).get('list', [])
            for item in room_list:
                video = self._normalize_room_item(item)
                if video:
                    videos.append(video)
        return videos

    def _get_game_list(self, page, limit):
        """获取一起玩列表"""
        videos = []
        api_url = f"{self.api_host}/fxservice/activity/entrance/game/square/rooms"
        params = {
            "gameCode": "ALL_GAME",
            "appid": "1010",
            "version": "99999",
            "platform": "7",
            "device": "d5e6f3453f454395fb41be10305af348",
            "channel": "0",
            "pageSize": limit,
            "pageNum": page,
            "userKugouId": "0",
            "pid": "0"
        }
        
        resp = self.fetch(api_url, params=params, headers=self.header)
        data = resp.json()
        
        if data.get('code') == 0:
            room_list = data.get('data', {}).get('roomList', [])
            for item in room_list:
                video = self._normalize_game_item(item)
                if video:
                    videos.append(video)
        return videos

    def _get_music_list(self, page, limit):
        """获取音乐分类列表"""
        videos = []
        api_url = "https://fxservice3.kugou.com/mfanxing-home/h5/song/recommend/star/list"
        params = {
            "page": page,
            "platform": "7",
            "version": "99999",
            "device": "d5e6f3453f454395fb41be10305af348",
            "kugouId": "0",
            "pid": "0",
            "type": "8"
        }
        
        resp = self.fetch(api_url, params=params, headers=self.header)
        data = resp.json()
        
        if data.get('code') == 0:
            song_list = data.get('data', {}).get('list', [])
            for song_item in song_list:
                star_list = song_item.get('starList', [])
                song_name = song_item.get('songName', '')
                for star in star_list:
                    star['_song_name'] = song_name
                    video = self._normalize_music_item(star)
                    if video:
                        videos.append(video)
        return videos

    def _get_dance_list(self, page, limit):
        """获取舞蹈分类列表 (cid=7024)"""
        return self._get_list_v4(page, limit, "7024")

    def _get_face_list(self, page, limit):
        """获取颜值分类列表 (cid=1009)"""
        return self._get_list_v4(page, limit, "1009")

    def _get_acg_list(self, page, limit):
        """获取酷次元分类列表 (cid=3007)"""
        return self._get_list_v4(page, limit, "3007")

    def _get_chinese_list(self, page, limit):
        """获取新秀分类列表 (cid=1001)"""
        return self._get_list_v4(page, limit, "1001")

    def _get_list_v4(self, page, limit, cid):
        """通用list_v4接口"""
        videos = []
        api_url = "https://fx2.service.kugou.com/mfanxing-home/h5/cdn/room/index/list_v4"
        params = {
            "pid": "0",
            "kugouId": "0",
            "doubleLiveFirst": "1",
            "sysVersion": "0",
            "platform": "7",
            "device": "d5e6f3453f454395fb41be10305af348",
            "channel": "0",
            "version": "99999",
            "longitude": "0",
            "latitude": "0",
            "appid": "1010",
            "liveTypeFilter": "0",
            "isNew": "0",
            "entranceType": "0",
            "uiMode": "0",
            "page": page,
            "cid": cid
        }
        
        resp = self.fetch(api_url, params=params, headers=self.header)
        data = resp.json()
        
        if data.get('code') == 0:
            room_list = data.get('data', {}).get('list', [])
            for item in room_list:
                room_data = item.get('data', {})
                if room_data:
                    video = self._normalize_v4_item(room_data, cid)
                    if video:
                        videos.append(video)
        return videos

    def _normalize_room_item(self, raw):
        """标准化推荐房间数据"""
        if not isinstance(raw, dict):
            return None

        room_id = str(raw.get('roomId', ''))
        if not room_id:
            return None

        nickname = raw.get('nickName', '')
        if not nickname:
            nickname = f"主播{room_id}"

        pic = raw.get('imgPath', '')
        if pic and not pic.startswith('http'):
            pic = 'http:' + pic

        tag_text = ''
        city_name = ''
        tags = raw.get('tags', [])
        for tag in tags:
            if tag.get('tagId') == 26:
                city_name = tag.get('tagName', '')
            else:
                if tag.get('tagName'):
                    if tag_text:
                        tag_text += "," + tag.get('tagName')
                    else:
                        tag_text = tag.get('tagName')

        online = raw.get('viewerNum', 0)

        # 存入缓存
        self._save_room_cache(room_id, nickname, pic, city_name, tag_text, online)

        if online:
            online = f"🔥{online}"

        category_name = ''
        categories = raw.get('category', [])
        if categories:
            category_name = categories[0].get('name', '')

        remark = ' '.join(filter(None, [category_name, tag_text, online]))

        return {
            "vod_id": f"{room_id}@@{room_id}",
            "vod_name": nickname,
            "vod_pic": pic or '',
            "vod_remarks": remark,
            "vod_content": nickname
        }

    def _normalize_game_item(self, raw):
        """标准化一起玩房间数据"""
        if not isinstance(raw, dict):
            return None

        room_id = str(raw.get('roomId', ''))
        if not room_id:
            return None

        star_name = raw.get('starName', '')
        if not star_name:
            star_name = f"主播{room_id}"

        pic = raw.get('starCover', '')
        if pic and not pic.startswith('http'):
            pic = 'http://p3.fx.kgimg.com' + pic

        game_name = raw.get('gameName', '')
        status_text = raw.get('statusText', '')
        bottom_data = raw.get('bottomData', {})
        main_title = bottom_data.get('mainTitle', '')
        
        remark_parts = []
        if game_name:
            remark_parts.append(f"🎮{game_name}")
        if status_text:
            remark_parts.append(status_text)
        if main_title:
            remark_parts.append(main_title)
        
        remark = ' '.join(remark_parts) if remark_parts else '一起玩'

        # 游戏分类缺少城市标签，简单缓存
        self._save_room_cache(room_id, star_name, pic, "", game_name, 0)

        return {
            "vod_id": f"{room_id}@@{room_id}",
            "vod_name": star_name,
            "vod_pic": pic or '',
            "vod_remarks": remark,
            "vod_content": f"{game_name} - {main_title}" if main_title else game_name
        }

    def _normalize_music_item(self, raw):
        """标准化音乐分类房间数据"""
        if not isinstance(raw, dict):
            return None

        room_id = str(raw.get('roomId', ''))
        if not room_id:
            return None

        nickname = raw.get('nickName', '')
        if not nickname:
            nickname = f"主播{room_id}"

        pic = raw.get('imgPath', '')
        if pic and not pic.startswith('http'):
            pic = 'http:' + pic

        song_name = raw.get('_song_name', '')
        city_name = raw.get('cityName', '')
        
        tag_text = ''
        tags = raw.get('tags', [])
        if tags:
            tag_text = tags[0].get('tagName', '') if tags[0].get('tagName') else ''
        
        viewer_num = raw.get('getViewerNum', 0)
        online = f"🔥{viewer_num}" if viewer_num else ''
        
        remark_parts = []
        if song_name:
            remark_parts.append(f"🎵{song_name}")
        if city_name:
            remark_parts.append(city_name)
        if tag_text:
            remark_parts.append(tag_text)
        if online:
            remark_parts.append(online)
        
        remark = ' '.join(remark_parts) if remark_parts else '音乐直播'

        self._save_room_cache(room_id, nickname, pic, city_name, tag_text, viewer_num)

        return {
            "vod_id": f"{room_id}@@{room_id}",
            "vod_name": nickname,
            "vod_pic": pic or '',
            "vod_remarks": remark,
            "vod_content": f"演唱《{song_name}》" if song_name else nickname
        }

    def _normalize_v4_item(self, raw, cid):
        """标准化list_v4分类房间数据 (舞蹈/颜值/酷次元/新秀)"""
        if not isinstance(raw, dict):
            return None

        room_id = str(raw.get('roomId', ''))
        if not room_id:
            return None

        nickname = raw.get('nickName', '')
        if not nickname:
            nickname = f"主播{room_id}"

        pic = raw.get('imgPath', '')
        if pic and not pic.startswith('http'):
            pic = 'http:' + pic

        city_name = raw.get('cityName', '')
        
        tag_text = ''
        tags = raw.get('tags', [])
        if tags:
            tag_text = tags[0].get('tagName', '') if tags[0].get('tagName') else ''
        
        viewer_num = raw.get('getViewerNum', 0)
        online = f"🔥{viewer_num}" if viewer_num else ''
        
        # 标签V2 - 可能包含"主播热舞中"等信息
        label_v2 = raw.get('labelV2', {})
        label_title = label_v2.get('title', '') if isinstance(label_v2, dict) else ''
        
        # 分类名称映射
        cid_names = {
            "7024": "舞蹈",
            "1009": "颜值",
            "3007": "酷次元",
            "1001": "新秀"
        }
        cate_name = cid_names.get(str(cid), "")
        
        remark_parts = []
        if cate_name:
            remark_parts.append(cate_name)
        if label_title:
            remark_parts.append(label_title)
        if city_name:
            remark_parts.append(city_name)
        if tag_text:
            remark_parts.append(tag_text)
        if online:
            remark_parts.append(online)
        
        remark = ' '.join(remark_parts) if remark_parts else f'{cate_name}直播'

        self._save_room_cache(room_id, nickname, pic, city_name, tag_text, viewer_num)

        return {
            "vod_id": f"{room_id}@@{room_id}",
            "vod_name": nickname,
            "vod_pic": pic or '',
            "vod_remarks": remark,
            "vod_content": f"{nickname} - {cate_name}直播"
        }

    def searchContent(self, key, quick, pg="1"):
        """搜索直播"""
        videos = []
        page = int(pg or 1)
        
        try:
            search_url = "https://fxpc.kugou.com/fx/search/live"
            params = {
                "keyword": key,
                "page": page,
                "pagesize": 30,
                "platform": "pc",
                "version": "1.0"
            }
            
            resp = self.fetch(search_url, params=params, headers=self.header)
            data = resp.json()
            
            if data.get('errcode') == 0:
                room_list = data.get('data', {}).get('list', [])
                for item in room_list:
                    video = self._normalize_room_item(item)
                    if video:
                        videos.append(video)
                        
        except Exception as e:
            print(f"搜索失败: {e}")
        
        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        }

    def detailContent(self, ids):
        """获取直播详情和播放地址"""
        if not ids:
            return {'list': []}
        
        raw_id = ids[0]
        parts = raw_id.split('@@')
        room_id = parts[1] if len(parts) == 2 else parts[0]
        
        result = {'list': []}
        
        try:
            # ============核心修改：优先读取缓存，不重复请求==========
            if room_id in self.room_info_cache:
                room_info = self.room_info_cache[room_id]
            else:
                # 缓存不存在，才降级请求
                room_info = self._get_room_detail(room_id)

            nickname = room_info.get('nickName', f'主播{room_id}')
            city_name = room_info.get('cityName', '')
            tag_text = room_info.get('tagText', '')
            online = room_info.get('viewerNum', 0)
            online_text = f"🔥{online}" if online else ''
            pic = room_info.get('imgPath', '')
            if pic and not pic.startswith('http'):
                pic = 'http:' + pic
            
            # 获取播放地址
            play_url = self._get_play_url(room_id)
            
            if play_url:
                # 构建详情内容
                content_parts = []
                if nickname:
                    content_parts.append(f"主播：{nickname}")
                if room_id:
                    content_parts.append(f"房间号：{room_id}")
                if city_name:
                    content_parts.append(f"来自：{city_name}")
                if tag_text:
                    content_parts.append(f"标签：{tag_text}")
                if online_text:
                    content_parts.append(f"在线：{online_text}")
                
                vod_content = '，'.join(content_parts) if content_parts else f'酷狗直播 {room_id}'
                
                video = {
                    "vod_id": f"{room_id}@@{room_id}",
                    "vod_name": f"{nickname}的直播间" if nickname else f"酷狗直播间 {room_id}",
                    "vod_pic": pic,
                    "vod_actor": nickname,
                    "vod_content": vod_content,
                    "vod_play_from": "酷狗直播",
                    "vod_play_url": f"直播${play_url}"
                }
                result['list'] = [video]
            else:
                video = {
                    "vod_id": f"{room_id}@@{room_id}",
                    "vod_name": f"{nickname}的直播间" if nickname else f"酷狗直播间 {room_id}",
                    "vod_pic": pic,
                    "vod_actor": nickname,
                    "vod_content": "该房间当前未直播或无法获取播放地址"
                }
                result['list'] = [video]
                
        except Exception as e:
            print(f"获取详情失败: {e}")
            # 返回基本信息
            video = {
                "vod_id": f"{room_id}@@{room_id}",
                "vod_name": f"酷狗直播间 {room_id}",
                "vod_pic": '',
                "vod_actor": f"主播：{room_id}",
                "vod_content": f"酷狗直播房间 {room_id}"
            }
            result['list'] = [video]
        
        return result

    def _get_room_detail(self, room_id):
        """获取房间详细信息（仅缓存缺失时调用）"""
        room_info = {
            'roomId': room_id,
            'nickName': f'主播{room_id}',
            'cityName': '',
            'tagText': '',
            'viewerNum': 0,
            'imgPath': ''
        }
        
        try:
            # 尝试房间页面抓取
            url = f"{self.host}/{room_id}"
            resp = self.fetch(url, headers=self.header)
            html = resp.text
            
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    room = data.get('room', {})
                    if room:
                        room_info['nickName'] = room.get('nickname', room_info['nickName'])
                        room_info['cityName'] = room.get('cityName', '')
                        tags = room.get('tags', [])
                        for tag in tags:
                            if tag.get('tagId') == 26:
                                room_info['cityName'] = tag.get('tagName', '')
                                break
                            if tag.get('tagName') and tag.get('tagId') != 26:
                                if room_info['tagText']:
                                    room_info['tagText'] += f", {tag.get('tagName')}"
                                else:
                                    room_info['tagText'] = tag.get('tagName')
                        room_info['viewerNum'] = room.get('viewerNum', 0)
                        room_info['imgPath'] = room.get('cover', '')
                        return room_info
                except:
                    pass
            
            match = re.search(r'window\.liveInitData\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    room_info['nickName'] = data.get('nickname', room_info['nickName'])
                    room_info['cityName'] = data.get('cityName', '')
                    room_info['viewerNum'] = data.get('viewerNum', 0)
                    room_info['imgPath'] = data.get('cover', '')
                    return room_info
                except:
                    pass
                    
        except Exception as e:
            print(f"获取房间详情失败: {e}")
        
        return room_info

    def _get_play_url(self, room_id):
        """获取播放地址"""
        try:
            api_url = "https://fx1.service.kugou.com/video/mo/live/pull/h5/v3/streamaddr"
            params = {
                "roomId": room_id,
                "platform": "12",
                "version": "1000",
                "streamType": "3-6",
                "liveType": "1",
                "ch": "fx",
                "ua": "fx-mobile-h5",
                "kugouId": "0",
                "layout": "1",
                "appid": "2815",
                "token": ""
            }
            
            resp = self.fetch(api_url, params=params, headers=self.header)
            data = resp.json()
            
            if data.get('code') != 0:
                return None
            
            if data.get('data', {}).get('status') == 0:
                return None
            
            live_data = None
            if data.get('data', {}).get('vertical'):
                live_data = data['data']['vertical']
            elif data.get('data', {}).get('horizontal'):
                live_data = data['data']['horizontal']
            
            if not live_data or not isinstance(live_data, list) or len(live_data) == 0:
                return None
            
            source = live_data[0]
            
            if source.get('hls') and isinstance(source['hls'], list) and len(source['hls']) > 0:
                return source['hls'][0]
            elif source.get('httpshls') and isinstance(source['httpshls'], list) and len(source['httpshls']) > 0:
                return source['httpshls'][0]
            elif source.get('flv') and isinstance(source['flv'], list) and len(source['flv']) > 0:
                return source['flv'][0]
            
            return None
            
        except Exception as e:
            print(f"获取播放地址失败: {e}")
            return None

    def playerContent(self, flag, id, vipFlags):
        """播放器"""
        if not id:
            return {"parse": 0, "playUrl": "", "url": ""}
        
        headers = {
            "User-Agent": self.header['User-Agent'],
            "Referer": "https://fx.kugou.com/"
        }
        
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": json.dumps(headers)
        }

    def isVideoFormat(self, url):
        video_formats = ['.m3u8', '.mp4', '.flv', '.ts']
        return any(url.lower().endswith(fmt) for fmt in video_formats)

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None
