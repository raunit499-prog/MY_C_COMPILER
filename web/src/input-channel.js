// A bounded, synchronous stdin bridge. Only the worker waits; the page stays responsive.
export const INPUT_CAPACITY = 65536;
const HEADER_BYTES = 16;
export function createInputBuffer() { return new SharedArrayBuffer(HEADER_BYTES + INPUT_CAPACITY); }
function views(buffer) { return {control:new Int32Array(buffer,0,4),data:new Uint8Array(buffer,HEADER_BYTES)}; }
export function deliverInput(buffer, text, eof = false) {
  const {control,data}=views(buffer);
  const bytes=new TextEncoder().encode(text);
  if(bytes.length>INPUT_CAPACITY) throw new Error('Each input submission must fit in 64 KiB.');
  if(Atomics.load(control,2)!==1 || Atomics.compareExchange(control,0,0,3)!==0) return false;
  data.set(bytes);Atomics.store(control,1,bytes.length);
  Atomics.store(control,0,eof?2:1);Atomics.notify(control,0);
  return true;
}
export function blockingInput(buffer, waiting = () => {}) {
  const {control,data}=views(buffer);let closed=false;
  return () => {
    if(closed)return null;
    Atomics.store(control,2,1);waiting(true);
    let state;
    while((state=Atomics.load(control,0))===0 || state===3) Atomics.wait(control,0,state);
    Atomics.store(control,2,0);
    if(state===2){closed=true;waiting(false,true);return null;}
    const bytes=data.slice(0,Atomics.load(control,1));
    Atomics.store(control,0,0);waiting(false,false);
    return bytes;
  };
}
