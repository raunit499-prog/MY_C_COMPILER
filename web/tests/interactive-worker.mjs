import {parentPort,workerData} from 'node:worker_threads';
import {readFile} from 'node:fs/promises';
import {CompilerEngine} from '../src/engine.js';
import {blockingInput} from '../src/input-channel.js';
const emit=(kind,value)=>parentPort.postMessage({kind,value});
const engine=new CompilerEngine(emit);
try{
 await engine.init({frontendBytes:new Uint8Array(await readFile(new URL('../public/customc.wasm',import.meta.url)))});
 await engine.build(workerData.source,workerData.config);
 const result=await engine.run(workerData.initial||'',{stdin:blockingInput(workerData.buffer,(waiting,eof)=>emit('input-state',{waiting,eof}))});
 emit('complete',result);
}catch(error){emit('failure',error.stack);}
