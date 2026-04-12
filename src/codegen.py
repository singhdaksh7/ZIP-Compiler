"""
Code Generator for the ZIP language.

Converts the AST into x86-64 assembly (AT&T syntax, System V ABI).
The generated assembly can be assembled and linked on Linux (or WSL):

    gcc -o output output.s -no-pie

Usage:
    codegen = CodeGenerator()
    asm = codegen.generate(ast)
"""

from ast_nodes import (
    Program, Function, Parameter,
    LetStatement, AssignStatement, ReturnStatement,
    IfStatement, WhileStatement, ForStatement, ExpressionStatement,
    BreakStatement, ContinueStatement,
    BinaryOp, UnaryOp, IntLiteral, StringLiteral, BoolLiteral,
    Identifier, FunctionCall,
)


class CodeGenError(Exception):
    """Raised when code generation fails."""
    pass


class CodeGenerator:
    def __init__(self):
        self.output = []            # lines of assembly
        self.string_literals = []   # collected string constants
        self.label_count = 0        # for generating unique labels

        # Per-function state (reset in generate_function)
        self.variables = {}         # var name -> stack offset from %rbp
        self.var_types = {}         # var name -> type ("int", "string", "bool")
        self.stack_offset = 0       # current top-of-locals offset
        self.max_stack_offset = 0   # maximum depth reached (for PLACEHOLDER patch)
        self.scope_stack = []       # for saving/restoring scopes across blocks

        # Loop label stack for break/continue: list of (loop_top_label, loop_end_label)
        self.loop_labels = []

        # Function signatures (populated from Program before body gen)
        self.func_return_types = {} # fn name -> return type string

    def emit(self, line: str):
        """Add a line of assembly."""
        self.output.append(line)

    def label(self, prefix: str) -> str:
        """Generate a unique label."""
        self.label_count += 1
        return f".L{prefix}_{self.label_count}"

    def add_string(self, value: str) -> str:
        """Add a string literal to the data section and return its label."""
        label = f".str_{len(self.string_literals)}"
        self.string_literals.append((label, value))
        return label

    def push_scope(self):
        """Save the current variable scope (variables, types, and stack_offset)."""
        self.scope_stack.append((
            dict(self.variables),
            dict(self.var_types),
            self.stack_offset,
        ))

    def pop_scope(self):
        """
        Restore the previous variable scope.

        IMPORTANT: we restore stack_offset so that stack slots used by
        out-of-scope variables can be reused — but we keep max_stack_offset
        at the high-water mark so the function prologue reserves enough space.
        """
        self.variables, self.var_types, self.stack_offset = self.scope_stack.pop()

    def alloc_var(self, name: str, var_type: str):
        """Allocate 8 bytes on the stack for a new variable."""
        self.stack_offset += 8
        self.variables[name] = self.stack_offset
        self.var_types[name] = var_type
        if self.stack_offset > self.max_stack_offset:
            self.max_stack_offset = self.stack_offset

    def expr_type(self, expr) -> str:
        """
        Best-effort type inference for an expression (used by print).
        Returns "string", "int", "bool", or "unknown".
        """
        if isinstance(expr, StringLiteral):
            return "string"
        if isinstance(expr, IntLiteral):
            return "int"
        if isinstance(expr, BoolLiteral):
            return "int"   # bools are 0/1 integers at runtime
        if isinstance(expr, Identifier):
            return self.var_types.get(expr.name, "unknown")
        if isinstance(expr, FunctionCall):
            return self.func_return_types.get(expr.name, "unknown")
        if isinstance(expr, BinaryOp):
            if expr.op in ("+", "-", "*", "/", "%"):
                left = self.expr_type(expr.left)
                if left == "string":
                    return "string"
                return "int"
            if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                return "int"   # booleans stored as int
        if isinstance(expr, UnaryOp):
            if expr.op == "-":
                return "int"
            if expr.op == "!":
                return "int"
        return "unknown"

    # ─── Main Entry Point ──────────────────────────────────────

    def generate(self, program: Program) -> str:
        """Generate x86-64 assembly for the entire program."""

        # Collect function return types for type-aware code generation
        for fn in program.functions:
            self.func_return_types[fn.name] = fn.return_type
        # Built-ins
        self.func_return_types["print"] = "void"

        # Text section
        self.emit("    .text")

        # Generate each function
        for fn in program.functions:
            self.generate_function(fn)

        # Build the final output with data section at the top
        result = []

        # User string literals
        if self.string_literals:
            result.append("    .section .rodata")
            for lbl, value in self.string_literals:
                escaped = (value
                           .replace("\\", "\\\\")
                           .replace('"', '\\"')
                           .replace("\n", "\\n")
                           .replace("\t", "\\t"))
                result.append(f'{lbl}:')
                result.append(f'    .string "{escaped}"')
            result.append("")

        # Printf format strings
        result.append("    .section .rodata")
        result.append('.int_fmt:')
        result.append('    .string "%d\\n"')
        result.append('.str_fmt:')
        result.append('    .string "%s\\n"')
        result.append("")

        result.extend(self.output)
        return "\n".join(result)

    # ─── Functions ─────────────────────────────────────────────

    def generate_function(self, fn: Function):
        """Generate assembly for a function definition."""
        # Reset per-function state
        self.variables = {}
        self.var_types = {}
        self.stack_offset = 0
        self.max_stack_offset = 0
        self.scope_stack = []
        self.loop_labels = []

        self.emit(f"    .globl {fn.name}")
        self.emit(f"{fn.name}:")

        # Prologue
        self.emit("    pushq %rbp")
        self.emit("    movq %rsp, %rbp")

        # Reserve stack space — patch after body so we know the real size
        stack_reserve_index = len(self.output)
        self.emit("    subq $PLACEHOLDER, %rsp")

        # Spill parameters from registers to the stack (System V ABI)
        param_registers = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]
        for i, param in enumerate(fn.params):
            if i >= len(param_registers):
                raise CodeGenError(f"Function '{fn.name}': more than 6 parameters not supported")
            self.alloc_var(param.name, param.type_name)
            self.emit(f"    movq {param_registers[i]}, -{self.stack_offset}(%rbp)")

        # Generate body
        for stmt in fn.body:
            self.generate_statement(stmt)

        # Implicit return 0 if the last statement is not a return
        if not fn.body or not isinstance(fn.body[-1], ReturnStatement):
            self.emit("    movq $0, %rax")
            self.emit("    leave")
            self.emit("    ret")

        # Patch PLACEHOLDER with the actual (max) stack size, 16-byte aligned
        total = self.max_stack_offset
        if total % 16 != 0:
            total += 16 - (total % 16)
        if total == 0:
            total = 16   # always reserve at least 16 bytes
        self.output[stack_reserve_index] = f"    subq ${total}, %rsp"

        self.emit("")  # blank line between functions

    # ─── Statements ────────────────────────────────────────────

    def generate_statement(self, stmt):
        """Dispatch to the appropriate statement generator."""
        if isinstance(stmt, LetStatement):
            self.generate_let(stmt)
        elif isinstance(stmt, AssignStatement):
            self.generate_assign(stmt)
        elif isinstance(stmt, ReturnStatement):
            self.generate_return(stmt)
        elif isinstance(stmt, IfStatement):
            self.generate_if(stmt)
        elif isinstance(stmt, WhileStatement):
            self.generate_while(stmt)
        elif isinstance(stmt, ForStatement):
            self.generate_for(stmt)
        elif isinstance(stmt, ExpressionStatement):
            self.generate_expression(stmt.expression)
        elif isinstance(stmt, BreakStatement):
            self.generate_break(stmt)
        elif isinstance(stmt, ContinueStatement):
            self.generate_continue(stmt)
        else:
            raise CodeGenError(f"Unknown statement type: {type(stmt).__name__}")

    def generate_let(self, stmt: LetStatement):
        """Generate: let x: type = expr;"""
        self.generate_expression(stmt.value)
        self.alloc_var(stmt.name, stmt.type_name)
        self.emit(f"    movq %rax, -{self.stack_offset}(%rbp)")

    def generate_assign(self, stmt: AssignStatement):
        """Generate: x = expr;"""
        self.generate_expression(stmt.value)
        if stmt.name not in self.variables:
            raise CodeGenError(f"Undeclared variable '{stmt.name}' in assignment")
        offset = self.variables[stmt.name]
        self.emit(f"    movq %rax, -{offset}(%rbp)")

    def generate_return(self, stmt: ReturnStatement):
        """Generate: return expr;"""
        if stmt.value:
            self.generate_expression(stmt.value)
        else:
            self.emit("    movq $0, %rax")
        self.emit("    leave")
        self.emit("    ret")

    def generate_if(self, stmt: IfStatement):
        """Generate: if cond { ... } else { ... }"""
        else_label = self.label("else")
        end_label = self.label("endif")

        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")

        if stmt.else_body:
            self.emit(f"    je {else_label}")
        else:
            self.emit(f"    je {end_label}")

        self.push_scope()
        for s in stmt.then_body:
            self.generate_statement(s)
        self.pop_scope()

        if stmt.else_body:
            self.emit(f"    jmp {end_label}")
            self.emit(f"{else_label}:")
            self.push_scope()
            for s in stmt.else_body:
                self.generate_statement(s)
            self.pop_scope()

        self.emit(f"{end_label}:")

    def generate_while(self, stmt: WhileStatement):
        """Generate: while cond { ... }"""
        loop_label = self.label("while")
        end_label = self.label("endwhile")

        self.loop_labels.append((loop_label, end_label))
        self.emit(f"{loop_label}:")

        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")
        self.emit(f"    je {end_label}")

        self.push_scope()
        for s in stmt.body:
            self.generate_statement(s)
        self.pop_scope()

        self.emit(f"    jmp {loop_label}")
        self.emit(f"{end_label}:")
        self.loop_labels.pop()

    def generate_for(self, stmt: ForStatement):
        """Generate: for init; cond; update { ... }"""
        cond_label   = self.label("for")
        update_label = self.label("for_update")   # continue target: run update first
        end_label    = self.label("endfor")

        self.push_scope()
        self.generate_statement(stmt.init)

        # For `continue`: jump to update (not condition), so the increment runs.
        self.loop_labels.append((update_label, end_label))
        self.emit(f"{cond_label}:")

        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")
        self.emit(f"    je {end_label}")

        for s in stmt.body:
            self.generate_statement(s)

        self.emit(f"{update_label}:")
        self.generate_statement(stmt.update)
        self.emit(f"    jmp {cond_label}")
        self.emit(f"{end_label}:")

        self.loop_labels.pop()
        self.pop_scope()

    def generate_break(self, stmt: BreakStatement):
        """Generate: break;  — jump to end of nearest enclosing loop."""
        if not self.loop_labels:
            raise CodeGenError("'break' used outside of a loop")
        _, end_label = self.loop_labels[-1]
        self.emit(f"    jmp {end_label}")

    def generate_continue(self, stmt: ContinueStatement):
        """Generate: continue;  — jump to top of nearest enclosing loop."""
        if not self.loop_labels:
            raise CodeGenError("'continue' used outside of a loop")
        loop_label, _ = self.loop_labels[-1]
        self.emit(f"    jmp {loop_label}")

    # ─── Expressions ───────────────────────────────────────────
    # All expressions leave their result in %rax

    def generate_expression(self, expr):
        """Generate code for an expression. Result ends up in %rax."""

        if isinstance(expr, IntLiteral):
            self.emit(f"    movq ${expr.value}, %rax")

        elif isinstance(expr, BoolLiteral):
            self.emit(f"    movq ${'1' if expr.value else '0'}, %rax")

        elif isinstance(expr, StringLiteral):
            lbl = self.add_string(expr.value)
            self.emit(f"    leaq {lbl}(%rip), %rax")

        elif isinstance(expr, Identifier):
            if expr.name not in self.variables:
                raise CodeGenError(f"Undeclared variable '{expr.name}'")
            offset = self.variables[expr.name]
            self.emit(f"    movq -{offset}(%rbp), %rax")

        elif isinstance(expr, BinaryOp):
            self.generate_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            self.generate_unary_op(expr)

        elif isinstance(expr, FunctionCall):
            self.generate_call(expr)

        else:
            raise CodeGenError(f"Unknown expression type: {type(expr).__name__}")

    def generate_binary_op(self, expr: BinaryOp):
        """Generate code for a binary operation. Result in %rax."""
        # Evaluate left, save on stack
        self.generate_expression(expr.left)
        self.emit("    pushq %rax")

        # Evaluate right
        self.generate_expression(expr.right)
        self.emit("    movq %rax, %rcx")   # right -> %rcx

        # Restore left to %rax
        self.emit("    popq %rax")          # left -> %rax

        # Arithmetic
        if expr.op == "+":
            self.emit("    addq %rcx, %rax")
        elif expr.op == "-":
            self.emit("    subq %rcx, %rax")
        elif expr.op == "*":
            self.emit("    imulq %rcx, %rax")
        elif expr.op == "/":
            self.emit("    cqto")
            self.emit("    idivq %rcx")
        elif expr.op == "%":
            self.emit("    cqto")
            self.emit("    idivq %rcx")
            self.emit("    movq %rdx, %rax")

        # Comparisons — produce 1 or 0
        elif expr.op in ("==", "!=", "<", ">", "<=", ">="):
            self.emit("    cmpq %rcx, %rax")
            set_map = {
                "==": "sete",  "!=": "setne",
                "<":  "setl",  ">":  "setg",
                "<=": "setle", ">=": "setge",
            }
            self.emit(f"    {set_map[expr.op]} %al")
            self.emit("    movzbq %al, %rax")

        # Logical &&  (short-circuit already evaluated both sides, but that's OK
        # for a simple compiler; true short-circuit needs jump-based lazy eval)
        elif expr.op == "&&":
            self.emit("    cmpq $0, %rax")
            short = self.label("and_short")
            end   = self.label("and_end")
            self.emit(f"    je {short}")
            self.emit("    cmpq $0, %rcx")
            self.emit("    setne %al")
            self.emit("    movzbq %al, %rax")
            self.emit(f"    jmp {end}")
            self.emit(f"{short}:")
            self.emit("    movq $0, %rax")
            self.emit(f"{end}:")

        elif expr.op == "||":
            self.emit("    cmpq $0, %rax")
            short = self.label("or_short")
            end   = self.label("or_end")
            self.emit(f"    jne {short}")
            self.emit("    cmpq $0, %rcx")
            self.emit("    setne %al")
            self.emit("    movzbq %al, %rax")
            self.emit(f"    jmp {end}")
            self.emit(f"{short}:")
            self.emit("    movq $1, %rax")
            self.emit(f"{end}:")

        else:
            raise CodeGenError(f"Unknown binary operator: '{expr.op}'")

    def generate_unary_op(self, expr: UnaryOp):
        """Generate code for a unary operation. Result in %rax."""
        self.generate_expression(expr.operand)
        if expr.op == "-":
            self.emit("    negq %rax")
        elif expr.op == "!":
            self.emit("    cmpq $0, %rax")
            self.emit("    sete %al")
            self.emit("    movzbq %al, %rax")
        else:
            raise CodeGenError(f"Unknown unary operator: '{expr.op}'")

    def generate_call(self, expr: FunctionCall):
        """Generate code for a function call. Return value in %rax."""
        if expr.name == "print":
            self.generate_print(expr)
            return

        arg_registers = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]

        # Evaluate all args and push to stack
        for arg in expr.args:
            self.generate_expression(arg)
            self.emit("    pushq %rax")

        # Pop into registers (reverse order)
        for i in range(len(expr.args) - 1, -1, -1):
            self.emit(f"    popq {arg_registers[i]}")

        self.emit("    movq $0, %rax")   # clear AL for variadic calls
        self.emit(f"    call {expr.name}")

    def generate_print(self, expr: FunctionCall):
        """
        Generate code for the built-in print(value).

        Uses printf with %d\\n for integers/bools and %s\\n for strings.
        The type is determined statically from the AST.
        """
        if not expr.args:
            return

        arg = expr.args[0]
        self.generate_expression(arg)   # result in %rax

        t = self.expr_type(arg)
        if t == "string":
            self.emit("    movq %rax, %rsi")
            self.emit("    leaq .str_fmt(%rip), %rdi")
        else:
            # int, bool, or unknown — default to %d
            self.emit("    movq %rax, %rsi")
            self.emit("    leaq .int_fmt(%rip), %rdi")

        self.emit("    movq $0, %rax")
        self.emit("    call printf")


# ─── Quick test ────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser
    from analyzer import Analyzer

    test_code = """
fn add(a: int, b: int) -> int {
    return a + b;
}

fn main() -> int {
    let x: int = 42;
    let y: int = 10;
    let sum: int = add(x, y);

    print(sum);

    if sum >= 50 {
        print(1);
    } else {
        print(0);
    }

    let i: int = 0;
    while i < 5 {
        if i == 3 {
            i = i + 1;
            continue;
        }
        print(i);
        i = i + 1;
    }

    for let j: int = 0; j < 3; j = j + 1 {
        if j == 2 {
            break;
        }
        print(j);
    }

    return 0;
}
"""

    print("=== ZIP Code Generator ===\n")

    lexer = Lexer(test_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    analyzer = Analyzer()
    analyzer.analyze(ast)
    codegen = CodeGenerator()
    asm = codegen.generate(ast)

    print(asm)
    print("\n--- Assembly generation complete! ---")
