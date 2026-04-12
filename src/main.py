"""
ZIP Compiler — Main CLI Entry Point

Compiles a .zip source file through all phases:
    1. Lexing   (source → tokens)
    2. Parsing  (tokens → AST)
    3. Analysis (type checking, error detection)
    4. CodeGen  (AST → x86-64 assembly)

Usage:
    python src/main.py <source_file> [-o output_name]
    python src/main.py examples/hello.zip -o hello

Options:
    -o <name>   Output file name (default: output)
    --tokens    Print tokens and exit
    --ast       Print AST and exit
    --asm       Print generated assembly and exit (don't write file)
    --run       Compile and immediately run the binary (Linux/WSL only)
"""

import sys
import os
import subprocess

# Add src directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer, LexerError
from parser import Parser, ParserError, print_ast
from analyzer import Analyzer, AnalyzerError
from codegen import CodeGenerator, CodeGenError


def compile_file(source_path: str, output_name: str = "output",
                 show_tokens=False, show_ast=False, show_asm=False, run=False):
    """Compile a ZIP source file through all phases."""

    # Read source file
    if not os.path.exists(source_path):
        print(f"Error: File '{source_path}' not found.")
        sys.exit(1)

    with open(source_path, "r") as f:
        source = f.read()

    filename = os.path.basename(source_path)
    print(f"\n  ZIP Compiler v0.1")
    print(f"  Compiling: {filename}")
    print(f"  {'-' * 40}")

    # Phase 1: Lexing
    print(f"  [1/4] Lexing...", end=" ")
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        print(f"OK ({len(tokens)} tokens)")
    except LexerError as e:
        print(f"FAILED")
        print(f"\n  {e}")
        sys.exit(1)

    if show_tokens:
        print(f"\n  === Tokens ===\n")
        for token in tokens:
            print(f"    {token}")
        return

    # Phase 2: Parsing
    print(f"  [2/4] Parsing...", end=" ")
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        print(f"OK")
    except ParserError as e:
        print(f"FAILED")
        print(f"\n  {e}")
        sys.exit(1)

    if show_ast:
        print(f"\n  === AST ===\n")
        print_ast(ast)
        return

    # Phase 3: Semantic Analysis
    print(f"  [3/4] Analyzing...", end=" ")
    try:
        analyzer = Analyzer()
        analyzer.analyze(ast)
    except AnalyzerError as e:
        print(f"FAILED")
        print(f"\n  {e}")
        sys.exit(1)

    # Phase 4: Code Generation
    print(f"  [4/4] Generating x86-64...", end=" ")
    try:
        codegen = CodeGenerator()
        asm = codegen.generate(ast)
        print(f"OK")
    except CodeGenError as e:
        print(f"FAILED")
        print(f"\n  {e}")
        sys.exit(1)

    if show_asm:
        print(f"\n  === Assembly ===\n")
        print(asm)
        return

    # Write assembly to file
    asm_file = f"{output_name}.s"
    with open(asm_file, "w") as f:
        f.write(asm)
    print(f"\n  Output: {asm_file}")

    # Try to assemble and link with GCC (if available)
    print(f"  {'-' * 40}")
    linked = False
    try:
        result = subprocess.run(
            ["gcc", "-o", output_name, asm_file, "-no-pie"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  Linked:  ./{output_name}")
            linked = True
        else:
            print(f"  Link failed:")
            for line in result.stderr.strip().splitlines():
                print(f"    {line}")
            print(f"  To retry manually: gcc -o {output_name} {asm_file} -no-pie")
    except FileNotFoundError:
        print(f"  GCC not found. To compile the assembly on Linux/WSL:")
        print(f"    gcc -o {output_name} {asm_file} -no-pie")

    if linked and run:
        print(f"\n  Running ./{output_name}:")
        print(f"  {'-' * 40}")
        try:
            proc = subprocess.run([f"./{output_name}"], text=True)
            print(f"  {'-' * 40}")
            print(f"  Exited with code {proc.returncode}")
        except Exception as e:
            print(f"  Could not run binary: {e}")
    elif linked and not run:
        print(f"\n  Run with: ./{output_name}")

    print()


def main():
    """Parse CLI arguments and compile."""
    if len(sys.argv) < 2:
        print("\n  ZIP Compiler v0.1")
        print("  Usage: python src/main.py <source.zip> [-o output_name]")
        print()
        print("  Options:")
        print("    -o <name>    Output file name (default: output)")
        print("    --tokens     Print tokens and exit")
        print("    --ast        Print AST and exit")
        print("    --asm        Print generated assembly and exit")
        print("    --run        Compile and run immediately (Linux/WSL)")
        print()
        print("  Example:")
        print("    python src/main.py examples/hello.zip -o hello")
        print()
        sys.exit(0)

    source_path = sys.argv[1]
    output_name = "output"
    show_tokens = False
    show_ast = False
    show_asm = False
    run = False

    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "-o" and i + 1 < len(sys.argv):
            output_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--tokens":
            show_tokens = True
            i += 1
        elif sys.argv[i] == "--ast":
            show_ast = True
            i += 1
        elif sys.argv[i] == "--asm":
            show_asm = True
            i += 1
        elif sys.argv[i] == "--run":
            run = True
            i += 1
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    compile_file(source_path, output_name, show_tokens, show_ast, show_asm, run)


if __name__ == "__main__":
    main()
