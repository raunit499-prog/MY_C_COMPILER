# C Compiler — Arithmetic-to-Assembly Milestone

This milestone is part of our group project to understand how compilers work. We built a small compiler in **C** that translates a limited subset of C into **x86-64 assembly**, with the aim of adding language features gradually.

This README covers the separate arithmetic compiler. It is different from our strict custom-keyword frontend and desktop GUI. The examples here use ordinary C names, including `return`.

## Our team

- **Satyajeet Singh**
- **Yug Sharma**
- **Raunit Singh**
- **Ayush Kestwal**

## What this milestone can do

The following is a complete supported input program:

```c
int main() {
  return 2 + 3 * 4;
}
```

Our compiler generates assembly for the expression. After the assembly is assembled and linked, the executable returns **14** to the operating system.

It does not print `14` on the screen. A function's `return` value and output produced by `printf` serve different purposes.

## Requirements

For the Windows instructions, use:

- A **Windows x64** computer with GCC from **MSYS2 UCRT64** available in the terminal.
- **VS Code** as the editor.
- **PowerShell** as the terminal.

The project also runs with GCC on **x86-64 Linux**. Linux commands are included below. This arithmetic milestone does not require Python, a GUI toolkit, or an online compiler.

## Build and run on Windows

1. Extract the ZIP. In VS Code, select **File → Open Folder** and open the `my-c-compiler` folder that contains this README and the `src` directory.
2. Select **Terminal → New Terminal**, then choose PowerShell.
3. Check that GCC is available and targets the correct platform:

```powershell
gcc --version
gcc -dumpmachine
```

The second command should report an `x86_64` Windows target, commonly `x86_64-w64-mingw32`. A 32-bit or ARM target requires a different backend. If PowerShell does not recognize `gcc`, it cannot find the GCC installation.

4. Build our compiler by pasting the following command as **one line**:

```powershell
gcc -std=c11 -Wall -Wextra -Wpedantic src/main.c src/lexer.c src/parser.c src/codegen.c -o minic.exe
```

5. Translate the sample program into assembly:

```powershell
.\minic.exe tests\test01.c output.s
```

6. Ask GCC to invoke the assembler and linker to create the executable:

```powershell
gcc output.s -o program.exe
```

7. Run the executable and immediately check its exit status:

```powershell
.\program.exe
$LASTEXITCODE
```

The expected result is **14**. If a command fails, resolve that error before continuing to the next step.

## Why we use GCC

There are two separate C programs involved:

| Program | How it is processed |
| --- | --- |
| Our compiler implementation in `src/*.c` | GCC builds these files into `minic.exe`. |
| An input program such as `tests/test01.c` | Our lexer, parser, and code generator translate it into `output.s`. |

GCC then invokes the assembler and linker for `output.s`. Our mini compiler does not pass the input C program to GCC for C compilation. Reusing an assembler and linker allows us to focus on the translation stages that we are learning to implement.

## Inspecting tokens and assembly

To see the tokens produced by the lexer, run:

```powershell
.\minic.exe --tokens tests\test01.c
```

A token is a meaningful piece of source text, such as a keyword, number, or operator. The command prints each token with its line and column. For `return 2 + 3 * 4;`, the tokens include `return`, `2`, `+`, `3`, `*`, `4`, and `;`.

Open `output.s` to inspect the generated assembly. A useful starting point is `return 7;`: the instruction `movl $7, %eax` places the return value in a CPU register. More complex expressions require additional instructions.

## Files and responsibilities

| File | Purpose |
| --- | --- |
| `src/main.c` | Reads command-line arguments and the input file, connects the compiler stages, and writes assembly. |
| `src/lexer.c` | Splits source text into tokens while skipping whitespace and comments. |
| `src/lexer.h` | Declares token types, lexer state, and lexer functions. |
| `src/parser.c` | Checks the supported grammar and builds an expression tree. |
| `src/parser.h` | Declares the tree nodes and parser state. |
| `src/codegen.c` | Walks the expression tree and writes x86-64 assembly instructions. |
| `src/codegen.h` | Declares the code-generation function. |
| `tests/test01.c` | Checks that multiplication happens before addition; expected return value: **14**. |
| `tests/test02.c` | Checks parentheses; expected return value: **20**. |
| `tests/test03.c` | Checks integer division and subtraction; expected return value: **10**. |
| `docs/notes.md` | Provides a beginner walkthrough and outlines later milestones. |
| `docs/validation.md` | Records what has been tested and what remains unverified. |
| `Makefile` | Provides an optional build recipe when Make is available; the Windows commands above do not require it. |

The `.c` files contain implementations. The `.h` files share declarations between source files. Header guards prevent a header from being included more than once in a single translation unit.

## Supported language features

This milestone supports:

- Exactly one function, in the form `int main() { return expression; }` or `int main(void) { return expression; }`.
- Decimal integer literals from **0 to 2147483647**. Leading zeros are rejected, except for the literal `0` itself.
- Binary addition, subtraction, multiplication, and division: `+`, `-`, `*`, and `/`.
- Unary `+` and `-`, and expressions grouped with parentheses.
- Normal arithmetic precedence and left associativity.
- Spaces, line breaks, `//` comments, and `/* ... */` comments.
- Error messages containing the filename, line, and column.

Generated arithmetic uses **signed 32-bit integers**. Integer division truncates toward zero. Division by zero and signed overflow have undefined behavior in C, and this teaching compiler does not diagnose those arithmetic conditions. We recommend using small calculations whose results are defined while exploring this milestone.

The literal `2147483648` is rejected, even when it follows a unary minus sign.

## Features not yet implemented

This milestone does not yet support variables, assignments, `printf`, `scanf`, `#include`, macros, `%`, comparisons, `if`, loops, additional functions, arrays, pointers, floating-point numbers, strings, or a full semantic analysis pass.

These limits apply to the arithmetic compiler described here, rather than to every other component in the group project.

### Size and nesting limits

| Item | Limit |
| --- | --- |
| Source file | **16 KiB**. |
| Expression tree | **256 nodes**. |
| Nested factors, including parentheses and unary signs | **64 levels**. |

This is a learning compiler for **Windows x64** and **Linux x86-64**. It is not a complete or standards-conforming C implementation.

## A short exercise

Create a file named `tests/my_first.c`:

```c
int main() {
  return (10 + 5) * 2;
}
```

Use the same build and run steps, replacing the sample input filename with this one. Before checking the exit status, predict the result.

Then try the following:

1. Remove the parentheses and predict the new result.
2. Compile and run the modified program to check the prediction.
3. Remove the semicolon, compile again, and read the error message.

Understanding every source file is not required before trying this exercise. Start with `docs/notes.md`, then follow one token through `lexer.c`.

## Build and run on Linux x86-64

Run these commands from the arithmetic compiler's project folder:

```sh
gcc -std=c11 -Wall -Wextra -Wpedantic src/main.c src/lexer.c src/parser.c src/codegen.c -o minic
./minic tests/test01.c output.s
gcc output.s -o program
./program
echo $?
```

The expected exit status is **14**. Linux shells expose only the lowest eight bits of the exit status, so use values from **0 to 255** when checking calculations this way.

## Platform output and references

Our Windows backend emits stack-unwind directives for Windows. Our Linux backend emits ELF function metadata and a non-executable stack note. Neither backend requires third-party C libraries beyond the normal GCC runtime.

We use GCC and the platform toolchains as existing tools. Their authorship remains with their respective developers.

- [GCC compilation, assembly and linking stages](https://gcc.gnu.org/onlinedocs/gcc/Overall-Options.html)
- [Microsoft x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)
