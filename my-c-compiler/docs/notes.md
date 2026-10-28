# My compiler notes

## 1. The main idea

A compiler translates a program from one language into another representation.
My compiler reads a small part of C and produces assembly instructions for an
x86-64 CPU. An assembler converts those instructions to machine code. A linker
connects the machine code to the normal startup code to make an executable.

The compiler itself is a C program. Its input is text that happens to contain
another C program. You can read that text as characters using standard file I/O.
Initially GCC builds the compiler; later, a sufficiently capable compiler could
compile its own source. That later milestone is called self-hosting.

## 2. Read the input

`main.c` opens the input file using `fopen`, reads bytes using `fgetc`, and
terminates the source buffer with `\0`. The compiler can now inspect each
character. It also keeps the source buffer alive while later stages use it.

## 3. Lexer: recognize words, numbers and symbols

For this input:

```c
return 2 + 3 * 4;
```

The lexer recognizes:

| Text | Meaning |
| --- | --- |
| `return` | Return keyword |
| `2` | Integer literal |
| `+` | Addition symbol |
| `3` | Integer literal |
| `*` | Multiplication symbol |
| `4` | Integer literal |
| `;` | Statement terminator |

A `Token` stores a category, a position in the input, a length, a line/column,
and a numeric value when appropriate. A token is more useful than a bare
character: `123` is one number token, even though it contains three characters.

Read `lexer_next` in `lexer.c`. Trace the path for the character `7` first.
Then trace `+`. Leave comment handling until those paths make sense.

## 4. Parser: check structure and arithmetic order

The parser checks the outer function and the return statement. For the returned
expression it uses these simplified grammar rules:

```text
program    = "int" "main" "(" ["void"] ")" "{" "return" expression ";" "}"
expression = term { ("+" | "-") term }
term       = factor { ("*" | "/") factor }
factor     = number | "+" factor | "-" factor | "(" expression ")"
```

Square brackets mean optional; braces mean repeated zero or more times. These
notations describe grammar; they are not C source code.

`parse_expression` calls `parse_term`, which calls `parse_factor`. Grouping
multiplication/division in `parse_term` gives them higher precedence.
The loops build left-associative trees: `20 - 5 - 3` means `(20 - 5) - 3`.

For `2 + 3 * 4`, the root node is addition. Its left child is `2`; its right
child is multiplication with children `3` and `4`. This is an abstract syntax
tree, or AST. The parser stores nodes in a fixed-size array so you can learn
the algorithm before dealing with dynamic allocation and freeing trees.

## 5. Code generator: translate the tree

`codegen.c` visits the tree and writes instructions. A CPU register is a small,
fast storage location in the processor. I use EAX for each expression result.

For a binary operation:

1. Generate instructions for the left operand.
2. Save its result in a temporary stack slot.
3. Generate instructions for the right operand.
4. Move the right result to ECX and restore the left result into EAX.
5. Emit the arithmetic instruction, leaving the new result in EAX.

The stack slots are temporary memory inside the function's allocated stack
frame. EAX and ECX are 32-bit registers. RSP points to the stack and is 64-bit.
The backend calculates how many temporary slots it needs before emitting the
function prologue. The Windows version also writes stack-unwind metadata.

You can postpone the operating-system metadata and stack-alignment details.
First understand `return 7;`, then one addition, then a nested expression.

## 6. Assemble, link and inspect the result

My compiler's work ends with `output.s`. Running GCC on this assembly file
assembles and links it. Running the resulting program makes the CPU execute the
instructions the compiler generated.

`return 14;` sends 14 back to the caller and ultimately the process exit status.
It does not show text in the terminal. In PowerShell, `$LASTEXITCODE` lets you
inspect the result immediately after running the executable.

## 7. What to learn before modifying each part

| C concept | Where you will use it |
| --- | --- |
| Loops and conditions | Scan characters and recognize symbols. |
| Character arrays and strings | Hold source text and compare keywords. |
| `struct` | Describe tokens, nodes and compiler state. |
| `enum` | Give names to token and node categories. |
| Pointers | Refer to source characters and connect tree nodes. |
| Functions and recursion | Parse nesting and visit an expression tree. |
| File handling | Read C source and write assembly. |
| Headers and separate compilation | Split the implementation into modules. |

Learn these alongside the project. You do not need to memorize all of them
before opening the lexer.

## 8. Planned milestones

| Milestone | Example goal | New idea |
| --- | --- | --- |
| 1 — current | `return 2 + 3 * 4;` | Tokens, grammar, AST, assembly. |
| 2 | `int a = 5; return a + 2;` | Local variables, a symbol table, semantic checks. |
| 3 | `a = a + 1; return a;` | Multiple statements and assignments. |
| 4 | `if (a > 3) return 1; return 0;` | Comparisons, labels and jumps. |
| 5 | `while (a < 10) { a = a + 1; }` | Loop control flow. |
| 6 | `return add(2, 3);` | Function definitions and calling conventions. |
| 7 | A small text-printing program | Strings and C library calls. |
| 8 | Small arrays and pointer operations | Addresses, memory layout and type rules. |

Add one feature and one meaningful example at a time. A complete C compiler
also needs substantially more work on preprocessing, declarations, types,
diagnostics, platform details and conformance.

## Review questions

1. Why does the lexer treat `123` as one token?
2. Why does `2 + 3 * 4` produce 14 rather than 20?
3. Which file would you inspect for a missing-semicolon error?
4. Why does a program with only `return 14;` print nothing?

Answers: it is one integer literal; multiplication has higher precedence;
`parser.c`; a return value and terminal output are different things.
