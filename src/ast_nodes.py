"""
AST (Abstract Syntax Tree) node definitions for the ZIP language.

Each node represents a construct in the language:
- Programs contain functions
- Functions contain statements
- Statements contain expressions
"""

from dataclasses import dataclass, field
from typing import Optional


# ─── Expressions ───────────────────────────────────────────────

@dataclass
class IntLiteral:
    """A literal integer value: 42"""
    value: int
    line: int = 0
    col: int = 0

@dataclass
class StringLiteral:
    """A literal string value: "hello" """
    value: str
    line: int = 0
    col: int = 0

@dataclass
class BoolLiteral:
    """A literal boolean value: true, false"""
    value: bool
    line: int = 0
    col: int = 0

@dataclass
class Identifier:
    """A variable or function name: x, foo, my_var"""
    name: str
    line: int = 0
    col: int = 0

@dataclass
class BinaryOp:
    """A binary operation: x + y, a == b, 3 * 4"""
    left: object       # left-hand expression
    op: str            # operator: +, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||
    right: object      # right-hand expression
    line: int = 0
    col: int = 0

@dataclass
class UnaryOp:
    """A unary operation: -x, !flag"""
    op: str            # operator: -, !
    operand: object    # the expression being operated on
    line: int = 0
    col: int = 0

@dataclass
class FunctionCall:
    """A function call: print(x), add(1, 2)"""
    name: str
    args: list = field(default_factory=list)
    line: int = 0
    col: int = 0


# ─── Statements ────────────────────────────────────────────────

@dataclass
class LetStatement:
    """Variable declaration: let x: int = 42;"""
    name: str                  # variable name
    type_name: str             # type annotation: int, bool, string
    value: object              # initializer expression
    line: int = 0
    col: int = 0

@dataclass
class AssignStatement:
    """Variable assignment: x = 10;"""
    name: str                  # variable name
    value: object              # new value expression
    line: int = 0
    col: int = 0

@dataclass
class ReturnStatement:
    """Return statement: return 0;"""
    value: Optional[object] = None   # expression to return (None for bare return)
    line: int = 0
    col: int = 0

@dataclass
class IfStatement:
    """If/else statement: if x > 0 { ... } else { ... }"""
    condition: object                          # condition expression
    then_body: list = field(default_factory=list)   # statements in if block
    else_body: list = field(default_factory=list)   # statements in else block (can be empty)
    line: int = 0
    col: int = 0

@dataclass
class WhileStatement:
    """While loop: while x > 0 { ... }"""
    condition: object                          # loop condition
    body: list = field(default_factory=list)   # statements in loop body
    line: int = 0
    col: int = 0

@dataclass
class ForStatement:
    """For loop: for let i: int = 0; i < 10; i = i + 1 { ... }"""
    init: object               # initializer (let statement or assignment)
    condition: object          # loop condition
    update: object             # update statement (assignment)
    body: list = field(default_factory=list)   # statements in loop body
    line: int = 0
    col: int = 0

@dataclass
class ExpressionStatement:
    """A standalone expression used as a statement: print(x);"""
    expression: object
    line: int = 0
    col: int = 0

@dataclass
class BreakStatement:
    """Break out of the nearest enclosing loop: break;"""
    line: int = 0
    col: int = 0

@dataclass
class ContinueStatement:
    """Skip to the next iteration of the nearest enclosing loop: continue;"""
    line: int = 0
    col: int = 0


# ─── Top-level ─────────────────────────────────────────────────

@dataclass
class Parameter:
    """A function parameter: x: int"""
    name: str
    type_name: str

@dataclass
class Function:
    """Function definition: fn add(a: int, b: int) -> int { ... }"""
    name: str
    params: list = field(default_factory=list)       # list of Parameter
    return_type: str = "void"
    body: list = field(default_factory=list)          # list of statements
    line: int = 0
    col: int = 0

@dataclass
class Program:
    """The root AST node — a complete ZIP program."""
    functions: list = field(default_factory=list)     # list of Function
