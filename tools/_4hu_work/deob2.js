// 4hu d.js 反混淆：把 _0x207e(0xNN) 调用替换为解码后的字符串，输出可读源码。
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const WORK = __dirname;
let src = fs.readFileSync(path.join(WORK, 'd.js'), 'utf8');

// 先加载前缀定义（字符串数组 + 解码函数）
const cutoff = src.indexOf('var AP_BOOT_SRC');
const head = src.slice(0, cutoff > 0 ? cutoff : 8000);
const sandbox = { console, Math, Date, String, Number, Array, Object, RegExp, Error,
  decodeURIComponent, parseInt, parseFloat, isNaN };
vm.createContext(sandbox);
vm.runInContext(head + '\n;this.__p=_0x207e;', sandbox);
const dec = sandbox.__p;

// 替换所有 _0x207e(0x1a2) 形式
let replaced = 0;
const out = src.replace(/_0x[0-9a-f]+\((0x[0-9a-f]+)\)/g, (m, hex) => {
  try {
    const v = dec(parseInt(hex, 16));
    if (typeof v === 'string') { replaced++; return JSON.stringify(v); }
  } catch (e) {}
  return m;
});

console.log('// 替换次数:', replaced);
fs.writeFileSync(path.join(WORK, 'd.deob.js'), out, 'utf8');

// 打印 AP_BOOT_SRC 之后的主体（前 6000 字符）
const idx = out.indexOf('AP_BOOT_SRC');
console.log('\n=== 主体（AP_BOOT_SRC 起）===');
console.log(out.slice(idx, idx + 6000));
