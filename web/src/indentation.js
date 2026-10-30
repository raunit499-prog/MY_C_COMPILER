import {EditorState} from '@codemirror/state';
import {cppLanguage} from '@codemirror/lang-cpp';
import {indentUnit,indentNodeProp,ensureSyntaxTree} from '@codemirror/language';
import {insertNewlineAndIndent} from '@codemirror/commands';
import {indentationShadow,codeTokens} from './formatting.js';
const language=cppLanguage.configure({props:[indentNodeProp.add({
    CaseStatement:context=>context.lineIndent(context.node.from)+context.unit
})]});
export function insertCustomNewline({state,dispatch}){
    if(state.readOnly)return false;
    const selection=state.selection.main,line=state.doc.lineAt(selection.head);
    const prefix=line.text.slice(0,selection.head-line.from),leading=/^\s*/.exec(prefix)[0];
    // An unfinished case has no body node yet in the incremental syntax tree.
    const label=codeTokens(state.doc.toString()).find(token=>token.from===line.from+leading.length);
    if(state.selection.ranges.length===1&&selection.empty&&
        (label?.text==='match'||label?.text==='otherwise')&&/:\s*$/.test(prefix)){
        const insert='\n'+leading+'    ';
        let to=selection.head;while(to<line.to&&/[ \t]/.test(state.doc.sliceString(to,to+1)))to++;
        dispatch(state.update({changes:{from:selection.head,to,insert},
            selection:{anchor:selection.head+insert.length},scrollIntoView:true,userEvent:'input'}));
        return true;
    }
    const shadow=EditorState.create({doc:indentationShadow(state.doc.toString()),selection:state.selection,
        extensions:[language,indentUnit.of('    '),EditorState.tabSize.of(4)]});
    ensureSyntaxTree(shadow,shadow.selection.main.head,50);
    return insertNewlineAndIndent({state:shadow,dispatch:transaction=>dispatch(state.update({
        changes:transaction.changes,selection:transaction.selection,scrollIntoView:true,userEvent:'input'
    }))});
}
