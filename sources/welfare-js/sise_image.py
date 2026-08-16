# -*- coding: utf-8 -*-
"""
四色 - 图片版（仅暴露图片区分类）
用于福利漫画栏目，复用 sise.py 的所有解析逻辑，只过滤出图片分类。
封面图和详情图均返回原始 URL（不走本地代理），由客户端 PlatformImageLoader 通过 Referer 防盗链加载。
"""

import sys
import json
import base64

sys.path.append('.')

from sise import Spider as SiseBaseSpider, _DOMAIN_CANDIDATES, IMG_HOST


class Spider(SiseBaseSpider):
    """四色图片专用蜘蛛 —— 只返回图片区分类，适合漫画/套图栏目展示。"""

    def init(self, ext=''):
        """初始化，复用父类逻辑。"""
        super().init(ext)

    def _pic(self, path):
        """覆盖父类：返回原始图片 URL，不走本地代理。
        客户端 PlatformImageLoader 会通过 imageReferer 自动注入 Referer 防盗链。
        """
        if not path:
            return ''
        # base64 解密
        try:
            path += '=' * ((4 - len(path) % 4) % 4)
            decoded = base64.b64decode(path).decode('utf-8', errors='ignore')
        except Exception:
            decoded = path

        if decoded.startswith('http://') or decoded.startswith('https://'):
            return decoded
        if decoded.startswith('//'):
            return 'https:' + decoded
        if decoded.startswith('/'):
            return IMG_HOST + decoded
        return IMG_HOST + '/' + decoded

    def _image(self, path):
        """覆盖父类：返回原始图片 URL，不走代理。"""
        if not path:
            return ''
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('//'):
            return 'https:' + path
        if path.startswith('/'):
            return IMG_HOST + path
        return IMG_HOST + '/' + path

    def _proxy(self, kind, url):
        """覆盖父类：直接返回原始 URL（图片平台不需要代理）。"""
        return url

    def homeContent(self, filter=False):
        """首页：只返回图片区的分类和推荐内容。"""
        result_json = super().homeContent(filter=filter)

        try:
            data = json.loads(result_json)
        except (json.JSONDecodeError, TypeError):
            return result_json

        # 只保留图片分类
        classes = data.get('class', [])
        image_classes = [c for c in classes if c.get('type_id') == 'image']
        data['class'] = image_classes

        # filters 只保留 image 分类的
        filters = data.get('filters', {})
        image_filters = {k: v for k, v in filters.items() if k == 'image'}
        data['filters'] = image_filters

        return json.dumps(data, ensure_ascii=False)

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        """分类内容：直接复用父类（图片区的子分类路径已能正确解析）。"""
        return super().categoryContent(tid, pg, filter, extend)

    def detailContent(self, ids):
        """详情内容：复用父类，已返回 pics:// 格式图片集（原始 URL）。"""
        return super().detailContent(ids)

    def playerContent(self, flag, id, vipFlags=None):
        """播放内容：如果是 pics:// 协议直接返回。"""
        if id.startswith('pics://'):
            return {'parse': 0, 'url': id}
        return {'parse': 0, 'url': ''}


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('=== 首页 ===')
    result = sp.homeContent(True)
    data = json.loads(result)
    classes = data.get('class', [])
    print(f'分类数: {len(classes)}')
    for c in classes:
        print(f'  - {c.get("type_name")} ({c.get("type_id")})')
