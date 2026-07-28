/*
 * 瓜子影视 JS 蜘蛛 v3.0.3.2 关梯版
 * 适配 vbox-ios JSSpiderEngine (JavaScriptCore / type:3 独立引擎)
 * 动态设备注册获取token / RSA公钥加密+私钥解密 / AES+MD5签名 / 双域名轮询
 * 移植自 Python 版 gz.py (v3.0.3.2)
 *
 * 关键修复 (相比旧版):
 *  - UTF-8 正确编解码: AES/RSA 加密前先把字符串转成 UTF-8 字节, 中文搜索/筛选不再加密错误
 *  - 请求响应兼容: req() 返回 {content, status, ok}, 优先读取 content
 *  - 完整 RSA PKCS1v1.5 公钥加密 + 私钥解密 (响应的 keys 字段)
 *  - 设备注册 signUp -> refresh 全流程, 失败自动重新认证
 *  - 双域名轮询 + 3 次重试
 */

// ===================== UTF-8 编解码 (关键修复) =====================
// JavaScriptCore 的 charCodeAt 返回 UTF-16 code unit, 对中文需要先转 UTF-8 字节
function utf8Encode(str) {
    var bytes = [];
    for (var i = 0; i < str.length; i++) {
        var c = str.charCodeAt(i);
        if (c < 0x80) {
            bytes.push(c);
        } else if (c < 0x800) {
            bytes.push(0xC0 | (c >> 6));
            bytes.push(0x80 | (c & 0x3F));
        } else if (c < 0xD800 || c >= 0xE000) {
            bytes.push(0xE0 | (c >> 12));
            bytes.push(0x80 | ((c >> 6) & 0x3F));
            bytes.push(0x80 | (c & 0x3F));
        } else {
            // 代理对 (Surrogate pair) -> UTF-8 四字节
            i++;
            var c2 = str.charCodeAt(i);
            var cp = 0x10000 + (((c & 0x3FF) << 10) | (c2 & 0x3FF));
            bytes.push(0xF0 | (cp >> 18));
            bytes.push(0x80 | ((cp >> 12) & 0x3F));
            bytes.push(0x80 | ((cp >> 6) & 0x3F));
            bytes.push(0x80 | (cp & 0x3F));
        }
    }
    return bytes;
}

function utf8Decode(bytes) {
    var str = '';
    var i = 0;
    while (i < bytes.length) {
        var b1 = bytes[i++];
        if (b1 < 0x80) {
            str += String.fromCharCode(b1);
        } else if (b1 < 0xE0) {
            var b2 = bytes[i++];
            str += String.fromCharCode(((b1 & 0x1F) << 6) | (b2 & 0x3F));
        } else if (b1 < 0xF0) {
            var b2 = bytes[i++];
            var b3 = bytes[i++];
            str += String.fromCharCode(((b1 & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F));
        } else {
            var b2 = bytes[i++];
            var b3 = bytes[i++];
            var b4 = bytes[i++];
            var cp = ((b1 & 0x07) << 18) | ((b2 & 0x3F) << 12) | ((b3 & 0x3F) << 6) | (b4 & 0x3F);
            cp -= 0x10000;
            str += String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF));
        }
    }
    return str;
}

// ===================== Base64 工具 =====================
function b64decode(s) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    s = String(s).replace(/[\s\r\n]/g, '');
    var pad = (4 - s.length % 4) % 4;
    s += '===='.slice(0, pad);
    var result = [], buf = 0, bits = 0;
    for (var i = 0; i < s.length; i++) {
        var idx = chars.indexOf(s[i]);
        if (idx < 0) continue;
        buf = (buf << 6) | idx;
        bits += 6;
        if (bits >= 8) { bits -= 8; result.push((buf >> bits) & 0xFF); }
    }
    return result;
}

function b64encode(bytes) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var result = '';
    for (var i = 0; i < bytes.length; i += 3) {
        var b1 = bytes[i] || 0, b2 = bytes[i+1] || 0, b3 = bytes[i+2] || 0;
        result += chars[b1 >> 2];
        result += chars[((b1 & 3) << 4) | (b2 >> 4)];
        result += (i + 1 < bytes.length) ? chars[((b2 & 15) << 2) | (b3 >> 6)] : '=';
        result += (i + 2 < bytes.length) ? chars[b3 & 63] : '=';
    }
    return result;
}

// ===================== MD5 (返回大写) =====================
var md5 = (function() {
    function safeAdd(x, y) { var l = (x & 0xFFFF) + (y & 0xFFFF); return (((x >> 16) + (y >> 16) + (l >> 16)) << 16) | (l & 0xFFFF); }
    function bitRL(n, c) { return (n << c) | (n >>> (32 - c)); }
    function cmn(q, a, b, x, s, t) { return safeAdd(bitRL(safeAdd(safeAdd(a, q), safeAdd(x, t)), s), b); }
    function ff(a,b,c,d,x,s,t){return cmn((b&c)|((~b)&d),a,b,x,s,t);}
    function gg(a,b,c,d,x,s,t){return cmn((b&d)|(c&(~d)),a,b,x,s,t);}
    function hh(a,b,c,d,x,s,t){return cmn(b^c^d,a,b,x,s,t);}
    function ii(a,b,c,d,x,s,t){return cmn(c^(b|(~d)),a,b,x,s,t);}
    function binl(x, l) {
        x[l>>5]|=0x80<<(l%32); x[(((l+64)>>>9)<<4)+14]=l;
        var a=1732584193,b=-271733879,c=-1732584194,d=271733878;
        for(var i=0;i<x.length;i+=16){
            var oa=a,ob=b,oc=c,od=d;
            a=ff(a,b,c,d,x[i],7,-680876936);d=ff(d,a,b,c,x[i+1],12,-389564586);c=ff(c,d,a,b,x[i+2],17,606105819);b=ff(b,c,d,a,x[i+3],22,-1044525330);
            a=ff(a,b,c,d,x[i+4],7,-176418897);d=ff(d,a,b,c,x[i+5],12,1200080426);c=ff(c,d,a,b,x[i+6],17,-1473231341);b=ff(b,c,d,a,x[i+7],22,-45705983);
            a=ff(a,b,c,d,x[i+8],7,1770035416);d=ff(d,a,b,c,x[i+9],12,-1958414417);c=ff(c,d,a,b,x[i+10],17,-42063);b=ff(b,c,d,a,x[i+11],22,-1990404162);
            a=ff(a,b,c,d,x[i+12],7,1804603682);d=ff(d,a,b,c,x[i+13],12,-40341101);c=ff(c,d,a,b,x[i+14],17,-1502002290);b=ff(b,c,d,a,x[i+15],22,1236535329);
            a=gg(a,b,c,d,x[i+1],5,-165796510);d=gg(d,a,b,c,x[i+6],9,-1069501632);c=gg(c,d,a,b,x[i+11],14,643717713);b=gg(b,c,d,a,x[i],20,-373897302);
            a=gg(a,b,c,d,x[i+5],5,-701558691);d=gg(d,a,b,c,x[i+10],9,38016083);c=gg(c,d,a,b,x[i+15],14,-660478335);b=gg(b,c,d,a,x[i+4],20,-405537848);
            a=gg(a,b,c,d,x[i+9],5,568446438);d=gg(d,a,b,c,x[i+14],9,-1019803690);c=gg(c,d,a,b,x[i+3],14,-187363961);b=gg(b,c,d,a,x[i+8],20,1163531501);
            a=gg(a,b,c,d,x[i+13],5,-1444681467);d=gg(d,a,b,c,x[i+2],9,-51403784);c=gg(c,d,a,b,x[i+7],14,1735328473);b=gg(b,c,d,a,x[i+12],20,-1926607734);
            a=hh(a,b,c,d,x[i+5],4,-378558);d=hh(d,a,b,c,x[i+8],11,-2022574463);c=hh(c,d,a,b,x[i+11],16,1839030562);b=hh(b,c,d,a,x[i+14],23,-35309556);
            a=hh(a,b,c,d,x[i+1],4,-1530992060);d=hh(d,a,b,c,x[i+4],11,1272893353);c=hh(c,d,a,b,x[i+7],16,-155497632);b=hh(b,c,d,a,x[i+10],23,-1094730640);
            a=hh(a,b,c,d,x[i+13],4,681279174);d=hh(d,a,b,c,x[i],11,-358537222);c=hh(c,d,a,b,x[i+3],16,-722521979);b=hh(b,c,d,a,x[i+6],23,76029189);
            a=hh(a,b,c,d,x[i+9],4,-640364487);d=hh(d,a,b,c,x[i+12],11,-421815835);c=hh(c,d,a,b,x[i+15],16,530742520);b=hh(b,c,d,a,x[i+2],23,-995338651);
            a=ii(a,b,c,d,x[i],6,-198630844);d=ii(d,a,b,c,x[i+7],10,1126891415);c=ii(c,d,a,b,x[i+14],15,-1416354905);b=ii(b,c,d,a,x[i+5],21,-57434055);
            a=ii(a,b,c,d,x[i+12],6,1700485571);d=ii(d,a,b,c,x[i+3],10,-1894986606);c=ii(c,d,a,b,x[i+10],15,-1051523);b=ii(b,c,d,a,x[i+1],21,-2054922799);
            a=ii(a,b,c,d,x[i+8],6,1873313359);d=ii(d,a,b,c,x[i+15],10,-30611744);c=ii(c,d,a,b,x[i+6],15,-1560198380);b=ii(b,c,d,a,x[i+13],21,1309151649);
            a=ii(a,b,c,d,x[i+4],6,-145523070);d=ii(d,a,b,c,x[i+11],10,-1120210379);c=ii(c,d,a,b,x[i+2],15,718787259);b=ii(b,c,d,a,x[i+9],21,-343485551);
            a=safeAdd(a,oa);b=safeAdd(b,ob);c=safeAdd(c,oc);d=safeAdd(d,od);
        }
        return [a,b,c,d];
    }
    // 关键修复: 用 UTF-8 字节而非 UTF-16 code unit
    function s2b(s){var b=utf8Encode(s);var arr=[];for(var i=0;i<b.length*8;i+=8)arr[i>>5]|=b[i/8]<<(i%32);return arr;}
    function b2h(b){var h='0123456789abcdef',s='';for(var i=0;i<b.length*4;i++)s+=h.charAt((b[i>>2]>>((i%4)*8+4))&0xF)+h.charAt((b[i>>2]>>((i%4)*8))&0xF);return s;}
    return function(s){return b2h(binl(s2b(s),utf8Encode(s).length*8)).toUpperCase();};
})();

// ===================== AES-128-CBC =====================
var AES = (function() {
    var SBOX = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16];
    var INV_SBOX = [0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d];
    var RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];

    function mul(a,b){var r=0;for(var i=0;i<8;i++){if(b&1)r^=a;var hi=a&0x80;a=(a<<1)&0xFF;if(hi)a^=0x1b;b>>=1;}return r;}

    function keyExpansion(key) {
        var nk = key.length / 4, nb = 4, nr = nk + 6;
        var w = [];
        for (var i = 0; i < nk; i++) w[i] = (key[i*4]<<24)|(key[i*4+1]<<16)|(key[i*4+2]<<8)|key[i*4+3];
        for (i = nk; i < nb * (nr + 1); i++) {
            var t = w[i-1];
            if (i % nk === 0) { t = ((SBOX[(t>>16)&0xFF]<<24)|(SBOX[(t>>8)&0xFF]<<16)|(SBOX[t&0xFF]<<8)|SBOX[(t>>24)&0xFF])^(RCON[i/nk-1]<<24); }
            else if (nk > 6 && i % nk === 4) { t = (SBOX[(t>>24)&0xFF]<<24)|(SBOX[(t>>16)&0xFF]<<16)|(SBOX[(t>>8)&0xFF]<<8)|SBOX[t&0xFF]; }
            w[i] = w[i-nk] ^ t;
        }
        return w;
    }

    // 关键修复: 列 j 对应 w[r*4+j], 行 i 对应该 word 的第 i 字节 (MSB first)
    function addRoundKey(s, w, r) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]^=(w[r*4+j]>>>(24-8*i))&0xFF; }
    function subBytes(s) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]=SBOX[s[i][j]]; }
    function invSubBytes(s) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]=INV_SBOX[s[i][j]]; }
    function shiftRows(s) { var t; t=s[1][0];s[1][0]=s[1][1];s[1][1]=s[1][2];s[1][2]=s[1][3];s[1][3]=t; t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t; t=s[3][3];s[3][3]=s[3][2];s[3][2]=s[3][1];s[3][1]=s[3][0];s[3][0]=t; }
    function invShiftRows(s) { var t; t=s[1][3];s[1][3]=s[1][2];s[1][2]=s[1][1];s[1][1]=s[1][0];s[1][0]=t; t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t; t=s[3][0];s[3][0]=s[3][1];s[3][1]=s[3][2];s[3][2]=s[3][3];s[3][3]=t; }
    // 关键修复: MixColumns 必须按列操作, 不是按行
    function mixColumns(s) { for(var col=0;col<4;col++){var a=s[0][col],b=s[1][col],c=s[2][col],d=s[3][col];s[0][col]=mul(a,2)^mul(b,3)^c^d;s[1][col]=a^mul(b,2)^mul(c,3)^d;s[2][col]=a^b^mul(c,2)^mul(d,3);s[3][col]=mul(a,3)^b^c^mul(d,2);} }
    function invMixColumns(s) { for(var col=0;col<4;col++){var a=s[0][col],b=s[1][col],c=s[2][col],d=s[3][col];s[0][col]=mul(a,14)^mul(b,11)^mul(c,13)^mul(d,9);s[1][col]=mul(a,9)^mul(b,14)^mul(c,11)^mul(d,13);s[2][col]=mul(a,13)^mul(b,9)^mul(c,14)^mul(d,11);s[3][col]=mul(a,11)^mul(b,13)^mul(c,9)^mul(d,14);} }

    function bytesToState(b) { var s=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]]; for(var i=0;i<16;i++) s[i%4][Math.floor(i/4)]=b[i]; return s; }
    // 关键修复: stateToBytes 必须按列读取, 与 bytesToState 的按列填充保持一致
    function stateToBytes(s) { var b=[]; for(var j=0;j<4;j++) for(var i=0;i<4;i++) b.push(s[i][j]); return b; }

    function encryptBlock(input, w) {
        var s = bytesToState(input), nr = w.length / 4 - 1;
        addRoundKey(s, w, 0);
        for (var r = 1; r < nr; r++) { subBytes(s); shiftRows(s); mixColumns(s); addRoundKey(s, w, r); }
        subBytes(s); shiftRows(s); addRoundKey(s, w, nr);
        return stateToBytes(s);
    }

    function decryptBlock(input, w) {
        var s = bytesToState(input), nr = w.length / 4 - 1;
        addRoundKey(s, w, nr);
        for (var r = nr - 1; r > 0; r--) { invShiftRows(s); invSubBytes(s); addRoundKey(s, w, r); invMixColumns(s); }
        invShiftRows(s); invSubBytes(s); addRoundKey(s, w, 0);
        return stateToBytes(s);
    }

    function xorBlocks(a, b) { var r=[]; for(var i=0;i<a.length;i++) r[i]=a[i]^b[i]; return r; }

    return {
        encrypt: function(plaintext, keyStr, ivStr) {
            // 关键修复: 用 UTF-8 字节, 支持中文
            var key = utf8Encode(keyStr).slice(0, 16);
            while (key.length < 16) key.push(0);
            var iv = utf8Encode(ivStr).slice(0, 16);
            while (iv.length < 16) iv.push(0);
            var w = keyExpansion(key);
            // 关键修复: PKCS7 填充 - 计算固定填充值, 且长度为16倍数时追加完整块
            var pt = utf8Encode(plaintext);
            var padLen = 16 - (pt.length % 16);
            for (var p = 0; p < padLen; p++) pt.push(padLen);
            var ct=[];
            for(var i=0;i<pt.length;i+=16){var block=xorBlocks(pt.slice(i,i+16),i===0?iv:ct.slice(i-16,i));ct=ct.concat(encryptBlock(block,w));}
            var hex='';for(i=0;i<ct.length;i++) hex+=('0'+ct[i].toString(16)).slice(-2);
            return hex.toUpperCase();
        },
        decrypt: function(hexStr, keyStr, ivStr) {
            var key = utf8Encode(keyStr).slice(0, 16);
            while (key.length < 16) key.push(0);
            var iv = utf8Encode(ivStr).slice(0, 16);
            while (iv.length < 16) iv.push(0);
            var w = keyExpansion(key);
            var ct=[]; for(var i=0;i<hexStr.length;i+=2) ct.push(parseInt(hexStr.substr(i,2),16));
            var pt=[];
            for(i=0;i<ct.length;i+=16){var dec=decryptBlock(ct.slice(i,i+16),w);var xored=xorBlocks(dec,i===0?iv:ct.slice(i-16,i));pt=pt.concat(xored);}
            var pad=pt[pt.length-1]; if(pad<1||pad>16) pad=0;
            pt=pt.slice(0,pt.length-pad);
            // 关键修复: 用 UTF-8 解码, 支持中文
            return utf8Decode(pt);
        }
    };
})();

// ===================== BigInt 辅助 =====================
// 注: JavaScriptCore (iOS 16+) 支持 BigInt 字面量 1n
function modPow(base, exp, mod) {
    base = ((base % mod) + mod) % mod;
    var result = 1n;
    while (exp > 0n) {
        if (exp & 1n) result = (result * base) % mod;
        exp >>= 1n;
        base = (base * base) % mod;
    }
    return result;
}

function bigIntToBytes(n, len) {
    var bytes = [];
    var tmp = n;
    while (tmp > 0n) { bytes.unshift(Number(tmp & 0xFFn)); tmp >>= 8n; }
    while (bytes.length < len) bytes.unshift(0);
    if (bytes.length > len) bytes = bytes.slice(bytes.length - len);
    return bytes;
}

// ===================== RSA 公钥加密 (PKCS1v1.5) =====================
// 用于加密 AES key/iv JSON，生成请求的 keys 字段
function rsaEncrypt(plaintext, publicKeyB64) {
    var der = b64decode(publicKeyB64);

    function readTag(buf, offset) {
        var tag = buf[offset];
        var len = buf[offset + 1];
        offset += 2;
        if (len >= 0x80) {
            var nb = len & 0x7F;
            len = 0;
            for (var i = 0; i < nb; i++) len = (len << 8) | buf[offset + i];
            offset += nb;
        }
        return { tag: tag, offset: offset, length: len };
    }

    function readInt(buf, offset) {
        var info = readTag(buf, offset);
        var val = 0n;
        for (var i = 0; i < info.length; i++) {
            val = (val << 8n) | BigInt(buf[info.offset + i]);
        }
        return { value: val, end: info.offset + info.length };
    }

    var pos = 0;
    var outer = readTag(der, pos); pos = outer.offset;
    var algSeq = readTag(der, pos); pos = algSeq.offset + algSeq.length;
    var bitStr = readTag(der, pos); pos = bitStr.offset;
    pos += 1;
    var innerSeq = readTag(der, pos); pos = innerSeq.offset;
    var nInt = readInt(der, pos); pos = nInt.end;
    var eInt = readInt(der, pos);

    var n = nInt.value;
    var e = eInt.value;

    // 关键修复: 用 UTF-8 字节
    var msgBytes = utf8Encode(plaintext);

    var keyLen = 128;
    var padLen = keyLen - msgBytes.length - 3;
    if (padLen < 8) return '';

    var padded = [0x00, 0x02];
    for (var j = 0; j < padLen; j++) {
        var rb = 0;
        while (rb === 0) {
            rb = Math.floor(Math.random() * 256);
        }
        padded.push(rb);
    }
    padded.push(0x00);
    padded = padded.concat(msgBytes);

    var m = 0n;
    for (var k = 0; k < padded.length; k++) {
        m = (m << 8n) | BigInt(padded[k]);
    }

    var c = modPow(m, e, n);
    var encBytes = bigIntToBytes(c, keyLen);
    return b64encode(encBytes);
}

// ===================== RSA 私钥解密 (PKCS1v1.5) =====================
function rsaDecrypt(encryptedB64, privateKeyPem) {
    var b64 = privateKeyPem.replace(/-----BEGIN[\s\S]*?-----/g, '').replace(/-----END[\s\S]*?-----/g, '').replace(/\s/g, '');
    var der = b64decode(b64);

    function readTag(buf, offset) {
        var tag = buf[offset];
        var len = buf[offset + 1];
        offset += 2;
        if (len >= 0x80) {
            var nb = len & 0x7F;
            len = 0;
            for (var i = 0; i < nb; i++) len = (len << 8) | buf[offset + i];
            offset += nb;
        }
        return { tag: tag, offset: offset, length: len };
    }

    function readInt(buf, offset) {
        var info = readTag(buf, offset);
        var val = 0n;
        for (var i = 0; i < info.length; i++) {
            val = (val << 8n) | BigInt(buf[info.offset + i]);
        }
        return { value: val, end: info.offset + info.length };
    }

    var pos = 0;
    var outer = readTag(der, pos); pos = outer.offset;
    var ver = readInt(der, pos); pos = ver.end;
    var algTag = readTag(der, pos);
    pos = algTag.offset + algTag.length;
    var octInfo = readTag(der, pos); pos = octInfo.offset;
    var inner = readTag(der, pos); pos = inner.offset;
    var innerVer = readInt(der, pos); pos = innerVer.end;
    var nInt = readInt(der, pos); pos = nInt.end;
    var eInt = readInt(der, pos); pos = eInt.end;
    var dInt = readInt(der, pos); pos = dInt.end;

    var n = nInt.value;
    var d = dInt.value;

    var encBytes = b64decode(encryptedB64);
    var c = 0n;
    for (var i = 0; i < encBytes.length; i++) {
        c = (c << 8n) | BigInt(encBytes[i]);
    }

    var m = modPow(c, d, n);
    var decBytes = bigIntToBytes(m, 128);

    if (decBytes[0] !== 0x00 || decBytes[1] !== 0x02) return '';
    var idx = 2;
    while (idx < decBytes.length && decBytes[idx] !== 0x00) idx++;
    idx++;
    var result = [];
    for (var j = idx; j < decBytes.length; j++) result.push(decBytes[j]);

    // 关键修复: 用 UTF-8 解码
    return utf8Decode(result);
}

// ===================== 随机工具 =====================
function randomDeviceId() {
    var base = 864150060000000;
    var r = Math.floor(Math.random() * 10000);
    return String(base + r);
}

function randomDeviceKey() {
    var chars = '0123456789ABCDEF';
    var s = '';
    for (var i = 0; i < 40; i++) s += chars.charAt(Math.floor(Math.random() * 16));
    return s;
}

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        // ---- 配置 (v3.0.3.2) ----
        var HOSTS = [
            'https://apinew.uozvr.com',
            'https://api.w32z7vtd.com'
        ];
        var hostIndex = 0;

        var AES_KEY = 'OITxa5OqAYjhswxx';
        var AES_IV = 'rCMNwZASNBKZ8mXV';

        var RSA_PUBLIC_KEY = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUM5+/y8sPsWkd1/RQS64X259EUwxFXFE5HlA65MqrxnPs0JqoSRojSDy5QhwvROlaD6TwRQHKMY2OAZ6SnQeUJsChTEFIR9qUkwrs3/MVUMxjsv6JS6Oe/juclyJGTgVmDhB55EafXsD0SQYVj/QXXsxR6ewR5E2kL52yAAD4yQIDAQAB';
        var RSA_PRIVATE_KEY = '-----BEGIN RSA PRIVATE KEY-----\nMIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1\nozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU\n1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK\nZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7\nHetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW\nV9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI\nDblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34\nsaTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM\niMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM\nWBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8\njUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ\nK7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b\nL3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa\nt5lYKfpe8k83ZA==\n-----END RSA PRIVATE KEY-----';

        var DEVICE_OLD_KEY = 'aLFBMWpxBrIDAD1Si/KVvm41';

        // 设备信息
        var deviceId = randomDeviceId();
        var deviceKey = randomDeviceKey();
        var token = '';
        var token_id = '';
        var registered = false;

        var cache = {};
        var CACHE_TIMEOUT = 300; // 5分钟

        function makeHeader() {
            var host = HOSTS[hostIndex];
            return {
                'User-Agent': 'Lavf/57.83.100',
                'code': 'GZ0369',
                'deviceId': deviceId,
                'lang': 'zh_cn',
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Version': '2604028',
                'PackageName': 'com.ae06aebdbb.y286327f5a.ofe849883320260517',
                'Ver': '3.0.3.2',
                'api-ver': '3.0.3.2',
                'Referer': host
            };
        }

        // URL 编码参数
        function encodeParams(obj) {
            var parts = [];
            for (var k in obj) {
                if (obj.hasOwnProperty(k)) {
                    parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(obj[k]));
                }
            }
            return parts.join('&');
        }

        // ---- 认证流程 ----
        function authRequest(params, path) {
            return sendEncryptedRequest(params, path, true);
        }

        function signUp() {
            print('>>> guazi signUp...');
            var params = {
                new_key: deviceKey,
                old_key: DEVICE_OLD_KEY,
                phone_type: 1,
                code: ''
            };
            var result = authRequest(params, '/App/Authentication/Device/signUp');
            if (result) {
                applyAuth(result);
                registered = true;
            } else {
                throw 'signUp failed';
            }
        }

        function signIn() {
            print('>>> guazi signIn...');
            var params = {
                new_key: deviceKey,
                old_key: DEVICE_OLD_KEY
            };
            var result = authRequest(params, '/App/Authentication/Device/signIn');
            if (result) {
                applyAuth(result);
            } else {
                throw 'signIn failed';
            }
        }

        function refreshToken() {
            print('>>> guazi refreshToken...');
            var result = authRequest({}, '/App/Authentication/Authenticator/refresh');
            if (result) {
                applyAuth(result);
            } else {
                throw 'refresh failed';
            }
        }

        function applyAuth(result) {
            if (!result || !result.token) {
                throw 'auth result has no token';
            }
            token = result.token;
            if (result.app_user_id) {
                token_id = String(result.app_user_id);
            }
            print('>>> guazi token获取成功, token前缀: ' + token.substring(0, 30) + '...');
        }

        function ensureToken() {
            if (!token || !token_id) {
                if (registered) {
                    signIn();
                } else {
                    signUp();
                }
                refreshToken();
            }
        }

        // ---- 核心加密请求 ----
        function sendEncryptedRequest(data, path, isAuth) {
            try {
                if (!isAuth) {
                    ensureToken();
                }

                // 1. AES 加密请求参数
                var jsonParams = JSON.stringify(data);
                var requestKey = AES.encrypt(jsonParams, AES_KEY, AES_IV);

                // 2. RSA 公钥加密 AES key/iv JSON → keys 字段
                var keyJson = JSON.stringify({ iv: AES_IV, key: AES_KEY });
                var keys = rsaEncrypt(keyJson, RSA_PUBLIC_KEY);
                if (!keys) {
                    print('>>> guazi RSA加密失败');
                    return null;
                }

                // 3. 生成签名 (MD5 大写)
                var t = Math.floor(Date.now() / 1000).toString();
                var signStr = 'token_id=,token=' + token + ',phone_type=1,request_key=' + requestKey + ',app_id=1,time=' + t + ',keys=' + keys + '*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br';
                var signature = md5(signStr);

                // 4. 构建请求体
                var postBody = {
                    token: token,
                    token_id: '',
                    phone_type: '1',
                    time: t,
                    phone_model: 'xiaomi-25031',
                    keys: keys,
                    request_key: requestKey,
                    signature: signature,
                    app_id: '1',
                    ad_version: '1'
                };

                // 5. 发送请求
                var host = HOSTS[hostIndex];
                var bodyStr = encodeParams(postBody);
                var url = host + path;
                var header = makeHeader();

                var respObj = req(url, {
                    method: 'POST',
                    headers: header,
                    data: bodyStr
                });

                if (!respObj) { print('>>> guazi req returned null: ' + path); return null; }

                // 兼容 req() 返回: {content, status, ok, headers}
                var respStr = '';
                if (typeof respObj === 'string') {
                    respStr = respObj;
                } else if (respObj.content) {
                    respStr = respObj.content;
                } else if (respObj.data) {
                    respStr = respObj.data;
                } else if (respObj.body) {
                    respStr = respObj.body;
                } else {
                    print('>>> guazi req resp has no content/data/body');
                    return null;
                }

                if (typeof respStr === 'object') {
                    respStr = JSON.stringify(respStr);
                }

                var respJson = JSON.parse(respStr);
                if (!respJson) { print('>>> guazi respJson parse failed'); return null; }

                // 检查业务 code
                if (respJson.code && respJson.code !== 200) {
                    print('>>> guazi 业务错误码: ' + respJson.code + ', path: ' + path + ', msg: ' + (respJson.msg || respJson.message || ''));
                    return null;
                }

                if (!respJson.data) { print('>>> guazi respJson has no .data'); return null; }

                var dataResp = respJson.data;
                var encryptedResponse = dataResp.response_key;
                var encryptedKeys = dataResp.keys;

                if (!encryptedResponse || !encryptedKeys) {
                    print('>>> guazi data 缺少 response_key 或 keys');
                    return null;
                }

                // 6. RSA 解密响应密钥
                var decryptedKeysJson = rsaDecrypt(encryptedKeys, RSA_PRIVATE_KEY);
                if (!decryptedKeysJson) { print('>>> guazi RSA解密失败'); return null; }
                var keyInfo = JSON.parse(decryptedKeysJson);

                // 7. AES 解密响应数据
                var decryptedData = AES.decrypt(encryptedResponse, keyInfo.key, keyInfo.iv);
                if (!decryptedData) { print('>>> guazi AES解密失败'); return null; }

                return JSON.parse(decryptedData);
            } catch (e) {
                print('>>> guazi sendEncryptedRequest ERROR (' + path + '): ' + e);
                return null;
            }
        }

        // ---- 带重试和域名轮询的数据获取 ----
        function getData(data, path, useCache) {
            useCache = useCache !== false;
            try {
                var cacheKey = path + '_' + md5(JSON.stringify(data));
                if (useCache && cache[cacheKey]) {
                    var cached = cache[cacheKey];
                    if (Math.floor(Date.now() / 1000) - cached.time < CACHE_TIMEOUT) {
                        return cached.data;
                    }
                }

                for (var attempt = 0; attempt < 3; attempt++) {
                    var tried = 0;
                    while (tried < HOSTS.length) {
                        var result = sendEncryptedRequest(data, path, false);
                        if (result !== null) {
                            if (useCache) {
                                cache[cacheKey] = { data: result, time: Math.floor(Date.now() / 1000) };
                            }
                            return result;
                        }
                        // 切换域名
                        hostIndex = (hostIndex + 1) % HOSTS.length;
                        tried++;
                    }

                    // 所有域名失败，尝试重新认证
                    if (attempt < 2) {
                        print('>>> guazi 所有域名失败，尝试重新认证...');
                        try {
                            token = '';
                            token_id = '';
                            registered = false;
                            ensureToken();
                        } catch (e) {
                            print('>>> guazi 重新认证失败: ' + e);
                        }
                        hostIndex = 0;
                    } else {
                        break;
                    }
                }
                return null;
            } catch (e) {
                print('>>> guazi getData异常: ' + e);
                return null;
            }
        }

        // ---- 初始化 token ----
        function initToken() {
            try {
                print('>>> guazi 初始化设备认证...');
                if (!registered) {
                    signUp();
                }
                refreshToken();
            } catch (e) {
                print('>>> guazi 初始化token失败: ' + e);
            }
        }

        // 启动时初始化
        initToken();

        return {
            init: function(config) {
                return true;
            },

            homeContent: function(filter) {
                var classes = [
                    { type_name: '电影', type_id: '1' },
                    { type_name: '电视剧', type_id: '2' },
                    { type_name: '动漫', type_id: '4' },
                    { type_name: '综艺', type_id: '3' },
                    { type_name: '短剧', type_id: '64' }
                ];

                var filters = {};
                var areaVals = [
                    { n: '全部', v: '0' }, { n: '大陆', v: '大陆' }, { n: '香港', v: '香港' },
                    { n: '台湾', v: '台湾' }, { n: '美国', v: '美国' }, { n: '韩国', v: '韩国' },
                    { n: '日本', v: '日本' }, { n: '英国', v: '英国' }, { n: '法国', v: '法国' },
                    { n: '泰国', v: '泰国' }, { n: '印度', v: '印度' }, { n: '其他', v: '其他' }
                ];
                var yearVals = [
                    { n: '全部', v: '0' }, { n: '2026', v: '2026' }, { n: '2025', v: '2025' },
                    { n: '2024', v: '2024' }, { n: '2023', v: '2023' }, { n: '2022', v: '2022' },
                    { n: '2021', v: '2021' }, { n: '2020', v: '2020' }, { n: '2019', v: '2019' },
                    { n: '2018', v: '2018' }, { n: '2017', v: '2017' }, { n: '2016', v: '2016' },
                    { n: '2015', v: '2015' }, { n: '2014', v: '2014' }, { n: '2013', v: '2013' },
                    { n: '2012', v: '2012' }, { n: '2011', v: '2011' }, { n: '2010', v: '2010' },
                    { n: '2009', v: '2009' }, { n: '2008', v: '2008' }, { n: '2007', v: '2007' },
                    { n: '2006', v: '2006' }, { n: '2005', v: '2005' }, { n: '更早', v: '2004' }
                ];
                var sortVals = [
                    { n: '最新', v: 'd_id' },
                    { n: '最热', v: 'd_hits' },
                    { n: '推荐', v: 'd_score' }
                ];
                for (var i = 0; i < classes.length; i++) {
                    filters[classes[i].type_id] = [
                        { key: 'area', name: '地区', value: areaVals },
                        { key: 'year', name: '年份', value: yearVals },
                        { key: 'sort', name: '排序', value: sortVals }
                    ];
                }

                return {
                    class: classes,
                    filters: filters
                };
            },

            homeVideoContent: function() {
                return { list: [] };
            },

            categoryContent: function(tid, pg, extend) {
                var ext = {};
                try { ext = typeof extend === 'string' ? JSON.parse(extend) : (extend || {}); } catch(e) {}

                var body = {
                    area: ext.area || '0',
                    year: ext.year || '0',
                    pageSize: '30',
                    sort: ext.sort || 'd_id',
                    page: String(pg),
                    tid: String(tid)
                };

                var data = getData(body, '/App/IndexList/indexList', true);
                var videos = [];
                if (data && data.list) {
                    for (var i = 0; i < data.list.length; i++) {
                        var item = data.list[i];
                        var vc = item.vod_continu || 0;
                        videos.push({
                            vod_id: item.vod_id + '/' + vc,
                            vod_name: item.vod_name || '',
                            vod_pic: item.vod_pic || '',
                            vod_remarks: vc === 0 ? '电影' : ('更新至' + vc + '集')
                        });
                    }
                }
                return {
                    list: videos,
                    page: parseInt(pg) || 1,
                    pagecount: 9999,
                    limit: 30,
                    total: 999999
                };
            },

            detailContent: function(ids) {
                try {
                    var firstId = String(ids).split(',')[0];
                    var vodId = firstId.split('/')[0];

                    // 获取视频详情
                    var t = Math.floor(Date.now() / 1000).toString();
                    var body1 = {
                        token_id: token_id,
                        vod_id: vodId,
                        mobile_time: t,
                        token: token
                    };
                    var qdata = getData(body1, '/App/IndexPlay/playInfo', true);

                    // 获取播放列表
                    var body2 = {
                        vurl_cloud_id: '2',
                        vod_d_id: vodId
                    };
                    var jdata = getData(body2, '/App/Resource/Vurl/show', true);

                    if (!qdata || !qdata.vodInfo) return { list: [] };
                    var vod = qdata.vodInfo;

                    var videoDetail = {
                        vod_id: vodId,
                        vod_name: vod.vod_name || '',
                        vod_pic: vod.vod_pic || '',
                        vod_year: vod.vod_year || '',
                        vod_area: vod.vod_area || '',
                        vod_actor: vod.vod_actor || '',
                        vod_director: vod.vod_director || '',
                        vod_content: (vod.vod_use_content || '').trim(),
                        vod_play_from: '瓜子影视',
                        vod_play_url: ''
                    };

                    var playList = [];
                    if (jdata && jdata.list) {
                        for (var idx = 0; idx < jdata.list.length; idx++) {
                            var item = jdata.list[idx];
                            if (item.play) {
                                var names = [];
                                var params = [];
                                for (var key in item.play) {
                                    if (item.play.hasOwnProperty(key) && item.play[key].param) {
                                        names.push(key);
                                        params.push(item.play[key].param);
                                    }
                                }
                                if (params.length > 0) {
                                    var playName = String(idx + 1);
                                    if (jdata.list.length === 1) playName = vod.vod_name || '';
                                    var playUrl = params[params.length - 1] + '||' + names.join('@');
                                    playList.push(playName + '$' + playUrl);
                                }
                            }
                        }
                    }
                    videoDetail.vod_play_url = playList.join('#');
                    return { list: [videoDetail] };
                } catch (e) {
                    print('>>> guazi detailContent error: ' + e);
                    return { list: [] };
                }
            },

            searchContent: function(key, quick, pg) {
                try {
                    var keyword = String(key || '').trim();
                    var page = parseInt(pg || 1) || 1;
                    // 兼容部分引擎按 2 参数调用 searchContent(key, pg) 的情况。
                    if ((!pg || String(pg) === 'undefined') && quick !== undefined && quick !== null) {
                        var quickAsPage = parseInt(quick);
                        if (!isNaN(quickAsPage) && quickAsPage > 0) page = quickAsPage;
                    }

                    var body = {
                        keywords: keyword,
                        order_val: '1',
                        page: String(page)
                    };

                    var data = getData(body, '/App/Index/findMoreVod', false);
                    var videos = [];
                    if (data && data.list) {
                        for (var i = 0; i < data.list.length; i++) {
                            var item = data.list[i];
                            var vc = item.vod_continu || 0;
                            videos.push({
                                vod_id: item.vod_id + '/' + vc,
                                vod_name: item.vod_name || '',
                                vod_pic: item.vod_pic || '',
                                vod_remarks: vc === 0 ? '电影' : ('更新至' + vc + '集')
                            });
                        }
                    }

                    // 瓜子接口会返回较宽泛的 100 条结果。优先保留标题包含关键词的结果，
                    // 避免 vbox 搜索页出现大量弱相关内容；若过滤后为空，则保留原始结果兜底。
                    var filtered = [];
                    var kw = keyword.toLowerCase().replace(/\s+/g, '');
                    if (kw) {
                        for (var j = 0; j < videos.length; j++) {
                            var name = String(videos[j].vod_name || '').toLowerCase().replace(/\s+/g, '');
                            if (name.indexOf(kw) >= 0) {
                                filtered.push(videos[j]);
                            }
                        }
                    }
                    if (filtered.length > 0) {
                        videos = filtered;
                    }

                    // 限制单页展示数量，避免接口一次返回 100 条造成界面显示 99+。
                    var limit = 30;
                    if (videos.length > limit) {
                        videos = videos.slice(0, limit);
                    }

                    return {
                        list: videos,
                        page: page,
                        pagecount: 1,
                        limit: limit,
                        total: videos.length
                    };
                } catch (e) {
                    print('>>> guazi searchContent error: ' + e);
                    return { list: [], page: 1, pagecount: 1, limit: 30, total: 0 };
                }
            },

            playerContent: function(vodId, flag, url) {
                try {
                    var parts = String(url).split('||');
                    if (parts.length < 2) return { parse: 0, playUrl: '', url: '' };

                    var paramStr = parts[0];
                    var resolutions = parts[1].split('@');

                    // 解析参数
                    var params = {};
                    var pairs = paramStr.split('&');
                    for (var i = 0; i < pairs.length; i++) {
                        var eqIdx = pairs[i].indexOf('=');
                        if (eqIdx > 0) {
                            params[pairs[i].substring(0, eqIdx)] = pairs[i].substring(eqIdx + 1);
                        }
                    }

                    // 按分辨率排序（从大到小）
                    resolutions.sort(function(a, b) { return (parseInt(b) || 0) - (parseInt(a) || 0); });

                    if (resolutions.length > 0) {
                        params.resolution = resolutions[0];
                        var data = getData(params, '/App/Resource/VurlDetail/showOne', false);
                        if (data && data.url) {
                            return {
                                parse: 0,
                                playUrl: '',
                                url: data.url,
                                header: JSON.stringify({ 'User-Agent': 'Lavf/57.83.100', 'Referer': 'http://WJiZxLXA2.com/' })
                            };
                        }
                    }

                    return { parse: 0, playUrl: '', url: '' };
                } catch (e) {
                    print('>>> guazi playerContent error: ' + e);
                    return { parse: 0, playUrl: '', url: '' };
                }
            }
        };
    }
};
