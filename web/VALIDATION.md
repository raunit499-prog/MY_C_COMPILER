# Browser validation

See [the project validation report](../docs/VALIDATION.md) for the review and limitations.

Locally confirmed: 72 Node tests execute the actual C frontend, Clang linker, WASI runtime, and live-input bridge. All pass. They include 21 shared GCC/Clang control-flow and input cases, forbidden spellings, syntax errors, original positions, UTF-8, runtime traps, recovery, live input, EOF, blocking-read Stop, and bounded output.

The browser no longer has an execution timer. Automated bridge tests verify live stdin; browser UI and production checks must be distinguished from those tests. Windows, physical Android/iOS devices, and exhaustive C undefined behavior are not verified by these tests.
