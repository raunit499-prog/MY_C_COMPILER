# My C Compiler

I built this project to experiment with my own C-like language. My frontend is written in C, my desktop interface uses Python/Tkinter, and GCC compiles the generated standard C into a native executable.

## My strict vocabulary

My programs must use these custom spellings. The standard spelling on the left is rejected as a complete identifier in submitted program code, including macro bodies. Strings and comments may contain these words as text.

| Standard C spelling (rejected) | My spelling (accepted) |
| --- | --- |
| `printf` | `output` |
| `scanf` | `input` |
| `for` | `each` |
| `if` | `when` |
| `else` | `given` |
| `while` | `until` |
| `do` | `execute` |
| `switch` | `choose` |
| `case` | `match` |
| `default` | `otherwise` |
| `break` | `snap` |
| `continue` | `so_on` |
| `return` | `provide` |

I still use C types and punctuation: int, void, char, braces, parentheses, semicolons, operators, and preprocessor directives such as #include. I have not renamed every word in the C language. The C implementation itself, generated C, included standard headers, and the separate arithmetic reference compiler naturally contain standard C words.

**until keeps while behavior: it repeats while the condition is true.** It does not invert the condition. execute { ... } until (condition); runs its body at least once.

## A working program

```c
#include <stdio.h>

int main(void) {
    int number;
    output("Enter a number: ");
    when (input("%d", &number) != 1) {
        output("Invalid input.\n");
        provide 1;
    }
    each (int i = 0; i < number; i++) {
        when (i == 2) so_on;
        when (i == 10) snap;
        output("%d\n", i);
    }
    provide 0;
}
```

Writing printf, scanf, for, if, else, while, do, switch, case, default, break, continue, or return as program identifiers raises an error naming the required custom word. All thirteen mappings are required; the configuration cannot restore their standard spellings. Alias names remain editable, but the program must use the current configuration.

## Start on Windows

1. Extract MY_C_COMPILER.zip. Do not run from inside the ZIP viewer.
2. Install Python 3.10 or newer with Tcl/Tk, and GCC 11 or newer.
3. Open the extracted MY_C_COMPILER folder.
4. Double-click START_GUI.bat.
5. If needed, click Choose GCC and select the actual gcc.exe.
6. Click Run or press F5 to run the Hello World example.

For MSYS2 UCRT64, GCC is usually C:\msys64\ucrt64\bin\gcc.exe. Python and GCC are installed separately; I have not bundled their runtimes.

Manual launch from PowerShell:

```powershell
py -3 gui\app.py
```

## Linux desktop

Install Python with Tkinter and GCC 11 or newer, then run from the extracted folder:

```sh
sh START_GUI.sh
```

A graphical desktop is required for this Tkinter application. It is not a website or an Android APK. No pip dependencies are required for normal use.

## My interface

- **Source / Generated C / Keywords:** edit my language, inspect the translation, or edit the dictionary.
- **Translate:** perform lexical translation only. Compile and Run additionally check C syntax/types using GCC.
- **Compile / Run / F5:** compile the current editor/configuration snapshot; Run starts the executable after a successful build.
- **Problems:** show errors, warnings and notes with original source line/column positions. Double-click or press Enter on a problem to jump to it. Configuration errors jump to Keywords.
- **Error highlights:** show error lines and the reported character in the appropriate editor. Editing clears old highlighting; stale problem navigation asks for a fresh build.
- **Build log:** show GCC/translator output with original source excerpts and caret markers. Messages about included headers retain their real header paths.
- **Go to line / Ctrl+G:** jump to a source line.
- **Language help:** show all thirteen default mappings and the main language rules.
- **Progress indicator:** animate while a build/run is active.
- **Examples:** Hello World, all keywords, number guessing, and star pattern.
- **Program input:** preload values or choose the execution timeout.
- **stdin / Send:** send a line to the running program. Send EOF closes input; Stop requests termination.
- **New / Open / Save / Save keywords:** manage source/configuration files.
- **Export program:** copy a current successful executable to a permanent destination.

The vocabulary table displays all thirteen configured pairs. The first build creates the C frontend; later builds cache it until its source or selected GCC path changes.

## My diagnostics

I used the C workflow in OnlineGDB and GCC's diagnostic documentation as references for compilation feedback. My application uses GCC's actual diagnostics; it is not affiliated with OnlineGDB and does not include its website or a GDB debugger.

My C scanner rejects forbidden standard spellings and malformed literals/comments. GCC checks the translated program's declarations, expressions, syntax and types. Unknown function calls are errors rather than permissive implicit declarations. Failed builds are never run.

In the GUI, I map reported generated-C locations back to the original custom source. This accounts for alias length changes, CRLF normalization, ordinary backslash-newline continuations, UTF-8 byte columns, and tabs. The log shows a source excerpt and caret; Problems lets me jump to the reported character. Native scanner errors also retain original source positions after normalization.

Example:

```text
source.myc:4:5: error: standard spelling 'printf' is disabled; use 'output' instead
    4 |     printf("Hello");
      |     ^
```

GCC messages can mention standard C function names because GCC sees the translated source. The location and excerpt shown by the GUI refer to my original source. Some errors are reported at the next token, at end-of-file, inside an included header, or by the linker; not every failure has a unique source character. This is how real compiler diagnostics work too. Correct syntax does not prove correct program logic, and runtime undefined behavior is not exhaustively detected.

Python, Java, JavaScript, or C++ examples with syntax that is not valid in my language fail compilation. Source text that happens to be valid in more than one language cannot reliably be classified by its intended language. File extensions do not determine acceptance.

## Input and execution limits

- At most 1 MiB of source with no embedded NUL bytes.
- At most 63 ASCII identifier characters per alias, starting with a letter.
- At most 64 KiB of preloaded stdin.
- Default execution timeout: 30 seconds, including time waiting for input; selectable up to 300 seconds.
- Output cap: 512 KiB per run.
- Compiler-command deadline: 45 seconds.

The C translator preserves identifiers in preprocessor directives rather than translating custom spellings there. Standard directive names such as #if remain allowed, while forbidden identifiers in macro bodies are rejected. Use standard C in separately included headers: they are processed by GCC, not by my custom scanner. Advanced preprocessing, explicit #line remapping and compiler extensions can limit source mapping; diagnostics from those constructs remain best-effort. This tool is intended for my own local programs, not isolated execution of untrusted public submissions.

## Project files

| Path | My responsibility for this part |
| --- | --- |
| custom-keywords/src/ | C dictionary validation, source scanning and strict vocabulary checks. |
| custom-keywords/keywords.cfg | My thirteen configurable spellings. |
| custom-keywords/examples/ | Programs using provide, snap and so_on as well as the other custom words. |
| gui/app.py | Native Tk editor, controls, problem navigation, highlights and help. |
| gui/backend.py | Translation, GCC processes, live input/output, cancellation and execution limits. |
| gui/diagnostics.py | Mapping generated diagnostic positions back to custom source. |
| gui/runtime_io.h | Immediate output prompts through GUI pipes. |
| tests/ | Backend, strict-language and GUI regression tests. |
| custom-keywords/tests/ | C translator regression tests. |
| my-c-compiler/ | My separate arithmetic-to-assembly learning reference; it is not the GUI backend or strict dialect compiler. |
| docs/VALIDATION.md | Current verification and platform limits. |

Generated build files and Python caches are not shipped. settings.json, saved source files and exported executables are created during use.

## Command-line frontend

From the project folder on Linux:

```sh
mkdir -p build
gcc -std=c11 -Wall -Wextra -Wpedantic custom-keywords/src/main.c custom-keywords/src/keywords.c custom-keywords/src/translate.c -o build/customc
./build/customc custom-keywords/keywords.cfg custom-keywords/examples/hello.myc build/hello.c
gcc -std=c11 build/hello.c -o build/hello
./build/hello
```

The standalone translator checks lexical rules; it does not itself invoke GCC. The GUI adds full compilation, original-source GCC diagnostic mapping and execution controls.

## References

- https://www.onlinegdb.com/online_c_compiler
- https://docs.onlinegdb.com/IDE/
- https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html
- https://www.python.org/downloads/
- https://www.msys2.org/
