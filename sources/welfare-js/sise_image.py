# -*- coding: utf-8 -*-
"""
四色 - 图片版（仅暴露图片区分类）
用于福利漫画栏目，复用 sise.py 的所有解析逻辑，只过滤出图片分类。
"""

import sys
import json

sys.path.append('..')

from sise import Spider as SiseBaseSpider, _DOMAIN_CANDIDATES, _discover_domain


class Spider(SiseBaseSpider):
    """四色图片专用蜘蛛 —— 只返回图片区分类，适合漫画/套图栏目展示。"""

    def init(self, ext=''):
        """初始化，复用父类逻辑，但只保留图片相关分类。"""
        # 调用父类初始化（域名探测等）
        super().init(ext)

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
        """详情内容：复用父类，已返回 pics:// 格式图片集。"""
        return super().detailContent(ids)

    def playerContent(self, flag, id, vipFlags=None):
        """播放内容：图片平台不需要播放，返回空。"""
        return json.dumps({'parse': 0, 'url': ''}, ensure_ascii=False)


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('=== 首页 ===')
    print(sp.homeContent(True)[:500])
    print()
    print('=== 图片分类 ===')
    print(sp.categoryContent('image', 1, True, None)[:500])
