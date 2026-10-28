# Arithmetic compiler validation

Verified on Linux x86-64 with GCC:

- The compiler builds with `-std=c11 -Wall -Wextra -Wpedantic -Werror`.
- 55 valid programs compile, assemble, link and run. Their exit statuses match
  independently compiled GCC reference programs. Cases cover precedence,
  parentheses, associativity, signs, signed division and nested expressions.
- All three bundled sample programs return their documented values.
- 21 invalid inputs are rejected without creating an assembly output file.
  Cases include malformed syntax, unsupported features, oversized literals,
  invalid comments, embedded NUL bytes and the documented input limits.
- Token-viewer output includes the expected text and line/column positions.

Windows execution was not available in the documented test environment. The Windows
backend and PowerShell instructions are included, but native Windows assembly,
linking and execution still need to be checked on your x64 GCC installation.
The compiler is a teaching implementation, not a complete C implementation.
