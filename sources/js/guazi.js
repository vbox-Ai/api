/*
 * 瓜子影视 JS 蜘蛛 v1.9.2 关梯版
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 硬编码 token / 内联加密(RSA+AES+MD5) / 无需翻墙
 */

// ===================== Base64 工具 =====================
function b64decode(s) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    s = s.replace(/[\s\r\n]/g, '');
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
        var b1 = bytes[i], b2 = bytes[i+1], b3 = bytes[i+2];
        result += chars[b1 >> 2];
        result += chars[((b1 & 3) << 4) | (b2 >> 4 || 0)];
        result += (i + 1 < bytes.length) ? chars[((b2 & 15) << 2) | (b3 >> 6 || 0)] : '=';
        result += (i + 2 < bytes.length) ? chars[b3 & 63] : '=';
    }
    return result;
}

// ===================== MD5 =====================
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
    function s2b(s){var b=[],m=0xFF;for(var i=0;i<s.length*8;i+=8)b[i>>5]|=(s.charCodeAt(i/8)&m)<<(i%32);return b;}
    function b2h(b){var h='0123456789abcdef',s='';for(var i=0;i<b.length*4;i++)s+=h.charAt((b[i>>2]>>((i%4)*8+4))&0xF)+h.charAt((b[i>>2]>>((i%4)*8))&0xF);return s;}
    return function(s){return b2h(binl(s2b(s),s.length*8));};
})();

// ===================== AES-128-CBC =====================
var AES = (function() {
    var SBOX = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16];
    var INV_SBOX = [0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d];
    var RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];

    function xtime(a) { return ((a<<1)^(a>>7)&0xFF)&0xFF; }
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

    function addRoundKey(s, w, r) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]^=w[r*4+j]>>(24-8*i)&0xFF; }
    function subBytes(s) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]=SBOX[s[i][j]]; }
    function invSubBytes(s) { for(var i=0;i<4;i++) for(var j=0;j<4;j++) s[i][j]=INV_SBOX[s[i][j]]; }
    function shiftRows(s) { var t; t=s[1][0];s[1][0]=s[1][1];s[1][1]=s[1][2];s[1][2]=s[1][3];s[1][3]=t; t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t; t=s[3][3];s[3][3]=s[3][2];s[3][2]=s[3][1];s[3][1]=s[3][0];s[3][0]=t; }
    function invShiftRows(s) { var t; t=s[1][3];s[1][3]=s[1][2];s[1][2]=s[1][1];s[1][1]=s[1][0];s[1][0]=t; t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t; t=s[3][0];s[3][0]=s[3][1];s[3][1]=s[3][2];s[3][2]=s[3][3];s[3][3]=t; }
    function mixColumns(s) { for(var i=0;i<4;i++){var a=s[i][0],b=s[i][1],c=s[i][2],d=s[i][3];s[i][0]=mul(a,2)^mul(b,3)^c^d;s[i][1]=a^mul(b,2)^mul(c,3)^d;s[i][2]=a^b^mul(c,2)^mul(d,3);s[i][3]=mul(a,3)^b^c^mul(d,2);} }
    function invMixColumns(s) { for(var i=0;i<4;i++){var a=s[i][0],b=s[i][1],c=s[i][2],d=s[i][3];s[i][0]=mul(a,14)^mul(b,11)^mul(c,13)^mul(d,9);s[i][1]=mul(a,9)^mul(b,14)^mul(c,11)^mul(d,13);s[i][2]=mul(a,13)^mul(b,9)^mul(c,14)^mul(d,11);s[i][3]=mul(a,11)^mul(b,13)^mul(c,9)^mul(d,14);} }

    function bytesToState(b) { var s=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]]; for(var i=0;i<16;i++) s[i%4][Math.floor(i/4)]=b[i]; return s; }
    function stateToBytes(s) { var b=[]; for(var i=0;i<4;i++) for(var j=0;j<4;j++) b.push(s[i][j]); return b; }

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
            var key=[], iv=[];
            for(var i=0;i<keyStr.length&&i<16;i++) key.push(keyStr.charCodeAt(i));
            for(i=0;i<16-key.length;i++) key.push(0);
            for(i=0;i<ivStr.length&&i<16;i++) iv.push(ivStr.charCodeAt(i));
            for(i=0;i<16-iv.length;i++) iv.push(0);
            var w = keyExpansion(key);
            var pt=[]; for(i=0;i<plaintext.length;i++) pt.push(plaintext.charCodeAt(i));
            while(pt.length%16!==0) pt.push(16-pt.length%16);
            var ct=[];
            for(i=0;i<pt.length;i+=16){var block=xorBlocks(pt.slice(i,i+16),i===0?iv:ct.slice(i-16,i));ct=ct.concat(encryptBlock(block,w));}
            var hex='';for(i=0;i<ct.length;i++) hex+=('0'+ct[i].toString(16)).slice(-2);
            return hex.toUpperCase();
        },
        decrypt: function(hexStr, keyStr, ivStr) {
            var key=[], iv=[];
            for(var i=0;i<keyStr.length&&i<16;i++) key.push(keyStr.charCodeAt(i));
            for(i=0;i<16-key.length;i++) key.push(0);
            for(i=0;i<ivStr.length&&i<16;i++) iv.push(ivStr.charCodeAt(i));
            for(i=0;i<16-iv.length;i++) iv.push(0);
            var w = keyExpansion(key);
            var ct=[]; for(i=0;i<hexStr.length;i+=2) ct.push(parseInt(hexStr.substr(i,2),16));
            var pt=[];
            for(i=0;i<ct.length;i+=16){var dec=decryptBlock(ct.slice(i,i+16),w);var xored=xorBlocks(dec,i===0?iv:ct.slice(i-16,i));pt=pt.concat(xored);}
            var pad=pt[pt.length-1]; if(pad<1||pad>16) pad=0;
            pt=pt.slice(0,pt.length-pad);
            var str=''; for(i=0;i<pt.length;i++) str+=String.fromCharCode(pt[i]);
            return str;
        }
    };
})();

// ===================== RSA PKCS1v1_5 解密 (BigInt) =====================
function rsaDecrypt(encryptedB64, privateKeyPem) {
    // 解析 PEM
    var b64 = privateKeyPem.replace(/-----BEGIN[\s\S]*?-----/g, '').replace(/-----END[\s\S]*?-----/g, '').replace(/\s/g, '');
    var der = b64decode(b64);

    // ASN.1 DER 解析辅助
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

    // 读取 INTEGER → BigInt
    function readInt(buf, offset) {
        var info = readTag(buf, offset);
        var val = 0n;
        for (var i = 0; i < info.length; i++) {
            val = (val << 8n) | BigInt(buf[info.offset + i]);
        }
        return { value: val, end: info.offset + info.length };
    }

    // 解析 PKCS#8: SEQUENCE { version, algId, OCTET STRING { SEQUENCE { version, n, e, d, ... } } }
    var pos = 0;
    var outer = readTag(der, pos); pos = outer.offset; // 外层 SEQUENCE
    var ver = readInt(der, pos); pos = ver.end; // version INTEGER (0)
    // 跳过 AlgorithmIdentifier SEQUENCE
    var algTag = readTag(der, pos);
    pos = algTag.offset + algTag.length;
    // 读取 OCTET STRING (内含 RSAPrivateKey)
    var octInfo = readTag(der, pos); pos = octInfo.offset;
    // 解析内层 RSAPrivateKey SEQUENCE
    var inner = readTag(der, pos); pos = inner.offset;
    var innerVer = readInt(der, pos); pos = innerVer.end; // version
    var nInt = readInt(der, pos); pos = nInt.end; // n (modulus)
    var eInt = readInt(der, pos); pos = eInt.end; // e (publicExponent)
    var dInt = readInt(der, pos); pos = dInt.end; // d (privateExponent)

    var n = nInt.value;
    var d = dInt.value;

    // Base64 解码密文
    var encBytes = b64decode(encryptedB64);
    // 转为 BigInt
    var c = 0n;
    for (var i = 0; i < encBytes.length; i++) {
        c = (c << 8n) | BigInt(encBytes[i]);
    }

    // RSA 解密: m = c^d mod n
    var m = modPow(c, d, n);

    // 转回字节数组
    var decBytes = bigIntToBytes(m, 128);

    // PKCS1 v1.5 去填充: 0x00 0x02 [non-zero padding] 0x00 [message]
    if (decBytes[0] !== 0x00 || decBytes[1] !== 0x02) return '';
    var idx = 2;
    while (idx < decBytes.length && decBytes[idx] !== 0x00) idx++;
    idx++; // 跳过 0x00 分隔符
    var result = [];
    for (var j = idx; j < decBytes.length; j++) result.push(decBytes[j]);

    // 转为字符串
    var str = '';
    for (var k = 0; k < result.length; k++) str += String.fromCharCode(result[k]);
    return str;
}

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

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://api.w32z7vtd.com';
        var TOKEN = '1be86e8e18a9fa18b2b8d5432699dad0.ac008ed650fd087bfbecf2fda9d82e9835253ef24843e6b18fcd128b10763497bcf9d53e959f5377cde038c20ccf9d17f604c9b8bb6e61041def86729b2fc7408bd241e23c213ac57f0226ee656e2bb0a583ae0e4f3bf6c6ab6c490c9a6f0d8cdfd366aacf5d83193671a8f77cd1af1ff2e9145de92ec43ec87cf4bdc563f6e919fe32861b0e93b118ec37d8035fbb3c.59dd05c5d9a8ae726528783128218f15fe6f2c0c8145eddab112b374fcfe3d79';
        var AES_KEY = 'mvXBSW7ekreItNsT';
        var AES_IV = '2U3IrJL8szAKp0Fj';
        var SIGN_KEYS = 'Qmxi5ciWXbQzkr7o+SUNiUuQxQEf8/AVyUWY4T/BGhcXBIUz4nOyHBGf9A4KbM0iKF3yp9M7WAY0rrs5PzdTAOB45plcS2zZ0wUibcXuGJ29VVGRWKGwE9zu2vLwhfgjTaaDpXo4rby+7GxXTktzJmxvneOUdYeHi+PZsThlvPI=';
        var RSA_PK = '-----BEGIN PRIVATE KEY-----\nMIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1\nozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU\n1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK\nZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7\nHetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW\nV9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI\nDblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34\nsaTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM\niMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM\nWBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8\njUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ\nK7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b\nL3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa\nt5lYKfpe8k83ZA==\n-----END PRIVATE KEY-----';

        var HEADER = {
            'Cache-Control': 'no-cache',
            'Version': '2406025',
            'PackageName': 'com.uf076bf0c246.qe439f0d5e.m8aaf56b725a.ifeb647346f',
            'Ver': '1.9.2',
            'Referer': HOST,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'okhttp/3.12.0'
        };

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

        // 核心 API 请求
        function apiRequest(data, path) {
            try {
                print('>>> apiRequest start: ' + path);

                // AES 加密请求数据
                var jsonData = JSON.stringify(data);
                print('>>> apiRequest data: ' + jsonData.substring(0, 80));
                var requestKey = AES.encrypt(jsonData, AES_KEY, AES_IV);
                if (!requestKey) { print('>>> AES encrypt failed'); return null; }
                print('>>> requestKey: ' + requestKey.substring(0, 40) + '...');

                // 生成签名
                var t = Math.floor(Date.now() / 1000).toString();
                var signStr = 'token_id=,token=' + TOKEN + ',phone_type=1,request_key=' + requestKey + ',app_id=1,time=' + t + ',keys=' + SIGN_KEYS + '*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br';
                var signature = md5(signStr);
                print('>>> sign=' + signature.substring(0, 20) + '..., t=' + t);

                // 构建请求体
                var postBody = {
                    'token': TOKEN,
                    'token_id': '',
                    'phone_type': '1',
                    'time': t,
                    'phone_model': 'xiaomi-22021211rc',
                    'keys': SIGN_KEYS,
                    'request_key': requestKey,
                    'signature': signature,
                    'app_id': '1',
                    'ad_version': '1'
                };

                // 发送请求 — req() 读 opts.data（不是body），返回 {data: content, ...} 对象
                var bodyStr = encodeParams(postBody);
                var url = HOST + path;
                print('>>> req url=' + url + ', bodyLen=' + bodyStr.length);

                var respObj = req(url, {
                    method: 'POST',
                    headers: HEADER,
                    data: bodyStr
                });

                if (!respObj) { print('>>> req returned null'); return null; }
                print('>>> req resp type=' + typeof respObj);

                var respStr = '';
                if (typeof respObj === 'string') {
                    respStr = respObj;
                } else if (respObj.data) {
                    respStr = respObj.data;
                } else if (respObj.content) {
                    respStr = respObj.content;
                } else {
                    print('>>> req resp has no data/content');
                    return null;
                }
                print('>>> respStr len=' + respStr.length + ', head=' + respStr.substring(0, 60));

                var respJson = (typeof respStr === 'object') ? respStr : JSON.parse(respStr);
                if (!respJson || !respJson.data) {
                    print('>>> respJson has no .data');
                    return null;
                }
                print('>>> respJson.code=' + (respJson.code || 'null'));

                var dataResp = respJson.data;

                // RSA 解密响应密钥
                var bodykiJson = rsaDecrypt(dataResp.keys, RSA_PK);
                if (!bodykiJson) { print('>>> rsaDecrypt failed'); return null; }
                var bodyki = JSON.parse(bodykiJson);
                print('>>> bodyki.key=' + bodyki.key + ', iv=' + bodyki.iv);

                // AES 解密响应数据
                var decrypted = AES.decrypt(dataResp.response_key, bodyki.key, bodyki.iv);
                if (!decrypted) { print('>>> AES decrypt failed'); return null; }
                print('>>> decrypted len=' + decrypted.length + ', head=' + decrypted.substring(0, 60));

                var result = JSON.parse(decrypted);
                print('>>> apiRequest OK: ' + path);
                return result;
            } catch (e) {
                print('>>> apiRequest ERROR (' + path + '): ' + e);
                return null;
            }
        }

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

                var data = apiRequest(body, '/App/IndexList/indexList');
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
                        token_id: '1649412',
                        vod_id: vodId,
                        mobile_time: t,
                        token: TOKEN
                    };
                    var qdata = apiRequest(body1, '/App/IndexPlay/playInfo');

                    // 获取播放列表
                    var body2 = {
                        vurl_cloud_id: '2',
                        vod_d_id: vodId
                    };
                    var jdata = apiRequest(body2, '/App/Resource/Vurl/show');

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
                        vod_play_from: '拾光请你看瓜子',
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
                    print('detailContent error: ' + e);
                    return { list: [] };
                }
            },

            searchContent: function(keyword, pg) {
                pg = pg || 1;
                try {
                    var body = {
                        keywords: keyword,
                        order_val: '1',
                        page: String(pg)
                    };

                    var data = apiRequest(body, '/App/Index/findMoreVod');
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
                } catch (e) {
                    print('searchContent error: ' + e);
                    return { list: [] };
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
                        var data = apiRequest(params, '/App/Resource/VurlDetail/showOne');
                        if (data && data.url) {
                            return {
                                parse: 0,
                                playUrl: '',
                                url: data.url,
                                header: JSON.stringify({ 'User-Agent': 'Lavf/57.83.100' })
                            };
                        }
                    }

                    return { parse: 0, playUrl: '', url: '' };
                } catch (e) {
                    print('playerContent error: ' + e);
                    return { parse: 0, playUrl: '', url: '' };
                }
            }
        };
    }
};