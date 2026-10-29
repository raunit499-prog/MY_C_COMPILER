import {blockingInput} from './input-channel.js';
import {sha256} from '@noble/hashes/sha2.js';
import { CompilerEngine, CompilerFailure } from './engine.js';
// The managed HTTP preview lacks Web Crypto. Keep SHA-256 verification with
// a pure JavaScript implementation; HTTPS browsers use native Web Crypto.
if (!globalThis.crypto?.subtle) {
  const digest = async (algorithm, data) => {
    if ((typeof algorithm === 'string' ? algorithm : algorithm.name).toUpperCase() !== 'SHA-256')
      throw new Error('Only SHA-256 is supported by the preview fallback.');
    const bytes = ArrayBuffer.isView(data) ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength) : new Uint8Array(data);
    return sha256(bytes).buffer;
  };
  if (globalThis.crypto) Object.defineProperty(globalThis.crypto, 'subtle', {value:{digest}});
  else Object.defineProperty(globalThis, 'crypto', {value:{subtle:{digest}}});
}
let id;
let outputBuffer = '', outputKind = 'stdout', lastOutput = 0;
const send = (kind, value) => postMessage({id, kind, value});
function flushOutput() { if(outputBuffer) {send(outputKind,outputBuffer);outputBuffer='';} }
const emit = (kind, value) => {
  if(kind === 'stdout' || kind === 'stderr') {
    if(kind !== outputKind) flushOutput();
    outputKind=kind;outputBuffer+=value;
    if(outputBuffer.length>65536)outputBuffer=outputBuffer.slice(-65536);
    if(performance.now()-lastOutput>=40){flushOutput();lastOutput=performance.now();}
  } else {flushOutput();send(kind,value);}
};
const engine = new CompilerEngine(emit);
self.onmessage = async ({ data }) => {
  id = data.id;
  try {
    if (!engine.frontend) {
      const response = await fetch('/customc.wasm');
      if (!response.ok) throw new Error('Could not load the C frontend. Refresh and try again.');
      await engine.init({ baseUrl: new URL('/clang/', self.location.href).href, frontendBytes: new Uint8Array(await response.arrayBuffer()) });
    }
    const started = performance.now();
    if (data.action === 'translate') {
      await engine.translate(data.source, data.config);
      emit('complete', { action: 'translate', elapsed: performance.now() - started });
    } else {
      await engine.build(data.source, data.config);
      if (data.action === 'run') {
        const readInput=data.inputBuffer?blockingInput(data.inputBuffer,(waiting,eof)=>emit('input-state',{waiting,eof})):()=>{throw new Error('Live input requires HTTPS and cross-origin isolation. Open the deployed site in a recent browser, or preload enough input.');};
        const initial=data.input&&!data.input.endsWith('\n')?data.input+'\n':data.input;
        const result = await engine.run(initial,{stdin:readInput});
        emit('complete', { action: 'run', exitCode: result.exitCode, elapsed: performance.now() - started });
      } else {
        emit('complete', { action: 'compile', elapsed: performance.now() - started });
      }
    }
  } catch (error) {
    emit('failure', { message: error.message, log: error.log || '', phase: error instanceof CompilerFailure ? error.phase : 'runtime' });
  }
};
