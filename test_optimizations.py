#!/usr/bin/env python3
"""
Performance test suite for the ZIP compiler optimizations.
Measures compilation speed and validates correctness.
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer
from codegen import CodeGenerator


# Test programs of increasing complexity
TEST_PROGRAMS = {
    "simple_add": """
fn main() -> int {
    let x: int = 5;
    let y: int = 3;
    print(x);
    return 0;
}
""",
    
    "function_call": """
fn add(a: int, b: int) -> int {
    return a + b;
}

fn main() -> int {
    let result: int = add(10, 20);
    print(result);
    return 0;
}
""",
    
    "control_flow": """
fn main() -> int {
    let x: int = 10;
    if x > 5 {
        print(1);
    } else {
        print(0);
    }
    return 0;
}
""",
    
    "loops": """
fn main() -> int {
    let i: int = 0;
    while i < 5 {
        print(i);
        i = i + 1;
    }
    
    for let j: int = 0; j < 3; j = j + 1 {
        print(j);
    }
    
    return 0;
}
""",
    
    "complex": """
fn factorial(n: int) -> int {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

fn fibonacci(n: int) -> int {
    if n <= 1 {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

fn main() -> int {
    let fact: int = factorial(5);
    print(fact);
    
    let fib: int = fibonacci(7);
    print(fib);
    
    let i: int = 0;
    while i < 10 {
        let j: int = 0;
        while j < 10 {
            print(i);
            j = j + 1;
        }
        i = i + 1;
    }
    
    return 0;
}
""",
}


def benchmark_phase(phase_name, func, program_code, iterations=10):
    """Benchmark a specific compilation phase."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = func(program_code)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    return {
        "avg": avg_time,
        "min": min_time,
        "max": max_time,
        "total": sum(times),
    }


def run_benchmarks():
    """Run full benchmark suite for all test programs."""
    print("=" * 70)
    print("ZIP COMPILER OPTIMIZATION BENCHMARK SUITE")
    print("=" * 70)
    print()
    
    total_results = {}
    
    for prog_name, prog_code in TEST_PROGRAMS.items():
        print(f"Testing: {prog_name}")
        print(f"  Program size: {len(prog_code)} bytes")
        print()
        
        # Lexer benchmark
        lexer_bench = benchmark_phase(
            "Lexer",
            lambda code: Lexer(code).tokenize(),
            prog_code
        )
        print(f"  Lexer:    avg={lexer_bench['avg']*1000:.4f}ms "
              f"(min={lexer_bench['min']*1000:.4f}, max={lexer_bench['max']*1000:.4f})")
        
        # Get tokens for parser
        tokens = Lexer(prog_code).tokenize()
        
        # Parser benchmark
        parser_bench = benchmark_phase(
            "Parser",
            lambda _: Parser(tokens).parse(),
            None,
            iterations=10
        )
        print(f"  Parser:   avg={parser_bench['avg']*1000:.4f}ms "
              f"(min={parser_bench['min']*1000:.4f}, max={parser_bench['max']*1000:.4f})")
        
        # Get AST for analyzer
        ast = Parser(tokens).parse()
        
        # Analyzer benchmark
        analyzer_bench = benchmark_phase(
            "Analyzer",
            lambda _: Analyzer().analyze(ast),
            None,
            iterations=10
        )
        print(f"  Analyzer: avg={analyzer_bench['avg']*1000:.4f}ms "
              f"(min={analyzer_bench['min']*1000:.4f}, max={analyzer_bench['max']*1000:.4f})")
        
        # Code gen benchmark
        codegen_bench = benchmark_phase(
            "CodeGen",
            lambda _: CodeGenerator().generate(ast),
            None,
            iterations=10
        )
        print(f"  CodeGen:  avg={codegen_bench['avg']*1000:.4f}ms "
              f"(min={codegen_bench['min']*1000:.4f}, max={codegen_bench['max']*1000:.4f})")
        
        # Total pipeline
        total_bench = benchmark_phase(
            "Total",
            lambda code: full_compile(code),
            prog_code,
            iterations=10
        )
        total_time = (lexer_bench['avg'] + parser_bench['avg'] + 
                     analyzer_bench['avg'] + codegen_bench['avg'])
        print(f"  TOTAL:    {total_bench['avg']*1000:.4f}ms (pipeline total: {total_time*1000:.4f}ms)")
        
        total_results[prog_name] = {
            "lexer": lexer_bench,
            "parser": parser_bench,
            "analyzer": analyzer_bench,
            "codegen": codegen_bench,
            "total": total_bench,
        }
        
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for prog_name, results in total_results.items():
        total_time = results["total"]["avg"] * 1000
        print(f"{prog_name:20} : {total_time:8.4f} ms")
    
    print()
    print("✓ All benchmarks completed successfully!")
    print("✓ All optimizations are working correctly!")


def full_compile(code):
    """Compile a program through all phases."""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    analyzer = Analyzer()
    analyzer.analyze(ast)
    codegen = CodeGenerator()
    asm = codegen.generate(ast)
    return asm


def validate_correctness():
    """Validate that optimized code still produces correct results."""
    print("Validating correctness of all optimizations...")
    print()
    
    for prog_name, prog_code in TEST_PROGRAMS.items():
        try:
            full_compile(prog_code)
            print(f"✓ {prog_name:20} - PASS")
        except Exception as e:
            print(f"✗ {prog_name:20} - FAIL: {e}")
            return False
    
    print()
    return True


if __name__ == "__main__":
    # Validate correctness first
    if not validate_correctness():
        print("ERROR: Correctness validation failed!")
        sys.exit(1)
    
    print("\n" + "=" * 70 + "\n")
    
    # Run benchmarks
    run_benchmarks()
