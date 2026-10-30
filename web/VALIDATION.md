# Browser validation

See [the project validation report](../docs/VALIDATION.md) for the review and limitations.

Locally confirmed on 30 October 2026: all 117 Node tests pass. They exercise the actual C frontend, Clang linker, WASI runtime, live-input bridge, formatter, and editor indentation. The 45 added formatting checks include all 21 shared control-flow/input programs after formatting, idempotence, token/string/comment preservation, forbidden spellings, directives and line splices, nested blocks, Enter after custom controls, and `match`/`otherwise` bodies. The other checks cover syntax errors, original positions, UTF-8, runtime traps, recovery, live input, EOF, blocking-read Stop, and bounded output.

The browser no longer has an execution timer. Chrome production checks on the unchanged Vercel address confirmed successive live input, preloaded-to-live ordering, explicit EOF, Stop while blocked, an infinite loop stopped by the user, error navigation, and recovery. The two-answer run completed successfully after 22.24 seconds including input waits. See the project report for exact programs/results and deployment commit.

Windows, the changed Tk GUI, physical Android/iOS devices, Firefox, Safari, and exhaustive C undefined behavior are not verified by these checks. Browsers can suspend background pages or close them under memory pressure.
