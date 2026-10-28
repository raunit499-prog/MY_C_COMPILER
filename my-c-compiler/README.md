# My C Compiler — first working milestone

This is my first compiler milestone: a small compiler written in **C** that
translates a limited subset of C into **x86-64 assembly**. My plan is to add
language features one at a time.

For example, this is a complete supported input program:

```c
int main() {
  return 2 + 3 * 4;
}
```

The resulting executable returns **14** to the operating system. It does not
print 14: `return` and `printf` have different jobs.

## Requirements

- A Windows x64 computer with GCC from MSYS2 UCRT64 available in your terminal.
- VS Code as your editor.
- PowerShell as your terminal.

The same project also runs with GCC on x86-64 Linux; commands appear below.
You do not need Python, a GUI toolkit, or an online compiler to use it.

## Run it on Windows

1. Extract the ZIP. In VS Code, choose **File → Open Folder** and open the
   extracted `my-c-compiler` folder containing this README and the `src` folder.
2. Choose **Terminal → New Terminal**. Select PowerShell.
3. Check GCC:

```powershell
gcc --version
gcc -dumpmachine
```

The second command should identify an `x86_64` Windows target, commonly
`x86_64-w64-mingw32`. A 32-bit or ARM compiler needs a different backend.
If `gcc` is not recognized, your terminal cannot find your GCC installation.

4. Build the compiler. Paste this as **one line**:

```powershell
gcc -std=c11 -Wall -Wextra -Wpedantic src/main.c src/lexer.c src/parser.c src/codegen.c -o minic.exe
```

5. Use the compiler to translate the sample C program into assembly:

```powershell
.\minic.exe tests\test01.c output.s
```

6. Use GCC's assembler and linker to create the executable:

```powershell
gcc output.s -o program.exe
```

7. Run it, then immediately inspect its return value:

```powershell
.\program.exe
$LASTEXITCODE
```

Expected result: **14**. If any build command reports an error, fix that error
before running the next command.

### Why I use GCC

There are two different C programs here:

- The compiler implementation in `src/*.c`. GCC builds it into `minic.exe`.
- My compiler's input, such as `tests/test01.c`. The **lexer, parser and
  code generator** translate this into `output.s`.

GCC then invokes tools that assemble and link `output.s`. The mini compiler
does not send the input C program to GCC. Reusing an assembler and linker lets
me concentrate on how a compiler translates a language.

## Inspect the first stage

```powershell
.\minic.exe --tokens tests\test01.c
```

This prints each token with its line and column. For `return 2 + 3 * 4;`, the
tokens include `return`, `2`, `+`, `3`, `*`, `4`, and `;`.

Open `output.s` to inspect the assembly the compiler generated. Begin with
`return 7;`: look for `movl $7, %eax`, which puts the return value in a CPU
register. The other instructions handle more complex expressions.

## Files and responsibilities

| File | Job |
| --- | --- |
| `src/main.c` | Reads arguments and the input file; connects all stages; writes assembly. |
| `src/lexer.c` | Splits source characters into tokens, skipping spaces and comments. |
| `src/lexer.h` | Declares token types, lexer state, and lexer functions. |
| `src/parser.c` | Checks the supported grammar and constructs an expression tree. |
| `src/parser.h` | Declares tree nodes and parser state. |
| `src/codegen.c` | Walks the tree and writes x86-64 assembly instructions. |
| `src/codegen.h` | Declares the code generation function. |
| `tests/test01.c` | Checks multiplication before addition; expected return value 14. |
| `tests/test02.c` | Checks parentheses; expected return value 20. |
| `tests/test03.c` | Checks integer division and subtraction; expected return value 10. |
| `docs/notes.md` | Beginner walkthrough and the next milestones. |
| `docs/validation.md` | What was tested and what remains unverified. |
| `Makefile` | Optional build recipe for environments with Make; Windows commands above do not require it. |

`.c` files contain implementations. `.h` files share declarations between them.
Header guards prevent a header from being included twice in one translation unit.

## Features in this milestone

- Exactly one function: `int main() { return expression; }` or
  `int main(void) { return expression; }`.
- Decimal integer literals from 0 to 2147483647, without leading zeros except `0`.
- Binary `+`, `-`, `*`, `/`; unary `+` and `-`; parentheses.
- Normal arithmetic precedence and left associativity.
- Spaces, line breaks, `//` comments and `/* ... */` comments.
- Errors with filename, line and column.

The generated arithmetic uses signed 32-bit integers. Integer division truncates
toward zero. Division by zero and signed overflow have undefined behavior in C;
this teaching compiler does not diagnose those arithmetic conditions. Use small,
defined calculations while learning. The literal `2147483648` is rejected,
including when preceded by unary minus.

**Not implemented yet:** variables, assignments, `printf`, `scanf`, `#include`,
macros, `%`, comparisons, `if`, loops, additional functions, arrays, pointers,
floating-point numbers, strings, and a full semantic analysis pass.

Limits: 16 KiB source files, 256 expression-tree nodes, and 64 nested factors
(parentheses/unary signs). This is a learning compiler for Windows x64 and Linux
x86-64, not a complete or standards-conforming C implementation.

## A simple exercise

Create `tests/my_first.c`:

```c
int main() {
  return (10 + 5) * 2;
}
```

Compile and run it using the same commands, changing only the input filename.
Predict the return value before checking it. Then remove the parentheses and
predict the new value. Finally, remove the semicolon and read the error message.

You do not need to understand every file before doing this exercise. Read
`docs/notes.md` and start by following one token through `lexer.c`.

## Run it on Linux x86-64

```sh
gcc -std=c11 -Wall -Wextra -Wpedantic src/main.c src/lexer.c src/parser.c src/codegen.c -o minic
./minic tests/test01.c output.s
gcc output.s -o program
./program
echo $?
```

Expected result: **14**. On Linux, the shell exposes only the lowest eight bits
of the exit status, so use values from 0 to 255 when checking results this way.

## Reference documentation

- [GCC compilation, assembly and linking stages](https://gcc.gnu.org/onlinedocs/gcc/Overall-Options.html)
- [Microsoft x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)

The Windows backend emits Windows stack-unwind directives. The Linux backend
emits ELF function metadata and a non-executable stack note. Neither backend
requires third-party C libraries beyond the normal GCC runtime.
