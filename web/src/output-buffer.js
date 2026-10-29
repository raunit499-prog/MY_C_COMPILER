// Retain recent output in fixed memory. A full console never kills a running program.
export const OUTPUT_CAPACITY = 512 * 1024;
export class OutputBuffer {
  constructor(limit=OUTPUT_CAPACITY){this.limit=limit;this.buffer=new Uint8Array(limit);this.cursor=0;this.length=0;this.truncated=false;}
  append(text){
    const bytes=new TextEncoder().encode(text);if(!bytes.length)return;
    this.truncated ||= this.length+bytes.length>this.limit;
    if(bytes.length>=this.limit){this.buffer.set(bytes.subarray(bytes.length-this.limit));this.cursor=0;this.length=this.limit;return;}
    const first=Math.min(bytes.length,this.limit-this.cursor);
    this.buffer.set(bytes.subarray(0,first),this.cursor);this.buffer.set(bytes.subarray(first),0);
    this.cursor=(this.cursor+bytes.length)%this.limit;this.length=Math.min(this.limit,this.length+bytes.length);
  }
  text(){
    const result=new Uint8Array(this.length);
    if(this.length<this.limit)result.set(this.buffer.subarray(0,this.length));
    else {const tail=this.limit-this.cursor;result.set(this.buffer.subarray(this.cursor));result.set(this.buffer.subarray(0,this.cursor),tail);}
    let start=0;while(start<result.length&&(result[start]&192)===128)start++;
    return new TextDecoder().decode(result.subarray(start));
  }
}
