// Translate compiler byte columns into editor positions in the original custom source.
const tokens = text => [...text.matchAll(/\/\/[^\n]*|\/\*[\s\S]*?\*\/|(?:u8|[LuU])?(?:"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*')|[A-Za-z_\u0080-\uffff][\w\u0080-\uffff]*|\s+|[\s\S]/g)];
export function normalizedSource(source) {
  let text = '', positions = [];
  for (let i = source.startsWith('\ufeff') ? 1 : 0; i < source.length; i++) {
    positions.push(i);
    if (source[i] === '\r') { text += '\n'; if (source[i + 1] === '\n') i++; }
    else text += source[i];
  }
  let result = '', offsets = [];
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '\\' && text[i + 1] === '\n') { i++; continue; }
    result += text[i]; offsets.push(positions[i]);
  }
  offsets.push(source.length);
  return { text: result, offsets };
}
export function sourceMapping(source, generated) {
  const {text, offsets} = normalizedSource(source), a = tokens(text), b = tokens(generated);
  if (a.length !== b.length) return null;
  const result = [];
  for (let i = 0; i < a.length; i++) {
    for (let j = 0; j < b[i][0].length; j++) {
      result.push(offsets[a[i].index + (a[i][0] === b[i][0] ? j : 0)]);
    }
  }
  result.push(source.length); return result;
}
function lineStarts(text){return [0,...[...text.matchAll(/\r\n|\r|\n/g)].map(match=>match.index+match[0].length)];}
function byteOffset(text,row,column){
  const starts=lineStarts(text),begin=starts[row-1]??text.length,end=starts[row]??text.length;
  let offset=begin,bytes=0;
  for(const char of text.slice(begin,end).replace(/[\r\n]+$/,'')){
    const size=new TextEncoder().encode(char).length;if(bytes+size>column-1)break;bytes+=size;offset+=char.length;
  }
  return Math.min(offset,text.length);
}
export function parseDiagnostics(log, source, generated = '') {
  const map = generated ? sourceMapping(source, generated) : null;
  const result = [];
  for (const line of log.split('\n')) {
    const match = line.match(/^(.+?):(\d+):(\d+):\s*(fatal error|error|warning|note):\s*(.*)$/);
    if (!match) continue;
    const [, file, row, column, severity, message] = match;
    const isGenerated = /(^|\/)generated\.c$/.test(file);
    const isSource = /(^|\/)source\.myc$/.test(file);
    let offset = null;
    if (isGenerated && map) offset = map[byteOffset(generated, +row, +column)];
    if (isSource) offset = byteOffset(source, +row, +column);
    if (offset !== null && offset !== undefined) {
      const starts=lineStarts(source);let row=0;while(row+1<starts.length&&starts[row+1]<=offset)row++;
      result.push({file:'main.myc', line:row+1, column:offset-starts[row]+1,
        severity, message, offset, source});
    } else result.push({file, line:+row, column:+column, severity, message, offset:null, source});
  }
  return result;
}
