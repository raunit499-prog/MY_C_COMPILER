# Browser validation

See [the project validation report](../docs/VALIDATION.md) for the review and limitations.

Locally confirmed: 72 Node tests execute the actual C frontend, Clang linker, WASI runtime, and live-input bridge. All pass. They include 21 shared GCC/Clang control-flow and input cases, forbidden spellings, syntax errors, original positions, UTF-8, runtime traps, recovery, live input, EOF, blocking-read Stop, and bounded output.

The browser no longer has an execution timer. Chrome production checks on the unchanged Vercel address confirmed successive live input, preloaded-to-live ordering, explicit EOF, Stop while blocked, an infinite loop stopped by the user, error navigation, and recovery. The two-answer run completed successfully after 22.24 seconds including input waits. See the project report for exact programs/results and deployment commit.

Windows, the changed Tk GUI, physical Android/iOS devices, Firefox, Safari, and exhaustive C undefined behavior are not verified by these checks. Browsers can suspend background pages or close them under memory pressure.
