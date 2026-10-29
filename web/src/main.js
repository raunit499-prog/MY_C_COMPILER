import {createInputBuffer, deliverInput} from './input-channel.js';
import {OutputBuffer} from './output-buffer.js';
import './style.css';
import {EditorState, StateEffect, StateField} from '@codemirror/state';
import {EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection, highlightSpecialChars, Decoration, ViewPlugin, MatchDecorator} from '@codemirror/view';
import {cpp} from '@codemirror/lang-cpp';
import {history, historyKeymap, defaultKeymap, indentWithTab} from '@codemirror/commands';
import {syntaxHighlighting, HighlightStyle, bracketMatching} from '@codemirror/language';
import {tags} from '@lezer/highlight';
import {keywords, config} from './language.js';
import {parseDiagnostics} from './diagnostics.js';
import examples from './examples.json';

const $ = id => document.getElementById(id);
const text = (id, value) => { $(id).textContent = value; };
let worker = null, busy = false, workerJobs = 0, jobId = 0, timer, toastTimer, saveTimer;
let sourceSnapshot = '', generated = '', generatedSource = '', logs = '', stdout = '', diagnostics = [], activePanel = 'console', activeFile = 'source';
let lastSaved = null;
let inputBuffer=null, waitingForInput=false, inputClosed=false, programRunning=false, outputBuffer=new OutputBuffer();
const decorationsEffect = StateEffect.define();
const errorLines = StateField.define({
  create: () => Decoration.none,
  update(value, transaction) {
    value = value.map(transaction.changes);
    for (const effect of transaction.effects) if (effect.is(decorationsEffect)) value = effect.value;
    if (transaction.docChanged) return Decoration.none;
    return value;
  },
  provide: field => EditorView.decorations.from(field)
});
const matcher = new MatchDecorator({regexp:new RegExp('\\b(?:' + keywords.map(k=>k[0]).join('|') + ')\\b','g'), decoration:Decoration.mark({class:'custom-keyword'})});
const customSyntax = ViewPlugin.fromClass(class {
  constructor(view) {this.decorations=matcher.createDeco(view);}
  update(update) {this.decorations=matcher.updateDeco(update,this.decorations);}
}, {decorations:instance=>instance.decorations});
const codeColors = HighlightStyle.define([
  {tag:tags.comment,color:'#6d8a93',fontStyle:'italic'},
  {tag:[tags.keyword,tags.controlKeyword],color:'#d6b0eb'},
  {tag:[tags.typeName,tags.standard(tags.typeName)],color:'#88cbd3'},
  {tag:[tags.string,tags.character],color:'#d8c596'},
  {tag:[tags.number,tags.bool],color:'#9cd7c1'},
  {tag:[tags.function(tags.variableName)],color:'#a6c9e7'},
  {tag:[tags.meta,tags.annotation],color:'#8db8ca'},
  {tag:tags.operator,color:'#a6c8cf'},
  {tag:tags.punctuation,color:'#9bb3bc'}
]);
const editorTheme = EditorView.theme({
  '&':{color:'#c4d3dd',backgroundColor:'#111a1e'},
  '.cm-gutters':{backgroundColor:'#111a1e',color:'#435f6c',border:'none'},
  '.cm-activeLineGutter':{color:'#b4c9c6',backgroundColor:'transparent'},
  '.cm-activeLine':{backgroundColor:'#1a292e66'},
  '.cm-cursor':{borderLeftColor:'#b0f3cf'},
  '.cm-selectionBackground, &.cm-focused .cm-selectionBackground':{backgroundColor:'#35564b88'},
  '.cm-matchingBracket':{backgroundColor:'#3f675a66',outline:'1px solid #72a99255'},
  '.cm-tooltip':{backgroundColor:'#23333b',color:'#dce7e9',borderColor:'#476069'}
},{dark:true});
let initial = examples.hello;
try { const saved = localStorage.getItem('my-c-compiler-draft-v1'); if (saved !== null && new TextEncoder().encode(saved).length<=1024*1024) initial=saved; }
catch {text('save-status','Local saving unavailable');}
const view = new EditorView({
  state:EditorState.create({doc:initial,extensions:[
    lineNumbers(), highlightSpecialChars(), history(), drawSelection(), highlightActiveLine(), cpp(),
    syntaxHighlighting(codeColors), bracketMatching(), customSyntax, errorLines, editorTheme,
    EditorView.contentAttributes.of({'aria-label':'Custom C source code','spellcheck':'false'}),
    EditorState.tabSize.of(4),
    keymap.of([{key:'Mod-Enter',run:()=>{perform('run');return true;}},{key:'Mod-s',run:()=>{download();return true;}},{key:'Mod-g',run:()=>{goToLine();return true;}},indentWithTab,...defaultKeymap,...historyKeymap]),
    EditorView.updateListener.of(update=>{
      if(update.selectionSet||update.docChanged) updatePosition();
      if(update.docChanged){
        text('save-status','Saving draft…');
        clearTimeout(saveTimer); saveTimer=setTimeout(saveDraft,400);
        if(generated) text('generated-note','Source has changed. Translate or compile again to refresh this C.');
      }
    })
  ]}), parent:$('editor')
});
const generatedView = new EditorView({state:EditorState.create({doc:'',extensions:[lineNumbers(),cpp(),syntaxHighlighting(codeColors),editorTheme,EditorState.readOnly.of(true),EditorView.editable.of(false),EditorView.contentAttributes.of({'aria-label':'Generated standard C code'})]}),parent:$('generated-editor')});
function updatePosition(){const head=view.state.selection.main.head,line=view.state.doc.lineAt(head);text('go-line',`Ln ${line.number}, Col ${head-line.from+1}`);}
function saveDraft(){
  try{const value=view.state.doc.toString();if(new TextEncoder().encode(value).length>1024*1024){text('save-status','Draft exceeds 1 MiB');return;}localStorage.setItem('my-c-compiler-draft-v1',value);lastSaved=value;text('save-status','Draft saved locally');}
  catch{text('save-status','Download to save your work');}
}
function toast(message){text('toast',message);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4200);}
function showFile(file){activeFile=file;$('editor').hidden=file!=='source';$('generated-panel').hidden=file!=='generated';for(const type of ['source','generated']){const selected=type===file;$(type+'-tab').classList.toggle('active',selected);$(type+'-tab').setAttribute('aria-selected',String(selected));}if(file==='source')view.focus();}
function showPanel(panel){activePanel=panel;for(const type of ['console','problems','log'])$(type+'-panel').hidden=type!==panel;document.querySelectorAll('.terminal-tab').forEach(button=>{const selected=button.dataset.panel===panel;button.classList.toggle('active',selected);button.setAttribute('aria-selected',String(selected));});}
function setBusy(value){busy=value;if(!value){programRunning=false;waitingForInput=false;inputClosed=false;updateInputControls();}for(const id of ['run-button','compile-button','translate-button'])$(id).disabled=value;$('stop-button').disabled=!value;$('progress-track').hidden=!value;$('runtime-dot').className='status-dot'+(value?' busy':'');}
function updateInputControls(){
  $('send-input').disabled=!busy||!waitingForInput||inputClosed;
  $('send-eof').disabled=!busy||!waitingForInput||inputClosed;
}
function sendInput(eof=false){
  if(!busy||!waitingForInput||!inputBuffer)return;
  const value=eof?'':$('stdin').value+( $('stdin').value.endsWith('\n')?'':'\n');
  try{
    if(!deliverInput(inputBuffer,value,eof)){toast('The program is no longer waiting for input.');return;}
    $('stdin').value='';waitingForInput=false;inputClosed=eof;updateInputControls();
    text('runtime-state',eof?'Running · input closed':'Running your program');
  }catch(error){toast(error.message);}
}
function setPhase(phase){
  text('runtime-state',phase);clearTimeout(timer);
  if(phase==='Running your program')programRunning=true;
  if(programRunning)return; // No execution deadline, including time spent waiting for input.
  const seconds=phase.includes('Loading')?180:90;
  timer=setTimeout(()=>terminate(`Stopped: ${seconds}-second preparation limit reached.`),seconds*1000);
}
function finish(message,failed=false){clearTimeout(timer);setBusy(false);text('runtime-state',message);if(failed)$('runtime-dot').classList.add('error');}
function terminate(reason='Stopped by you.'){if(!busy)return;worker?.terminate();worker=null;workerJobs=0;jobId++;finish(reason,true);text('run-result','Stopped');$('run-result').classList.add('failed');appendLog(reason+'\nThe next run will restart the compiler worker.');showPanel('log');}
function appendLog(value){if(!value)return;logs+=(logs?'\n':'')+value;if(logs.length>256*1024)logs=logs.slice(-256*1024);text('build-log',logs);}
function refreshDiagnostics(){
  diagnostics=parseDiagnostics(logs,sourceSnapshot,generated);
  const unique=new Map();for(const item of diagnostics)unique.set([item.file,item.line,item.column,item.severity,item.message].join('|'),item);
  diagnostics=[...unique.values()];text('problem-count',diagnostics.length);
  const panel=$('problems-panel');panel.replaceChildren();
  if(!diagnostics.length){const node=document.createElement('div');node.className='no-problems';node.textContent='No source diagnostics. See Build log for compiler or runtime messages.';panel.append(node);}
  for(const item of diagnostics){
    const button=document.createElement(item.offset===null?'div':'button');button.className='problem-item '+item.severity;
    const location=document.createElement('span');location.className='problem-location';location.textContent=`${item.severity.toUpperCase()} · ${item.file}:${item.line}:${item.column}`;
    const message=document.createElement('span');message.className='problem-message';message.textContent=item.message;
    button.append(location,message);
    if(item.offset!==null){
      const snippet=document.createElement('span');snippet.className='problem-snippet';snippet.textContent=sourceSnapshot.split('\n')[item.line-1]||'';button.append(snippet);
      button.addEventListener('click',()=>{
        if(view.state.doc.toString()!==item.source){toast('Source changed. Compile again to refresh error locations.');return;}
        showFile('source');const offset=Math.min(item.offset,view.state.doc.length),line=view.state.doc.lineAt(offset);
        view.dispatch({selection:{anchor:offset},effects:[EditorView.scrollIntoView(offset,{y:'center'}),decorationsEffect.of(Decoration.set([Decoration.line({class:'cm-error-line'}).range(line.from)]))]});view.focus();
      });
    }
    panel.append(button);
  }
}
function attachWorker(){
  worker=new Worker(new URL('./compiler.worker.js',import.meta.url),{type:'module'});
  worker.addEventListener('message',({data})=>{
    if(data.id!==jobId||!busy)return;
    const {kind,value}=data;
    if(kind==='phase')setPhase(value);
    else if(kind==='input-state'){waitingForInput=value.waiting;inputClosed=!!value.eof;updateInputControls();text('runtime-state',value.waiting?'Waiting for input · type a value and press Send':value.eof?'Running · input closed':'Running your program');if(value.waiting){$('stdin').focus();}}
    else if(kind==='log'){appendLog(value);refreshDiagnostics();}
    else if(kind==='generated'){
      generated=value;generatedSource=sourceSnapshot;
      generatedView.dispatch({changes:{from:0,to:generatedView.state.doc.length,insert:value}});
      text('generated-note','Standard C generated by your C frontend. Compile or Run checks the complete program.');
    }
    else if(kind==='stdout'||kind==='stderr'){
      if(kind==='stderr')appendLog(value);
      outputBuffer.append(value);stdout=outputBuffer.text();text('console-output',(outputBuffer.truncated?'[Earlier output hidden to keep the console responsive]\n':'')+stdout);$('console-empty').hidden=true;
      const panel=$('console-panel');panel.scrollTop=panel.scrollHeight;
    }
    else if(kind==='compiled')appendLog(`Linked successfully · ${(value.bytes/1024).toFixed(1)} KiB WebAssembly`);
    else if(kind==='complete'){
      const duration=(value.elapsed/1000).toFixed(2)+' s';
      const label=value.action==='run'?`Exit ${value.exitCode} · ${duration}`:value.action==='compile'?`Compiled · ${duration}`:`Translated · ${duration}`;
      text('run-result',label);$('run-result').classList.toggle('failed',value.action==='run'&&value.exitCode!==0);
      appendLog(label);refreshDiagnostics();
      finish(value.action==='run'?(value.exitCode===0?'Finished successfully':`Program returned ${value.exitCode}`):value.action==='compile'?'Compiled successfully':'Translation complete',value.action==='run'&&value.exitCode!==0);
      if(value.action==='translate')showFile('generated');
      if(value.action!=='run')showPanel(diagnostics.some(d=>d.severity==='error')?'problems':'log');
      else if(!stdout){$('console-empty').hidden=true;}
    }
    else if(kind==='failure'){
      if(value.log&&!logs.includes(value.log))appendLog(value.log);
      appendLog(value.message);refreshDiagnostics();text('run-result','Failed');$('run-result').classList.add('failed');finish(value.message,true);showPanel(diagnostics.length?'problems':'log');
      // A runtime trap may leave toolchain state unusable; start clean next time.
      if(value.phase==='runtime'||value.phase==='frontend'){worker?.terminate();worker=null;workerJobs=0;}
    }
  });
  worker.addEventListener('error',event=>{if(!busy)return;appendLog(event.message||'The browser worker failed.');finish('Worker failed. Try Run again.',true);text('run-result','Failed');showPanel('log');worker?.terminate();worker=null;workerJobs=0;});
}
function perform(action){
  if(busy)return;
  const source=view.state.doc.toString();
  if(new TextEncoder().encode(source).length>1024*1024){toast('Source exceeds the 1 MiB limit.');return;}
  if(action==='run'&&new TextEncoder().encode($('stdin').value).length>65536){toast('Input exceeds the 64 KiB limit.');return;}
  // Recycle compiler memory periodically; the browser can reuse cached static assets.
  if(workerJobs>=15){worker?.terminate();worker=null;workerJobs=0;}
  const cold=!worker;
  if(!worker)attachWorker();
  sourceSnapshot=source;generated='';logs='';stdout='';diagnostics=[];outputBuffer=new OutputBuffer();programRunning=false;waitingForInput=false;inputClosed=false;
  const initialInput=$('stdin').value;
  inputBuffer=action==='run'&&typeof SharedArrayBuffer==='function'&&globalThis.crossOriginIsolated?createInputBuffer():null;
  if(action==='run')$('stdin').value='';
  updateInputControls();
  generatedView.dispatch({changes:{from:0,to:generatedView.state.doc.length,insert:''}});text('generated-note','Waiting for a successful translation.');
  text('console-output','');text('build-log','');text('run-result','');text('problem-count','0');$('run-result').classList.remove('failed');$('console-empty').hidden=true;
  view.dispatch({effects:decorationsEffect.of(Decoration.none)});
  refreshDiagnostics();showPanel(action==='run'?'console':'log');setBusy(true);setPhase(cold?'Loading tools · first download about 29 MB':'Checking your code');
  saveDraft();jobId++;workerJobs++;
  worker.postMessage({id:jobId,action,source,config,input:initialInput,inputBuffer});
}
function replaceSource(source){view.dispatch({changes:{from:0,to:view.state.doc.length,insert:source},selection:{anchor:0}});showFile('source');closeMenu();}
function download(){
  const value=activeFile==='generated'?generatedView.state.doc.toString():view.state.doc.toString();
  if(!value&&activeFile==='generated'){toast('Translate your code first.');return;}
  const url=URL.createObjectURL(new Blob([value],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=activeFile==='generated'?'generated.c':'main.myc';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('File downloaded.');
}
function goToLine(){const value=prompt(`Go to line (1–${view.state.doc.lines})`);if(value===null)return;const number=Number(value);if(!Number.isInteger(number)||number<1||number>view.state.doc.lines){toast('Enter a valid line number.');return;}showFile('source');const line=view.state.doc.line(number);view.dispatch({selection:{anchor:line.from},effects:EditorView.scrollIntoView(line.from,{y:'center'})});view.focus();}
const definitions=[
  ['hello','Hello, world','01',''],['all_features','All 13 keywords','02','2\n'],['star_pattern','Star pattern','03','5\n'],
  ['error_demo','Spot the error','04','']
];
examples.error_demo='#include <stdio.h>\n\nint main(void) {\n  printf("Try changing printf to output!\\n");\n  provide 0;\n}\n';
for(const [key,title,icon,input]of definitions){
  const button=document.createElement('button');button.className='example-item';button.dataset.example=key;
  const number=document.createElement('span');number.className='example-icon';number.textContent=icon;
  const name=document.createElement('span');name.textContent=title;
  const arrow=document.createElement('span');arrow.className='arrow';arrow.textContent='↗';button.append(number,name,arrow);
  button.addEventListener('click',()=>{replaceSource(examples[key]);$('stdin').value=input;document.querySelectorAll('.example-item').forEach(b=>b.classList.toggle('selected',b===button));toast(key==='error_demo'?'This example contains a deliberate error. Run to find it.':`Loaded ${title}.`);});$('examples').append(button);
}
function keywordRow(alias,canonical){const row=document.createElement('div');row.className='keyword-row';for(const [name,value]of [['alias',alias],['map-arrow','→'],['canonical',canonical]]){const span=document.createElement('span');span.className=name;span.textContent=value;row.append(span);}return row;}
for(const [alias,canonical]of keywords){$('keyword-list').append(keywordRow(alias,canonical));$('help-keywords').append(keywordRow(alias,canonical));}
const backdrop=document.createElement('button');backdrop.className='menu-backdrop';backdrop.setAttribute('aria-label','Close workspace');document.body.append(backdrop);
function closeMenu(){$('sidebar').classList.remove('open');$('menu-toggle').setAttribute('aria-expanded','false');backdrop.classList.remove('visible');}
$('menu-toggle').addEventListener('click',()=>{const open=$('sidebar').classList.toggle('open');$('menu-toggle').setAttribute('aria-expanded',String(open));backdrop.classList.toggle('visible',open);});backdrop.addEventListener('click',closeMenu);
for(const id of ['help-button','about-button','language-help'])$(id).addEventListener('click',()=>{$('help-dialog').showModal();closeMenu();});
for(const id of ['close-help','help-done'])$(id).addEventListener('click',()=>$('help-dialog').close());
$('source-tab').addEventListener('click',()=>showFile('source'));$('generated-tab').addEventListener('click',()=>showFile('generated'));$('main-file').addEventListener('click',()=>{showFile('source');closeMenu();});
for(const action of ['run','compile','translate'])$(action+'-button').addEventListener('click',()=>perform(action));
$('send-input').addEventListener('click',()=>sendInput(false));$('send-eof').addEventListener('click',()=>sendInput(true));
$('stdin').addEventListener('keydown',event=>{if(busy&&(event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();event.stopPropagation();sendInput(false);}});
$('stop-button').addEventListener('click',()=>terminate());$('download-source').addEventListener('click',download);$('go-line').addEventListener('click',goToLine);
$('new-file').addEventListener('click',()=>{replaceSource('int main(void) {\n  provide 0;\n}\n');$('stdin').value='';toast('New program ready.');});
$('open-file').addEventListener('click',()=>$('file-input').click());$('file-input').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;if(file.size>1024*1024){toast('File exceeds the 1 MiB limit.');event.target.value='';return;}try{replaceSource(await file.text());toast('Opened '+file.name);}catch{toast('Could not read this file.');}event.target.value='';});
for(const button of document.querySelectorAll('.terminal-tab'))button.addEventListener('click',()=>showPanel(button.dataset.panel));
$('copy-output').addEventListener('click',async()=>{const value=activePanel==='console'?stdout:activePanel==='log'?logs:diagnostics.map(d=>`${d.file}:${d.line}:${d.column}: ${d.severity}: ${d.message}`).join('\n');try{await navigator.clipboard.writeText(value);toast('Copied to clipboard.');}catch{toast('Clipboard unavailable. Select the text and copy it.');}});
$('clear-output').addEventListener('click',()=>{if(busy){toast('Stop the program before clearing results.');return;}logs='';stdout='';diagnostics=[];text('console-output','');text('build-log','');text('run-result','');text('problem-count','0');$('console-empty').hidden=false;refreshDiagnostics();view.dispatch({effects:decorationsEffect.of(Decoration.none)});toast('Results cleared.');});
window.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();perform('run');}if(event.key==='Escape')closeMenu();});
window.addEventListener('pagehide',()=>{clearTimeout(saveTimer);saveDraft();});
updatePosition();saveDraft();
