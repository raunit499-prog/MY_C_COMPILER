import {test,before} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {format} from '@wasm-fmt/clang-format';
import {EditorState} from '@codemirror/state';
import {cpp} from '@codemirror/lang-cpp';
import {indentUnit} from '@codemirror/language';
import {formatProgram,codeTokens} from '../src/formatting.js';
import {insertCustomNewline} from '../src/indentation.js';
import {CompilerEngine} from '../src/engine.js';
import {config,keywords} from '../src/language.js';
const cases=JSON.parse(await readFile(new URL('../../tests/program_cases.json',import.meta.url)));
let engine;
before(async()=>{engine=new CompilerEngine();await engine.init({frontendBytes:new Uint8Array(await readFile(new URL('../public/customc.wasm',import.meta.url)))});});
for(const item of cases)test('formatted program keeps result: '+item.name,async()=>{
 const source=formatProgram(item.source,format);
 assert.equal(formatProgram(source,format),source,'formatting is idempotent');
 assert.deepEqual(codeTokens(source).map(t=>t.text),codeTokens(item.source).map(t=>t.text));
 await engine.build(source,config);const result=await engine.run(item.input);
 assert.equal(result.exitCode,0);assert.equal(result.stdout,item.output);
});
test('compact nested aliases become readable four-space blocks',()=>{
 const source='int main(void){each(int i=0;i<3;i++){when(i){output("x");}given{output("y");}}execute{output("z");}until(0);provide 0;}';
 const result=formatProgram(source,format);
 assert.match(result,/\n    each \(int i = 0; i < 3; i\+\+\) \{\n        when \(i\) \{\n            output/);
 assert.match(result,/\n        \} given \{/);assert.match(result,/\n    execute \{/);assert.match(result,/\} until \(0\);/);
 assert(!result.includes('\t'));
});
test('formatting preserves strings, comments, headers, directives, macros and spliced tokens',async()=>{
 const source='#include <stdio.h>\n#define DOUBLE(x) ((x)+(x))\n#if 1\n/* output when { π } */\nint main(void){out\\\nput("when { provide } \\tπ\\n");output("%d",DOUBLE(2));provide 0;}\n#endif\n';
 const result=formatProgram(source,format);
 assert(result.includes('/* output when { π } */'));assert(result.includes('out\\\nput('));assert(result.includes('"when { provide } \\tπ\\n"'));
 await engine.build(result,config);const output=await engine.run();assert.equal(output.stdout,'when { provide } \tπ\n4');
});
for(const [alias,canonical] of keywords)test('formatting cannot enable forbidden '+canonical,async()=>{
 const source=formatProgram('int main(void){'+canonical+';}',format);
 assert(source.includes(canonical));await assert.rejects(()=>engine.translate(source,config),error=>error.log.includes("standard spelling '"+canonical+"'"));
});
test('formatter token changes are refused',()=>{assert.throws(()=>formatProgram('int main(void){provide 1;}',s=>s.replace('1','2')),/preserve/);});
test('format-control comments stay intact without disabling required indentation',()=>{
 const result=formatProgram('// clang-format off\nint main(void){\nprovide 0;\n}\n// clang-format on\n',format);
 assert(result.includes('// clang-format off'));assert(result.includes('// clang-format on'));
 assert.match(result,/\n    provide 0;/);
});
for(const [name,source,spaces] of [
 ['function','int main(void) {',4],
 ['each block','int main(void) {\n    each (int i=0;i<2;i++) {',8],
 ['when without braces','int main(void) {\n    when (1)',8],
 ['given without braces','int main(void) {\n    when (0)\n        provide 1;\n    given',8],
 ['execute block','int main(void) {\n    execute {',8],
 ['switch match','int main(void) {\n    choose (1) {\n        match 1:',12],
 ['switch otherwise','int main(void) {\n    choose (1) {\n        otherwise:',12]
])test('Enter indents '+name,()=>{
 let state=EditorState.create({doc:source,selection:{anchor:source.length},extensions:[cpp(),indentUnit.of('    '),EditorState.tabSize.of(4)]});
 assert(insertCustomNewline({state,dispatch:tr=>{state=tr.state;}}));assert.equal(state.doc.toString(),source+'\n'+' '.repeat(spaces));
});
