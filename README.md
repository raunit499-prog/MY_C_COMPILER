# C Compiler — Group Project

**Live web app:** [Open C Compiler](https://c-compiler-raunit.vercel.app/)

We developed this project to explore how a custom C-like language can be translated, compiled, and run. Our frontend is written in **C**, our desktop interface uses **Python and Tkinter**, and **GCC** compiles the generated standard C into a native executable.

Our work focuses on the keyword frontend, its connection to GCC, and the desktop interface. We use GCC as the native compilation backend; we do not claim to have written GCC or a complete C implementation from scratch.

## Our team

- **Satyajeet Singh**
- **Yug Sharma**
- **Raunit Singh**
- **Ayush Kestwal**

## Try the web app

Our browser version is hosted on **Vercel**:

**[https://c-compiler-raunit.vercel.app/](https://c-compiler-raunit.vercel.app/)**

Open this link in a recent browser on a computer or phone. You do not need to install Python, Tkinter, or GCC to use the website.

1. Choose **Hello, world** or **All 13 keywords** from the example menu. On a smaller screen, open the workspace menu to find the examples.
2. Write or edit a program using our thirteen custom keywords.
3. If the program reads input, you can preload values or wait until it asks. Type a value in **Program input** and click **Send input** (Ctrl+Enter in that box). Use **Send EOF** when you want to close input.
4. Click **Run code**, or press **Ctrl+Enter** (**Command+Enter** on a Mac).
5. Read the **Console**. Click an entry in **Problems** to jump to its reported source line and column.

**Translate** shows the generated standard C. **Compile** translates, compiles, and links without running. **Run code** also executes the compiled program. **Stop** terminates the browser worker; the next action starts a new worker.

The web editor applies **four-space indentation** before Translate, Compile, or Run. Press **Enter** for an indented new line, or use **Format code** (**Alt+Shift+F**) to format the whole program. **Tab** and **Shift+Tab** adjust indentation. Formatting can be undone with Ctrl+Z. Error locations refer to the source displayed after formatting.

The first compilation downloads about **30 MB** of compiler and formatter tools from the site, so allow time for that initial load. Later loads may benefit from browser caching.

### How the browser version works

Our C frontend translates the custom keywords into standard C. **Clang/WASI** then compiles and links that C into **WebAssembly**, which runs in a separate browser worker. Vercel hosts the website and its assets; compilation takes place on the user's device rather than through a remote compiler API.

The web interface uses HTML, CSS, JavaScript, and CodeMirror. It uses the project's C frontend together with the third-party Clang/WASI toolchain; we do not claim authorship of those third-party tools.

| Version | Compiler/runtime | Input and setup |
| --- | --- | --- |
| **Live web app** | C keyword frontend, Clang, WebAssembly, and WASI in the browser. | No local compiler installation. Supports preloaded input and live input through Send input / Send EOF. |
| **Desktop application in this repository** | C keyword frontend and native GCC, with a Python/Tkinter interface. | Requires Python/Tkinter and GCC. Supports preloaded input and live input through stdin / Send. |
| **Arithmetic milestone in `my-c-compiler/`** | Our small C-to-x86-64 assembly compiler, followed by an assembler and linker. | Separate command-line learning compiler with the limited arithmetic features described in its own README. |

The web app uses the same thirteen default custom names and the same `until` behavior. Its keyword map is fixed in the interface. The desktop version allows its aliases to be configured.

The browser version has a **1 MiB** source limit and a **64 KiB** limit per input submission. **Program execution has no time limit:** it continues until the program finishes, encounters a runtime error, or you press Stop. Input stays open until you send EOF. The console keeps recent output in a bounded buffer without killing a program that prints continuously. Desktop operating-system commands, native GUI libraries, sockets, and access to the real machine filesystem are unavailable through this WASI runtime.

Our browser source is included in `web/`. The local desktop launch commands below describe the **desktop project**, unless a section explicitly says otherwise. Live browser input needs HTTPS (or localhost), cross-origin isolation, and a browser with SharedArrayBuffer support. The Vercel headers configure this isolation.

## Our custom vocabulary

Programs submitted to our custom-language frontend must use the spellings in the right-hand column. The corresponding standard names are rejected when they appear as complete identifiers in program code, including macro bodies. These words can still appear as ordinary text inside strings and comments.

| Standard C spelling (rejected) | Our spelling (accepted) |
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

We have changed selected names, rather than every word in C. Types such as `int`, `void`, and `char` retain their usual names. Braces, parentheses, semicolons, operators, and preprocessor directives such as `#include` also keep their usual form.

The compiler implementation, generated C, included standard headers, and separate arithmetic reference compiler use ordinary C names. The strict vocabulary rules apply to source submitted to our custom-language frontend.

**`until` behaves exactly like C's `while`: it repeats while the condition is true.** It does not reverse the condition. Similarly, `execute { ... } until (condition);` behaves like a C `do ... while` loop and runs its body at least once.

## Example program

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

The frontend translates the custom names into standard C before GCC compiles the result. If a program uses one of the thirteen replaced standard names, the frontend reports an error and identifies the required custom spelling.

All thirteen mappings must be present. In the desktop version, the configuration can change an alias, but it cannot restore that mapping's original standard spelling. Desktop programs must use the aliases in the current configuration; the web app uses the fixed default map shown above.

## Getting started on Windows

1. Extract `MY_C_COMPILER.zip` into a writable folder. Do not launch the project from inside the ZIP viewer.
2. Install **Python 3.10 or newer**, including Tcl/Tk, and **GCC 11 or newer**.
3. Open the extracted `MY_C_COMPILER` folder.
4. Double-click `START_GUI.bat`.
5. If the application asks for GCC, click **Choose GCC** and select the actual `gcc.exe` file.
6. Click **Run**, or press **F5**, to try the included Hello World example.

For an MSYS2 UCRT64 installation, the usual GCC location is `C:\msys64\ucrt64\bin\gcc.exe`. Python and GCC must be installed separately; their runtimes are not bundled with this project.

To open the interface manually, run this command from the project folder in PowerShell:

```powershell
py -3 gui\app.py
```

## Getting started on a Linux desktop

Install Python with Tkinter and GCC 11 or newer. From the extracted project folder, run:

```sh
sh START_GUI.sh
```

This Tkinter application needs a graphical desktop. It is a desktop program, not a website or an Android APK. Normal use does not require additional pip packages.

## Using our desktop interface

| Feature | What it does |
| --- | --- |
| **Source / Generated C / Keywords** | Lets us write custom-language source, inspect its standard C translation, and edit the keyword dictionary. |
| **Translate** | Checks lexical rules and translates keywords. It does not perform the full syntax and type checks provided by GCC. |
| **Compile / Run / F5** | Builds a snapshot of the current source and configuration. Run starts the executable only after a successful build. |
| **Problems** | Lists errors, warnings, and notes with original source positions. Double-click an entry, or press Enter, to jump to it. Configuration errors open the Keywords editor. |
| **Error highlights** | Marks the reported line and character in the relevant editor. Editing clears old highlights; navigation to a stale problem requests a fresh build. |
| **Build log** | Shows translator and GCC messages, original source excerpts, and caret markers. Diagnostics from included headers keep their actual header paths. |
| **Go to line / Ctrl+G** | Moves to a chosen source line. |
| **Language help** | Explains the thirteen default mappings and the main language rules. |
| **Progress indicator** | Animates while compilation or execution is active. |
| **Examples** | Provides Hello World, all keywords, number guessing, and star pattern programs. |
| **Program input** | Lets us preload input values. Running programs have no execution deadline; Stop ends them. |
| **stdin / Send** | Sends a line to a running program. Send EOF closes its input, and Stop requests termination. |
| **New / Open / Save / Save keywords** | Creates, opens, and saves source or configuration files. |
| **Export program** | Copies a current, successfully built executable to a permanent destination. |

The vocabulary table shows all thirteen configured pairs. On the first build, the application builds the C frontend. Later builds reuse it until the frontend source or selected GCC path changes.

## How errors are reported

We referred to the C workflow in OnlineGDB and GCC's diagnostic documentation when designing compilation feedback. Our application displays actual GCC diagnostics. It is not affiliated with OnlineGDB, and it does not include the OnlineGDB website or a GDB debugger.

The checks happen in two main stages:

1. **Our C frontend** rejects forbidden standard spellings and malformed literals or comments.
2. **GCC** checks declarations, expressions, syntax, and types in the translated C program. Unknown function calls are treated as errors rather than accepted as implicit declarations.

A failed build is never executed.

Our GUI maps diagnostic locations in generated C back to the original custom-language source. The mapping accounts for different alias lengths, CRLF line-ending normalization, ordinary backslash-newline continuations, UTF-8 byte columns, and tabs. The build log shows the original source excerpt and a caret, while Problems provides navigation to the reported character. Native scanner errors also retain their original source positions after normalization.

For example:

```text
source.myc:4:5: error: standard spelling 'printf' is disabled; use 'output' instead
    4 |     printf("Hello");
      |     ^
```

GCC messages may mention standard C function names because GCC processes the translated program. The source location and excerpt shown by our GUI refer to the original custom-language code.

Some errors are reported at the next token, at the end of the file, in an included header, or by the linker. A failure does not always have one uniquely identifiable source character. Successful compilation also does not guarantee correct program logic, and runtime undefined behavior is not exhaustively detected.

Python, Java, JavaScript, or C++ source containing syntax that is invalid in our language fails compilation. However, text that is valid in more than one language cannot reliably be classified by its intended language. Acceptance depends on the submitted source and language rules, rather than the filename extension.

## Input and execution limits

| Item | Limit |
| --- | --- |
| Source file | At most **1 MiB**, with no embedded NUL bytes. |
| Configured alias | At most **63 ASCII identifier characters**, beginning with a letter. |
| Preloaded standard input | At most **64 KiB**. |
| Program execution | **No time limit.** Runs until completion, a runtime failure, or Stop. |
| Visible program output | Recent output is retained in a bounded console buffer. Older display text is discarded without stopping execution. |
| Compiler command | A **45-second** deadline. |

The translator leaves identifiers inside preprocessor directives unchanged rather than translating their custom spellings there. Standard directive names such as `#if` are allowed, while forbidden standard identifiers in macro bodies are rejected. Separately included headers should use standard C because GCC processes them without passing them through our custom scanner.

Advanced preprocessing, explicit `#line` remapping, and compiler extensions can limit source mapping. Diagnostics involving those constructs remain best-effort. This application is intended for our own local programs; it does not provide isolated execution for untrusted public submissions.

## Project structure

| Path | Purpose |
| --- | --- |
| `custom-keywords/src/` | Implements dictionary validation, source scanning, and strict vocabulary checks in C. |
| `custom-keywords/keywords.cfg` | Stores our thirteen configurable spellings. |
| `custom-keywords/examples/` | Contains programs using all custom words, including `provide`, `snap`, and `so_on`. |
| `gui/app.py` | Creates the Tk editor, controls, problem navigation, highlights, and help. |
| `gui/backend.py` | Handles translation, GCC processes, live input/output, cancellation, and execution limits. |
| `gui/diagnostics.py` | Maps generated diagnostic locations back to the custom source. |
| `gui/runtime_io.h` | Makes output prompts appear immediately through the GUI pipes. |
| `tests/` | Contains backend, strict-language, and GUI regression tests. |
| `custom-keywords/tests/` | Contains regression tests for the C translator. |
| `my-c-compiler/` | Contains our separate arithmetic-to-assembly learning reference. It is not the GUI backend or the strict dialect compiler. |
| `docs/VALIDATION.md` | Records verification results and platform limitations. |
| `web/` | Contains the browser interface, WASI runtime integration, live stdin bridge, and browser compiler tests. |
| `vercel.json` | Builds `web/` and supplies the response headers required for live input. |

Generated build files and Python caches are not included in the distributed project. Files such as `settings.json`, saved source files, and exported executables are created during use.

## Using the frontend from the command line

Run these commands from the project folder on Linux:

```sh
mkdir -p build
gcc -std=c11 -Wall -Wextra -Wpedantic custom-keywords/src/main.c custom-keywords/src/keywords.c custom-keywords/src/translate.c -o build/customc
./build/customc custom-keywords/keywords.cfg custom-keywords/examples/hello.myc build/hello.c
gcc -std=c11 build/hello.c -o build/hello
./build/hello
```

The standalone translator checks lexical rules and writes standard C; it does not invoke GCC itself. Our GUI connects that translation stage to full compilation, diagnostic mapping, and execution controls.

## Building the browser version

From the repository root, with Node.js 24 and npm installed:

```sh
npm --prefix web ci
npm --prefix web run dev
```

To check and build it:

```sh
npm --prefix web test
npm --prefix web run build
```

The production output is `web/dist/`. Vercel uses the root `vercel.json` to install and build the browser app. Compiler assets are copied from the pinned npm dependency, and the browser C frontend is built from `custom-keywords/src/`; generated binaries and `node_modules/` are not committed.

## References and tools

We use GCC, Python, Tkinter, and other established tools as part of the project. Their authorship remains with their respective developers.

- [OnlineGDB C compiler](https://www.onlinegdb.com/online_c_compiler)
- [OnlineGDB IDE documentation](https://docs.onlinegdb.com/IDE/)
- [GCC diagnostic formatting options](https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html)
- [Python downloads](https://www.python.org/downloads/)
- [MSYS2](https://www.msys2.org/)
