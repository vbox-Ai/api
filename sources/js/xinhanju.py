"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '新韩剧网',
  lang: 'hipy'
})
"""

#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/12/21 14:45
# @file    : 新韩剧网.min

D=print
C=Exception
import re,sys,requests as B
from urllib import parse
try:
    from pyquery import PyQuery as F
except Exception:
    class _MiniQuery:
        def __init__(self, html):
            self.html = html or ''
        def __call__(self, selector):
            return _MiniQuerySet(_select(self.html, selector))
    class _MiniQuerySet:
        def __init__(self, items):
            self.items_list = items
        def items(self):
            for html in self.items_list:
                yield _MiniNode(html)
        def attr(self, name):
            return _MiniNode(self.items_list[0] if self.items_list else '').attr(name)
        def text(self):
            return _text(' '.join(self.items_list))
    class _MiniNode(_MiniQuery):
        def attr(self, name):
            m = re.search(r'\s%s=["\']([^"\']*)["\']' % re.escape(name), self.html, re.I)
            return m.group(1) if m else None
        def text(self):
            return _text(self.html)
    def _text(html):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html or '')).strip()
    def _select(html, selector):
        if selector in ('div.list ul li', 'div.txt ul li', 'div.play ul li'):
            return re.findall(r'<li\b[^>]*>.*?</li>', html, re.I | re.S)
        if selector == 'a':
            m = re.search(r'<a\b[^>]*>.*?</a>', html, re.I | re.S); return [m.group(0)] if m else []
        if selector == 'span.tip':
            m = re.search(r'<span\b[^>]*class=["\'][^"\']*tip[^"\']*["\'][^>]*>.*?</span>', html, re.I | re.S); return [m.group(0)] if m else []
        if selector == '#actor':
            m = re.search(r'<[^>]+\bid=["\']actor["\'][^>]*>.*?</[^>]+>', html, re.I | re.S); return [m.group(0)] if m else []
        if selector == '#playlist':
            m = re.search(r'<[^>]+\bid=["\']playlist["\'][^>]*>.*?</[^>]+>', html, re.I | re.S); return [m.group(0)] if m else []
        if selector == 'div.juqing':
            m = re.search(r'<div\b[^>]*class=["\'][^"\']*juqing[^"\']*["\'][^>]*>.*?</div>', html, re.I | re.S); return [m.group(0)] if m else []
        m = re.match(r'div\.detail div\.info dl:eq\((\d+)\) dd', selector)
        if m:
            dls = re.findall(r'<dl\b[^>]*>.*?</dl>', html, re.I | re.S)
            idx = int(m.group(1))
            if idx < len(dls):
                dd = re.search(r'<dd\b[^>]*>.*?</dd>', dls[idx], re.I | re.S)
                return [dd.group(0)] if dd else []
        return []
    F = _MiniQuery
from Crypto.Cipher import AES as A
from Crypto.Util.Padding import unpad
import base64 as I
sys.path.append('..')
from base.spider import Spider as E
class Spider(E):
	
	def getName(A):return A.name
	def init(A,extend='{}'):
		A.debug=False;A.name='新韩剧网';A.error_play_url='https://kjjsaas-sh.oss-cn-shanghai.aliyuncs.com/u/3401405881/20240818-936952-fc31b16575e80a7562cdb1f81a39c6b0.mp4';A.home_url='https://www.hanju7.com';A.headers={'User-Agent':'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36','Referer':'https://www.hanju7.com/'};A.extend=extend
	def homeContent(E,filter):
		G={'class':[{'type_id':'1','type_name':'韩剧'},{'type_id':'3','type_name':'韩国电影'},{'type_id':'4','type_name':'韩国综艺'},{'type_id':'hot','type_name':'排行榜'},{'type_id':'new','type_name':'最新更新'}],'filters':{},'list':[],'parse':0,'jx':0}
		try:
			H=B.get(E.home_url,headers=E.headers);H.encoding='utf-8';I=F(H.text)
			for A in I('div.list ul li').items():G['list'].append({'vod_id':A('a').attr('href'),'vod_name':A('a').attr('title'),'vod_pic':(lambda u:u if u.startswith(('https','http'))else'https:'+u)(A('a').attr('data-original')),'vod_remarks':A('span.tip').text()})
		except C as J:D(J)
		return G
	def categoryContent(I,cid,page,filter,ext):
		H=page;G=cid;E={'list':[],'parse':0,'jx':0};H=int(H)
		if G in['hot','new']:J=I.home_url+f"/{G}.html"
		else:J=I.home_url+f"/list/{G}---{H-1}.html"
		try:
			K=B.get(J,headers=I.headers);K.encoding='utf-8';L=F(K.text)
			if G in['hot','new']:
				for A in L('div.txt ul li').items():
					M=A('a').attr('href')
					if M is None:continue
					E['list'].append({'vod_id':A('a').attr('href'),'vod_name':A('a').text(),'vod_pic':'https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png','vod_remarks':A('#actor').text(),'style':{'type':'list'}})
				E['pagecount']=1;E['page']=H
			else:
				for A in L('div.list ul li').items():E['list'].append({'vod_id':A('a').attr('href'),'vod_name':A('a').attr('title'),'vod_pic':(lambda u:u if u.startswith(('https','http'))else'https:'+u)(A('a').attr('data-original')),'vod_remarks':A('span.tip').text()})
		except C as N:D(N)
		return E
	def detailContent(E,did):
		G={'list':[],'parse':0,'jx':0};H=did[0]
		try:
			I=B.get(E.home_url+H,headers=E.headers);I.encoding='utf-8';A=F(I.text);J=[]
			for K in A('div.play ul li').items():L=K('a').text();M=re.search("'(.*?)'",K('a').attr('onclick')).group(1);J.append(f"{L}${M}")
			N={'type_name':A('div.detail div.info dl:eq(2) dd').text(),'vod_id':H,'vod_name':A('div.detail div.info dl:eq(0) dd').text(),'vod_remarks':A('div.detail div.info dl:eq(4) dd').text(),'vod_year':A('div.detail div.info dl:eq(5) dd').text(),'vod_area':'','vod_actor':A('div.detail div.info dl:eq(1) dd').text(),'vod_director':'','vod_content':A('div.juqing').text(),'vod_play_from':A('#playlist').text(),'vod_play_url':'#'.join(J)};G['list'].append(N)
		except C as O:D(O)
		return G
	def searchContent(G,key,quick,page='1'):
		A={'list':[],'parse':0,'jx':0}
		try:
			H=G.headers.copy();H['Content-type']='application/x-www-form-urlencoded';I=B.post(G.home_url+'/search/',headers=H,data=f"show=searchkey&keyboard={parse.quote(key)}");I.encoding='utf-8';J=F(I.text)
			for E in J('div.txt ul li').items():
				K=E('a').attr('href')
				if K is None:continue
				A['list'].append({'vod_id':E('a').attr('href'),'vod_name':E('a').text(),'vod_pic':'https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png','vod_remarks':E('#actor').text(),'style':{'type':'list'}})
			A['pagecount']=1;A['page']=1
		except C as L:D(L)
		return A
	def playerContent(E,flag,pid,vipFlags):
		F={'url':E.error_play_url,'parse':0,'jx':0,'header':{}}
		try:
			G=B.get(E.home_url+f"/u/u1.php?ud={pid}",headers=E.headers)
			if G.ok:J=bytes([109,121,45,116,111,45,110,101,119,104,97,110,45,50,48,50,53,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]);H=I.b64decode(G.text);K=H[:16];L=H[16:];M=A.new(J,A.MODE_CBC,K);N=unpad(M.decrypt(L),A.block_size).decode();F['url']=N.strip()
		except C as O:D(O)
		return F
	def homeVideoContent(A):
		return {'list':[]}
	def isVideoFormat(A,url):
		return url.endswith(('.mp4','.m3u8','.flv','.avi','.wmv','.mkv'))
	def manualVideoCheck(A):
		return False
	def localProxy(A,params):
		return None
if __name__=='__main__':0
