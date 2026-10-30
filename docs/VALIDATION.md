# Our validation record

The earlier package validation recorded 42 passing tests: 9 translator, 12 backend, 12 strict-language and 9 GUI tests. This is a historical baseline; the current review results appear below.

That earlier validation used Linux, GCC and Tk widgets in a virtual display. Native Windows execution was not available. The current environment has no display server, so the changed Tk interface has not been revalidated visually.

Our validation commands from the project root are:

```sh
python custom-keywords/tests/test_translation.py
python tests/test_backend.py
python tests/test_strict_language.py
python tests/test_gui.py
```

The GUI suite needs a graphical or virtual display. The other suites run without one. `docs/TEST_RESULTS.txt` contains the earlier package results, not the results of the runtime review below.

Coverage includes all thirteen forbidden standard spellings, accepted custom examples, comments/strings, malformed source/configuration, numeric/literal boundaries, line endings and continuations, renamed alias lengths, Unicode/tabs, foreign-language examples, unknown functions, missing semicolons, real generated executables, live input and EOF, cancellation, bounded output display, local headers and paths with spaces.

GUI checks invoke Run, Compile, Translate, Send and Stop, verify error highlighting and source navigation, jump to an invalid Keywords entry, exercise Go to line and help, and round-trip source Open/Save with controlled picker paths. Not every dialog, platform, language construct or possible failing program is covered. Compiler error detection is not a proof of program correctness.

The existing screenshot belongs to the earlier Tk package validation. The separate arithmetic reference is retained but is not the strict GUI compiler backend.


## Runtime and input review — 29 October 2026

Program execution deadlines were removed from the desktop and browser interfaces. Compilation/preparation deadlines remain. Long output is bounded for display rather than terminating the program. Desktop preloaded input is ordered before live input and EOF.

The browser source and root Vercel configuration are now included in the repository, addressing the previous deployment that attempted to build a repository without the browser files. Toolchain binaries are reproduced from pinned npm dependencies during the build. Live browser stdin uses a shared-memory channel and cross-origin isolation headers; only the worker waits, so Stop remains available.

Automated checks completed locally: 72 WebAssembly/compiler/input tests passed; the desktop backend/diagnostic suite passed (26 tests reported, Tk GUI setup skipped); 9 C translator regression tests passed. The shared matrix includes 21 control-flow/input programs compiled through both GCC and Clang/WASI. Cases include empty loops, omitted for clauses, negative steps, nested loops, break/continue equivalents, switch fall-through/default, character/string/float input, invalid conversions, fgets, and EOF. Further tests reject malformed control flow and test runtime division by zero, failed-build recovery, UTF-8 output boundaries, and CR-only source locations.

Chrome's managed HTTP preview confirmed hello execution, an infinite loop continuing beyond the former execution deadline until Stop, and successful recompilation after Stop. The preview must start from the repository root so the browser build can read the native frontend sources. Live-input bridge tests execute real WebAssembly in Node workers and validate prompt-before-read, successive input, preloaded-to-live ordering, EOF, and worker termination while blocked. The managed HTTP preview cannot enable SharedArrayBuffer; production HTTPS browser checks are recorded separately when completed.

Limits: these are representative regression cases, not a proof that every possible C program or undefined behavior is handled. Windows execution and the Tk GUI have not been revalidated in this Linux environment because no display server is available. The arithmetic-to-assembly reference is unchanged.

### Production verification

Vercel successfully built commit `55a36ffd6bdf6514d0d43bf473e40be73a6415f4` from this repository. Chrome testing used the existing HTTPS address, https://c-compiler-raunit.vercel.app/, with no project or domain rename.

The live interface displayed an unterminated prompt, waited for two separate answers (4 and 7), and printed `Sum = 11`. That run lasted 22.24 seconds including input waits. A second program consumed preloaded 2 before live 3, then stopped its input loop on Send EOF and printed `Sum = 5`. Stop ended a worker waiting for input. An infinite loop continued beyond the former execution deadline until Stop. Subsequent programs compiled successfully.

The live Problems panel reported forbidden `printf` at original line 3, column 3; clicking it moved the editor to that position. A malformed `each` loop received the compiler's missing-semicolon diagnostic at original line 2, column 19. The original source, rather than the shorter translated C spelling, determined that position.

A fresh frontend build and production asset build succeeded locally; the Vercel deployment also succeeded. Physical mobile browsers, Firefox, Safari, Windows process handling, and the changed Tk widgets remain unverified. A browser may suspend a background tab or close a page under memory pressure; unlimited execution time does not make the app an always-on remote service.

## Indentation review — 30 October 2026

All 117 browser tests pass, including 45 formatter/editor checks. Each of the 21 shared control-flow/input programs was formatted, compiled with the actual frontend and Clang/WASI, and checked against its expected output. The tests also verify idempotence, preservation of tokens, strings and comments, standard-spelling rejection after formatting, directives and line splices, and Enter-key indentation for custom controls and switch labels.

The production build succeeds with the formatter WASM bundled as a same-origin Vite asset. Chrome preview checks confirmed the Format code button, Alt+Shift+F, Undo restoring compact source, automatic formatting before Run, and a nested each/when/given program printing `1 even 3 even ` from input 4. Enter after an indented `match` label moved the cursor to column 13 for its body.

The formatter uses a canonical parser copy and restores the original tokens. The compiler still enforces the custom vocabulary. Formatting is an editor change: diagnostics and line-sensitive macros use the displayed layout. The desktop GUI and compiler language rules are unchanged by this indentation update.
