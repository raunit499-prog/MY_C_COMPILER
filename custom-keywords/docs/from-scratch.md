# How my strict frontend works

I keep my language's spellings in keywords.cfg. keywords_load loads all thirteen mappings, rejects omissions, duplicates, reserved collisions and aliases identical to their standard words. keywords.h shares the records between C modules.

My translator entry point, src/main.c, reads a source file, normalizes it, and calls translate_source. The scanner identifies complete words while preserving strings, character literals, comments and numbers. A standard spelling such as return causes an error recommending provide. A custom spelling such as provide becomes return in generated C.

I retain original byte line/column maps while normalizing CRLF/CR line endings and removing ordinary backslash-newline pairs. This lets native lexical errors point back to the original physical source. My source input is limited to 1 MiB; the position arrays follow that limit.

The scanner translates into a temporary stream before writing the final output, so lexical errors do not overwrite an existing destination. GCC compilation is a separate step. In the GUI, gui/backend.py manages both the translator and GCC and does not run a failed build.

My gui/diagnostics.py maps generated tokens and their locations back to the custom input. Unchanged tokens retain their character positions; positions within a replaced word map to that original word's start. GCC byte columns are converted into character offsets for Tk. Error excerpts come from the original source. A diagnostic event goes through the queue to gui/app.py, which populates Problems and marks the editor.

My GUI has a background worker for compilation/execution and a polling callback on the Tk thread for screen updates. Clicking a problem returns to Source or Keywords. If I edit the relevant text, the old diagnostic is no longer safe to navigate until I compile again.

## Meaning of my control-flow words

- each uses the ordinary three-part for-loop syntax.
- when and given implement if/else.
- until repeats while its condition is true.
- execute with until implements a do-while loop.
- choose, match and otherwise implement switch/case/default.
- snap leaves a loop or switch.
- so_on skips to the next loop iteration.
- provide returns a value from the current function.

My C implementation uses ordinary C because GCC builds it. Only submitted custom-language program text uses the renamed words. The independent arithmetic reference is under my-c-compiler/src/ and is not used by the GUI.

## Practice

1. Open Hello World and click Translate. output becomes printf and provide becomes return.
2. Run it and compare printed output with the separate process exit status.
3. Replace output with printf in the source; compile and inspect Problems.
4. Double-click the error, restore output, and run again.
5. Try the all-keywords example to exercise snap and so_on.

Refer to the root README for preprocessing limits, installation and diagnostic limitations. Compilers diagnose syntax/type errors, not every possible logic or runtime error.
