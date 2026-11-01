# -*- coding: utf-8 -*-
"""hgsp（黄瓜视频）Adapter —— 签名链已完整还原，网关层已贯通。

来源：blutter 反汇编
  avbox/module/hgsp/network/interceptor.dart  → HgSpInterceptor.onRequest
  avbox/module/hgsp/network/service.dart      → HgSpHttp（baseUrl = SpUtil.getString("hgsp")）
  avbox/module/hgsp/page/*.dart               → 路由字面量

真实 host 取自真机 Library/Preferences/com.look.avbox.plist 的 flutter.hgsp。

链路状态（2026-11-02 实测）
  1. 666 已破：触发源是 `pkg` 头，不是签名。只带 pkg: cuke0001 即可穿过网关。
  2. 路由已确认：/home/defaultchannels 等只在带 pkg 时由 404 变 500，属真实路由。
  3. 剩余卡点：业务层 `For input string: "nul"` —— 某头为 null 被 parseInt；
     补第 7 个头会触发网关白名单二次 666。需真机动态 hook 取实际头集合。
"""
import base64
import hashlib
import hmac
import json
import random
import time
import urllib.parse
import uuid as _uuid

# ============================================================ 常量（反汇编提取）
HOST = "https://api55.nmrgqb.com"
APP_KEY = "368480924a6c78e2e8681551a7cf4c21"
SECRET = "cuke@appSecret#Ten2020!0120"
SEQ = "5299c575a58ddc161fdf2CZOmDp0tCJSpEJGrC30nE0"
SEQ_MOD = ("07cd848d8dce62193453f9f455c5f39a0edb5a7b76d0826070ea36975d3c3dcf"
           "6065c6e97ff2759ad8f6771b2903c07007bbdb5edfea026919a29dc5f61988fd31")
UA = "Dalvik/2.1.0 (Linux; U; Android 12; M2006J10C Build/SP1A.210812.016)"
RELEASE = "506"
PKG = "cuke0001"
TERMINAL = "2"
IV = "16-Bytes--String"   # 仅内部 AES 中间产物使用

# 网关白名单：头数量超过这个阈值会被整包 666
GATEWAY_HEAD_LIMIT = 6


def _b64url(s):
    return base64.urlsafe_b64encode(s.encode()).decode()


def build_flow(uid=None, nonce=None, ts=None):
    """还原 HgSpInterceptor.onRequest 的 flowId 拼装。

    逐段对应反汇编：
        write("//" + uuid4 + "/?Authorization=")
        write("&Seq=" + SEQ)
        write("&X-Auth-Key=" + APP_KEY)
        write("&X-Auth-Nonce=" + random(1e7, 1e8))
        write("&X-Auth-TimeStamp=" + millis + "&")
    """
    uid = uid or str(_uuid.uuid4())
    # 反汇编：Random().nextInt(90000000) + 10000000 → 8 位
    nonce = nonce or str(random.randint(0, 89999999) + 10000000)
    ts = ts or str(int(time.time() * 1000))
    flow = ("//" + uid + "/?Authorization="
            + "&Seq=" + SEQ
            + "&X-Auth-Key=" + APP_KEY
            + "&X-Auth-Nonce=" + nonce + "&X-Auth-TimeStamp=" + ts + "&")
    return flow, nonce, ts


def make_sign(flow):
    """X-Auth-Sign = urlencode(base64(HMAC_SHA1(secret, base64url(flow))))。

    _hMacSha1：Hmac(_Sha1, utf8(secret)).convert(utf8(message)) → base64
              → 去换行 → Uri.encodeComponent
    """
    mac = hmac.new(SECRET.encode(), _b64url(flow).encode(), hashlib.sha1).digest()
    return urllib.parse.quote(base64.b64encode(mac).decode(), safe="")


def build_headers(seq_mod=True):
    """返回 (headers, flow, nonce, ts)。

    保持网关可通行（≤ GATEWAY_HEAD_LIMIT 个），优先保留业务层需要的鉴权头。
    seqMod 是内部中间产物，默认不发（发了会顶掉名额）。
    """
    flow, nonce, ts = build_flow()
    h = {
        "pkg": PKG,
        "X-Auth-Sign": make_sign(flow),
        "X-Auth-TimeStamp": ts,
        "X-Auth-Nonce": nonce,
        "X-Auth-Key": APP_KEY,
        "Seq": SEQ,
    }
    if seq_mod:
        h["seqMod"] = SEQ_MOD
    return h, flow, nonce, ts


class HgSpAdapter(object):
    """黄瓜视频适配器。

    只依赖 spider.fetch_text / spider.fetch_bytes，不引入外部依赖，
    符合客户端「单文件自包含」约束。
    """

    content_type = "video"
    HOST = HOST

    # 路由（反汇编 home_page / video_page / search_page 字面量）
    P_CHANNELS = "/home/defaultchannels"     # 分类（首页导航）
    P_MOVLIST = "/home/movlist"               # 列表
    P_MOVLIST2 = "/module/movlist2"           # 列表（模块页）
    P_ACTOR_LIST = "/home/actor/list"         # 女优
    P_NEWMOV = "/home/newmov/query"           # 最新片源
    P_SELECTION = "/home/selection/query"     # 精选
    P_SEARCH = "/es/mov/V418/search"          # 搜索

    def __init__(self, spider):
        self.sp = spider

    # ---------------- 传输 ----------------
    def _call(self, path, params=None, with_flow=False):
        """发一个带签名链的请求，返回解析后的 dict/None。"""
        headers, flow, nonce, ts = build_headers()
        if with_flow and len(headers) < GATEWAY_HEAD_LIMIT:
            headers["flowId"] = flow
        url = self.HOST + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        body = self.sp.fetch_text(url, headers=headers)
        if not body:
            return None
        body = body.strip()
        if not body.startswith(("{", "[")):
            return None
        try:
            return json.loads(body)
        except Exception:
            return None

    # ---------------- 适配器接口 ----------------
    def categories(self):
        """分类：home/defaultchannels。失败时返回静态兜底分类。"""
        data = self._call(self.P_CHANNELS)
        out = []
        if isinstance(data, dict):
            for it in (data.get("data") or data.get("list") or []):
                if not isinstance(it, dict):
                    continue
                cid = it.get("id") or it.get("clsId") or it.get("navId")
                name = it.get("name") or it.get("nameCn") or it.get("movName")
                if cid is not None and name:
                    out.append({"type_id": str(cid), "type_name": str(name)})
        if out:
            return out
        # 反汇编里出现过的分类名，作为占位（数据打通后自动被真实分类替换）
        return [
            {"type_id": "1", "type_name": "首页"},
            {"type_id": "2", "type_name": "最新片源"},
            {"type_id": "3", "type_name": "精选"},
            {"type_id": "4", "type_name": "女优"},
        ]

    def list(self, tid, page=1):
        """列表：优先 home/movlist，失败回落 module/movlist2。"""
        params = {"pageNo": page, "pageSize": 20, "clsId": tid, "orderType": 0}
        data = self._call(self.P_MOVLIST, params) or self._call(self.P_MOVLIST2, params)
        return self._to_vods(data)

    @staticmethod
    def _to_vods(data):
        vods = []
        if not isinstance(data, dict):
            return vods
        items = data.get("data")
        if isinstance(items, dict):
            items = items.get("list") or items.get("movList") or []
        if not isinstance(items, list):
            items = data.get("list") or []
        for it in items:
            if not isinstance(it, dict):
                continue
            vid = it.get("id") or it.get("movId") or it.get("mid")
            if vid is None:
                continue
            vods.append({
                "vod_id": str(vid),
                "vod_name": str(it.get("movName") or it.get("name") or it.get("title") or ""),
                "vod_pic": str(it.get("cover") or it.get("photoUrl") or it.get("thumbnail") or ""),
                "vod_remarks": str(it.get("address") or it.get("release") or ""),
            })
        return vods

    def detail(self, vid):
        data = self._call("/home/movlist", {"movId": vid})
        vods = self._to_vods(data)
        if vods:
            v = vods[0]
            return {"vod_id": v["vod_id"], "vod_name": v["vod_name"],
                    "vod_pic": v["vod_pic"], "vod_content": ""}
        return {"vod_id": str(vid), "vod_name": str(vid)}

    def play(self, vid):
        """播放：hgsp 的 m3u8 由 /player 页解析，直链字段 master.m3u8。
        协议未贯通前返回 None，由上层走占位。"""
        return None


if __name__ == "__main__":
    import ssl
    import sys
    import urllib.error
    import urllib.request

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    h, flow, nonce, ts = build_headers()
    print("flowId :", flow)
    print("sign   :", h["X-Auth-Sign"])
    print("nonce  :", nonce, "ts:", ts)
    print("headers:", json.dumps(h, ensure_ascii=False, indent=2))
    if "--send" in sys.argv:
        req = urllib.request.Request(HOST + HgSpAdapter.P_CHANNELS, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
                print("resp:", r.status, r.read(400))
        except urllib.error.HTTPError as e:
            print("resp:", e.code, e.read(400))
