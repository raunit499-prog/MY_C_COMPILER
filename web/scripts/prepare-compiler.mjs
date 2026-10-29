// Build the original C translator for the browser. The desktop project is unchanged.
import { readFile, writeFile, cp, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { CompilerEngine } from '../src/engine.js';
// Reproduce the self-hosted toolchain from the pinned npm dependency at build time.
const assets=new URL('../assets/',import.meta.resolve('@live-codes/clang-wasm'));
await mkdir(new URL('../public/clang/',import.meta.url),{recursive:true});
await cp(assets,new URL('../public/clang/',import.meta.url),{recursive:true});
const frontendDirectory=new URL('../../custom-keywords/src/',import.meta.url);
const parts=[];
for(const name of ['keywords.h','translate.h','keywords.c','translate.c','main.c']) {
  parts.push('/* Original file: '+name+' */\n'+(await readFile(new URL(name,frontendDirectory),'utf8')).replace(/^#include "(?:keywords|translate)\.h"\s*$/gm,''));
}
const source=parts.join('\n').replace('FILE *temporary = tmpfile();','FILE *temporary = fopen("translation.tmp", "w+b");');
await writeFile(new URL('../public/frontend.c',import.meta.url),source);
const hash = createHash('sha256').update(source).digest('hex');
const receipt = new URL('../public/customc.sha256', import.meta.url);
const output = new URL('../public/customc.wasm', import.meta.url);
try {
  if ((await readFile(receipt, 'utf8')).trim() === hash && (await readFile(output)).length) {
    console.log('C frontend is up to date.'); process.exit(0);
  }
} catch { /* First build. */ }
const engine = new CompilerEngine((kind, value) => { if (kind === 'log' && value) console.log(value); });
await engine.init({ frontendSource: source });
await writeFile(output, engine.frontendBytes);
await writeFile(receipt, hash + '\n');
console.log(`Built C frontend: ${engine.frontendBytes.byteLength} bytes.`);
