/*
 * 哇哇影视 JS 蜘蛛 v1.3
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: MacCMS API (zjv6.vod)
 * 特点: AES-128-ECB 接口配置解密 + RSA-SHA256 请求签名 + Gitee 远程配置
 * v1.4: 修复vod_id等字段类型转换(数字→字符串)，修复Swift JSONDecoder解码失败导致无数据
 * v1.3: 修复lang/letter筛选参数、playerContent直链/解析器判断、emoji编解码
 * v1.2: 完全自包含纯JS实现(AES-ECB/SHA-256/RSA-SHA256/UUID/hex-base64)
 *       无需更新vbox即可使用，原生桥接可用时自动加速
 * 流程: Gitee获取加密配置 → AES-ECB解密 → RSA签名请求API → 返回视频数据
 */

// ===================== Base64 工具（带换行处理+纯JS回退） =====================
function b64decodeToBytes(s) {
    s = String(s).replace(/[\s\r\n]/g, '');
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
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

function b64decodeStr(s) {
    if (typeof crypto !== 'undefined' && crypto.base64 && crypto.base64.decode) {
        var r = crypto.base64.decode(String(s).replace(/[\s\r\n]/g, ''));
        if (r) return r;
    }
    var bytes = b64decodeToBytes(s);
    // 正确解码 UTF-8（支持中文等多字节字符）
    var str = '', i = 0;
    while (i < bytes.length) {
        var b = bytes[i++];
        if (b < 0x80) { str += String.fromCharCode(b); }
        else if (b < 0xE0) { str += String.fromCharCode(((b & 0x1F) << 6) | (bytes[i++] & 0x3F)); }
        else if (b < 0xF0) { str += String.fromCharCode(((b & 0x0F) << 12) | ((bytes[i++] & 0x3F) << 6) | (bytes[i++] & 0x3F)); }
        else { var cp = ((b & 0x07) << 18) | ((bytes[i++] & 0x3F) << 12) | ((bytes[i++] & 0x3F) << 6) | (bytes[i++] & 0x3F); cp -= 0x10000; str += String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)); }
    }
    return str;
}

function b64encodeStr(str) {
    if (typeof crypto !== 'undefined' && crypto.base64 && crypto.base64.encode) {
        return crypto.base64.encode(str);
    }
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var bytes = [];
    for (var i = 0; i < str.length; i++) {
        var c = str.charCodeAt(i);
        if (c < 0x80) bytes.push(c);
        else if (c < 0x800) bytes.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
        else if (c < 0xD800 || c >= 0xE000) bytes.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
        else { i++; var c2 = str.charCodeAt(i); var cp = 0x10000 + (((c & 0x3FF) << 10) | (c2 & 0x3FF)); bytes.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)); }
    }
    var result = '';
    for (i = 0; i < bytes.length; i += 3) {
        var b1 = bytes[i] || 0, b2 = bytes[i+1] || 0, b3 = bytes[i+2] || 0;
        result += chars[b1 >> 2];
        result += chars[((b1 & 3) << 4) | (b2 >> 4)];
        result += (i + 1 < bytes.length) ? chars[((b2 & 15) << 2) | (b3 >> 6)] : '=';
        result += (i + 2 < bytes.length) ? chars[b3 & 63] : '=';
    }
    return result;
}

// ===================== UUID v4（带纯JS回退） =====================
function genUuid() {
    if (typeof crypto !== 'undefined' && crypto.uuid) {
        return crypto.uuid();
    }
    return 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0;
        var v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// ===================== Hex 转 Base64（带纯JS回退） =====================
function hexToB64(hexStr) {
    if (typeof crypto !== 'undefined' && crypto.hex && crypto.hex.toBase64) {
        return crypto.hex.toBase64(hexStr);
    }
    hexStr = hexStr.replace(/[\s\r\n]/g, '');
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var result = '';
    for (var i = 0; i < hexStr.length; i += 6) {
        var b1 = parseInt(hexStr.substr(i, 2) || '00', 16);
        var b2 = parseInt(hexStr.substr(i+2, 2) || '00', 16);
        var b3 = parseInt(hexStr.substr(i+4, 2) || '00', 16);
        result += chars[b1 >> 2];
        result += chars[((b1 & 3) << 4) | (b2 >> 4)];
        if (i + 4 <= hexStr.length) result += chars[((b2 & 15) << 2) | (b3 >> 6)];
        else result += '=';
        if (i + 6 <= hexStr.length) result += chars[b3 & 63];
        else result += '=';
    }
    return result;
}

// ===================== SHA-256 纯JS实现 =====================
var SHA256 = (function() {
    var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    function rotr(n, x) { return (x >>> n) | (x << (32 - n)); }
    function add(x, y) {
        var l = (x & 0xFFFF) + (y & 0xFFFF);
        var m = (x >>> 16) + (y >>> 16) + (l >>> 16);
        return ((m & 0xFFFF) << 16) | (l & 0xFFFF);
    }
    function strToBytes(s) {
        var b = [];
        for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            if (c < 0x80) b.push(c);
            else if (c < 0x800) b.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
            else if (c < 0xD800 || c >= 0xE000) b.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
            else { i++; var c2 = s.charCodeAt(i); var cp = 0x10000 + (((c & 0x3FF) << 10) | (c2 & 0x3FF)); b.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)); }
        }
        return b;
    }
    function hash(str) {
        var bytes = strToBytes(str);
        var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
        var len = bytes.length;
        bytes.push(0x80);
        while (bytes.length % 64 !== 56) bytes.push(0);
        var bitLen = len * 8;
        bytes.push(0, 0, 0, 0);
        bytes.push((bitLen >>> 24) & 0xFF, (bitLen >>> 16) & 0xFF, (bitLen >>> 8) & 0xFF, bitLen & 0xFF);
        for (var off = 0; off < bytes.length; off += 64) {
            var W = [];
            for (var j = 0; j < 16; j++) W[j] = (bytes[off+j*4]<<24)|(bytes[off+j*4+1]<<16)|(bytes[off+j*4+2]<<8)|bytes[off+j*4+3];
            for (j = 16; j < 64; j++) {
                var s0 = rotr(7, W[j-15]) ^ rotr(18, W[j-15]) ^ (W[j-15] >>> 3);
                var s1 = rotr(17, W[j-2]) ^ rotr(19, W[j-2]) ^ (W[j-2] >>> 10);
                W[j] = add(add(add(W[j-16], s0), W[j-7]), s1);
            }
            var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
            for (j = 0; j < 64; j++) {
                var S1 = rotr(6, e) ^ rotr(11, e) ^ rotr(25, e);
                var ch = (e & f) ^ ((~e) & g);
                var t1 = add(add(add(add(h, S1), ch), K[j]), W[j]);
                var S0 = rotr(2, a) ^ rotr(13, a) ^ rotr(22, a);
                var maj = (a & b) ^ (a & c) ^ (b & c);
                var t2 = add(S0, maj);
                h=g; g=f; f=e; e=add(d, t1); d=c; c=b; b=a; a=add(t1, t2);
            }
            H[0]=add(H[0],a); H[1]=add(H[1],b); H[2]=add(H[2],c); H[3]=add(H[3],d);
            H[4]=add(H[4],e); H[5]=add(H[5],f); H[6]=add(H[6],g); H[7]=add(H[7],h);
        }
        var hex = '';
        for (i = 0; i < 8; i++) { var h = H[i] >>> 0; var s = h.toString(16); while (s.length < 8) s = '0' + s; hex += s; }
        return hex;
    }
    return { hash: hash };
})();

// ===================== AES-128-ECB（纯JS实现，可选原生加速） =====================
var AES_ECB = (function() {
    var SBOX = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16];
    var INV_SBOX = [0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d];
    var RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];
    function mul(a,b){var r=0;for(var i=0;i<8;i++){if(b&1)r^=a;var hi=a&0x80;a=(a<<1)&0xff;if(hi)a^=0x1b;b>>=1;}return r;}
    function keyExpansion(key){var nk=key.length/4,nb=4,nr=nk+6,w=[];for(var i=0;i<nk;i++)w[i]=(key[i*4]<<24)|(key[i*4+1]<<16)|(key[i*4+2]<<8)|key[i*4+3];for(i=nk;i<nb*(nr+1);i++){var t=w[i-1];if(i%nk===0){t=((SBOX[(t>>16)&0xff]<<24)|(SBOX[(t>>8)&0xff]<<16)|(SBOX[t&0xff]<<8)|SBOX[(t>>24)&0xff])^(RCON[i/nk-1]<<24);}else if(nk>6&&i%nk===4){t=(SBOX[(t>>24)&0xff]<<24)|(SBOX[(t>>16)&0xff]<<16)|(SBOX[(t>>8)&0xff]<<8)|SBOX[t&0xff];}w[i]=w[i-nk]^t;}return w;}
    function addRoundKey(s,w,r){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]^=w[r*4+i]>>(24-8*j)&0xff;}
    function invSubBytes(s){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]=INV_SBOX[s[i][j]];}
    function invShiftRows(s){var t;t=s[0][1];s[0][1]=s[3][1];s[3][1]=s[2][1];s[2][1]=s[1][1];s[1][1]=t;t=s[0][2];s[0][2]=s[2][2];s[2][2]=t;t=s[1][2];s[1][2]=s[3][2];s[3][2]=t;t=s[0][3];s[0][3]=s[1][3];s[1][3]=s[2][3];s[2][3]=s[3][3];s[3][3]=t;}
    function invMixColumns(s){for(var i=0;i<4;i++){var a=s[i][0],b=s[i][1],c=s[i][2],d=s[i][3];s[i][0]=mul(a,14)^mul(b,11)^mul(c,13)^mul(d,9);s[i][1]=mul(a,9)^mul(b,14)^mul(c,11)^mul(d,13);s[i][2]=mul(a,13)^mul(b,9)^mul(c,14)^mul(d,11);s[i][3]=mul(a,11)^mul(b,13)^mul(c,9)^mul(d,14);}}
    function bytesToState(b){var s=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];for(var i=0;i<16;i++)s[Math.floor(i/4)][i%4]=b[i];return s;}
    function stateToBytes(s){var b=[];for(var i=0;i<4;i++)for(var j=0;j<4;j++)b.push(s[i][j]);return b;}
    function decryptBlock(input,w){var s=bytesToState(input),nr=w.length/4-1;addRoundKey(s,w,nr);for(var r=nr-1;r>0;r--){invShiftRows(s);invSubBytes(s);addRoundKey(s,w,r);invMixColumns(s);}invShiftRows(s);invSubBytes(s);addRoundKey(s,w,0);return stateToBytes(s);}
    function unpad(pt){var pad=pt[pt.length-1];if(pad<1||pad>16)pad=0;return pt.slice(0,pt.length-pad);}
    function bytesToUtf8(pt){var str='',ui=0;while(ui<pt.length){var b=pt[ui++];if(b<0x80){str+=String.fromCharCode(b);}else if(b<0xe0){str+=String.fromCharCode(((b&0x1f)<<6)|(pt[ui++]&0x3f));}else if(b<0xf0){str+=String.fromCharCode(((b&0x0f)<<12)|((pt[ui++]&0x3f)<<6)|(pt[ui++]&0x3f));}else{var cp=((b&0x07)<<18)|((pt[ui++]&0x3f)<<12)|((pt[ui++]&0x3f)<<6)|(pt[ui++]&0x3f);cp-=0x10000;str+=String.fromCharCode(0xd800+(cp>>10),0xdc00+(cp&0x3ff));}}return str;}

    function decryptECB(encDataB64, keyB64) {
        if (typeof crypto !== 'undefined' && crypto.AES && crypto.AES.decryptECB) {
            return crypto.AES.decryptECB(encDataB64, keyB64);
        }
        var keyBytes = b64decodeToBytes(keyB64);
        var w = keyExpansion(keyBytes);
        var ct = b64decodeToBytes(encDataB64);
        var pt = [];
        for (var i = 0; i < ct.length; i += 16) {
            pt = pt.concat(decryptBlock(ct.slice(i, i + 16), w));
        }
        return bytesToUtf8(unpad(pt));
    }

    return { decryptECB: decryptECB };
})();

// ===================== RSA-SHA256 PKCS#1 v1.5 签名（原生桥接 + BigInt纯JS回退） =====================
function checkRsaSignAvailable() {
    return (typeof crypto !== 'undefined' && crypto.RSA && typeof crypto.RSA.sign === 'function');
}

function rsaSign(message, privateKeyB64) {
    // 优先使用原生桥接（vbox 3.1073+）
    if (checkRsaSignAvailable()) {
        return crypto.RSA.sign(message, privateKeyB64);
    }
    // 纯JS BigInt回退
    return rsaSignJs(message, privateKeyB64);
}

function rsaSignJs(message, privateKeyB64) {
    try {
        if (typeof BigInt === 'undefined') {
            print('>>> wawa RSA: BigInt不支持，无法签名');
            return '';
        }

        // 1. 解码私钥 base64 → DER 字节数组
        var keyBytes = b64decodeToBytes(privateKeyB64);

        // 2. 解析 PKCS#8 DER 结构，提取 modulus(n) 和 privateExponent(d)
        function readDerLen(bytes, offset) {
            var b = bytes[offset];
            if (b < 0x80) return { len: b, next: offset + 1 };
            var numBytes = b & 0x7f;
            var len = 0;
            for (var i = 0; i < numBytes; i++) len = (len << 8) | bytes[offset + 1 + i];
            return { len: len, next: offset + 1 + numBytes };
        }
        function skipElement(bytes, offset) {
            var li = readDerLen(bytes, offset + 1);
            return li.next + li.len;
        }
        function readIntHex(bytes, offset) {
            var li = readDerLen(bytes, offset + 1);
            var start = li.next, end = li.next + li.len;
            while (start < end && bytes[start] === 0) start++;
            var hex = '';
            for (var i = start; i < end; i++) {
                var b = bytes[i].toString(16);
                hex += b.length < 2 ? '0' + b : b;
            }
            return { hex: hex || '0', next: end };
        }

        var pos = 0;
        // 进入外层 SEQUENCE (PKCS#8 PrivateKeyInfo)
        var li = readDerLen(keyBytes, 1);
        pos = li.next;
        // 跳过 version INTEGER
        pos = skipElement(keyBytes, pos);
        // 跳过 AlgorithmIdentifier SEQUENCE
        pos = skipElement(keyBytes, pos);
        // 进入 OCTET STRING (包含 RSAPrivateKey)
        li = readDerLen(keyBytes, pos + 1);
        pos = li.next;
        // 进入 RSAPrivateKey SEQUENCE
        li = readDerLen(keyBytes, pos + 1);
        pos = li.next;
        // 跳过 version
        pos = skipElement(keyBytes, pos);
        // 读取 modulus n
        var nR = readIntHex(keyBytes, pos);
        var nHex = nR.hex;
        pos = nR.next;
        // 跳过 publicExponent e
        pos = skipElement(keyBytes, pos);
        // 读取 privateExponent d
        var dR = readIntHex(keyBytes, pos);
        var dHex = dR.hex;

        print('>>> wawa RSA: n=' + nHex.length + 'hex d=' + dHex.length + 'hex');

        // 3. 转换为 BigInt
        var n = BigInt('0x' + nHex);
        var d = BigInt('0x' + dHex);

        // 4. SHA-256 哈希
        var hashHex = SHA256.hash(message);

        // 5. PKCS#1 v1.5 填充
        var keyLen = Math.ceil(nHex.length / 2);
        var digestInfoHex = '3031300d060960864801650304020105000420' + hashHex;
        var tLen = digestInfoHex.length / 2;
        var psLen = keyLen - tLen - 3;
        if (psLen < 8) { print('>>> wawa RSA: 密钥太短'); return ''; }

        var emHex = '0001';
        for (var i = 0; i < psLen; i++) emHex += 'ff';
        emHex += '00' + digestInfoHex;
        while (emHex.length < keyLen * 2) emHex = '0' + emHex;

        // 6. 模幂运算: signature = EM^d mod n
        var em = BigInt('0x' + emHex);
        var result = BigInt(1);
        var base = em % n;
        var exp = d;
        var two = BigInt(2);
        var zero = BigInt(0);
        var one = BigInt(1);

        while (exp > zero) {
            if (exp % two === one) {
                result = (result * base) % n;
            }
            exp = exp / two;
            base = (base * base) % n;
        }

        // 7. 转换为 base64
        var sigHex = result.toString(16);
        while (sigHex.length < keyLen * 2) sigHex = '0' + sigHex;
        print('>>> wawa RSA: 签名完成 sigLen=' + sigHex.length + 'hex');
        return hexToB64(sigHex);
    } catch (e) {
        print('>>> wawa rsaSignJs ERROR: ' + e);
        return '';
    }
}

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        // ====== 常量 ======
        var AES_KEY = 'Crm4FXWkk5JItpYirFDpqg==';
        var GITEE_TOKEN = '74d5879931b9774be10dee3d8c51008e';
        var GITEE_CONF_KEY = '3bbf7348cf314874883a18d6b6fcf67a';
        var GITEE_CONF_URL = 'https://gitee.com/api/v5/repos/aycapp/openapi/contents/wawaconf.txt?access_token=' + GITEE_TOKEN;
        var UA = 'okhttp/4.9.3';

        // ====== 配置缓存 ======
        var CONF = null;
        var HOST = '';
        var APP_KEY = '';
        var RSA_KEY = '';

        // ====== 工具函数 ======
        function getTimestamp() {
            return String(Date.now());
        }

        function md5(text) {
            if (typeof crypto !== 'undefined' && crypto.MD5) {
                return crypto.MD5(text);
            }
            print('>>> wawa WARNING: crypto.MD5 not available');
            return '';
        }

        // 解密 Gitee 配置
        function decryptConfig(giteeContentB64) {
            try {
                var hexStr = b64decodeStr(giteeContentB64);
                var rawB64 = hexToB64(hexStr);
                var decrypted = AES_ECB.decryptECB(rawB64, AES_KEY);
                return decrypted;
            } catch (e) {
                print('>>> wawa decryptConfig ERROR: ' + e);
                return '';
            }
        }

        // 从 Gitee 获取基础配置（带缓存）
        function getBaseInfo() {
            if (CONF) return CONF;
            try {
                var uid = genUuid();
                var t = getTimestamp();
                var sign = md5('appKey=' + GITEE_CONF_KEY + '&uid=' + uid + '&time=' + t);

                var resp = req(GITEE_CONF_URL, {
                    method: 'GET',
                    headers: {
                        'User-Agent': UA,
                        'uid': uid,
                        'time': t,
                        'sign': sign
                    }
                });

                if (!resp) { print('>>> wawa getBaseInfo: null resp'); return null; }
                var content = resp.content || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                if (!content || content.length < 10) {
                    print('>>> wawa getBaseInfo: empty resp, status=' + (resp.status || 0));
                    return null;
                }

                var data = JSON.parse(content);
                if (!data || !data.content) {
                    print('>>> wawa getBaseInfo: no content field');
                    return null;
                }

                var decrypted = decryptConfig(data.content);
                if (!decrypted) {
                    print('>>> wawa getBaseInfo: decrypt failed');
                    return null;
                }

                CONF = JSON.parse(decrypted);
                HOST = CONF.baseUrl || '';
                APP_KEY = CONF.appKey || '';
                RSA_KEY = CONF.appSecret || '';
                print('>>> wawa getBaseInfo OK: HOST=' + HOST + ' APP_KEY=' + APP_KEY);
                print('>>> wawa RSA: native=' + checkRsaSignAvailable() + ' BigInt=' + (typeof BigInt !== 'undefined'));
                return CONF;
            } catch (e) {
                print('>>> wawa getBaseInfo ERROR: ' + e);
                return null;
            }
        }

        // 生成请求头（RSA-SHA256签名，原生优先+JS回退）
        function getHeaders() {
            getBaseInfo();
            var uid = genUuid();
            var t = getTimestamp();
            var message = 'appKey=' + APP_KEY + '&time=' + t + '&uid=' + uid;

            var sign = rsaSign(message, RSA_KEY);
            if (!sign) {
                print('>>> wawa ERROR: RSA签名失败');
            }

            return {
                'User-Agent': UA,
                'uid': uid,
                'time': t,
                'appKey': APP_KEY,
                'sign': sign
            };
        }

        // 通用 API 请求
        function fetchApi(path) {
            getBaseInfo();
            if (!HOST) { print('>>> wawa fetchApi: no HOST'); return null; }
            try {
                var url = HOST + path;
                var resp = req(url, { method: 'GET', headers: getHeaders() });
                if (!resp) { print('>>> wawa fetchApi null: ' + path); return null; }
                var content = resp.content || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                if (!content || content.length < 2) {
                    print('>>> wawa fetchApi empty: ' + path + ' status=' + (resp.status || 0));
                    return null;
                }
                return JSON.parse(content);
            } catch (e) {
                print('>>> wawa fetchApi ERROR (' + path + '): ' + e);
                return null;
            }
        }

        function b64encodeJson(obj) {
            return b64encodeStr(JSON.stringify(obj));
        }

        // 标准视频条目映射（关键：确保所有字段为String类型，否则Swift JSONDecoder解码失败）
        function vod(item) {
            if (!item) return { vod_id: '', vod_name: '', vod_pic: '', vod_remarks: '' };
            return {
                vod_id: String(item.vod_id || ''),
                vod_name: String(item.vod_name || ''),
                vod_pic: String(item.vod_pic || ''),
                vod_remarks: String(item.vod_remarks || '')
            };
        }

        // ====== 蜘蛛 API ======
        return {
            init: function(config) {
                print('>>> wawa init: nativeRSA=' + checkRsaSignAvailable() + ' BigInt=' + (typeof BigInt !== 'undefined'));
                return true;
            },

            homeContent: function(filter) {
                var result = { class: [], list: [], filters: {} };

                var typeData = fetchApi('/api.php/zjv6.vod/types');
                if (!typeData || !typeData.data || !typeData.data.list) {
                    print('>>> wawa homeContent: no type data');
                    return result;
                }

                var dy = { class: '类型', area: '地区', lang: '语言', year: '年份', letter: '字母', by: '排序' };
                var sl = { '按更新': 'time', '按播放': 'hits', '按评分': 'score', '按收藏': 'store_num' };

                for (var i = 0; i < typeData.data.list.length; i++) {
                    var item = typeData.data.list[i];
                    var tid = String(item.type_id);
                    result.class.push({ type_id: String(item.type_id), type_name: String(item.type_name || '') });

                    result.filters[tid] = [];
                    var ext = item.type_extend || {};
                    ext.by = '按更新,按播放,按评分,按收藏';

                    for (var key in dy) {
                        if (ext[key]) {
                            var values = ext[key].split(',');
                            var valueArray = [];
                            for (var j = 0; j < values.length; j++) {
                                if (!values[j]) continue;
                                valueArray.push({
                                    n: values[j],
                                    v: (key === 'by' ? (sl[values[j]] || values[j]) : values[j])
                                });
                            }
                            if (valueArray.length > 0) {
                                result.filters[tid].push({ key: key, name: dy[key], value: valueArray });
                            }
                        }
                    }
                }

                var homeData = fetchApi('/api.php/zjv6.vod/vodPhbAll');
                if (homeData && homeData.data && homeData.data.list &&
                    homeData.data.list[0] && homeData.data.list[0].vod_list) {
                    var rawList = homeData.data.list[0].vod_list;
                    for (var k = 0; k < rawList.length; k++) result.list.push(vod(rawList[k]));
                    print('>>> wawa homeContent: list=' + result.list.length);
                }

                result.page = 1;
                result.pagecount = 1;
                result.limit = 20;
                result.total = 20;
                return result;
            },

            homeVideoContent: function() {
                return { list: [] };
            },

            categoryContent: function(tid, pg, extend) {
                var page = parseInt(pg) || 1;
                var ext = {};
                if (extend) {
                    try {
                        if (typeof extend === 'string' && extend !== '{}') {
                            ext = JSON.parse(extend);
                        } else if (typeof extend === 'object') {
                            ext = extend;
                        }
                    } catch (e) {}
                }

                var params = 'type=' + tid + '&page=' + page + '&limit=12';
                params += '&class=' + (ext.class || '');
                params += '&area=' + (ext.area || '');
                params += '&lang=' + (ext.lang || '');
                params += '&year=' + (ext.year || '');
                params += '&letter=' + (ext.letter || '');
                params += '&by=' + (ext.by || '');

                var data = fetchApi('/api.php/zjv6.vod?' + params);
                var rawList = (data && data.data && data.data.list) ? data.data.list : [];

                var vlist = [];
                for (var j = 0; j < rawList.length; j++) vlist.push(vod(rawList[j]));

                return {
                    list: vlist,
                    page: page,
                    pagecount: 999,
                    limit: 12,
                    total: 9999
                };
            },

            detailContent: function(ids) {
                var vodId = String(ids).split(',')[0].trim();
                print('>>> wawa detailContent: vodId=' + vodId);

                var data = fetchApi('/api.php/zjv6.vod/detail?vod_id=' + vodId + '&rel_limit=10');
                if (!data || !data.data) {
                    print('>>> wawa detailContent: no data');
                    return { list: [] };
                }

                var item = data.data;
                var playFrom = [];
                var playUrls = [];

                if (item.vod_play_list && item.vod_play_list.length > 0) {
                    for (var i = 0; i < item.vod_play_list.length; i++) {
                        var list = item.vod_play_list[i];
                        var show = (list.player_info && list.player_info.show) ? list.player_info.show : ('线路' + (i + 1));
                        playFrom.push(show);

                        var urls = [];
                        if (list.urls && list.urls.length > 0) {
                            for (var j = 0; j < list.urls.length; j++) {
                                var u = list.urls[j];
                                if (list.player_info) {
                                    if (list.player_info.parse2) u.parse = list.player_info.parse2;
                                    if (list.player_info.ag) u.ag = list.player_info.ag;
                                }
                                urls.push(u.name + '$' + b64encodeJson(u));
                            }
                        }
                        playUrls.push(urls.join('#'));
                    }
                }

                return {
                    list: [{
                        vod_id: String(item.vod_id || ''),
                        vod_name: String(item.vod_name || ''),
                        vod_pic: String(item.vod_pic || ''),
                        vod_remarks: String(item.vod_remarks || ''),
                        vod_year: String(item.vod_year || ''),
                        vod_area: String(item.vod_area || ''),
                        vod_content: String(item.vod_content || ''),
                        vod_play_from: playFrom.join('$$$'),
                        vod_play_url: playUrls.join('$$$')
                    }]
                };
            },

            searchContent: function(key, quick, pg) {
                var keyword = String(key || '');
                // 兼容iOS引擎2参数调用: searchContent(keyword, pg)
                if (pg === undefined && quick !== undefined) {
                    pg = quick;
                }
                var pageNum = parseInt(pg) || 1;

                var data = fetchApi('/api.php/zjv6.vod?page=' + pageNum + '&limit=20&wd=' + encodeURIComponent(keyword));
                var rawList = (data && data.data && data.data.list) ? data.data.list : [];

                var vlist = [];
                for (var j = 0; j < rawList.length; j++) vlist.push(vod(rawList[j]));

                return {
                    list: vlist,
                    page: pageNum,
                    pagecount: 9999,
                    limit: 20,
                    total: 999999
                };
            },

            playerContent: function(vodId, flag, url) {
                try {
                    print('>>> wawa playerContent: url=' + (url || '').substring(0, 60));
                    var b64Data = String(url || '');
                    if (b64Data.indexOf('$') >= 0) {
                        b64Data = b64Data.substring(b64Data.indexOf('$') + 1);
                    }

                    var jsonStr = b64decodeStr(b64Data);
                    var playData = JSON.parse(jsonStr);
                    var playUrl = playData.url || '';
                    var parseUrl = playData.parse || '';
                    var ua = playData.ag || 'dart:io';

                    print('>>> wawa playerContent: playUrl=' + (playUrl || '').substring(0, 80));

                    // 判断是否是直接可播放的媒体链接
                    var isDirect = /\.(m3u8|mp4|flv|mkv|avi|ts|mov)(\?|$|#)/i.test(playUrl);

                    if (isDirect) {
                        // 直链：直接播放
                        print('>>> wawa playerContent: 直链播放');
                        return {
                            parse: 0,
                            playUrl: '',
                            url: playUrl,
                            header: { 'User-Agent': ua }
                        };
                    } else if (parseUrl) {
                        // 非直链但有解析器：构造解析URL，交给vbox二次解析
                        var jxUrl = parseUrl + encodeURIComponent(playUrl);
                        print('>>> wawa playerContent: 解析器播放 jxUrl=' + jxUrl.substring(0, 80));
                        return {
                            parse: 1,
                            playUrl: jxUrl,
                            url: playUrl,
                            header: { 'User-Agent': ua }
                        };
                    } else {
                        // 非直链无解析器：交给vbox通用解析
                        print('>>> wawa playerContent: 通用解析');
                        return {
                            parse: 1,
                            playUrl: '',
                            url: playUrl,
                            header: { 'User-Agent': ua }
                        };
                    }
                } catch (e) {
                    print('>>> wawa playerContent ERROR: ' + e);
                    return { parse: 0, playUrl: '', url: '' };
                }
            }
        };
    }
};
