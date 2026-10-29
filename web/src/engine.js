// My C frontend performs the translation; Clang/WASI builds and runs the result.
import {WASI} from '@bjorn3/browser_wasi_shim';
import {createBrowserWasiHost} from '@wasm-idle/llvm-core/clang';
import {OutputBuffer} from './output-buffer.js';
import { createToolchain, compilerDiagnostics, CLANG_DRIVER_DEFAULT_ARGS } from '@live-codes/clang-wasm/toolchain';

const RUNTIME_IO = '#include <stdio.h>\n__attribute__((constructor)) static void myc_runtime_io(void){setvbuf(stdout,0,_IONBF,0);setvbuf(stderr,0,_IONBF,0);}\n';
const FLAGS = [...CLANG_DRIVER_DEFAULT_ARGS, '-std=c11', '-Wall', '-Wextra',
  '-Werror=implicit-function-declaration', '-ferror-limit', '10', '-O0'];
export class CompilerFailure extends Error {
  constructor(message, log, phase) { super(message); this.log = log; this.phase = phase; }
}
export class CompilerEngine {
  constructor(emit = () => {}) { this.emit = emit; this.toolchain = null; this.frontend = null; this.artifact = null; }
  async init({ baseUrl, frontendSource, frontendBytes }) {
    if (this.frontend) return;
    this.emit('phase', 'Loading the C toolchain');
    this.toolchain = await createToolchain({ baseUrl, onProgress: p => this.emit('progress', p) });
    this.emit('phase', 'Preparing your C frontend');
    this.frontendBytes = frontendBytes || (await this.compile(frontendSource, 'customc.c', 'frontend')).bytes;
    this.frontend = await WebAssembly.compile(this.frontendBytes);
    this.emit('ready', true);
  }
  async compile(code, name, phase = 'compile') {
    const tc = this.toolchain;
    const result = await tc.lock(() => tc.captureCompilerOutput(() =>
      tc.runtime.compileArtifact(code, { language: 'C', fileName: name, compileArgs: FLAGS, workspaceFiles: phase === 'compile' ? [{path:'runtime_io.c',content:RUNTIME_IO}] : [] })));
    const diagnostics = compilerDiagnostics(result.raw).join('\n');
    if (diagnostics) this.emit('log', diagnostics);
    if (result.error) throw new CompilerFailure('Compilation failed', diagnostics || result.error.message, phase);
    return result.result;
  }
  async translate(source, config) {
    if (new TextEncoder().encode(source).length > 1024 * 1024) throw new Error('Source exceeds the 1 MiB limit.');
    this.emit('phase', 'Checking and translating your keywords');
    const translated = await this.toolchain.runCommand(this.frontend, {
      programName: 'customc',
      args: ['keywords.cfg', 'source.myc', 'generated.c'],
      files: [{ path: 'source.myc', contents: source }, { path: 'keywords.cfg', contents: config }]
    });
    if (translated.exitCode !== 0) throw new CompilerFailure('Translation failed', translated.stderr, 'translate');
    const data = translated.readFile('generated.c');
    if (!data) throw new Error('The C frontend did not produce generated.c.');
    const code = new TextDecoder().decode(data);
    this.emit('log', translated.stdout.trim());
    this.emit('generated', code);
    return code;
  }
  async build(source, config) {
    this.artifact=null;
    const code = await this.translate(source, config);
    this.emit('phase', 'Compiling and linking with Clang');
    this.artifact = await this.compile(code, 'generated.c');
    this.emit('compiled', { bytes: this.artifact.bytes.byteLength });
    return code;
  }
  async run(input = '', {stdin = () => null} = {}) {
    if (new TextEncoder().encode(input).length > 65536) throw new Error('Input exceeds the 64 KiB limit.');
    if(!this.artifact)throw new Error('Compile a program before running it.');
    this.emit('phase', 'Running your program');
    let sent=false;
    const collected={stdout:new OutputBuffer(),stderr:new OutputBuffer()},decoders={};
    const host=createBrowserWasiHost({
      stdin:()=>{if(!sent&&input){sent=true;return input;}return stdin();}
    });
    for(const stream of ['stdout','stderr']){
      const fd=host[stream],decoder=decoders[stream]=new TextDecoder();
      fd.fd_write=data=>{
        const text=decoder.decode(data,{stream:true});collected[stream].append(text);this.emit(stream,text);
        return {ret:0,nwritten:data.byteLength};
      };
    }
    const wasi=new WASI(host.args,host.envEntries,host.fds,{debug:false});
    const module=this.artifact.wasm||await WebAssembly.compile(this.artifact.bytes);
    const instance=await WebAssembly.instantiate(module,{wasi_snapshot_preview1:wasi.wasiImport,wasi_unstable:wasi.wasiImport});
    const exitCode=wasi.start(instance);
    for(const stream of ['stdout','stderr']){const tail=decoders[stream].decode();if(tail){collected[stream].append(tail);this.emit(stream,tail);}}
    return {exitCode,stdout:collected.stdout.text(),stderr:collected.stderr.text(),outputTruncated:collected.stdout.truncated||collected.stderr.truncated};
  }
}
