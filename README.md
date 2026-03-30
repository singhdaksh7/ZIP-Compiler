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
│   ├── lexer.py        # Tokenizer
│   ├── parser.py       # Parser → AST
│   ├── ast_nodes.py    # AST node definitions
│   ├── analyzer.py     # Semantic analysis
│   ├── codegen.py      # x86-64 assembly generation
│   └── main.py         # CLI entry point
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

## Roadmap

- [x] Project setup
- [ ] Lexer
- [ ] Parser + AST
- [ ] Semantic analysis
- [ ] Code generation (x86-64)
- [ ] Standard library basics (print, exit)
- [ ] Control flow (if/else, while, for)
- [ ] Functions and call stack
- [ ] Self-hosting

## License

MIT
