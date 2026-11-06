p="sources/welfare-js/hhlz.py"
s=open(p,encoding="utf-8").read()

# 1) 常量：图片解密参数（asm images/decrypt_image_byte.dart 默认分支）
s=s.replace('RESP_IV = b"sciCuBC7orQtDHTO"',
 'RESP_IV = b"sciCuBC7orQtDHTO"\n'
 '# 图片解密（asm images/decrypt_image_byte.dart @0xa41bd4 / @0xa41be8，默认分支）\n'
 'IMG_KEY = b"saIZXc4yMvq0Iz56"\n'
 'IMG_IV = b"kbJYtBJUECT0oyjo"')

# 2) _px 改成 _img：抓取→AES 解密→data: URL
old_px = s[s.index("    @staticmethod\n    def _px(url):"):s.index("    def list_page(")]
new_px = '''    # ---------------- 图片：抓取 + AES 解密 + 内联 ----------------
    # 客户端（Flutter）内部没有 /proxy?do=py 路由，无法走本地代理；
    # 但漫画阅读器支持 `data:` 内联图 —— 所以这里直接把解密后的字节 base64 内联。
    @staticmethod
    def _dec_img(raw):
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return raw
        try:
            pt = AES.new(IMG_KEY, AES.MODE_CBC, IMG_IV).decrypt(raw[:len(raw) // 16 * 16])
            try:
                pt = unpad(pt, 16)
            except Exception:
                pass
            return pt
        except Exception:
            return raw

    def _inline(self, url, timeout=None):
        """返回 data: URL；失败则回落原地址。"""
        u = (url or "").strip()
        if not u.startswith("http"):
            return u
        key = ("img", u)
        if key in self._imgs:
            return self._imgs[key]
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
            with self._open(req, timeout or 15) as r:
                raw = r.read()
            raw = self._dec_img(raw)
            if raw[:4] == b"RIFF":
                mime = "image/webp"
            elif raw[:3] == b"\\xff\\xd8\\xff":
                mime = "image/jpeg"
            elif raw[:4] == b"\\x89PNG":
                mime = "image/png"
            else:
                mime = "image/jpeg"
            out = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode())
        except Exception:
            out = u
        self._imgs[key] = out
        return out

'''
s=s.replace(old_px,new_px,1)

# 3) __init__ 增加图片缓存
s=s.replace('        self.udid = str(uuid.uuid4())',
            '        self.udid = str(uuid.uuid4())\n        self._imgs = {}')

# 4) 列表/详情封面改用 _inline
s=s.replace('"vod_pic": self._px(it.get("cover") or it.get("vertical_cover") or ""),',
            '"vod_pic": self._inline(it.get("cover") or it.get("vertical_cover") or ""),')
s=s.replace('"vod_pic": self._px(info.get("horizontal_cover") or info.get("vertical_cover") or ""),',
            '"vod_pic": self._inline(info.get("horizontal_cover") or info.get("vertical_cover") or ""),')

# 5) 章节图并发解密内联
s=s.replace('''    def chapter(self, cid, chid):
        d = self.call("/comic/chapter", {"comic_id": str(cid), "chapter_id": str(chid)})
        imgs = []
        for im in (d.get("image_list") or []):
            if isinstance(im, dict) and im.get("img"):
                imgs.append(im["img"])
        return imgs''',
'''    def chapter(self, cid, chid):
        d = self.call("/comic/chapter", {"comic_id": str(cid), "chapter_id": str(chid)})
        urls = []
        for im in (d.get("image_list") or []):
            if isinstance(im, dict) and im.get("img"):
                urls.append(im["img"])
        if not urls:
            return []
        # 并发抓取 + 解密 + 内联（顺序保持）
        out = [None] * len(urls)
        def work(i, u):
            out[i] = self._inline(u, timeout=20)
        try:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=8) as ex:
                futs = [ex.submit(work, i, u) for i, u in enumerate(urls)]
                for f in futs:
                    f.result()
        except Exception:
            for i, u in enumerate(urls):
                if out[i] is None:
                    work(i, u)
        return [x for x in out if x]''')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("hhlz patched")
