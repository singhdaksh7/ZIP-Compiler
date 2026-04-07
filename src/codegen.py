"""
Code Generator for the ZIP language.

Converts the AST into x86-64 assembly (AT&T syntax, System V ABI).
The generated assembly can be assembled and linked on Linux (or WSL):

    as -o output.o output.s
    ld -o output output.o -lc -dynamic-linker /lib64/ld-linux-x86-64.so.2

Or with GCC:
    gcc -o output output.s -no-pie

Usage:
    codegen = CodeGenerator()
    asm = codegen.generate(ast)
"""

from ast_nodes import (
    Program, Function, Parameter,
    LetStatement, AssignStatement, ReturnStatement,
    IfStatement, WhileStatement, ForStatement, ExpressionStatement,
    BinaryOp, UnaryOp, IntLiteral, StringLiteral, BoolLiteral,
    Identifier, FunctionCall,
)


class CodeGenError(Exception):
    """Raised when code generation fails."""
    pass


class CodeGenerator:
    def __init__(self):
        self.output = []           # lines of assembly
        self.string_literals = []  # collected string constants
        self.label_count = 0       # for generating unique labels
        self.variables = {}        # variable name -> stack offset
        self.stack_offset = 0      # current stack offset
        self.scope_stack = []      # for saving/restoring scopes

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
        """Save the current variable scope."""
        self.scope_stack.append((dict(self.variables), self.stack_offset))

    def pop_scope(self):
        """Restore the previous variable scope."""
        self.variables, self.stack_offset = self.scope_stack.pop()

    # ─── Main Entry Point ──────────────────────────────────────

    def generate(self, program: Program) -> str:
        """Generate x86-64 assembly for the entire program."""

        # Data section (string literals will be added here)
        # We'll insert them at the end once we know all strings

        # Text section
        self.emit("    .text")

        # Generate each function
        for fn in program.functions:
            self.generate_function(fn)

        # Build the final output with data section
        result = []

        # Data section for string literals
        if self.string_literals:
            result.append("    .section .rodata")
            for label, value in self.string_literals:
                # Escape special characters for assembly
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
                result.append(f'{label}:')
                result.append(f'    .string "{escaped}"')
            result.append("")

        # Format string for printf (integers)
        result.append("    .section .rodata")
        result.append('.int_fmt:')
        result.append('    .string "%d\\n"')
        result.append('.str_fmt:')
        result.append('    .string "%s\\n"')
        result.append("")

        # Add the text section
        result.extend(self.output)

        return "\n".join(result)

    # ─── Functions ─────────────────────────────────────────────

    def generate_function(self, fn: Function):
        """Generate assembly for a function definition."""
        self.variables = {}
        self.stack_offset = 0
        self.scope_stack = []

        # Make the function visible to the linker
        self.emit(f"    .globl {fn.name}")
        self.emit(f"{fn.name}:")

        # Function prologue: set up stack frame
        self.emit("    pushq %rbp")
        self.emit("    movq %rsp, %rbp")

        # Reserve stack space (we'll patch this later)
        stack_reserve_index = len(self.output)
        self.emit("    subq $PLACEHOLDER, %rsp")

        # Store parameters on the stack
        # System V ABI: first 6 args in rdi, rsi, rdx, rcx, r8, r9
        param_registers = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]
        for i, param in enumerate(fn.params):
            if i < len(param_registers):
                self.stack_offset += 8
                self.variables[param.name] = self.stack_offset
                self.emit(f"    movq {param_registers[i]}, -{self.stack_offset}(%rbp)")

        # Generate body
        for stmt in fn.body:
            self.generate_statement(stmt)

        # If function has no explicit return, add one
        if not fn.body or not isinstance(fn.body[-1], ReturnStatement):
            self.emit("    movq $0, %rax")
            self.emit("    leave")
            self.emit("    ret")

        # Patch stack reservation (align to 16 bytes)
        total_stack = self.stack_offset
        if total_stack % 16 != 0:
            total_stack += 16 - (total_stack % 16)
        if total_stack == 0:
            total_stack = 16  # minimum reservation
        self.output[stack_reserve_index] = f"    subq ${total_stack}, %rsp"

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
        else:
            raise CodeGenError(f"Unknown statement type: {type(stmt).__name__}")

    def generate_let(self, stmt: LetStatement):
        """Generate: let x: int = expr;"""
        # Evaluate the expression (result goes in %rax)
        self.generate_expression(stmt.value)

        # Allocate stack space for this variable
        self.stack_offset += 8
        self.variables[stmt.name] = self.stack_offset

        # Store the value on the stack
        self.emit(f"    movq %rax, -{self.stack_offset}(%rbp)")

    def generate_assign(self, stmt: AssignStatement):
        """Generate: x = expr;"""
        self.generate_expression(stmt.value)
        offset = self.variables[stmt.name]
        self.emit(f"    movq %rax, -{offset}(%rbp)")

    def generate_return(self, stmt: ReturnStatement):
        """Generate: return expr;"""
        if stmt.value:
            self.generate_expression(stmt.value)
        else:
            self.emit("    movq $0, %rax")

        # Function epilogue
        self.emit("    leave")
        self.emit("    ret")

    def generate_if(self, stmt: IfStatement):
        """Generate: if cond { ... } else { ... }"""
        else_label = self.label("else")
        end_label = self.label("endif")

        # Evaluate condition
        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")

        if stmt.else_body:
            self.emit(f"    je {else_label}")
        else:
            self.emit(f"    je {end_label}")

        # Then body
        self.push_scope()
        for s in stmt.then_body:
            self.generate_statement(s)
        self.pop_scope()

        if stmt.else_body:
            self.emit(f"    jmp {end_label}")
            self.emit(f"{else_label}:")

            # Else body
            self.push_scope()
            for s in stmt.else_body:
                self.generate_statement(s)
            self.pop_scope()

        self.emit(f"{end_label}:")

    def generate_while(self, stmt: WhileStatement):
        """Generate: while cond { ... }"""
        loop_label = self.label("while")
        end_label = self.label("endwhile")

        self.emit(f"{loop_label}:")

        # Evaluate condition
        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")
        self.emit(f"    je {end_label}")

        # Body
        self.push_scope()
        for s in stmt.body:
            self.generate_statement(s)
        self.pop_scope()

        self.emit(f"    jmp {loop_label}")
        self.emit(f"{end_label}:")

    def generate_for(self, stmt: ForStatement):
        """Generate: for init; cond; update { ... }"""
        loop_label = self.label("for")
        end_label = self.label("endfor")

        self.push_scope()

        # Init
        self.generate_statement(stmt.init)

        # Loop start
        self.emit(f"{loop_label}:")

        # Condition
        self.generate_expression(stmt.condition)
        self.emit("    cmpq $0, %rax")
        self.emit(f"    je {end_label}")

        # Body
        for s in stmt.body:
            self.generate_statement(s)

        # Update
        self.generate_statement(stmt.update)

        self.emit(f"    jmp {loop_label}")
        self.emit(f"{end_label}:")

        self.pop_scope()

    # ─── Expressions ───────────────────────────────────────────
    # All expressions leave their result in %rax

    def generate_expression(self, expr):
        """Generate code for an expression. Result ends up in %rax."""

        if isinstance(expr, IntLiteral):
            self.emit(f"    movq ${expr.value}, %rax")

        elif isinstance(expr, BoolLiteral):
            val = 1 if expr.value else 0
            self.emit(f"    movq ${val}, %rax")

        elif isinstance(expr, StringLiteral):
            label = self.add_string(expr.value)
            self.emit(f"    leaq {label}(%rip), %rax")

        elif isinstance(expr, Identifier):
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
        """Generate code for a binary operation."""
        # Evaluate left side
        self.generate_expression(expr.left)
        self.emit("    pushq %rax")  # save left on stack

        # Evaluate right side
        self.generate_expression(expr.right)
        self.emit("    movq %rax, %rcx")  # right in %rcx

        # Restore left to %rax
        self.emit("    popq %rax")  # left in %rax

        # Arithmetic
        if expr.op == "+":
            self.emit("    addq %rcx, %rax")
        elif expr.op == "-":
            self.emit("    subq %rcx, %rax")
        elif expr.op == "*":
            self.emit("    imulq %rcx, %rax")
        elif expr.op == "/":
            self.emit("    cqto")           # sign-extend rax into rdx:rax
            self.emit("    idivq %rcx")     # result in rax, remainder in rdx
        elif expr.op == "%":
            self.emit("    cqto")
            self.emit("    idivq %rcx")
            self.emit("    movq %rdx, %rax")  # remainder is in rdx

        # Comparisons (result: 1 or 0 in %rax)
        elif expr.op in ("==", "!=", "<", ">", "<=", ">="):
            self.emit("    cmpq %rcx, %rax")
            cond_map = {
                "==": "sete",
                "!=": "setne",
                "<":  "setl",
                ">":  "setg",
                "<=": "setle",
                ">=": "setge",
            }
            self.emit(f"    {cond_map[expr.op]} %al")
            self.emit("    movzbq %al, %rax")

        # Logical
        elif expr.op == "&&":
            # Short-circuit: if left is 0, result is 0
            self.emit("    cmpq $0, %rax")
            short_label = self.label("and_short")
            end_label = self.label("and_end")
            self.emit(f"    je {short_label}")
            # Left is true, check right
            self.emit("    cmpq $0, %rcx")
            self.emit("    setne %al")
            self.emit("    movzbq %al, %rax")
            self.emit(f"    jmp {end_label}")
            self.emit(f"{short_label}:")
            self.emit("    movq $0, %rax")
            self.emit(f"{end_label}:")

        elif expr.op == "||":
            # Short-circuit: if left is 1, result is 1
            self.emit("    cmpq $0, %rax")
            short_label = self.label("or_short")
            end_label = self.label("or_end")
            self.emit(f"    jne {short_label}")
            # Left is false, check right
            self.emit("    cmpq $0, %rcx")
            self.emit("    setne %al")
            self.emit("    movzbq %al, %rax")
            self.emit(f"    jmp {end_label}")
            self.emit(f"{short_label}:")
            self.emit("    movq $1, %rax")
            self.emit(f"{end_label}:")

        else:
            raise CodeGenError(f"Unknown binary operator: '{expr.op}'")

    def generate_unary_op(self, expr: UnaryOp):
        """Generate code for a unary operation."""
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
        """Generate code for a function call."""
        # Handle print specially
        if expr.name == "print":
            self.generate_print(expr)
            return

        # Evaluate arguments and put them in the right registers
        arg_registers = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]

        # First, evaluate all args and push them (in case they clobber registers)
        for arg in expr.args:
            self.generate_expression(arg)
            self.emit("    pushq %rax")

        # Pop args into registers (in reverse order)
        for i in range(len(expr.args) - 1, -1, -1):
            self.emit(f"    popq {arg_registers[i]}")

        # Align stack to 16 bytes before call if needed
        self.emit("    movq $0, %rax")  # clear rax (for variadic functions)
        self.emit(f"    call {expr.name}")

    def generate_print(self, expr: FunctionCall):
        """Generate code for the built-in print function using printf."""
        if not expr.args:
            return

        # Evaluate the argument
        self.generate_expression(expr.args[0])

        # For now, we'll determine at compile time if it's a string or int
        arg = expr.args[0]
        if isinstance(arg, StringLiteral):
            # String: use %s format
            self.emit("    movq %rax, %rsi")           # string pointer as second arg
            self.emit("    leaq .str_fmt(%rip), %rdi")  # format string as first arg
        else:
            # Integer (default): use %d format
            self.emit("    movq %rax, %rsi")           # value as second arg
            self.emit("    leaq .int_fmt(%rip), %rdi")  # format string as first arg

        self.emit("    movq $0, %rax")  # no vector args for printf
        self.emit("    call printf")


# ─── Quick test ────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser
    from analyzer import Analyzer

    test_code = """
fn main() -> int {
    let x: int = 42;
    let y: int = 10;
    let sum: int = x + y;

    print(sum);

    if sum >= 50 {
        print(1);
    } else {
        print(0);
    }

    let i: int = 0;
    while i < 5 {
        print(i);
        i = i + 1;
    }

    return 0;
}
"""

    print("=== ZIP Code Generator ===\n")

    # Lex
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()

    # Analyze
    analyzer = Analyzer()
    analyzer.analyze(ast)

    # Generate
    codegen = CodeGenerator()
    asm = codegen.generate(ast)

    print(asm)
    print("\n--- Assembly generation complete! ---")
    print("To compile (on Linux/WSL):")
    print("  gcc -o program output.s -no-pie")
    print("  ./program")
