"""
Semantic Analyzer for the ZIP language.

Walks the AST and checks for errors that the parser can't catch:
- Undeclared variables
- Redeclared variables in the same scope
- Type mismatches (int vs string vs bool)
- Missing return statements
- Wrong number of arguments in function calls
- Calling undeclared functions
- Type checking for operators (can't add string + int, etc.)

Usage:
    analyzer = Analyzer()
    analyzer.analyze(ast)
    # Raises AnalyzerError if something is wrong
"""

from ast_nodes import (
    Program, Function, Parameter,
    LetStatement, AssignStatement, ReturnStatement,
    IfStatement, WhileStatement, ForStatement, ExpressionStatement,
    BreakStatement, ContinueStatement,
    BinaryOp, UnaryOp, IntLiteral, StringLiteral, BoolLiteral,
    Identifier, FunctionCall,
)


class AnalyzerError(Exception):
    """Raised when a semantic error is found."""
    def __init__(self, message, line=0, col=0):
        self.line = line
        self.col = col
        super().__init__(f"Semantic error at line {line}, col {col}: {message}")


class Scope:
    """
    Represents a variable scope.

    Each scope has a parent — when looking up a variable,
    we check the current scope first, then walk up to the parent.
    This handles nested blocks (if/while/for bodies).
    """
    def __init__(self, parent=None):
        self.parent = parent
        self.variables = {}   # name -> type (e.g. "x" -> "int")

    def declare(self, name: str, var_type: str, line=0, col=0):
        """Declare a variable in this scope."""
        if name in self.variables:
            raise AnalyzerError(f"Variable '{name}' already declared in this scope", line, col)
        self.variables[name] = var_type

    def lookup(self, name: str, line=0, col=0) -> str:
        """Look up a variable, walking up the scope chain."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name, line, col)
        raise AnalyzerError(f"Undeclared variable '{name}'", line, col)

    def child(self):
        """Create a new child scope with this scope as parent."""
        return Scope(parent=self)


class Analyzer:
    def __init__(self):
        self.functions = {}    # name -> {"params": [...], "return_type": str}
        self.current_function_return_type = "void"
        self.loop_depth = 0    # tracks nesting depth inside loops
        self.errors = []       # collect all errors instead of stopping at first one

    def analyze(self, program: Program):
        """Analyze the entire program."""
        # First pass: register all function signatures
        for fn in program.functions:
            if fn.name in self.functions:
                self.error(f"Function '{fn.name}' already defined", fn.line, fn.col)
            self.functions[fn.name] = {
                "params": [(p.name, p.type_name) for p in fn.params],
                "return_type": fn.return_type,
            }

        # Register built-in functions
        self.functions["print"] = {
            "params": [("value", "any")],  # print accepts any type
            "return_type": "void",
        }

        # Second pass: analyze each function body
        for fn in program.functions:
            self.analyze_function(fn)

        # Report errors
        if self.errors:
            error_msg = f"\n{len(self.errors)} semantic error(s) found:\n"
            for err in self.errors:
                error_msg += f"  - {err}\n"
            raise AnalyzerError(error_msg)

        print(f"  Semantic analysis passed! ({len(program.functions)} function(s), 0 errors)")

    def error(self, message, line=0, col=0):
        """Record an error without stopping."""
        self.errors.append(f"Line {line}, col {col}: {message}")

    def analyze_function(self, fn: Function):
        """Analyze a single function."""
        self.current_function_return_type = fn.return_type

        # Create scope with parameters
        scope = Scope()
        for param in fn.params:
            scope.declare(param.name, param.type_name)

        # Analyze body
        for stmt in fn.body:
            self.analyze_statement(stmt, scope)

        # Check for missing return in non-void functions
        if fn.return_type != "void":
            if not self.has_return(fn.body):
                self.error(f"Function '{fn.name}' may not return a value (return type is '{fn.return_type}')",
                           fn.line, fn.col)

    def has_return(self, statements) -> bool:
        """Check if a list of statements always returns a value."""
        for stmt in statements:
            if isinstance(stmt, ReturnStatement):
                return True
            if isinstance(stmt, IfStatement):
                # Both branches must return for the if to guarantee a return
                if stmt.else_body and self.has_return(stmt.then_body) and self.has_return(stmt.else_body):
                    return True
        return False

    # ─── Statements ────────────────────────────────────────────

    def analyze_statement(self, stmt, scope: Scope):
        """Dispatch to the appropriate statement analyzer."""
        if isinstance(stmt, LetStatement):
            self.analyze_let(stmt, scope)
        elif isinstance(stmt, AssignStatement):
            self.analyze_assign(stmt, scope)
        elif isinstance(stmt, ReturnStatement):
            self.analyze_return(stmt, scope)
        elif isinstance(stmt, IfStatement):
            self.analyze_if(stmt, scope)
        elif isinstance(stmt, WhileStatement):
            self.analyze_while(stmt, scope)
        elif isinstance(stmt, ForStatement):
            self.analyze_for(stmt, scope)
        elif isinstance(stmt, ExpressionStatement):
            self.analyze_expression(stmt.expression, scope)
        elif isinstance(stmt, BreakStatement):
            if self.loop_depth == 0:
                self.error("'break' used outside of a loop", stmt.line, stmt.col)
        elif isinstance(stmt, ContinueStatement):
            if self.loop_depth == 0:
                self.error("'continue' used outside of a loop", stmt.line, stmt.col)
        else:
            self.error(f"Unknown statement type: {type(stmt).__name__}")

    def analyze_let(self, stmt: LetStatement, scope: Scope):
        """Analyze: let x: int = 42;"""
        # Check the initializer expression type
        value_type = self.analyze_expression(stmt.value, scope)

        # Check type mismatch
        if value_type and value_type != "any" and stmt.type_name != value_type:
            self.error(
                f"Type mismatch: cannot assign '{value_type}' to variable '{stmt.name}' of type '{stmt.type_name}'",
                stmt.line, stmt.col
            )

        # Declare the variable in current scope
        try:
            scope.declare(stmt.name, stmt.type_name, stmt.line, stmt.col)
        except AnalyzerError as e:
            self.errors.append(str(e))

    def analyze_assign(self, stmt: AssignStatement, scope: Scope):
        """Analyze: x = 10;"""
        # Check that variable exists
        try:
            var_type = scope.lookup(stmt.name, stmt.line, stmt.col)
        except AnalyzerError as e:
            self.errors.append(str(e))
            self.analyze_expression(stmt.value, scope)
            return

        # Check expression type
        value_type = self.analyze_expression(stmt.value, scope)

        if value_type and value_type != "any" and var_type != value_type:
            self.error(
                f"Type mismatch: cannot assign '{value_type}' to variable '{stmt.name}' of type '{var_type}'",
                stmt.line, stmt.col
            )

    def analyze_return(self, stmt: ReturnStatement, scope: Scope):
        """Analyze: return expr;"""
        if stmt.value is None:
            if self.current_function_return_type != "void":
                self.error(
                    f"Empty return in function with return type '{self.current_function_return_type}'",
                    stmt.line, stmt.col
                )
        else:
            value_type = self.analyze_expression(stmt.value, scope)
            if value_type and value_type != "any" and value_type != self.current_function_return_type:
                self.error(
                    f"Return type mismatch: returning '{value_type}' but function expects '{self.current_function_return_type}'",
                    stmt.line, stmt.col
                )

    def analyze_if(self, stmt: IfStatement, scope: Scope):
        """Analyze: if cond { ... } else { ... }"""
        cond_type = self.analyze_expression(stmt.condition, scope)
        if cond_type and cond_type != "bool" and cond_type != "any":
            self.error(f"If condition must be 'bool', got '{cond_type}'", stmt.line, stmt.col)

        # Create child scopes for each branch
        then_scope = scope.child()
        for s in stmt.then_body:
            self.analyze_statement(s, then_scope)

        if stmt.else_body:
            else_scope = scope.child()
            for s in stmt.else_body:
                self.analyze_statement(s, else_scope)

    def analyze_while(self, stmt: WhileStatement, scope: Scope):
        """Analyze: while cond { ... }"""
        cond_type = self.analyze_expression(stmt.condition, scope)
        if cond_type and cond_type != "bool" and cond_type != "any":
            self.error(f"While condition must be 'bool', got '{cond_type}'", stmt.line, stmt.col)

        self.loop_depth += 1
        body_scope = scope.child()
        for s in stmt.body:
            self.analyze_statement(s, body_scope)
        self.loop_depth -= 1

    def analyze_for(self, stmt: ForStatement, scope: Scope):
        """Analyze: for init; cond; update { ... }"""
        # For loop gets its own scope (the init variable lives in it)
        for_scope = scope.child()

        self.analyze_statement(stmt.init, for_scope)

        cond_type = self.analyze_expression(stmt.condition, for_scope)
        if cond_type and cond_type != "bool" and cond_type != "any":
            self.error(f"For condition must be 'bool', got '{cond_type}'", stmt.line, stmt.col)

        self.analyze_statement(stmt.update, for_scope)

        self.loop_depth += 1
        for s in stmt.body:
            self.analyze_statement(s, for_scope)
        self.loop_depth -= 1

    # ─── Expressions ───────────────────────────────────────────

    def analyze_expression(self, expr, scope: Scope) -> str:
        """Analyze an expression and return its type."""

        if isinstance(expr, IntLiteral):
            return "int"

        if isinstance(expr, StringLiteral):
            return "string"

        if isinstance(expr, BoolLiteral):
            return "bool"

        if isinstance(expr, Identifier):
            try:
                return scope.lookup(expr.name, expr.line, expr.col)
            except AnalyzerError as e:
                self.errors.append(str(e))
                return "any"

        if isinstance(expr, BinaryOp):
            return self.analyze_binary_op(expr, scope)

        if isinstance(expr, UnaryOp):
            return self.analyze_unary_op(expr, scope)

        if isinstance(expr, FunctionCall):
            return self.analyze_call(expr, scope)

        self.error(f"Unknown expression type: {type(expr).__name__}")
        return "any"

    def analyze_binary_op(self, expr: BinaryOp, scope: Scope) -> str:
        """Analyze a binary operation and return its result type."""
        left_type = self.analyze_expression(expr.left, scope)
        right_type = self.analyze_expression(expr.right, scope)

        # Skip checks if either side has unknown type
        if left_type == "any" or right_type == "any":
            if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                return "bool"
            return "any"

        # Arithmetic operators: +, -, *, /, %
        if expr.op in ("+", "-", "*", "/", "%"):
            if expr.op == "+" and left_type == "string" and right_type == "string":
                return "string"  # string concatenation
            if left_type != "int" or right_type != "int":
                self.error(
                    f"Operator '{expr.op}' requires 'int' operands, got '{left_type}' and '{right_type}'",
                    expr.line, expr.col
                )
            return "int"

        # Comparison operators: ==, !=, <, >, <=, >=
        if expr.op in ("==", "!=", "<", ">", "<=", ">="):
            if left_type != right_type:
                self.error(
                    f"Cannot compare '{left_type}' with '{right_type}' using '{expr.op}'",
                    expr.line, expr.col
                )
            return "bool"

        # Logical operators: &&, ||
        if expr.op in ("&&", "||"):
            if left_type != "bool" or right_type != "bool":
                self.error(
                    f"Operator '{expr.op}' requires 'bool' operands, got '{left_type}' and '{right_type}'",
                    expr.line, expr.col
                )
            return "bool"

        self.error(f"Unknown operator: '{expr.op}'", expr.line, expr.col)
        return "any"

    def analyze_unary_op(self, expr: UnaryOp, scope: Scope) -> str:
        """Analyze a unary operation."""
        operand_type = self.analyze_expression(expr.operand, scope)

        if expr.op == "-":
            if operand_type != "int" and operand_type != "any":
                self.error(f"Unary '-' requires 'int', got '{operand_type}'", expr.line, expr.col)
            return "int"

        if expr.op == "!":
            if operand_type != "bool" and operand_type != "any":
                self.error(f"Unary '!' requires 'bool', got '{operand_type}'", expr.line, expr.col)
            return "bool"

        self.error(f"Unknown unary operator: '{expr.op}'", expr.line, expr.col)
        return "any"

    def analyze_call(self, expr: FunctionCall, scope: Scope) -> str:
        """Analyze a function call."""
        # Check function exists
        if expr.name not in self.functions:
            self.error(f"Undeclared function '{expr.name}'", expr.line, expr.col)
            # Still analyze arguments
            for arg in expr.args:
                self.analyze_expression(arg, scope)
            return "any"

        func_info = self.functions[expr.name]
        expected_params = func_info["params"]

        # Check argument count (skip for print which accepts any number)
        if expr.name != "print" and len(expr.args) != len(expected_params):
            self.error(
                f"Function '{expr.name}' expects {len(expected_params)} argument(s), got {len(expr.args)}",
                expr.line, expr.col
            )

        # Check argument types
        for i, arg in enumerate(expr.args):
            arg_type = self.analyze_expression(arg, scope)
            if i < len(expected_params):
                param_name, param_type = expected_params[i]
                if param_type != "any" and arg_type != "any" and arg_type != param_type:
                    self.error(
                        f"Argument {i + 1} of '{expr.name}' expects '{param_type}', got '{arg_type}'",
                        expr.line, expr.col
                    )

        return func_info["return_type"]


# ─── Quick test ────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    # --- Test 1: Valid program ---
    print("=== Test 1: Valid Program ===\n")
    valid_code = """
fn add(a: int, b: int) -> int {
    return a + b;
}

fn main() -> int {
    let x: int = 42;
    let name: string = "hello";

    if x >= 10 {
        print(x);
    } else {
        print(0);
    }

    let sum: int = add(x, 10);
    print(sum);

    return 0;
}
"""
    lexer = Lexer(valid_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    analyzer = Analyzer()
    try:
        analyzer.analyze(ast)
    except AnalyzerError as e:
        print(e)

    # --- Test 2: Program with errors ---
    print("\n=== Test 2: Program with Errors ===\n")
    bad_code = """
fn main() -> int {
    let x: int = "oops";
    print(y);
    let x: int = 5;
    return "wrong";
}
"""
    lexer2 = Lexer(bad_code)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    ast2 = parser2.parse()
    analyzer2 = Analyzer()
    try:
        analyzer2.analyze(ast2)
    except AnalyzerError as e:
        print(e)
