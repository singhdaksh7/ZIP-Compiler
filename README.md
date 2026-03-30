# ZIP Compiler

A compiler for **ZIP**, a custom toy programming language, targeting **x86-64 assembly**.

The bootstrap compiler is written in **Python**, with the long-term goal of self-hosting (rewriting the compiler in ZIP itself).

---

## Project Goals

- Design a clean, expressive toy language from scratch
- Compile ZIP source code to x86-64 assembly (Linux, System V ABI)
- Learn compiler fundamentals: lexing, parsing, semantic analysis, and code generation
- Eventually self-host: rewrite the compiler in ZIP and compile it with itself

## Architecture

```
ZIP Source (.zip)
       │
       ▼
   ┌────────┐
   │  Lexer │   → Tokens
   └────────┘
       │
       ▼
   ┌────────┐
   │ Parser │   → AST
   └────────┘
       │
       ▼
   ┌──────────────────┐
   │ Semantic Analysis │   → Validated AST
   └──────────────────┘
       │
       ▼
   ┌──────────┐
   │ Code Gen │   → x86-64 Assembly (.s)
   └──────────┘
       │
       ▼
   ┌────────────────┐
   │ Assembler (as) │   → Object file → Executable
   └────────────────┘
```

## Project Structure

```
compiler/
├── README.md
├── src/
│   ├── tokens.py       # Token types and keyword definitions
│   ├── lexer.py        # Tokenizer (source code → tokens)
│   ├── parser.py       # Parser → AST (planned)
│   ├── ast_nodes.py    # AST node definitions (planned)
│   ├── analyzer.py     # Semantic analysis (planned)
│   ├── codegen.py      # x86-64 assembly generation (planned)
│   └── main.py         # CLI entry point (planned)
├── tests/              # Test programs and unit tests
├── examples/           # Example ZIP programs
└── docs/               # Language specification and notes
```

## Getting Started

### Prerequisites

- Python 3.10+
- GCC or GNU `as` + `ld` (for assembling and linking)
- Linux x86-64 (or WSL)

### Usage

```bash
# Compile a ZIP source file
python src/main.py examples/hello.zip -o hello

# Run the resulting executable
./hello
```

## Language Overview

ZIP is a statically typed, imperative language. Here's a taste of what it will look like:

```
fn main() -> int {
    let x: int = 42;
    print(x);
    return 0;
}
```

> The full language spec will evolve in `docs/` as the project grows.

## Lexer

The lexer (tokenizer) is complete. It converts raw ZIP source code into a stream of tokens. Run it standalone to see the output:

```bash
python src/lexer.py
```

**Supported tokens:**

| Category    | Tokens                                                        |
|-------------|---------------------------------------------------------------|
| Keywords    | `fn`, `let`, `return`, `if`, `else`, `while`, `for`, `print`  |
| Types       | `int`, `bool`, `string`, `void`                               |
| Literals    | integers (`42`), strings (`"hello"`), booleans (`true/false`) |
| Operators   | `+`, `-`, `*`, `/`, `%`, `=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!` |
| Delimiters  | `(`, `)`, `{`, `}`, `;`, `:`, `,`, `->`                      |
| Comments    | `// single-line comments`                                     |

**Example:**

```
let x: int = 42;
```

Produces:

```
Token(LET, 'let', line=1, col=1)
Token(IDENTIFIER, 'x', line=1, col=5)
Token(COLON, ':', line=1, col=6)
Token(INT, 'int', line=1, col=8)
Token(ASSIGN, '=', line=1, col=12)
Token(INT_LITERAL, '42', line=1, col=14)
Token(SEMICOLON, ';', line=1, col=16)
```

## Roadmap

- [x] Project setup
- [x] Lexer
- [ ] Parser + AST
- [ ] Semantic analysis
- [ ] Code generation (x86-64)
- [ ] Standard library basics (print, exit)
- [ ] Control flow (if/else, while, for)
- [ ] Functions and call stack
- [ ] Self-hosting

## License

MIT
