import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {config} from '../src/language.js';
import {createInputBuffer,deliverInput} from '../src/input-channel.js';
import {OutputBuffer} from '../src/output-buffer.js';
async function interact(source,answers,initial=''){
 const buffer=createInputBuffer();let index=0,output='';
 const worker=new Worker(new URL('./interactive-worker.mjs',import.meta.url),{workerData:{source,config,buffer,initial}});
 try{return await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{reject(new Error('Interactive test timed out'));worker.terminate();},20000);
  worker.on('error',error=>{clearTimeout(timer);reject(error);});
  worker.on('message',({kind,value})=>{
   if(kind==='stdout')output+=value;
   if(kind==='input-state'&&value.waiting){
    try{assert(index<answers.length,'unexpected extra input request');const answer=answers[index++];if(answer?.prompt)assert(output.includes(answer.prompt),'prompt must be visible before input is requested');setTimeout(()=>{try{assert(deliverInput(buffer,answer===null?'':(answer.text??answer)+'\n',answer===null));}catch(error){clearTimeout(timer);reject(error);}},30);}
    catch(error){clearTimeout(timer);reject(error);}
   }
   if(kind==='complete'){clearTimeout(timer);resolve({...value,requests:index});}
   if(kind==='failure'){clearTimeout(timer);reject(new Error(value));}
  });
 });}finally{await worker.terminate();}
}
test('live input waits, displays an unterminated prompt, and accepts multiple answers',async()=>{
 const source='#include <stdio.h>\nint main(void){int a,b;output("First: ");input("%d",&a);output("Second: ");input("%d",&b);output("sum=%d",a+b);provide 0;}';
 const result=await interact(source,[{prompt:'First: ',text:'4'},{prompt:'Second: ',text:'7'}]);assert.equal(result.stdout,'First: Second: sum=11');assert.equal(result.exitCode,0);assert.equal(result.requests,2);
});
test('preloaded input is consumed before a live answer',async()=>{const result=await interact('#include <stdio.h>\nint main(void){int a,b;input("%d",&a);input("%d",&b);output("%d",a+b);provide 0;}',['7'],'4\n');assert.equal(result.stdout,'11');assert.equal(result.requests,1);});
test('live input loop terminates on explicit EOF',async()=>{const result=await interact('#include <stdio.h>\nint main(void){int n,s=0;until(input("%d",&n)==1)s+=n;output("sum=%d",s);provide 0;}',['2','3',null]);assert.equal(result.stdout,'sum=5');assert.equal(result.exitCode,0);});
test('live fgets preserves spaces and newlines',async()=>{const result=await interact('#include <stdio.h>\nint main(void){char s[40];when(fgets(s,sizeof s,stdin))output("%s",s);provide 0;}',['hello world']);assert.equal(result.stdout,'hello world\n');});
test('Stop can terminate a program blocked waiting for input',async()=>{
 const worker=new Worker(new URL('./interactive-worker.mjs',import.meta.url),{workerData:{source:'#include <stdio.h>\nint main(void){int n;input("%d",&n);provide 0;}',config,buffer:createInputBuffer()}});
 try{await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('No input request')),15000);worker.on('message',m=>{if(m.kind==='input-state'&&m.value.waiting){clearTimeout(timeout);resolve();}});worker.on('error',reject);});const before=Date.now();await worker.terminate();assert(Date.now()-before<3000);}finally{await worker.terminate();}
});
test('input submissions are bounded and require a waiting reader',()=>{const buffer=createInputBuffer();assert.equal(deliverInput(buffer,'x'),false);assert.throws(()=>deliverInput(buffer,'x'.repeat(65537)),/64 KiB/);});
test('bounded output retains a valid UTF-8 tail',()=>{const output=new OutputBuffer(10);output.append('abcdef');output.append('ππππ');assert.equal(output.text(),'efππππ');assert(output.truncated);output.append('Z');assert.equal(output.text(),'fππππZ');});
