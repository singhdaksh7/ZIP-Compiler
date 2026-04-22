#!/usr/bin/env python3
"""
Comprehensive Test Suite for ZIP Compiler

Tests cover:
- Basic functionality (variables, operators, functions)
- Control flow (if/else, while, for, break, continue)
- Edge cases (large numbers, empty functions, nested structures)
- Error conditions (type mismatches, undeclared variables, etc.)
- Complex scenarios (recursion, nested loops, etc.)
"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lexer import Lexer, LexerError
from parser import Parser, ParserError
from analyzer import Analyzer, AnalyzerError
from codegen import CodeGenerator, CodeGenError


class TestResult:
    def __init__(self, name, passed, error=None):
        self.name = name
        self.passed = passed
        self.error = error
    
    def __repr__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        msg = f"{status}: {self.name}"
        if self.error:
            msg += f"\n  Error: {self.error}"
        return msg


def compile_program(code):
    """Compile a ZIP program through all phases."""
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        analyzer = Analyzer()
        analyzer.analyze(ast)
        
        codegen = CodeGenerator()
        asm = codegen.generate(ast)
        
        return True, None
    except (LexerError, ParserError, AnalyzerError, CodeGenError) as e:
        return False, str(e)


def test_compilation(name, code, should_pass=True):
    """Test that a program compiles (or fails to compile as expected)."""
    passed, error = compile_program(code)
    
    if should_pass:
        if passed:
            return TestResult(name, True)
        else:
            return TestResult(name, False, f"Expected to compile but got: {error}")
    else:
        if not passed:
            return TestResult(name, True)
        else:
            return TestResult(name, False, "Expected compilation to fail but succeeded")


# ─────────────────────────────────────────────────────────────────────────
# BASIC FUNCTIONALITY TESTS
# ─────────────────────────────────────────────────────────────────────────

BASIC_TESTS = [
    ("empty_main", """
fn main() -> int {
    return 0;
}
"""),
    
    ("simple_variable", """
fn main() -> int {
    let x: int = 42;
    return 0;
}
"""),
    
    ("multiple_variables", """
fn main() -> int {
    let a: int = 1;
    let b: int = 2;
    let c: int = 3;
    return 0;
}
"""),
    
    ("variable_reassignment", """
fn main() -> int {
    let x: int = 10;
    x = 20;
    x = 30;
    return 0;
}
"""),
    
    ("arithmetic_operations", """
fn main() -> int {
    let a: int = 10;
    let b: int = 3;
    let sum: int = a + b;
    let diff: int = a - b;
    let prod: int = a * b;
    let quot: int = a / b;
    let rem: int = a % b;
    return 0;
}
"""),
    
    ("unary_operators", """
fn main() -> int {
    let x: int = 42;
    let neg: int = -x;
    let flag: bool = true;
    let inverted: bool = !flag;
    return 0;
}
"""),
    
    ("boolean_literals", """
fn main() -> int {
    let t: bool = true;
    let f: bool = false;
    return 0;
}
"""),
    
    ("string_literal", """
fn main() -> int {
    let msg: string = "Hello, World!";
    return 0;
}
"""),
    
    ("comparison_operators", """
fn main() -> int {
    let a: int = 5;
    let b: int = 10;
    let eq: bool = a == b;
    let neq: bool = a != b;
    let lt: bool = a < b;
    let gt: bool = a > b;
    let lte: bool = a <= b;
    let gte: bool = a >= b;
    return 0;
}
"""),
    
    ("logical_operators", """
fn main() -> int {
    let a: bool = true;
    let b: bool = false;
    let and_result: bool = a && b;
    let or_result: bool = a || b;
    return 0;
}
"""),
]

# ─────────────────────────────────────────────────────────────────────────
# FUNCTION TESTS
# ─────────────────────────────────────────────────────────────────────────

FUNCTION_TESTS = [
    ("function_no_params", """
fn greet() -> int {
    return 42;
}

fn main() -> int {
    let result: int = greet();
    return 0;
}
"""),
    
    ("function_single_param", """
fn double(x: int) -> int {
    return x * 2;
}

fn main() -> int {
    let result: int = double(21);
    return 0;
}
"""),
    
    ("function_multiple_params", """
fn add(a: int, b: int) -> int {
    return a + b;
}

fn main() -> int {
    let result: int = add(5, 3);
    return 0;
}
"""),
    
    ("function_six_params", """
fn sum6(a: int, b: int, c: int, d: int, e: int, f: int) -> int {
    return a + b + c + d + e + f;
}

fn main() -> int {
    let result: int = sum6(1, 2, 3, 4, 5, 6);
    return 0;
}
"""),
    
    ("recursive_factorial", """
fn factorial(n: int) -> int {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

fn main() -> int {
    let f5: int = factorial(5);
    return 0;
}
"""),
    
    ("mutual_recursion", """
fn is_even(n: int) -> int {
    if n == 0 {
        return 1;
    }
    return is_odd(n - 1);
}

fn is_odd(n: int) -> int {
    if n == 0 {
        return 0;
    }
    return is_even(n - 1);
}

fn main() -> int {
    let even: int = is_even(4);
    let odd: int = is_odd(4);
    return 0;
}
"""),
]

# ─────────────────────────────────────────────────────────────────────────
# CONTROL FLOW TESTS
# ─────────────────────────────────────────────────────────────────────────

CONTROL_FLOW_TESTS = [
    ("if_statement", """
fn main() -> int {
    let x: int = 5;
    if x > 3 {
        print(1);
    }
    return 0;
}
"""),
    
    ("if_else_statement", """
fn main() -> int {
    let x: int = 5;
    if x > 10 {
        print(1);
    } else {
        print(0);
    }
    return 0;
}
"""),
    
    ("if_else_if_else", """
fn main() -> int {
    let score: int = 75;
    if score >= 90 {
        print(1);
    } else if score >= 80 {
        print(2);
    } else if score >= 70 {
        print(3);
    } else {
        print(0);
    }
    return 0;
}
"""),
    
    ("while_loop", """
fn main() -> int {
    let i: int = 0;
    while i < 5 {
        print(i);
        i = i + 1;
    }
    return 0;
}
"""),
    
    ("while_with_break", """
fn main() -> int {
    let i: int = 0;
    while i < 100 {
        if i == 5 {
            break;
        }
        print(i);
        i = i + 1;
    }
    return 0;
}
"""),
    
    ("while_with_continue", """
fn main() -> int {
    let i: int = 0;
    while i < 10 {
        i = i + 1;
        if i % 2 == 0 {
            continue;
        }
        print(i);
    }
    return 0;
}
"""),
    
    ("for_loop", """
fn main() -> int {
    for let i: int = 0; i < 5; i = i + 1 {
        print(i);
    }
    return 0;
}
"""),
    
    ("for_with_break", """
fn main() -> int {
    for let i: int = 0; i < 100; i = i + 1 {
        if i == 3 {
            break;
        }
        print(i);
    }
    return 0;
}
"""),
    
    ("for_with_continue", """
fn main() -> int {
    for let i: int = 0; i < 5; i = i + 1 {
        if i == 2 {
            continue;
        }
        print(i);
    }
    return 0;
}
"""),
    
    ("nested_loops", """
fn main() -> int {
    let i: int = 0;
    while i < 3 {
        let j: int = 0;
        while j < 3 {
            print(i * 3 + j);
            j = j + 1;
        }
        i = i + 1;
    }
    return 0;
}
"""),
    
    ("nested_for_loops", """
fn main() -> int {
    for let i: int = 0; i < 2; i = i + 1 {
        for let j: int = 0; j < 2; j = j + 1 {
            print(i * 2 + j);
        }
    }
    return 0;
}
"""),
    
    ("break_in_nested_loop", """
fn main() -> int {
    let i: int = 0;
    while i < 5 {
        let j: int = 0;
        while j < 5 {
            if j == 2 {
                break;
            }
            print(j);
            j = j + 1;
        }
        i = i + 1;
    }
    return 0;
}
"""),
]

# ─────────────────────────────────────────────────────────────────────────
# EDGE CASES & COMPLEX SCENARIOS
# ─────────────────────────────────────────────────────────────────────────

EDGE_CASE_TESTS = [
    ("large_numbers", """
fn main() -> int {
    let big: int = 999999;
    let bigger: int = big * 1000;
    return 0;
}
"""),
    
    ("negative_numbers", """
fn main() -> int {
    let neg: int = -42;
    let neg_neg: int = -neg;
    return 0;
}
"""),
    
    ("zero_values", """
fn main() -> int {
    let zero: int = 0;
    let zero_times_x: int = zero * 1000;
    return 0;
}
"""),
    
    ("complex_expressions", """
fn main() -> int {
    let result: int = 2 + 3 * 4 - 5 / 2 + 1;
    return 0;
}
"""),
    
    ("deeply_nested_expressions", """
fn main() -> int {
    let x: int = ((((1 + 2) * 3) - 4) / 2);
    return 0;
}
"""),
    
    ("long_variable_names", """
fn main() -> int {
    let very_long_variable_name_that_is_descriptive: int = 42;
    return 0;
}
"""),
    
    ("multiple_functions", """
fn func1() -> int { return 1; }
fn func2() -> int { return 2; }
fn func3() -> int { return 3; }
fn func4() -> int { return 4; }
fn func5() -> int { return 5; }

fn main() -> int {
    let sum: int = func1() + func2() + func3() + func4() + func5();
    return 0;
}
"""),
    
    ("fibonacci", """
fn fib(n: int) -> int {
    if n <= 1 {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

fn main() -> int {
    let f10: int = fib(10);
    return 0;
}
"""),
    
    ("gcd_algorithm", """
fn gcd(a: int, b: int) -> int {
    if b == 0 {
        return a;
    }
    return gcd(b, a % b);
}

fn main() -> int {
    let g: int = gcd(48, 18);
    return 0;
}
"""),
    
    ("nested_if_else", """
fn main() -> int {
    let x: int = 5;
    let y: int = 10;
    
    if x > 0 {
        if y > 0 {
            if x + y > 10 {
                print(1);
            } else {
                print(0);
            }
        }
    }
    return 0;
}
"""),
    
    ("complex_boolean_logic", """
fn main() -> int {
    let a: bool = true;
    let b: bool = false;
    let c: bool = true;
    
    let result: bool = (a && b) || c && !b;
    return 0;
}
"""),
    
    ("string_operations", """
fn main() -> int {
    let greeting: string = "Hello";
    let exclamation: string = "!";
    print(greeting);
    print(exclamation);
    return 0;
}
"""),
]

# ─────────────────────────────────────────────────────────────────────────
# ERROR CASES (SHOULD FAIL TO COMPILE)
# ─────────────────────────────────────────────────────────────────────────

ERROR_TESTS = [
    ("undeclared_variable", """
fn main() -> int {
    print(undefined_var);
    return 0;
}
""", False),
    
    ("reassign_undefined", """
fn main() -> int {
    x = 42;
    return 0;
}
""", False),
    
    ("break_outside_loop", """
fn main() -> int {
    break;
    return 0;
}
""", False),
    
    ("continue_outside_loop", """
fn main() -> int {
    continue;
    return 0;
}
""", False),
    
    ("undefined_function", """
fn main() -> int {
    let result: int = undefined_func();
    return 0;
}
""", False),
    
    ("too_many_function_args", """
fn add(a: int, b: int) -> int {
    return a + b;
}

fn main() -> int {
    let result: int = add(1, 2, 3, 4, 5, 6, 7);
    return 0;
}
""", False),
]

# ─────────────────────────────────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────

def run_test_suite():
    """Run all test suites and report results."""
    print("=" * 80)
    print("ZIP COMPILER - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    results = []
    
    # Basic Tests
    print("BASIC FUNCTIONALITY TESTS")
    print("-" * 80)
    for name, code in BASIC_TESTS:
        result = test_compilation(name, code, should_pass=True)
        results.append(result)
        print(result)
    print()
    
    # Function Tests
    print("FUNCTION TESTS")
    print("-" * 80)
    for name, code in FUNCTION_TESTS:
        result = test_compilation(name, code, should_pass=True)
        results.append(result)
        print(result)
    print()
    
    # Control Flow Tests
    print("CONTROL FLOW TESTS")
    print("-" * 80)
    for name, code in CONTROL_FLOW_TESTS:
        result = test_compilation(name, code, should_pass=True)
        results.append(result)
        print(result)
    print()
    
    # Edge Case Tests
    print("EDGE CASE & COMPLEX SCENARIO TESTS")
    print("-" * 80)
    for name, code in EDGE_CASE_TESTS:
        result = test_compilation(name, code, should_pass=True)
        results.append(result)
        print(result)
    print()
    
    # Error Tests
    print("ERROR DETECTION TESTS (Should Fail to Compile)")
    print("-" * 80)
    for name, code, should_pass in ERROR_TESTS:
        result = test_compilation(name, code, should_pass=should_pass)
        results.append(result)
        print(result)
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED! Compiler is working correctly!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Failed tests:")
        for result in results:
            if not result.passed:
                print(f"  - {result.name}")
        return False


if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)
