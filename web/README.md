# C Compiler — Browser Workspace

Our browser app uses the same thirteen custom keywords as the desktop compiler. It runs the C frontend, Clang, and the resulting WebAssembly program on the user's device.

**Live app:** https://c-compiler-raunit.vercel.app/

## Our team

- Satyajeet Singh
- Yug Sharma
- Raunit Singh
- Ayush Kestwal

## Run a program

1. Open an example or enter source in `main.myc`.
2. Click Run code (Ctrl+Enter in the editor).
3. When the program asks for input, enter a value in Program input and click Send input. Ctrl+Enter in that input box sends it too. A newline is added, as when pressing Enter in a terminal.
4. Send additional answers when requested. Optional values entered before Run are read first.
5. Use Send EOF to close input. Use Stop to terminate the worker, including a program blocked reading input or running an infinite loop.

**There is no program execution time limit.** The program continues until it exits, encounters a runtime error, or the user presses Stop. Compilation still has a preparation deadline so a broken build can be cancelled. Browsers may suspend or close background pages; this does not provide an always-on hosted process.

The console keeps recent output in fixed memory. Excessive printing discards old display text rather than ending the program. The output stream is UTF-8 decoded across writes. Input submissions are limited to 64 KiB and source to 1 MiB.

## Compiler behavior

The mapping is fixed in the web interface: output/printf, input/scanf, each/for, when/if, given/else, until/while, execute/do, choose/switch, match/case, otherwise/default, snap/break, so_on/continue, provide/return. Standard replaced spellings are rejected in submitted code. Strings and comments keep their contents. `until` repeats while its condition is true.

Translate checks lexical rules and shows standard C. Compile also performs C syntax/type checking and links. Run executes only a successful build. Failed builds clear the old executable. Diagnostics map generated C positions to original source, accounting for changed alias lengths, UTF-8 columns, BOM, CRLF, CR, and line splicing. Clicking a current diagnostic selects the original location; changed source requires a fresh build.

A separate runtime translation unit disables stdio buffering so prompts appear before input is requested. The C source itself is not prefixed or otherwise shifted to do this.

## Files and build

- `src/engine.js`: C translation, Clang compilation/linking, bounded WASI output, and execution.
- `src/compiler.worker.js`: worker protocol, buffered output, and blocking stdin callback.
- `src/input-channel.js`: a bounded SharedArrayBuffer/Atomics bridge; only the worker blocks.
- `src/output-buffer.js`: a fixed-size UTF-8 output ring.
- `src/diagnostics.js`: original-source positions.
- `src/main.js`, `index.html`, `src/style.css`: existing editor, results, input, and navigation.
- `scripts/prepare-compiler.mjs`: copies toolchain assets from npm and builds the browser frontend from the repository's C sources. It replaces native `tmpfile()` with a private in-memory WASI file.
- `tests/`: actual compiler/runtime, control-flow, diagnostic, stdin, EOF, Stop, and output-buffer checks.

From the repository root:

```sh
npm --prefix web ci
npm --prefix web run dev
npm --prefix web test
npm --prefix web run build
```

Use the URL printed by Vite. Production output is `web/dist/`. Vercel builds from the root `vercel.json`.

Live input requires a secure, cross-origin-isolated page with SharedArrayBuffer support. The root Vercel configuration supplies COOP and COEP headers. An HTTP preview on a non-localhost host cannot provide live input; it reports that limitation rather than silently returning EOF. Regular localhost development and the HTTPS production site support the intended path in compatible browsers.

The first toolchain load is about 29 MB. This is Clang/WASI, rather than desktop GCC or a full operating system. Native GUI libraries, sockets, and real device filesystem access are unavailable. C undefined behavior and memory exhaustion are not comprehensively diagnosed. There is no debugger added in this review.

## Credits

We use CodeMirror, @live-codes/clang-wasm, LLVM/Clang, WASI, and their dependencies under their respective licenses. See `public/THIRD-PARTY-NOTICES.md`. These third-party components were not written by our group.
