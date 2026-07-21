/*
 * 瓜子影视纯 JS 蜘蛛脚本
 * 运行环境: JavaScriptCore / QuickJS (iOS)
 * 依赖注入: globalThis.http(url, optionsObj) - 同步HTTP请求，options 为对象，返回 {status, content, headers}
 *
 * 加密实现 (纯 JS):
 *   - AES-CBC PKCS7 padding
 *   - RSA PKCS1v15 公钥加密 / 私钥解密 (基于 BigInteger)
 *   - MD5 哈希
 *
 * 业务逻辑 (与 Python 版完全对齐):
 *   - 5个域名轮询
 *   - 设备注册 signUp / 刷新 token refreshToken
 *   - 双层加密请求 (AES加密参数 + RSA加密AES密钥)
 *   - MD5 签名
 *   - 300秒缓存
 *   - 失败自动重试机制
 */

(function() {
'use strict';

// ============================================================
// 工具函数: Base64 编解码 (支持 UTF-8)
// ============================================================
var Base64 = (function() {
    var b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var b64lookup = {};
    for (var i = 0; i < b64chars.length; i++) {
        b64lookup[b64chars.charAt(i)] = i;
    }

    function utf8Encode(str) {
        var out = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) {
                out.push(c);
            } else if (c < 0x800) {
                out.push(0xc0 | (c >> 6));
                out.push(0x80 | (c & 0x3f));
            } else if (c < 0xd800 || c >= 0xe000) {
                out.push(0xe0 | (c >> 12));
                out.push(0x80 | ((c >> 6) & 0x3f));
                out.push(0x80 | (c & 0x3f));
            } else {
                // surrogate pair
                i++;
                var c2 = str.charCodeAt(i);
                var cp = 0x10000 + (((c & 0x3ff) << 10) | (c2 & 0x3ff));
                out.push(0xf0 | (cp >> 18));
                out.push(0x80 | ((cp >> 12) & 0x3f));
                out.push(0x80 | ((cp >> 6) & 0x3f));
                out.push(0x80 | (cp & 0x3f));
            }
        }
        return out;
    }

    function utf8Decode(bytes) {
        var out = '';
        var i = 0;
        while (i < bytes.length) {
            var b = bytes[i];
            if (b < 0x80) {
                out += String.fromCharCode(b);
                i++;
            } else if (b < 0xe0) {
                out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i+1] & 0x3f));
                i += 2;
            } else if (b < 0xf0) {
                out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i+1] & 0x3f) << 6) | (bytes[i+2] & 0x3f));
                i += 3;
            } else {
                var cp = ((b & 0x07) << 18) | ((bytes[i+1] & 0x3f) << 12) | ((bytes[i+2] & 0x3f) << 6) | (bytes[i+3] & 0x3f);
                cp -= 0x10000;
                out += String.fromCharCode(0xd800 + (cp >> 10));
                out += String.fromCharCode(0xdc00 + (cp & 0x3ff));
                i += 4;
            }
        }
        return out;
    }

    function encode(bytes) {
        // bytes 是数字数组
        var out = '';
        var len = bytes.length;
        var i = 0;
        while (i < len) {
            var b1 = bytes[i++];
            var b2 = i < len ? bytes[i++] : NaN;
            var b3 = i < len ? bytes[i++] : NaN;
            out += b64chars.charAt(b1 >> 2);
            if (isNaN(b2)) {
                out += b64chars.charAt((b1 & 3) << 4);
                out += '==';
                break;
            }
            out += b64chars.charAt(((b1 & 3) << 4) | (b2 >> 4));
            if (isNaN(b3)) {
                out += b64chars.charAt((b2 & 0xf) << 2);
                out += '=';
                break;
            }
            out += b64chars.charAt(((b2 & 0xf) << 2) | (b3 >> 6));
            out += b64chars.charAt(b3 & 0x3f);
        }
        return out;
    }

    function encodeStr(str) {
        return encode(utf8Encode(str));
    }

    function decode(str) {
        str = str.replace(/\s+/g, '').replace(/=+$/, '');
        var out = [];
        var buffer = 0;
        var bits = 0;
        for (var i = 0; i < str.length; i++) {
            var c = str.charAt(i);
            var v = b64lookup[c];
            if (v === undefined) continue;
            buffer = (buffer << 6) | v;
            bits += 6;
            if (bits >= 8) {
                bits -= 8;
                out.push((buffer >> bits) & 0xff);
            }
        }
        return out;
    }

    function decodeStr(str) {
        return utf8Decode(decode(str));
    }

    return { encode: encode, encodeStr: encodeStr, decode: decode, decodeStr: decodeStr, utf8Encode: utf8Encode, utf8Decode: utf8Decode };
})();

// ============================================================
// BigInteger (用于 RSA 运算，基于数组表示，基数 2^26)
// ============================================================
var BigInteger = (function() {
    var BASE = 1 << 26;
    var BASE_MASK = BASE - 1;
    var BASE_DIGITS = 26;

    function BigInt(val) {
        this.digits = [];
        this.sign = 0; // 0 = zero, 1 = positive, -1 = negative
        if (val === undefined || val === 0 || val === '0') {
            this.digits = [0];
            this.sign = 0;
        } else if (typeof val === 'number') {
            if (val < 0) { this.sign = -1; val = -val; } else { this.sign = 1; }
            while (val > 0) {
                this.digits.push(val & BASE_MASK);
                val = Math.floor(val / BASE);
            }
        } else if (typeof val === 'string') {
            // hex string
            this._fromHex(val);
        } else if (val instanceof BigInt) {
            this.digits = val.digits.slice();
            this.sign = val.sign;
        }
        if (this.digits.length === 0) { this.digits = [0]; this.sign = 0; }
        this._normalize();
    }

    BigInt.prototype._normalize = function() {
        while (this.digits.length > 1 && this.digits[this.digits.length - 1] === 0) {
            this.digits.pop();
        }
        if (this.digits.length === 1 && this.digits[0] === 0) {
            this.sign = 0;
        }
    };

    BigInt.prototype._fromHex = function(hex) {
        hex = hex.toLowerCase().replace(/^0x/, '').replace(/\s+/g, '');
        if (hex.charAt(0) === '-') { this.sign = -1; hex = hex.substring(1); }
        else { this.sign = 1; }
        // 从右向左，每 26 bits = 6.5 hex digits，我们用 6 hex digits = 24 bits 更简单
        // 改用 26 bits: 每 6.5 个 hex digit，所以我们逐位构建
        this.digits = [0];
        for (var i = 0; i < hex.length; i++) {
            var d = parseInt(hex.charAt(i), 16);
            // 左移 4 位
            this._shiftLeft(4);
            this.digits[0] |= d;
        }
        this._normalize();
    };

    BigInt.prototype._shiftLeft = function(bits) {
        // 整体左移 bits 位
        if (bits === 0 || this.sign === 0) return;
        var fullWords = Math.floor(bits / BASE_DIGITS);
        var remBits = bits % BASE_DIGITS;
        if (fullWords > 0) {
            for (var i = 0; i < fullWords; i++) this.digits.unshift(0);
        }
        if (remBits > 0) {
            var carry = 0;
            for (var i = 0; i < this.digits.length; i++) {
                var newCarry = (this.digits[i] >> (BASE_DIGITS - remBits)) & ((1 << remBits) - 1);
                this.digits[i] = (((this.digits[i] & BASE_MASK) << remBits) | carry) & BASE_MASK;
                carry = newCarry;
            }
            if (carry > 0) this.digits.push(carry);
        }
    };

    BigInt.prototype._shiftRight = function(bits) {
        if (bits === 0 || this.sign === 0) return;
        var fullWords = Math.floor(bits / BASE_DIGITS);
        var remBits = bits % BASE_DIGITS;
        if (fullWords > 0) {
            this.digits.splice(0, fullWords);
            if (this.digits.length === 0) { this.digits = [0]; this.sign = 0; return; }
        }
        if (remBits > 0) {
            var carry = 0;
            for (var i = this.digits.length - 1; i >= 0; i--) {
                var newCarry = this.digits[i] & ((1 << remBits) - 1);
                this.digits[i] = (this.digits[i] >> remBits) | (carry << (BASE_DIGITS - remBits));
                carry = newCarry;
            }
        }
        this._normalize();
    };

    BigInt.prototype.bitLength = function() {
        if (this.sign === 0) return 0;
        var top = this.digits[this.digits.length - 1];
        var bits = 0;
        while (top > 0) { top >>= 1; bits++; }
        return (this.digits.length - 1) * BASE_DIGITS + bits;
    };

    BigInt.prototype.testBit = function(n) {
        if (this.sign === 0) return false;
        var wordIdx = Math.floor(n / BASE_DIGITS);
        var bitIdx = n % BASE_DIGITS;
        if (wordIdx >= this.digits.length) return false;
        return ((this.digits[wordIdx] >> bitIdx) & 1) === 1;
    };

    // 比较绝对值: 1 if |this| > |other|, 0 if equal, -1 if less
    BigInt.prototype._absCompare = function(other) {
        if (this.digits.length !== other.digits.length) {
            return this.digits.length > other.digits.length ? 1 : -1;
        }
        for (var i = this.digits.length - 1; i >= 0; i--) {
            if (this.digits[i] !== other.digits[i]) {
                return this.digits[i] > other.digits[i] ? 1 : -1;
            }
        }
        return 0;
    };

    BigInt.prototype.compareTo = function(other) {
        if (!(other instanceof BigInt)) other = new BigInt(other);
        if (this.sign !== other.sign) {
            if (this.sign === 0) return -other.sign;
            if (other.sign === 0) return this.sign;
            return this.sign > other.sign ? 1 : -1;
        }
        if (this.sign === 0) return 0;
        return this.sign * this._absCompare(other);
    };

    // 加 (绝对值)
    BigInt.prototype._absAdd = function(other) {
        var result = new BigInt(0);
        result.digits = [];
        var carry = 0;
        var len = Math.max(this.digits.length, other.digits.length);
        for (var i = 0; i < len || carry > 0; i++) {
            var a = i < this.digits.length ? this.digits[i] : 0;
            var b = i < other.digits.length ? other.digits[i] : 0;
            var sum = a + b + carry;
            result.digits.push(sum & BASE_MASK);
            carry = sum >> BASE_DIGITS;
        }
        result.sign = 1;
        result._normalize();
        return result;
    };

    // 减 (绝对值, 要求 this >= other)
    BigInt.prototype._absSub = function(other) {
        var result = new BigInt(0);
        result.digits = [];
        var borrow = 0;
        for (var i = 0; i < this.digits.length; i++) {
            var a = this.digits[i] - borrow;
            var b = i < other.digits.length ? other.digits[i] : 0;
            borrow = 0;
            if (a < b) { a += BASE; borrow = 1; }
            result.digits.push(a - b);
        }
        result.sign = 1;
        result._normalize();
        return result;
    };

    BigInt.prototype.add = function(other) {
        if (!(other instanceof BigInt)) other = new BigInt(other);
        if (this.sign === 0) return new BigInt(other);
        if (other.sign === 0) return new BigInt(this);
        if (this.sign === other.sign) {
            var r = this._absAdd(other);
            r.sign = this.sign;
            return r;
        }
        var cmp = this._absCompare(other);
        if (cmp === 0) return new BigInt(0);
        if (cmp > 0) {
            var r2 = this._absSub(other);
            r2.sign = this.sign;
            return r2;
        } else {
            var r3 = other._absSub(this);
            r3.sign = other.sign;
            return r3;
        }
    };

    BigInt.prototype.subtract = function(other) {
        if (!(other instanceof BigInt)) other = new BigInt(other);
        var neg = new BigInt(other);
        neg.sign = -neg.sign;
        return this.add(neg);
    };

    BigInt.prototype.multiply = function(other) {
        if (!(other instanceof BigInt)) other = new BigInt(other);
        if (this.sign === 0 || other.sign === 0) return new BigInt(0);
        var result = new BigInt(0);
        result.digits = new Array(this.digits.length + other.digits.length).fill(0);
        for (var i = 0; i < this.digits.length; i++) {
            var carry = 0;
            var a = this.digits[i];
            for (var j = 0; j < other.digits.length || carry > 0; j++) {
                var b = j < other.digits.length ? other.digits[j] : 0;
                var prod = result.digits[i + j] + a * b + carry;
                result.digits[i + j] = prod & BASE_MASK;
                carry = Math.floor(prod / BASE);
            }
        }
        result.sign = this.sign * other.sign;
        result._normalize();
        return result;
    };

    // 除以一个小数字 (number), 返回 [quotient, remainder]
    BigInt.prototype._divSmall = function(n) {
        var remainder = 0;
        var result = new BigInt(0);
        result.digits = [];
        for (var i = this.digits.length - 1; i >= 0; i--) {
            var cur = remainder * BASE + this.digits[i];
            var q = Math.floor(cur / n);
            remainder = cur % n;
            result.digits.unshift(q);
        }
        result.sign = this.sign;
        result._normalize();
        return [result, remainder];
    };

    // 整除取模: 返回 [quotient, remainder], remainder 非负
    BigInt.prototype.divmod = function(other) {
        if (!(other instanceof BigInt)) other = new BigInt(other);
        if (other.sign === 0) throw new Error('division by zero');
        if (this.sign === 0) return [new BigInt(0), new BigInt(0)];
        if (this._absCompare(other) < 0) {
            var rem = new BigInt(this);
            if (this.sign < 0) {
                // 确保余数非负
                if (other.sign > 0) {
                    return [new BigInt(-1), other.add(rem)];
                } else {
                    var negOther = new BigInt(other); negOther.sign = -negOther.sign;
                    return [new BigInt(1), negOther.add(rem)];
                }
            }
            return [new BigInt(0), rem];
        }

        // 长除法
        var quotient = new BigInt(0);
        quotient.digits = [];
        var remainder = new BigInt(0);
        remainder.digits = [0];
        remainder.sign = 1;

        var thisAbs = new BigInt(this); thisAbs.sign = 1;
        var otherAbs = new BigInt(other); otherAbs.sign = 1;

        // 从最高位开始
        for (var i = thisAbs.digits.length - 1; i >= 0; i--) {
            // remainder = remainder * BASE + digit
            remainder._shiftLeft(BASE_DIGITS);
            remainder.digits[0] = thisAbs.digits[i];
            remainder._normalize();

            // 找到当前位的商 (0..BASE-1)
            // 用二分法
            var low = 0, high = BASE - 1;
            var qDigit = 0;
            while (low <= high) {
                var mid = (low + high) >> 1;
                var prod = otherAbs.multiply(new BigInt(mid));
                if (prod._absCompare(remainder) <= 0) {
                    qDigit = mid;
                    low = mid + 1;
                } else {
                    high = mid - 1;
                }
            }
            quotient.digits.unshift(qDigit);
            remainder = remainder.subtract(otherAbs.multiply(new BigInt(qDigit)));
        }

        quotient.sign = this.sign * other.sign;
        quotient._normalize();
        remainder.sign = 1;
        remainder._normalize();

        // 调整: 确保余数非负且小于除数
        if (this.sign < 0 && remainder.sign !== 0) {
            // 负的被除数，需要调整
            if (other.sign > 0) {
                quotient = quotient.subtract(new BigInt(1));
                remainder = otherAbs.subtract(remainder);
            } else {
                quotient = quotient.add(new BigInt(1));
                remainder = otherAbs.subtract(remainder);
            }
        }

        return [quotient, remainder];
    };

    BigInt.prototype.mod = function(other) {
        return this.divmod(other)[1];
    };

    BigInt.prototype.modPow = function(exp, mod) {
        // 蒙哥马利幂运算 (简化版: 二进制法)
        if (!(exp instanceof BigInt)) exp = new BigInt(exp);
        if (!(mod instanceof BigInt)) mod = new BigInt(mod);
        if (mod.sign === 0 || mod.sign < 0) throw new Error('invalid mod');
        if (exp.sign < 0) throw new Error('negative exponent');
        if (exp.sign === 0) return new BigInt(1).mod(mod);

        var result = new BigInt(1);
        var base = this.mod(mod);
        var e = new BigInt(exp);

        while (e.sign > 0) {
            if (e.testBit(0)) {
                result = result.multiply(base).mod(mod);
            }
            e._shiftRight(1);
            if (e.sign > 0) {
                base = base.multiply(base).mod(mod);
            }
        }
        return result;
    };

    BigInt.prototype.modInverse = function(mod) {
        // 扩展欧几里得算法
        if (!(mod instanceof BigInt)) mod = new BigInt(mod);
        var a = new BigInt(this); a.sign = 1;
        var m = new BigInt(mod); m.sign = 1;

        var old_r = a, r = m;
        var old_s = new BigInt(1), s = new BigInt(0);
        var old_t = new BigInt(0), t = new BigInt(1);

        while (r.sign !== 0) {
            var q = old_r.divmod(r)[0];
            var tmp;
            tmp = old_r.subtract(q.multiply(r)); old_r = r; r = tmp;
            tmp = old_s.subtract(q.multiply(s)); old_s = s; s = tmp;
            tmp = old_t.subtract(q.multiply(t)); old_t = t; t = tmp;
        }

        // old_r 应该是 1 (gcd)
        if (old_r._absCompare(new BigInt(1)) !== 0) {
            throw new Error('modular inverse does not exist');
        }
        return old_s.mod(m);
    };

    BigInt.prototype.toHex = function() {
        if (this.sign === 0) return '0';
        var hex = '';
        var tmp = new BigInt(this);
        tmp.sign = 1;
        while (tmp.sign > 0) {
            var dm = tmp._divSmall(16);
            hex = dm[1].toString(16) + hex;
            tmp = dm[0];
        }
        if (this.sign < 0) hex = '-' + hex;
        return hex;
    };

    // 转字节数组 (大端, 补零到指定长度字节)
    BigInt.prototype.toByteArray = function(length) {
        var hex = this.toHex();
        if (this.sign < 0) hex = hex.substring(1);
        if (hex.length % 2 !== 0) hex = '0' + hex;
        if (length && hex.length < length * 2) {
            while (hex.length < length * 2) hex = '0' + hex;
        }
        var bytes = [];
        for (var i = 0; i < hex.length; i += 2) {
            bytes.push(parseInt(hex.substring(i, i + 2), 16));
        }
        return bytes;
    };

    BigInt.fromByteArray = function(bytes) {
        var hex = '';
        for (var i = 0; i < bytes.length; i++) {
            var h = bytes[i].toString(16);
            if (h.length < 2) h = '0' + h;
            hex += h;
        }
        return new BigInt(hex);
    };

    return BigInt;
})();

// ============================================================
// MD5 哈希 (纯 JS 实现)
// ============================================================
var MD5 = (function() {
    function add32(a, b) {
        return (a + b) & 0xFFFFFFFF;
    }

    function cmn(q, a, b, x, s, t) {
        a = add32(add32(a, q), add32(x, t));
        return add32((a << s) | (a >>> (32 - s)), b);
    }

    function ff(a, b, c, d, x, s, t) {
        return cmn((b & c) | ((~b) & d), a, b, x, s, t);
    }

    function gg(a, b, c, d, x, s, t) {
        return cmn((b & d) | (c & (~d)), a, b, x, s, t);
    }

    function hh(a, b, c, d, x, s, t) {
        return cmn(b ^ c ^ d, a, b, x, s, t);
    }

    function ii(a, b, c, d, x, s, t) {
        return cmn(c ^ (b | (~d)), a, b, x, s, t);
    }

    function md5cycle(x, k) {
        var a = x[0], b = x[1], c = x[2], d = x[3];

        a = ff(a, b, c, d, k[0], 7, -680876936);
        d = ff(d, a, b, c, k[1], 12, -389564586);
        c = ff(c, d, a, b, k[2], 17,  606105819);
        b = ff(b, c, d, a, k[3], 22, -1044525330);
        a = ff(a, b, c, d, k[4], 7, -176418897);
        d = ff(d, a, b, c, k[5], 12,  1200080426);
        c = ff(c, d, a, b, k[6], 17, -1473231341);
        b = ff(b, c, d, a, k[7], 22,  -45705983);
        a = ff(a, b, c, d, k[8], 7,  1770035416);
        d = ff(d, a, b, c, k[9], 12, -1958414417);
        c = ff(c, d, a, b, k[10], 17,     -42063);
        b = ff(b, c, d, a, k[11], 22, -1990404162);
        a = ff(a, b, c, d, k[12], 7,  1804603682);
        d = ff(d, a, b, c, k[13], 12,   -40341101);
        c = ff(c, d, a, b, k[14], 17, -1502002290);
        b = ff(b, c, d, a, k[15], 22,  1236535329);

        a = gg(a, b, c, d, k[1], 5, -165796510);
        d = gg(d, a, b, c, k[6], 9, -1069501632);
        c = gg(c, d, a, b, k[11], 14,  643717713);
        b = gg(b, c, d, a, k[0], 20, -373897302);
        a = gg(a, b, c, d, k[5], 5, -701558691);
        d = gg(d, a, b, c, k[10], 9,   38016083);
        c = gg(c, d, a, b, k[15], 14, -660478335);
        b = gg(b, c, d, a, k[4], 20, -405537848);
        a = gg(a, b, c, d, k[9], 5,  568446438);
        d = gg(d, a, b, c, k[14], 9, -1019803690);
        c = gg(c, d, a, b, k[3], 14, -187363961);
        b = gg(b, c, d, a, k[8], 20, 1163531501);
        a = gg(a, b, c, d, k[13], 5, -1444681467);
        d = gg(d, a, b, c, k[2], 9,  -51403784);
        c = gg(c, d, a, b, k[7], 14, 1735328473);
        b = gg(b, c, d, a, k[12], 20, -1926607734);

        a = hh(a, b, c, d, k[5], 4,     -378558);
        d = hh(d, a, b, c, k[8], 11, -2022574463);
        c = hh(c, d, a, b, k[11], 16, 1839030562);
        b = hh(b, c, d, a, k[14], 23,  -35309556);
        a = hh(a, b, c, d, k[1], 4, -1530992060);
        d = hh(d, a, b, c, k[4], 11, 1272893353);
        c = hh(c, d, a, b, k[7], 16, -155497632);
        b = hh(b, c, d, a, k[10], 23, -1094730640);
        a = hh(a, b, c, d, k[13], 4,  681279174);
        d = hh(d, a, b, c, k[0], 11, -358537222);
        c = hh(c, d, a, b, k[3], 16, -722521979);
        b = hh(b, c, d, a, k[6], 23,   76029189);
        a = hh(a, b, c, d, k[9], 4, -640364487);
        d = hh(d, a, b, c, k[12], 11, -421815835);
        c = hh(c, d, a, b, k[15], 16,  530742520);
        b = hh(b, c, d, a, k[2], 23, -995338651);

        a = ii(a, b, c, d, k[0], 6, -198630844);
        d = ii(d, a, b, c, k[7], 10, 1126891415);
        c = ii(c, d, a, b, k[14], 15, -1416354905);
        b = ii(b, c, d, a, k[5], 21,  -57434055);
        a = ii(a, b, c, d, k[12], 6, 1700485571);
        d = ii(d, a, b, c, k[3], 10, -1894986606);
        c = ii(c, d, a, b, k[10], 15,   -1051523);
        b = ii(b, c, d, a, k[1], 21, -2054922799);
        a = ii(a, b, c, d, k[8], 6, 1873313359);
        d = ii(d, a, b, c, k[15], 10,  -30611744);
        c = ii(c, d, a, b, k[6], 15, -1560198380);
        b = ii(b, c, d, a, k[13], 21, 1309151649);
        a = ii(a, b, c, d, k[4], 6,  -145523070);
        d = ii(d, a, b, c, k[11], 10, -1120210379);
        c = ii(c, d, a, b, k[2], 15,  718787259);
        b = ii(b, c, d, a, k[9], 21, -343485551);

        x[0] = add32(a, x[0]);
        x[1] = add32(b, x[1]);
        x[2] = add32(c, x[2]);
        x[3] = add32(d, x[3]);
    }

    function md51(s) {
        var n = s.length;
        var state = [1732584193, -271733879, -1732584194, 271733878];
        var i;
        // 处理完整的 64 字节块
        for (i = 64; i <= n; i += 64) {
            var block = new Array(16);
            var base = i - 64;
            for (var j = 0; j < 16; j++) {
                var idx = base + j * 4;
                block[j] = s[idx] | (s[idx + 1] << 8) | (s[idx + 2] << 16) | (s[idx + 3] << 24);
            }
            md5cycle(state, block);
        }
        // 处理尾部
        var tail = new Array(16);
        for (var k = 0; k < 16; k++) tail[k] = 0;
        var tailStart = i - 64;
        var tailLen = n - tailStart;
        for (i = 0; i < tailLen; i++) {
            tail[i >> 2] |= s[tailStart + i] << ((i % 4) * 8);
        }
        tail[i >> 2] |= 0x80 << ((i % 4) * 8);
        if (tailLen > 55) {
            md5cycle(state, tail);
            for (var m = 0; m < 16; m++) tail[m] = 0;
        }
        // 设置长度（64位小端序）
        tail[14] = n * 8;
        tail[15] = ((n * 8) / 4294967296) | 0;
        md5cycle(state, tail);
        return state;
    }

    function toHex(digest) {
        var hex = '';
        for (var i = 0; i < 4; i++) {
            var val = digest[i];
            for (var j = 0; j < 4; j++) {
                var byte = (val >> (j * 8)) & 0xFF;
                var h = byte.toString(16);
                if (h.length < 2) h = '0' + h;
                hex += h;
            }
        }
        return hex;
    }

    function md5(str) {
        var bytes = Base64.utf8Encode(str);
        var digest = md51(bytes);
        return toHex(digest);
    }

    return { hash: md5 };
})();

// ============================================================
// AES-CBC PKCS7 (纯 JS 实现)
// ============================================================
var AES = (function() {
    // S-box
    var SBOX = [
        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
        0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
        0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
        0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
        0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
        0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
        0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
        0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
        0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
        0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
        0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
        0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
        0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
        0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
        0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
        0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
    ];

    var INV_SBOX = new Array(256);
    for (var i = 0; i < 256; i++) INV_SBOX[SBOX[i]] = i;

    // Rcon
    var RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36];

    function keyExpansion(key) {
        // key 是字节数组 (16/24/32 bytes)
        var Nk = key.length / 4;
        var Nr = Nk + 6;
        var Nb = 4;
        var w = [];
        var i, j;

        for (i = 0; i < Nk; i++) {
            w.push([key[4*i], key[4*i+1], key[4*i+2], key[4*i+3]]);
        }

        for (i = Nk; i < Nb * (Nr + 1); i++) {
            var temp = w[i-1].slice();
            if (i % Nk === 0) {
                // RotWord
                var t = temp[0];
                temp[0] = SBOX[temp[1]];
                temp[1] = SBOX[temp[2]];
                temp[2] = SBOX[temp[3]];
                temp[3] = SBOX[t];
                temp[0] ^= RCON[i / Nk];
            } else if (Nk > 6 && i % Nk === 4) {
                for (j = 0; j < 4; j++) temp[j] = SBOX[temp[j]];
            }
            var nw = [];
            for (j = 0; j < 4; j++) {
                nw.push(w[i-Nk][j] ^ temp[j]);
            }
            w.push(nw);
        }
        return w;
    }

    function addRoundKey(state, roundKeys, round) {
        for (var c = 0; c < 4; c++) {
            for (var r = 0; r < 4; r++) {
                state[r][c] ^= roundKeys[round * 4 + c][r];
            }
        }
    }

    function subBytes(state) {
        for (var r = 0; r < 4; r++) {
            for (var c = 0; c < 4; c++) {
                state[r][c] = SBOX[state[r][c]];
            }
        }
    }

    function invSubBytes(state) {
        for (var r = 0; r < 4; r++) {
            for (var c = 0; c < 4; c++) {
                state[r][c] = INV_SBOX[state[r][c]];
            }
        }
    }

    function shiftRows(state) {
        var temp;
        // row 1: shift left by 1
        temp = state[1][0];
        state[1][0] = state[1][1];
        state[1][1] = state[1][2];
        state[1][2] = state[1][3];
        state[1][3] = temp;
        // row 2: shift left by 2
        temp = state[2][0]; state[2][0] = state[2][2]; state[2][2] = temp;
        temp = state[2][1]; state[2][1] = state[2][3]; state[2][3] = temp;
        // row 3: shift left by 3 (same as right by 1)
        temp = state[3][3];
        state[3][3] = state[3][2];
        state[3][2] = state[3][1];
        state[3][1] = state[3][0];
        state[3][0] = temp;
    }

    function invShiftRows(state) {
        var temp;
        // row 1: shift right by 1
        temp = state[1][3];
        state[1][3] = state[1][2];
        state[1][2] = state[1][1];
        state[1][1] = state[1][0];
        state[1][0] = temp;
        // row 2: shift right by 2
        temp = state[2][0]; state[2][0] = state[2][2]; state[2][2] = temp;
        temp = state[2][1]; state[2][1] = state[2][3]; state[2][3] = temp;
        // row 3: shift right by 3 (same as left by 1)
        temp = state[3][0];
        state[3][0] = state[3][1];
        state[3][1] = state[3][2];
        state[3][2] = state[3][3];
        state[3][3] = temp;
    }

    function xtime(a) {
        return (a << 1) ^ ((a & 0x80) ? 0x1b : 0x00);
    }

    function mul(a, b) {
        var result = 0;
        for (var i = 0; i < 8; i++) {
            if (b & 1) result ^= a;
            var hi = a & 0x80;
            a = (a << 1) & 0xff;
            if (hi) a ^= 0x1b;
            b >>= 1;
        }
        return result & 0xff;
    }

    function mixColumns(state) {
        for (var c = 0; c < 4; c++) {
            var s0 = state[0][c], s1 = state[1][c], s2 = state[2][c], s3 = state[3][c];
            state[0][c] = (xtime(s0) ^ xtime(s1) ^ s1 ^ s2 ^ s3) & 0xff;
            state[1][c] = (s0 ^ xtime(s1) ^ xtime(s2) ^ s2 ^ s3) & 0xff;
            state[2][c] = (s0 ^ s1 ^ xtime(s2) ^ xtime(s3) ^ s3) & 0xff;
            state[3][c] = (xtime(s0) ^ s0 ^ s1 ^ s2 ^ xtime(s3)) & 0xff;
        }
    }

    function invMixColumns(state) {
        for (var c = 0; c < 4; c++) {
            var s0 = state[0][c], s1 = state[1][c], s2 = state[2][c], s3 = state[3][c];
            state[0][c] = (mul(s0, 0x0e) ^ mul(s1, 0x0b) ^ mul(s2, 0x0d) ^ mul(s3, 0x09)) & 0xff;
            state[1][c] = (mul(s0, 0x09) ^ mul(s1, 0x0e) ^ mul(s2, 0x0b) ^ mul(s3, 0x0d)) & 0xff;
            state[2][c] = (mul(s0, 0x0d) ^ mul(s1, 0x09) ^ mul(s2, 0x0e) ^ mul(s3, 0x0b)) & 0xff;
            state[3][c] = (mul(s0, 0x0b) ^ mul(s1, 0x0d) ^ mul(s2, 0x09) ^ mul(s3, 0x0e)) & 0xff;
        }
    }

    function encryptBlock(input, roundKeys, Nr) {
        var state = [[],[],[],[]];
        for (var c = 0; c < 4; c++) {
            for (var r = 0; r < 4; r++) {
                state[r][c] = input[c * 4 + r];
            }
        }
        addRoundKey(state, roundKeys, 0);
        for (var round = 1; round < Nr; round++) {
            subBytes(state);
            shiftRows(state);
            mixColumns(state);
            addRoundKey(state, roundKeys, round);
        }
        subBytes(state);
        shiftRows(state);
        addRoundKey(state, roundKeys, Nr);

        var output = new Array(16);
        for (c = 0; c < 4; c++) {
            for (r = 0; r < 4; r++) {
                output[c * 4 + r] = state[r][c];
            }
        }
        return output;
    }

    function decryptBlock(input, roundKeys, Nr) {
        var state = [[],[],[],[]];
        for (var c = 0; c < 4; c++) {
            for (var r = 0; r < 4; r++) {
                state[r][c] = input[c * 4 + r];
            }
        }
        addRoundKey(state, roundKeys, Nr);
        for (var round = Nr - 1; round >= 1; round--) {
            invShiftRows(state);
            invSubBytes(state);
            addRoundKey(state, roundKeys, round);
            invMixColumns(state);
        }
        invShiftRows(state);
        invSubBytes(state);
        addRoundKey(state, roundKeys, 0);

        var output = new Array(16);
        for (c = 0; c < 4; c++) {
            for (r = 0; r < 4; r++) {
                output[c * 4 + r] = state[r][c];
            }
        }
        return output;
    }

    function pkcs7Pad(data, blockSize) {
        var padLen = blockSize - (data.length % blockSize);
        var result = data.slice();
        for (var i = 0; i < padLen; i++) {
            result.push(padLen);
        }
        return result;
    }

    function pkcs7Unpad(data) {
        var padLen = data[data.length - 1];
        if (padLen <= 0 || padLen > data.length) return data;
        return data.slice(0, data.length - padLen);
    }

    function xorBytes(a, b) {
        var result = new Array(16);
        for (var i = 0; i < 16; i++) {
            result[i] = a[i] ^ b[i];
        }
        return result;
    }

    function encryptCBC(plaintextBytes, keyBytes, ivBytes) {
        var roundKeys = keyExpansion(keyBytes);
        var Nr = roundKeys.length / 4 - 1;
        var padded = pkcs7Pad(plaintextBytes, 16);
        var ciphertext = [];
        var prev = ivBytes.slice();

        for (var i = 0; i < padded.length; i += 16) {
            var block = padded.slice(i, i + 16);
            var xored = xorBytes(block, prev);
            var encrypted = encryptBlock(xored, roundKeys, Nr);
            ciphertext = ciphertext.concat(encrypted);
            prev = encrypted;
        }
        return ciphertext;
    }

    function decryptCBC(ciphertextBytes, keyBytes, ivBytes) {
        var roundKeys = keyExpansion(keyBytes);
        var Nr = roundKeys.length / 4 - 1;
        var plaintext = [];
        var prev = ivBytes.slice();

        for (var i = 0; i < ciphertextBytes.length; i += 16) {
            var block = ciphertextBytes.slice(i, i + 16);
            var decrypted = decryptBlock(block, roundKeys, Nr);
            var xored = xorBytes(decrypted, prev);
            plaintext = plaintext.concat(xored);
            prev = block;
        }
        return pkcs7Unpad(plaintext);
    }

    function bytesToHex(bytes) {
        var hex = '';
        for (var i = 0; i < bytes.length; i++) {
            var h = bytes[i].toString(16);
            if (h.length < 2) h = '0' + h;
            hex += h;
        }
        return hex;
    }

    function hexToBytes(hex) {
        var bytes = [];
        for (var i = 0; i < hex.length; i += 2) {
            bytes.push(parseInt(hex.substring(i, i + 2), 16));
        }
        return bytes;
    }

    return {
        encryptCBC: encryptCBC,
        decryptCBC: decryptCBC,
        bytesToHex: bytesToHex,
        hexToBytes: hexToBytes
    };
})();

// ============================================================
// RSA PKCS1v15 (纯 JS 实现, 基于 BigInteger)
// ============================================================
var RSA = (function() {
    // PKCS1v1.5 加密填充
    // 结构: 00 02 [随机非零字节] 00 [明文]
    function pkcs1Pad(messageBytes, keySizeBytes) {
        var mLen = messageBytes.length;
        if (mLen > keySizeBytes - 11) {
            throw new Error('Message too long for PKCS1v1.5 encryption');
        }
        var padded = new Array(keySizeBytes);
        padded[0] = 0x00;
        padded[1] = 0x02;
        // 填充随机非零字节
        var padLen = keySizeBytes - mLen - 3;
        for (var i = 0; i < padLen; i++) {
            padded[2 + i] = Math.floor(Math.random() * 255) + 1; // 1-255
        }
        padded[2 + padLen] = 0x00;
        for (var j = 0; j < mLen; j++) {
            padded[3 + padLen + j] = messageBytes[j];
        }
        return padded;
    }

    // PKCS1v1.5 解密去填充
    function pkcs1Unpad(paddedBytes) {
        if (paddedBytes[0] !== 0x00 || paddedBytes[1] !== 0x02) {
            // 尝试容错
        }
        // 找 00 分隔符
        var idx = -1;
        for (var i = 2; i < paddedBytes.length; i++) {
            if (paddedBytes[i] === 0x00) {
                idx = i;
                break;
            }
        }
        if (idx === -1) return [];
        return paddedBytes.slice(idx + 1);
    }

    // 公钥加密
    function encryptPublic(plaintextBytes, n, e) {
        var nBig = new BigInteger(n);
        var eBig = new BigInteger(e);
        var keySizeBytes = Math.ceil(nBig.bitLength() / 8);
        var padded = pkcs1Pad(plaintextBytes, keySizeBytes);
        var m = BigInteger.fromByteArray(padded);
        var c = m.modPow(eBig, nBig);
        return c.toByteArray(keySizeBytes);
    }

    // 私钥解密 (使用 CRT 参数加速)
    function decryptPrivate(ciphertextBytes, n, d, p, q, dp, dq, qinv) {
        var c = BigInteger.fromByteArray(ciphertextBytes);
        var pBig = new BigInteger(p);
        var qBig = new BigInteger(q);
        var dpBig = new BigInteger(dp);
        var dqBig = new BigInteger(dq);
        var qinvBig = new BigInteger(qinv);

        // 中国剩余定理
        var m1 = c.modPow(dpBig, pBig);
        var m2 = c.modPow(dqBig, qBig);
        var h = m1.subtract(m2).multiply(qinvBig).mod(pBig);
        var m = m2.add(h.multiply(qBig));

        var keySizeBytes = Math.ceil(new BigInteger(n).bitLength() / 8);
        var padded = m.toByteArray(keySizeBytes);
        return pkcs1Unpad(padded);
    }

    return {
        encryptPublic: encryptPublic,
        decryptPrivate: decryptPrivate
    };
})();

// ============================================================
// 瓜子蜘蛛主类
// ============================================================
function GuaziSpider() {
    this.name = '瓜子';
    this.hosts = [
        'https://apinew.uozvr.com',
        'https://api.w32z7vtd.com',
        'https://api.6a7nnf7.com',
        'https://api.umygrx3.com',
        'https://api.rmedphk.com'
    ];
    this.hostIndex = 0;
    this.host = this.hosts[this.hostIndex];

    // AES 固定密钥
    this.AES_KEY = 'OITxa5OqAYjhswxx';
    this.AES_IV = 'rCMNwZASNBKZ8mXV';

    // RSA 公钥参数 (hex)
    this.RSA_N = 'd4339fbfcbcb0fb1691dd7f4504bae17db9f44530c455c51391e503ae4caabc673ecd09aa8491a23483cb9421c2f44e95a0fa4f04501ca318d8e019e929d079426c0a14c414847da94930aecdff31550cc63b2fe894ba39efe3b9c9722464e05660e1079e4469f5ec0f44906158ff4175ecc51e9ec11e44da42f9db20000f8c9';
    this.RSA_E = '10001';

    // RSA 私钥参数 (hex) - 用于解密响应
    this.RSA_PRIV_N = '7ba84aad62e2d734268d34f5a336c4e1074578918dc6e6f195de86ac51b18a6c5f32c301e81a49869713a2e02acb0005a6988a7ad50105b5f062c614d7036beb8f175663e608c0b2e2b63cbdd9621676cc523d3ce8353a67efe85c1756537fdbd46d0337713dc142d14b070a653df08ff702235bec0a6de08f64794aa900f58d';
    this.RSA_PRIV_D = '247fb80b1574ff305570b881087bd200d9b497b1deb726d387f8f6a74635b135eba3800bc006824d47aa7418d688b4a8f653700c7172abccd7f74fa03716bb73912a71657d1669555ebf1585f073719a359d778d757153eed436c9a87fa1db5d731faf44c48625dd6dff99396c377dc00bd87480db94c020fb088a299e4a71d';
    this.RSA_PRIV_P = 'd5c09a90437835ec64179b473d1ad1e97398fd71df92a5f112132a98d6c1f54df8b1a4c99cb5881c2f085f2b3a426cf3df44edcc28ee3aa291472f8530ce1377';
    this.RSA_PRIV_Q = '941914f8ec182f91a9c1b952f54c88c3e19f07bf6d711e85284af3ac892bf83f5222ab3bcee1dda12ee60709a81ca04eadc1041a07da6777a6bfd6fa150c581b';
    this.RSA_PRIV_DP = 'a17e14c8add0e29ca8ba951c6b7419e7d0e863836730baa2b9cf353da7f37e4bdc7b0a4f30508e770ca9bc8d4244f16006ed62e3fe808e58487e89ce8d2304dd';
    this.RSA_PRIV_DQ = '8f45fc9e1c7a017b2009846a9759256eab5598bf3ef792992bb3e72d61bf21f8d0532de93c6a12699edf76ab86f1babca327f9f9dce313fa135dc0724bee9745';
    this.RSA_PRIV_QINV = '3ffe5c8b2d5b2f7361521b1a395cb9e4c1d79cf8dd7135f415a2e2fb26d76487c84363f8adbd7d995ab57de31b097873f8bd6b1bca1ab7995829fa5ef24f3764';

    this.DEVICE_OLD_KEY = 'aLFBMWpxBrIDAD1Si/KVvm41';

    // 设备信息
    this.deviceId = String(864150060000000 + Math.floor(Math.random() * 10000));
    this.deviceKey = this._genDeviceKey();
    this.token = '';
    this.tokenId = '';
    this.registered = false;

    // 请求头
    this.header = {
        'User-Agent': 'Lavf/57.83.100',
        'code': 'GZ0369',
        'deviceId': this.deviceId,
        'lang': 'zh_cn',
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Version': '2604028',
        'PackageName': 'com.ae06aebdbb.y286327f5a.ofe849883320260517',
        'Ver': '3.0.3.2',
        'api-ver': '3.0.3.2',
        'Referer': this.host
    };

    // 缓存
    this.cache = {};
    this.cacheTimeout = 300;

    // 初始化 token
    this._initToken();
}

GuaziSpider.prototype._genDeviceKey = function() {
    var chars = '0123456789ABCDEF';
    var key = '';
    for (var i = 0; i < 40; i++) {
        key += chars.charAt(Math.floor(Math.random() * 16));
    }
    return key;
};

GuaziSpider.prototype._getTime = function() {
    return Math.floor(Date.now() / 1000);
};

GuaziSpider.prototype._getMd5 = function(text) {
    return MD5.hash(text).toUpperCase();
};

// AES 加密: 明文 -> hex大写
GuaziSpider.prototype._aesEncrypt = function(text, key, iv) {
    try {
        var keyBytes = Base64.utf8Encode(key);
        var ivBytes = Base64.utf8Encode(iv);
        var plainBytes = Base64.utf8Encode(text);
        var encrypted = AES.encryptCBC(plainBytes, keyBytes, ivBytes);
        return AES.bytesToHex(encrypted).toUpperCase();
    } catch (e) {
        console.log('AES加密失败: ' + e.message);
        return '';
    }
};

// AES 解密: hex -> 明文
GuaziSpider.prototype._aesDecrypt = function(hexText, key, iv) {
    try {
        var keyBytes = Base64.utf8Encode(key);
        var ivBytes = Base64.utf8Encode(iv);
        var cipherBytes = AES.hexToBytes(hexText.toLowerCase());
        var decrypted = AES.decryptCBC(cipherBytes, keyBytes, ivBytes);
        return Base64.utf8Decode(decrypted);
    } catch (e) {
        console.log('AES解密失败: ' + e.message);
        return '';
    }
};

// RSA 公钥加密 -> base64
GuaziSpider.prototype._rsaEncrypt = function(text) {
    try {
        var plainBytes = Base64.utf8Encode(text);
        var encrypted = RSA.encryptPublic(plainBytes, this.RSA_N, this.RSA_E);
        return Base64.encode(encrypted);
    } catch (e) {
        console.log('RSA加密失败: ' + e.message);
        return '';
    }
};

// RSA 私钥解密 base64 -> 明文字符串
GuaziSpider.prototype._rsaDecrypt = function(encryptedBase64) {
    try {
        var cipherBytes = Base64.decode(encryptedBase64);
        var decrypted = RSA.decryptPrivate(
            cipherBytes,
            this.RSA_PRIV_N,
            this.RSA_PRIV_D,
            this.RSA_PRIV_P,
            this.RSA_PRIV_Q,
            this.RSA_PRIV_DP,
            this.RSA_PRIV_DQ,
            this.RSA_PRIV_QINV
        );
        return Base64.utf8Decode(decrypted);
    } catch (e) {
        console.log('RSA解密失败: ' + e.message);
        return '';
    }
};

// HTTP POST 请求 (使用注入的 http 函数)
GuaziSpider.prototype._post = function(url, headers, data) {
    try {
        // data 是对象，转成 form-urlencoded
        var body = '';
        var keys = Object.keys(data);
        for (var i = 0; i < keys.length; i++) {
            if (i > 0) body += '&';
            body += encodeURIComponent(keys[i]) + '=' + encodeURIComponent(data[keys[i]]);
        }
        var options = {
            method: 'POST',
            headers: headers,
            data: body
        };
        var result = http(url, options);
        return {
            status: result.status,
            content: result.content,
            headers: result.headers,
            json: function() {
                return JSON.parse(this.content);
            }
        };
    } catch (e) {
        console.log('HTTP请求失败: ' + e.message);
        return { status: 0, content: '', headers: {}, json: function() { return {}; } };
    }
};

// ---------- 设备注册与认证 ----------
GuaziSpider.prototype._initToken = function() {
    console.log('===== 初始化设备认证 =====');
    try {
        if (!this.registered) {
            this._signUp();
        }
        this._refreshToken();
    } catch (e) {
        console.log('初始化token失败: ' + e.message);
        // 兜底 token
        this.token = '024212ef0975c5306a1434e113a46463.bc77313e11a248558a6ca244ca980944ec3421fa480c50e0229ad91f1cb15aea582603202cd71796885c9e5163e500f1b72f737059aff1ddb8beea47c5a331d6760540345b7f88b2302a0e6e09589f9dcf3ff9175d8c905f990203f5fc04748008ea7a366571cbf5b09509a873dcfba3cf1d5590385f5f7ef6e01d1850974aa220eb5178c89e61c24411af9b9a19435e.06fde789ece48d9b33c5dc857e04e9b5838f08264d928b87237d3476c4484b46';
    }
};

GuaziSpider.prototype._signUp = function() {
    console.log('注册新设备...');
    var params = {
        new_key: this.deviceKey,
        old_key: this.DEVICE_OLD_KEY,
        phone_type: 1,
        code: ''
    };
    var result = this._authRequest('/App/Authentication/Device/signUp', params);
    this._applyAuth(result);
    this.registered = true;
};

GuaziSpider.prototype._signIn = function() {
    console.log('设备登录...');
    var params = {
        new_key: this.deviceKey,
        old_key: this.DEVICE_OLD_KEY
    };
    var result = this._authRequest('/App/Authentication/Device/signIn', params);
    this._applyAuth(result);
};

GuaziSpider.prototype._applyAuth = function(result) {
    if (!result) throw new Error('认证响应为空');
    var newToken = result.token || '';
    if (!newToken) {
        throw new Error('认证失败，无token返回: ' + JSON.stringify(result));
    }
    this.token = newToken;
    var newTokenId = result.app_user_id || '';
    if (newTokenId) {
        this.tokenId = newTokenId;
    }
    console.log('获取token成功, token前缀: ' + this.token.substring(0, 30) + '...');
};

GuaziSpider.prototype._refreshToken = function() {
    console.log('刷新token...');
    var result = this._authRequest('/App/Authentication/Authenticator/refresh', {});
    this._applyAuth(result);
};

GuaziSpider.prototype._authRequest = function(path, params) {
    return this._sendEncryptedRequest(params, path, true);
};

// ---------- 业务请求核心 ----------
GuaziSpider.prototype._ensureToken = function() {
    if (!this.token || !this.tokenId) {
        if (this.registered) {
            this._signIn();
        } else {
            this._signUp();
        }
        this._refreshToken();
    }
};

GuaziSpider.prototype._sendEncryptedRequest = function(data, path, isAuth) {
    try {
        if (!isAuth) {
            this._ensureToken();
        }

        // 1. 参数转 JSON 并 AES 加密
        var jsonParams = JSON.stringify(data);
        var encrypted = this._aesEncrypt(jsonParams, this.AES_KEY, this.AES_IV);
        var requestKey = encrypted.toUpperCase();

        // 2. RSA 加密 iv/key JSON
        var keyJson = JSON.stringify({ iv: this.AES_IV, key: this.AES_KEY });
        var keys = this._rsaEncrypt(keyJson);

        // 3. 生成签名
        var t = String(this._getTime());
        var signStr = 'token_id=,token=' + this.token + ',phone_type=1,request_key=' + requestKey +
                      ',app_id=1,time=' + t + ',keys=' + keys + '*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br';
        var signature = this._getMd5(signStr);

        // 4. 构建请求体
        var body = {
            token: this.token,
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
        var url = this.host + path;
        var response = this._post(url, this.header, body);

        if (response.status !== 200) {
            throw new Error('HTTP ' + response.status);
        }

        var respJson = response.json();
        if (respJson.code !== undefined && respJson.code !== 200) {
            console.log('业务错误码: ' + respJson.code + ', 信息: ' + JSON.stringify(respJson));
            throw new Error('业务错误');
        }

        var dataSection = respJson.data;
        if (!dataSection) {
            throw new Error('响应缺少data字段');
        }

        var encryptedResponse = dataSection.response_key || '';
        var encryptedKeys = dataSection.keys || '';

        // 6. 解密响应
        var decryptedKeysJson = this._rsaDecrypt(encryptedKeys);
        if (!decryptedKeysJson) throw new Error('RSA解密keys失败');
        var keyInfo = JSON.parse(decryptedKeysJson);
        var respKey = keyInfo.key;
        var respIv = keyInfo.iv;
        var decryptedData = this._aesDecrypt(encryptedResponse, respKey, respIv);
        if (!decryptedData) throw new Error('AES解密响应失败');

        return JSON.parse(decryptedData);

    } catch (e) {
        console.log('请求失败 [' + path + ']: ' + e.message);
        return null;
    }
};

// 带重试和域名轮询的数据获取
GuaziSpider.prototype._getData = function(data, path, useCache) {
    try {
        if (useCache === undefined) useCache = true;
        var cacheKey = null;
        if (useCache) {
            cacheKey = path + '_' + this._simpleHash(JSON.stringify(data));
            if (this.cache[cacheKey]) {
                var cached = this.cache[cacheKey];
                if (this._getTime() - cached.timestamp < this.cacheTimeout) {
                    return cached.data;
                }
            }
        }

        for (var attempt = 0; attempt < 3; attempt++) {
            var tried = 0;
            while (tried < this.hosts.length) {
                this.host = this.hosts[this.hostIndex];
                this.header.Referer = this.host;
                var result = this._sendEncryptedRequest(data, path, false);
                if (result !== null) {
                    console.log('请求成功: ' + path + ', 域名: ' + this.host);
                    if (useCache && cacheKey) {
                        this.cache[cacheKey] = { data: result, timestamp: this._getTime() };
                    }
                    return result;
                }
                // 切换域名
                this.hostIndex = (this.hostIndex + 1) % this.hosts.length;
                tried++;
            }
            // 所有域名失败，尝试重新认证
            if (attempt < 2) {
                console.log('所有域名失败，尝试重新认证...');
                try {
                    this.registered = false;
                    this.token = '';
                    this.tokenId = '';
                    this._ensureToken();
                } catch (e) {
                    console.log('重新认证失败: ' + e.message);
                }
                this.hostIndex = 0;
            } else {
                break;
            }
        }
        return null;
    } catch (e) {
        console.log('getData异常: ' + e.message);
        return null;
    }
};

GuaziSpider.prototype._simpleHash = function(str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash = hash & hash;
    }
    return String(hash);
};

GuaziSpider.prototype._getCachedData = function(cacheKey, data, path) {
    var currentTime = this._getTime();
    if (this.cache[cacheKey]) {
        var cached = this.cache[cacheKey];
        if (currentTime - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
    }
    var result = this._getData(data, path, false);
    if (result) {
        this.cache[cacheKey] = { data: result, timestamp: currentTime };
    }
    return result;
};

// ============================================================
// TVBox 蜘蛛接口
// ============================================================

GuaziSpider.prototype.init = function(extend) {
    // 初始化已在构造函数中完成
    return {};
};

GuaziSpider.prototype.homeContent = function(filter) {
    var classes = [
        { type_name: '电影', type_id: '1' },
        { type_name: '电视剧', type_id: '2' },
        { type_name: '动漫', type_id: '4' },
        { type_name: '综艺', type_id: '3' },
        { type_name: '短剧', type_id: '64' }
    ];
    var filters = {};
    var areaValues = [
        { n: '全部', v: '0' }, { n: '大陆', v: '大陆' }, { n: '香港', v: '香港' },
        { n: '台湾', v: '台湾' }, { n: '美国', v: '美国' }, { n: '韩国', v: '韩国' },
        { n: '日本', v: '日本' }, { n: '英国', v: '英国' }, { n: '法国', v: '法国' },
        { n: '泰国', v: '泰国' }, { n: '印度', v: '印度' }, { n: '其他', v: '其他' }
    ];
    var yearValues = [
        { n: '全部', v: '0' }, { n: '2025', v: '2025' }, { n: '2024', v: '2024' },
        { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, { n: '2021', v: '2021' },
        { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, { n: '2018', v: '2018' },
        { n: '2017', v: '2017' }, { n: '2016', v: '2016' }, { n: '2015', v: '2015' },
        { n: '2014', v: '2014' }, { n: '2013', v: '2013' }, { n: '2012', v: '2012' },
        { n: '2011', v: '2011' }, { n: '2010', v: '2010' }, { n: '2009', v: '2009' },
        { n: '2008', v: '2008' }, { n: '2007', v: '2007' }, { n: '2006', v: '2006' },
        { n: '2005', v: '2005' }, { n: '更早', v: '2004' }
    ];
    var sortValues = [
        { n: '最新', v: 'd_id' }, { n: '最热', v: 'd_hits' }, { n: '推荐', v: 'd_score' }
    ];

    for (var i = 0; i < classes.length; i++) {
        var tid = classes[i].type_id;
        filters[tid] = [
            { key: 'area', name: '地区', value: areaValues },
            { key: 'year', name: '年份', value: yearValues },
            { key: 'sort', name: '排序', value: sortValues }
        ];
    }

    // 首页推荐：获取热门电影（按热度排序，第一页前30条）
    var list = [];
    try {
        var body = {
            area: '0',
            year: '0',
            pageSize: '30',
            sort: 'd_hits',
            page: '1',
            tid: '1'
        };
        var data = this._getData(body, '/App/IndexList/indexList');
        if (data && data.list) {
            for (var j = 0; j < data.list.length; j++) {
                var item = data.list[j];
                var vodContinu = item.vod_continu || 0;
                var remarks = vodContinu === 0 ? '电影' : ('更新至' + vodContinu + '集');
                list.push({
                    vod_id: item.vod_id + '/' + vodContinu,
                    vod_name: item.vod_name || '',
                    vod_pic: item.vod_pic || '',
                    vod_remarks: remarks
                });
            }
        }
    } catch (e) {
        console.log('首页推荐获取失败: ' + e.message);
    }

    return { class: classes, filters: filters, list: list };
};

GuaziSpider.prototype.homeVideoContent = function() {
    return { list: [] };
};

GuaziSpider.prototype.categoryContent = function(tid, pg, filter, extend) {
    var videos = [];
    try {
        if (!extend) extend = {};
        var body = {
            area: extend.area || '0',
            year: extend.year || '0',
            pageSize: '30',
            sort: extend.sort || 'd_id',
            page: String(pg),
            tid: tid
        };
        var cacheKey = 'category_' + tid + '_' + pg + '_' + this._simpleHash(JSON.stringify(body));
        var data = this._getCachedData(cacheKey, body, '/App/IndexList/indexList');
        if (data && data.list) {
            for (var i = 0; i < data.list.length; i++) {
                var item = data.list[i];
                var vodContinu = item.vod_continu || 0;
                var remarks = vodContinu === 0 ? '电影' : ('更新至' + vodContinu + '集');
                videos.push({
                    vod_id: item.vod_id + '/' + vodContinu,
                    vod_name: item.vod_name || '',
                    vod_pic: item.vod_pic || '',
                    vod_remarks: remarks
                });
            }
        }
    } catch (e) {
        console.log('获取分类内容失败: ' + e.message);
    }
    return { list: videos, page: parseInt(pg), pagecount: 9999, limit: 30, total: 999999 };
};

GuaziSpider.prototype.detailContent = function(ids) {
    try {
        var vodId = ids[0].split('/')[0];
        var t = String(this._getTime());
        var body1 = { token_id: this.tokenId, vod_id: vodId, mobile_time: t, token: this.token };
        var qdata = this._getData(body1, '/App/IndexPlay/playInfo');
        var body2 = { vurl_cloud_id: '2', vod_d_id: vodId };
        var jdata = this._getData(body2, '/App/Resource/Vurl/show');

        if (!qdata || !qdata.vodInfo) {
            return { list: [] };
        }
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
            vod_play_from: '瓜子影视'
        };

        var playList = [];
        if (jdata && jdata.list) {
            for (var idx = 0; idx < jdata.list.length; idx++) {
                var item = jdata.list[idx];
                if (item.play) {
                    var n = [], p = [];
                    var playKeys = Object.keys(item.play);
                    for (var k = 0; k < playKeys.length; k++) {
                        var key = playKeys[k];
                        var value = item.play[key];
                        if (value.param && value.param !== '') {
                            n.push(key);
                            p.push(value.param);
                        }
                    }
                    if (p.length > 0) {
                        var playName = jdata.list.length !== 1 ? String(idx + 1) : (vod.vod_name || '');
                        var playUrl = p[p.length - 1] + '||' + n.join('@');
                        playList.push(playName + '$' + playUrl);
                    }
                }
            }
        }
        videoDetail.vod_play_url = playList.join('#');
        return { list: [videoDetail] };
    } catch (e) {
        console.log('获取详情失败: ' + e.message);
        return { list: [] };
    }
};

GuaziSpider.prototype.searchContent = function(key, quick, pg) {
    var videos = [];
    try {
        var body = { keywords: key, order_val: '1', page: String(pg || 1) };
        var data = this._getData(body, '/App/Index/findMoreVod', false);
        if (data && data.list) {
            for (var i = 0; i < data.list.length; i++) {
                var item = data.list[i];
                var vodContinu = item.vod_continu || 0;
                var remarks = vodContinu === 0 ? '电影' : ('更新至' + vodContinu + '集');
                videos.push({
                    vod_id: item.vod_id + '/' + vodContinu,
                    vod_name: item.vod_name || '',
                    vod_pic: item.vod_pic || '',
                    vod_remarks: remarks
                });
            }
        }
    } catch (e) {
        console.log('搜索失败: ' + e.message);
    }
    return { list: videos, page: parseInt(pg || 1), pagecount: 9999, limit: 30, total: 999999 };
};

GuaziSpider.prototype.playerContent = function(flag, id, vipFlags) {
    try {
        var parts = id.split('||');
        if (parts.length < 2) {
            return { parse: 0, playUrl: '', url: '' };
        }
        var paramStr = parts[0];
        var resolutions = parts[1] ? parts[1].split('@') : [];
        var params = {};
        var pairs = paramStr.split('&');
        for (var i = 0; i < pairs.length; i++) {
            var pair = pairs[i];
            var eqIdx = pair.indexOf('=');
            if (eqIdx > 0) {
                var key = pair.substring(0, eqIdx);
                var value = pair.substring(eqIdx + 1);
                params[key] = value;
            }
        }
        if (resolutions.length > 0) {
            // 按分辨率降序排序
            resolutions.sort(function(a, b) {
                var na = parseInt(a);
                var nb = parseInt(b);
                if (isNaN(na)) na = 0;
                if (isNaN(nb)) nb = 0;
                return nb - na;
            });
            params.resolution = resolutions[0];
            var data = this._getData(params, '/App/Resource/VurlDetail/showOne', false);
            if (data && data.url) {
                return {
                    parse: 0,
                    playUrl: '',
                    url: data.url,
                    header: JSON.stringify({ 'User-Agent': 'Lavf/57.83.100', 'Referer': 'http://WJiZxLXA2.com/' }),
                    danmaku: 'http://127.0.0.1:9978/proxy?do=diydanmu'
                };
            }
        }
        return { parse: 0, playUrl: '', url: '' };
    } catch (e) {
        console.log('播放解析失败: ' + e.message);
        return { parse: 0, playUrl: '', url: '' };
    }
};

// ============================================================
// 蜘蛛单例 & 全局接口
// ============================================================
var spiderInstance = null;

function getSpider() {
    if (!spiderInstance) {
        spiderInstance = new GuaziSpider();
    }
    return spiderInstance;
}

// 注册到全局
globalThis.__JS_SPIDER__ = {
    init: function(extend) {
        var s = getSpider();
        return s.init(extend);
    },
    homeContent: function(filter) {
        var s = getSpider();
        return s.homeContent(filter);
    },
    homeVideoContent: function() {
        var s = getSpider();
        return s.homeVideoContent();
    },
    categoryContent: function(tid, pg, filter, extend) {
        var s = getSpider();
        return s.categoryContent(tid, pg, filter, extend);
    },
    detailContent: function(ids) {
        var s = getSpider();
        return s.detailContent(ids);
    },
    searchContent: function(key, quick, pg) {
        var s = getSpider();
        return s.searchContent(key, quick, pg);
    },
    playerContent: function(flag, id, vipFlags) {
        var s = getSpider();
        return s.playerContent(flag, id, vipFlags);
    }
};

// 兼容可能的直接调用方式
if (typeof module !== 'undefined' && module.exports) {
    module.exports = globalThis.__JS_SPIDER__;
}

})();
