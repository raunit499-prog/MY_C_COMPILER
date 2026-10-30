// Format a canonical shadow copy, then restore every original C token.
// Clang-format sees real control statements; submitted keywords stay unchanged.
import {keywords} from './language.js';
import {normalizedSource} from './diagnostics.js';
const aliases=new Map(keywords);
const pattern=/\/\/[^\r\n]*|\/\*[\s\S]*?(?:\*\/|$)|(?:u8|[LuU])?(?:"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*')|[A-Za-z_\u0080-\uffff][\w\u0080-\uffff]*|(?:\d|\.\d)(?:[eEpP][+-]|[\w.])*|%:%:|>>=|<<=|\.\.\.|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||\*=|\/=|%=|\+=|-=|&=|\^=|\|=|##|<:|:>|<%|%>|%:|[^\s]/g;
export function codeTokens(text){return [...text.matchAll(pattern)].map(m=>({text:m[0],from:m.index,to:m.index+m[0].length,comment:m[0].startsWith('//')||m[0].startsWith('/*')}));}
export const FORMAT_STYLE=JSON.stringify({
    BasedOnStyle:'LLVM',IndentWidth:4,ContinuationIndentWidth:4,TabWidth:4,UseTab:'Never',
    ColumnLimit:100,IndentCaseLabels:true,BreakBeforeBraces:'Attach',
    AllowShortFunctionsOnASingleLine:'None',AllowShortBlocksOnASingleLine:'Never',
    AllowShortIfStatementsOnASingleLine:'Never',AllowShortLoopsOnASingleLine:false,
    SortIncludes:'Never',SortUsingDeclarations:'Never',ReflowComments:'Never',
    BreakStringLiterals:false,FixNamespaceComments:false,QualifierAlignment:'Leave',
    InsertBraces:false,RemoveBracesLLVM:false,RemoveParentheses:'Leave',RemoveSemicolon:false
});
export function formatProgram(source,formatter){
    const {text,offsets}=normalizedSource(source),tokens=codeTokens(text);
    let end=0;const pieces=[];
    for(const token of tokens){
        token.canonical=token.comment?token.text.replaceAll('clang-format','clang_format'):(aliases.get(token.text)||token.text);
        token.original=source.slice(offsets[token.from],offsets[token.to-1]+1);
        pieces.push(text.slice(end,token.from),token.canonical);end=token.to;
    }
    pieces.push(text.slice(end));
    const formatted=formatter(pieces.join(''),'main.c',FORMAT_STYLE),after=codeTokens(formatted);
    // Refuse a formatter result that adds, drops, or changes a non-comment token.
    if(after.length!==tokens.length||after.some((t,i)=>t.comment!==tokens[i].comment||(!t.comment&&t.text!==tokens[i].canonical)))
        throw new Error('Formatting could not preserve the original tokens. Your source was kept.');
    end=0;const result=[];
    after.forEach((token,i)=>{result.push(formatted.slice(end,token.from),tokens[i].original);end=token.to;});
    result.push(formatted.slice(end));return result.join('');
}
// Equal-length substitutions keep editor cursor positions while Enter is indented.
export function indentationShadow(source){
    let end=0;const result=[];
    for(const token of codeTokens(source)){
        const standard=aliases.get(token.text);
        result.push(source.slice(end,token.from),standard&&standard.length<=token.text.length?standard.padEnd(token.text.length):token.text);end=token.to;
    }
    result.push(source.slice(end));return result.join('');
}
