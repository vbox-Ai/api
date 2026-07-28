/*
 * 人人视频 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://api.rrmj.plus (Referer: https://m.yichengwlkj.com)
 * 特点: HMAC-SHA256 签名 + AES-128-ECB 接口解密 + AES-128-CBC 播放地址解密 + 302重定向
 * 无需登录，token 为空，使用固定 app_secret/aliId 签名
 */

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

// ===================== HMAC-SHA256 =====================
var HMAC_SHA256 = (function() {
    function rotr(n, x) { return (x >>> n) | (x << (32 - n)); }
    function safeAdd(x, y) {
        var lsw = (x & 0xFFFF) + (y & 0xFFFF);
        var msw = (x >> 16) + (y >> 16) + (lsw >> 16);
        return (msw << 16) | (lsw & 0xFFFF);
    }
    var K = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];
    function strToBytes(str) {
        var bytes = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) {
                bytes.push(c);
            } else if (c < 0x800) {
                bytes.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
            } else if (c < 0xD800 || c >= 0xE000) {
                bytes.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
            } else {
                i++;
                var c2 = str.charCodeAt(i);
                var cp = 0x10000 + (((c & 0x3FF) << 10) | (c2 & 0x3FF));
                bytes.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F));
            }
        }
        return bytes;
    }
    function bytesToWords(bytes) {
        var words = [];
        for (var i = 0; i < bytes.length; i++) {
            words[i >> 2] |= bytes[i] << (24 - (i % 4) * 8);
        }
        return words;
    }
    function wordsToBytes(words) {
        var bytes = [];
        for (var i = 0; i < words.length * 4; i++) {
            bytes.push((words[i >> 2] >> (24 - (i % 4) * 8)) & 0xFF);
        }
        return bytes;
    }
    function sha256Block(W, H) {
        for (var i = 16; i < 64; i++) {
            var s0 = rotr(7, W[i-15]) ^ rotr(18, W[i-15]) ^ (W[i-15] >>> 3);
            var s1 = rotr(17, W[i-2]) ^ rotr(19, W[i-2]) ^ (W[i-2] >>> 10);
            W[i] = safeAdd(safeAdd(safeAdd(W[i-16], s0), W[i-7]), s1);
        }
        var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
        for (var j = 0; j < 64; j++) {
            var S1 = rotr(6, e) ^ rotr(11, e) ^ rotr(25, e);
            var ch = (e & f) ^ ((~e) & g);
            var t1 = safeAdd(safeAdd(safeAdd(safeAdd(h, S1), ch), K[j]), W[j]);
            var S0 = rotr(2, a) ^ rotr(13, a) ^ rotr(22, a);
            var maj = (a & b) ^ (a & c) ^ (b & c);
            var t2 = safeAdd(S0, maj);
            h=g; g=f; f=e; e=safeAdd(d, t1); d=c; c=b; b=a; a=safeAdd(t1, t2);
        }
        H[0]=safeAdd(H[0],a); H[1]=safeAdd(H[1],b); H[2]=safeAdd(H[2],c); H[3]=safeAdd(H[3],d);
        H[4]=safeAdd(H[4],e); H[5]=safeAdd(H[5],f); H[6]=safeAdd(H[6],g); H[7]=safeAdd(H[7],h);
    }
    function sha256(bytes) {
        var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
        var len = bytes.length;
        bytes.push(0x80);
        while (bytes.length % 64 !== 56) bytes.push(0);
        var bits = [];
        for (var i = 0; i < 8; i++) bits.push((len * 8) >>> (56 - i * 8) & 0xFF);
        bytes = bytes.concat(bits);
        for (var off = 0; off < bytes.length; off += 64) {
            var W = [];
            for (var j = 0; j < 16; j++) {
                W[j] = (bytes[off+j*4]<<24)|(bytes[off+j*4+1]<<16)|(bytes[off+j*4+2]<<8)|bytes[off+j*4+3];
            }
            sha256Block(W, H);
        }
        return wordsToBytes(H);
    }
    return function(key, message) {
        var keyBytes = strToBytes(key);
        if (keyBytes.length > 64) keyBytes = sha256(keyBytes.slice());
        while (keyBytes.length < 64) keyBytes.push(0);
        var oKeyPad = [], iKeyPad = [];
        for (var i = 0; i < 64; i++) {
            oKeyPad.push(keyBytes[i] ^ 0x5c);
            iKeyPad.push(keyBytes[i] ^ 0x36);
        }
        var msgBytes = strToBytes(message);
        var inner = sha256(iKeyPad.concat(msgBytes));
        var outer = sha256(oKeyPad.concat(inner));
        return b64encode(outer);
    };
})();

// ===================== HMAC-SHA256 修正版（覆盖上方实现） =====================
HMAC_SHA256 = (function() {
    function utf8Bytes(str) {
        var out = [];
        str = String(str);
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) out.push(c);
            else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
            else if (c < 0xd800 || c >= 0xe000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
            else {
                i++;
                var c2 = str.charCodeAt(i);
                var cp = 0x10000 + (((c & 0x3ff) << 10) | (c2 & 0x3ff));
                out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f));
            }
        }
        return out;
    }
    function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }
    function add() {
        var r = 0;
        for (var i = 0; i < arguments.length; i++) r = (r + arguments[i]) >>> 0;
        return r;
    }
    var K = [
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ];
    function sha256(bytes) {
        bytes = bytes.slice();
        var bitLen = bytes.length * 8;
        bytes.push(0x80);
        while ((bytes.length % 64) !== 56) bytes.push(0);
        var high = Math.floor(bitLen / 0x100000000);
        var low = bitLen >>> 0;
        for (var i = 3; i >= 0; i--) bytes.push((high >>> (i * 8)) & 0xff);
        for (i = 3; i >= 0; i--) bytes.push((low >>> (i * 8)) & 0xff);
        var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
        var W = new Array(64);
        for (var off = 0; off < bytes.length; off += 64) {
            for (i = 0; i < 16; i++) W[i] = ((bytes[off+i*4] << 24) | (bytes[off+i*4+1] << 16) | (bytes[off+i*4+2] << 8) | bytes[off+i*4+3]) >>> 0;
            for (i = 16; i < 64; i++) {
                var s0 = (rotr(W[i-15], 7) ^ rotr(W[i-15], 18) ^ (W[i-15] >>> 3)) >>> 0;
                var s1 = (rotr(W[i-2], 17) ^ rotr(W[i-2], 19) ^ (W[i-2] >>> 10)) >>> 0;
                W[i] = add(W[i-16], s0, W[i-7], s1);
            }
            var a=H[0], b=H[1], c=H[2], d=H[3], e=H[4], f=H[5], g=H[6], h=H[7];
            for (i = 0; i < 64; i++) {
                var S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
                var ch = ((e & f) ^ ((~e) & g)) >>> 0;
                var temp1 = add(h, S1, ch, K[i], W[i]);
                var S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
                var maj = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
                var temp2 = add(S0, maj);
                h=g; g=f; f=e; e=add(d, temp1); d=c; c=b; b=a; a=add(temp1, temp2);
            }
            H[0]=add(H[0],a); H[1]=add(H[1],b); H[2]=add(H[2],c); H[3]=add(H[3],d);
            H[4]=add(H[4],e); H[5]=add(H[5],f); H[6]=add(H[6],g); H[7]=add(H[7],h);
        }
        var out = [];
        for (i = 0; i < H.length; i++) out.push((H[i]>>>24)&255, (H[i]>>>16)&255, (H[i]>>>8)&255, H[i]&255);
        return out;
    }
    return function(key, message) {
        var kb = utf8Bytes(key);
        if (kb.length > 64) kb = sha256(kb);
        while (kb.length < 64) kb.push(0);
        var ipad = [], opad = [];
        for (var i = 0; i < 64; i++) { ipad[i] = kb[i] ^ 0x36; opad[i] = kb[i] ^ 0x5c; }
        return b64encode(sha256(opad.concat(sha256(ipad.concat(utf8Bytes(message))))));
    };
})();

// ===================== AES-128 (ECB + CBC) =====================
var AES = (function() {
    var SBOX = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16];
    var INV_SBOX = [0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d];
    var RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];
    function mul(a,b){var r=0;for(var i=0;i<8;i++){if(b&1)r^=a;var hi=a&0x80;a=(a<<1)&0xFF;if(hi)a^=0x1b;b>>=1;}return r;}
    function keyExpansion(key){var nk=key.length/4,nb=4,nr=nk+6,w=[];for(var i=0;i<nk;i++)w[i]=(key[i*4]<<24)|(key[i*4+1]<<16)|(key[i*4+2]<<8)|key[i*4+3];for(i=nk;i<nb*(nr+1);i++){var t=w[i-1];if(i%nk===0){t=((SBOX[(t>>16)&0xFF]<<24)|(SBOX[(t>>8)&0xFF]<<16)|(SBOX[t&0xFF]<<8)|SBOX[(t>>24)&0xFF])^(RCON[i/nk-1]<<24);}else if(nk>6&&i%nk===4){t=(SBOX[(t>>24)&0xFF]<<24)|(SBOX[(t>>16)&0xFF]<<16)|(SBOX[(t>>8)&0xFF]<<8)|SBOX[t&0xFF];}w[i]=w[i-nk]^t;}return w;}
    function addRoundKey(s,w,r){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]^=w[r*4+j]>>>(24-8*i)&0xFF;}
    function invSubBytes(s){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]=INV_SBOX[s[i][j]];}
    function invShiftRows(s){var t;t=s[1][3];s[1][3]=s[1][2];s[1][2]=s[1][1];s[1][1]=s[1][0];s[1][0]=t;t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t;t=s[3][0];s[3][0]=s[3][1];s[3][1]=s[3][2];s[3][2]=s[3][3];s[3][3]=t;}
    function invMixColumns(s){for(var i=0;i<4;i++){var a=s[i][0],b=s[i][1],c=s[i][2],d=s[i][3];s[i][0]=mul(a,14)^mul(b,11)^mul(c,13)^mul(d,9);s[i][1]=mul(a,9)^mul(b,14)^mul(c,11)^mul(d,13);s[i][2]=mul(a,13)^mul(b,9)^mul(c,14)^mul(d,11);s[i][3]=mul(a,11)^mul(b,13)^mul(c,9)^mul(d,14);}}
    function bytesToState(b){var s=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];for(var i=0;i<16;i++)s[i%4][Math.floor(i/4)]=b[i];return s;}
    function stateToBytes(s){var b=[];for(var j=0;j<4;j++)for(var i=0;i<4;i++)b.push(s[i][j]);return b;}
    function decryptBlock(input,w){var s=bytesToState(input),nr=w.length/4-1;addRoundKey(s,w,nr);for(var r=nr-1;r>0;r--){invShiftRows(s);invSubBytes(s);addRoundKey(s,w,r);invMixColumns(s);}invShiftRows(s);invSubBytes(s);addRoundKey(s,w,0);return stateToBytes(s);}
    function xorBlocks(a,b){var r=[];for(var i=0;i<a.length;i++)r[i]=a[i]^b[i];return r;}
    function bytesToUtf8(bytes) {
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
    function strKeyToBytes(keyStr) {
        var bytes = [];
        for (var i = 0; i < keyStr.length && i < 16; i++) bytes.push(keyStr.charCodeAt(i));
        while (bytes.length < 16) bytes.push(0);
        return bytes;
    }
    // AES-128-ECB 解密 (Base64 输入 → UTF-8 字符串输出)
    function decryptECB(b64Data, keyStr) {
        var key = strKeyToBytes(keyStr);
        var w = keyExpansion(key);
        var ct = b64decode(b64Data);
        var pt = [];
        for (var i = 0; i < ct.length; i += 16) {
            pt = pt.concat(decryptBlock(ct.slice(i, i + 16), w));
        }
        var pad = pt[pt.length - 1];
        if (pad < 1 || pad > 16) pad = 0;
        pt = pt.slice(0, pt.length - pad);
        return bytesToUtf8(pt);
    }
    // AES-128-CBC 解密 (Base64 输入 → UTF-8 字符串输出)
    function decryptCBC(b64Data, keyStr, ivStr) {
        var key = strKeyToBytes(keyStr);
        var iv = strKeyToBytes(ivStr);
        var w = keyExpansion(key);
        var ct = b64decode(b64Data);
        var pt = [];
        for (var i = 0; i < ct.length; i += 16) {
            var dec = decryptBlock(ct.slice(i, i + 16), w);
            var xored = xorBlocks(dec, i === 0 ? iv : ct.slice(i - 16, i));
            pt = pt.concat(xored);
        }
        var pad = pt[pt.length - 1];
        if (pad < 1 || pad > 16) pad = 0;
        pt = pt.slice(0, pt.length - pad);
        return bytesToUtf8(pt);
    }
    return { decryptECB: decryptECB, decryptCBC: decryptCBC };
})();

// ===================== AES-128 修正版（覆盖上方实现） =====================
AES = (function() {
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
    function xorBlocks(a,b){var r=[];for(var i=0;i<a.length;i++)r[i]=a[i]^b[i];return r;}
    function strKeyToBytes(keyStr){var bytes=[];for(var i=0;i<keyStr.length&&i<16;i++)bytes.push(keyStr.charCodeAt(i));while(bytes.length<16)bytes.push(0);return bytes;}
    function bytesToUtf8(pt){var str='',ui=0;while(ui<pt.length){var b=pt[ui++];if(b<0x80){str+=String.fromCharCode(b);}else if(b<0xe0){str+=String.fromCharCode(((b&0x1f)<<6)|(pt[ui++]&0x3f));}else if(b<0xf0){str+=String.fromCharCode(((b&0x0f)<<12)|((pt[ui++]&0x3f)<<6)|(pt[ui++]&0x3f));}else{var cp=((b&0x07)<<18)|((pt[ui++]&0x3f)<<12)|((pt[ui++]&0x3f)<<6)|(pt[ui++]&0x3f);cp-=0x10000;str+=String.fromCharCode(0xd800+(cp>>10),0xdc00+(cp&0x3ff));}}return str;}
    function unpad(pt){var pad=pt[pt.length-1];if(pad<1||pad>16)pad=0;return pt.slice(0,pt.length-pad);}
    function decryptECB(b64Data,keyStr){var w=keyExpansion(strKeyToBytes(keyStr));var ct=b64decode(b64Data);var pt=[];for(var i=0;i<ct.length;i+=16)pt=pt.concat(decryptBlock(ct.slice(i,i+16),w));return bytesToUtf8(unpad(pt));}
    function decryptCBC(b64Data,keyStr,ivStr){var key=strKeyToBytes(keyStr),iv=strKeyToBytes(ivStr),w=keyExpansion(key),ct=b64decode(b64Data),pt=[];for(var i=0;i<ct.length;i+=16){var dec=decryptBlock(ct.slice(i,i+16),w);pt=pt.concat(xorBlocks(dec,i===0?iv:ct.slice(i-16,i)));}return bytesToUtf8(unpad(pt));}
    return { decryptECB: decryptECB, decryptCBC: decryptCBC };
})();

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        var XURL = 'https://api.rrmj.plus';
        var XURL1 = 'https://m.yichengwlkj.com';
        var KY_ID = 'BA21A0F5-7C57-41BA-8665-B7164A131832';
        var APP_SECRET = 'ES513W0B1CsdUrR13Qk5EgDAKPeeKZY';
        var AES_KEY_ECB = '3b744389882a4067';
        var CBC_IV = 'b1da7878016e4e2b';
        var HEADERX = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
        };

        function getTimestamp() {
            return String(Date.now());
        }

        function buildStringToSign(method, urlPath, aliId, ct, cv, t, params) {
            var parts = [method, 'aliId:' + aliId, 'ct:' + ct, 'cv:' + cv, 't:' + t];
            if (params) {
                var sortedKeys = Object.keys(params).sort();
                var queryParts = [];
                for (var i = 0; i < sortedKeys.length; i++) {
                    queryParts.push(sortedKeys[i] + '=' + params[sortedKeys[i]]);
                }
                var queryString = queryParts.join('&');
                if (queryString) {
                    parts.push(urlPath + '?' + queryString);
                } else {
                    parts.push(urlPath);
                }
            } else {
                parts.push(urlPath);
            }
            return parts.join('\n');
        }

        function calculateSign(stringToSign) {
            return HMAC_SHA256(APP_SECRET, stringToSign);
        }

        function createHeaders(urlPath, params) {
            var t = getTimestamp();
            var stringToSign = buildStringToSign('GET', urlPath, KY_ID, 'web_pc', '1.0.0', t, params);
            var sign = calculateSign(stringToSign);
            return {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Origin': XURL1,
                'Pragma': 'no-cache',
                'Referer': XURL1,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
                'aliId': KY_ID,
                'clientType': 'web_pc',
                'clientVersion': '1.0.0',
                'ct': 'web_pc',
                'cv': '1.0.0',
                'deviceId': KY_ID,
                't': t,
                'token': '',
                'uet': '9',
                'umid': KY_ID,
                'x-ca-sign': sign
            };
        }

        function decryptResponse(respText) {
            try {
                return JSON.parse(AES.decryptECB(respText, AES_KEY_ECB));
            } catch (e) {
                print('>>> renren decryptResponse ERROR: ' + e);
                return null;
            }
        }

        function doGet(urlPath, params) {
            try {
                var url = XURL + urlPath;
                var queryString = params ? buildQueryString(params) : '';
                if (queryString) url += '?' + queryString;
                var headers = createHeaders(urlPath, params);
                var resp = req(url, { method: 'GET', headers: headers });
                if (!resp) { print('>>> renren doGet null: ' + urlPath); return null; }
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                return decryptResponse(content);
            } catch (e) {
                print('>>> renren doGet ERROR (' + urlPath + '): ' + e);
                return null;
            }
        }

        function doPost(urlPath, params) {
            try {
                var url = XURL + urlPath;
                var headers = createHeaders(urlPath, null);
                headers['Content-Type'] = 'application/json';
                var body = JSON.stringify(params);
                var resp = req(url, { method: 'POST', headers: headers, data: body });
                if (!resp) { print('>>> renren doPost null: ' + urlPath); return null; }
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                return decryptResponse(content);
            } catch (e) {
                print('>>> renren doPost ERROR (' + urlPath + '): ' + e);
                return null;
            }
        }

        function buildQueryString(params) {
            if (!params) return '';
            var keys = Object.keys(params).sort();
            var parts = [];
            for (var i = 0; i < keys.length; i++) {
                parts.push(keys[i] + '=' + params[keys[i]]);
            }
            return parts.join('&');
        }

        function getRedirectLocation(url) {
            try {
                var resp = req(url, { method: 'GET', headers: HEADERX });
                if (!resp) { print('>>> renren getRedirectLocation null: ' + url); return ''; }
                // 优先从 headers 中取 Location
                var headers = resp.headers || {};
                var loc = headers['Location'] || headers['location'] || '';
                if (loc) { print('>>> renren redirect Location: ' + loc); return loc; }
                // 如果 headers 没有 Location, 但 content 是 URL, 可能是最终地址
                var content = resp.content || '';
                if (typeof content === 'string' && content.startsWith('http')) {
                    return content;
                }
                // resp.url 可能是最终 URL (如果引擎自动跟随重定向)
                var finalUrl = resp.url || '';
                if (finalUrl && finalUrl !== url) {
                    print('>>> renren redirect finalUrl: ' + finalUrl);
                    return finalUrl;
                }
                print('>>> renren getRedirectLocation: no Location found');
                return '';
            } catch (e) {
                print('>>> renren getRedirectLocation ERROR: ' + e);
                return '';
            }
        }

        return {
            init: function(config) {
                return true;
            },

            homeContent: function(filter) {
                var result = { class: [] };
                var urlPath = '/m-station/drama/get_drama_filter';
                var data = doGet(urlPath, null);
                if (!data || !data.data) {
                    print('>>> renren homeContent: no data');
                    return result;
                }
                var filterList = data.data[1] && data.data[1].dramaFilterItemList;
                if (!filterList) {
                    print('>>> renren homeContent: no dramaFilterItemList');
                    return result;
                }
                for (var i = 0; i < filterList.length; i++) {
                    var name = filterList[i].displayName;
                    if (name === '全部') continue;
                    result.class.push({
                        type_id: filterList[i].value,
                        type_name: name
                    });
                }
                return result;
            },

            homeVideoContent: function() {
                return { list: [] };
            },

            categoryContent: function(tid, pg, filter, extend) {
                var videos = [];
                var page = parseInt(pg) || 1;
                var params = {
                    area: '',
                    sort: 'hot',
                    year: '',
                    dramaType: String(tid || 'all'),
                    plotType: '',
                    contentLabel: '',
                    page: page,
                    rows: 30
                };
                var data = doPost('/m-station/drama/drama_filter_search', params);
                if (!data || !data.data) {
                    print('>>> renren categoryContent: no data');
                    return { list: [], page: page, pagecount: 1, limit: 30, total: 0 };
                }
                var arr = data.data;
                for (var i = 0; i < arr.length; i++) {
                    videos.push({
                        vod_id: arr[i].dramaId,
                        vod_name: arr[i].title,
                        vod_pic: arr[i].coverUrl || '',
                        vod_remarks: arr[i].year || ''
                    });
                }
                return {
                    list: videos,
                    page: page,
                    pagecount: 9999,
                    limit: 30,
                    total: 999999
                };
            },

            detailContent: function(ids) {
                var did = String(ids).split(',')[0];
                var params = {
                    hsdrOpen: '0',
                    isAgeLimit: '0',
                    dramaId: did,
                    quality: 'AI4K',
                    hevcOpen: '0',
                    tria4k: '1'
                };
                var data = doGet('/m-station/drama/page', params);
                if (!data || !data.data) {
                    return { list: [] };
                }
                var d = data.data;
                var episodeList = d.episodeList;
                if (!episodeList || episodeList.length === 0) {
                    return { msg: '温馨提示!正片还未上线哦' };
                }
                var dramaInfo = d.dramaInfo || {};
                var bofang = '';
                for (var i = 0; i < episodeList.length; i++) {
                    var name = String(episodeList[i].episodeNo);
                    var eid = did + '@' + String(episodeList[i].id);
                    bofang += name + '$' + eid + '#';
                }
                bofang = bofang.replace(/#$/, '');
                return {
                    list: [{
                        vod_id: did,
                        vod_name: dramaInfo.title || '',
                        vod_pic: dramaInfo.coverUrl || '',
                        vod_remarks: dramaInfo.playStatus || '',
                        vod_year: dramaInfo.year || '',
                        vod_area: dramaInfo.area || '',
                        vod_content: dramaInfo.introduction || dramaInfo.description || '',
                        vod_play_from: '人人专线',
                        vod_play_url: bofang
                    }]
                };
            },

            searchContent: function(key, quick, pg) {
                var videos = [];
                var params = {
                    keywords: String(key || ''),
                    size: '20',
                    searchAfter: ''
                };
                var data = doGet('/search/comprehensive/precise-mixed', params);
                if (!data || !data.data || !data.data.fuzzySeasonList) {
                    print('>>> renren searchContent: no data');
                    return { list: [], page: 1, pagecount: 1, limit: 20, total: 0 };
                }
                var arr = data.data.fuzzySeasonList;
                for (var i = 0; i < arr.length; i++) {
                    videos.push({
                        vod_id: arr[i].id,
                        vod_name: arr[i].title,
                        vod_pic: arr[i].cover || '',
                        vod_remarks: arr[i].year || ''
                    });
                }
                return {
                    list: videos,
                    page: 1,
                    pagecount: 9999,
                    limit: 20,
                    total: 999999
                };
            },

            playerContent: function(vodId, flag, url) {
                try {
                    print('>>> renren playerContent 入参: vodId=' + vodId + ' flag=' + flag + ' url=' + url);
                    var playId = '';
                    if (url && String(url).indexOf('@') >= 0) playId = String(url);
                    else if (flag && String(flag).indexOf('@') >= 0) playId = String(flag);
                    else if (vodId && String(vodId).indexOf('@') >= 0) playId = String(vodId);
                    var parts = playId.split('@');
                    if (parts.length < 2) {
                        print('>>> renren playerContent FAIL: parts < 2, playId=' + playId);
                        return { parse: 0, playUrl: '', url: '' };
                    }
                    var params = {
                        dramaId: parts[0],
                        episodeSid: parts[1],
                        hevcOpen: '0',
                        hsdrOpen: '0',
                        quality: 'AI4K',
                        tria4k: '1'
                    };
                    var data = doGet('/m-station/drama/play', params);
                    if (!data || !data.data || !data.data.m3u8) {
                        print('>>> renren playerContent FAIL: no m3u8 data');
                        return { parse: 0, playUrl: '', url: '' };
                    }
                    var encUrl = data.data.m3u8.url;
                    var newSign = data.data.newSign;
                    print('>>> renren playerContent encUrl=' + (encUrl || '').substring(0, 60));
                    print('>>> renren playerContent newSign=' + (newSign || '').substring(0, 40));
                    // AES-CBC 解密播放地址
                    var keyStr = newSign.substring(4, 20);
                    var decryptedUrl = AES.decryptCBC(encUrl, keyStr, CBC_IV);
                    print('>>> renren playerContent decryptedUrl=' + (decryptedUrl || '').substring(0, 80));
                    if (!decryptedUrl) {
                        print('>>> renren playerContent FAIL: decryptedUrl empty');
                        return { parse: 0, playUrl: '', url: '' };
                    }
                    // 获取重定向地址
                    var finalUrl = getRedirectLocation(decryptedUrl);
                    if (!finalUrl) {
                        finalUrl = decryptedUrl;
                    }
                    print('>>> renren playerContent SUCCESS: finalUrl=' + (finalUrl || '').substring(0, 80));
                    return {
                        parse: 0,
                        playUrl: '',
                        url: finalUrl,
                        header: JSON.stringify(HEADERX)
                    };
                } catch (e) {
                    print('>>> renren playerContent ERROR: ' + e);
                    return { parse: 0, playUrl: '', url: '' };
                }
            }
        };
    }
};
