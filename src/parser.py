"""
Parser for the ZIP language.

Converts a flat list of tokens (from the lexer) into an Abstract Syntax Tree (AST).
Uses recursive descent parsing with operator precedence.

Usage:
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
"""

from tokens import Token, TokenType
from ast_nodes import (
    Program, Function, Parameter,
    LetStatement, AssignStatement, ReturnStatement,
    IfStatement, WhileStatement, ForStatement, ExpressionStatement,
    BreakStatement, ContinueStatement,
    BinaryOp, UnaryOp, IntLiteral, StringLiteral, BoolLiteral,
    Identifier, FunctionCall,
)


class ParserError(Exception):
    """Raised when the parser encounters unexpected tokens."""
    def __init__(self, message, token):
        self.token = token
        super().__init__(f"Parse error at line {token.line}, col {token.column}: {message}")


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0   # current position in the token list
        self.token_count = len(tokens)  # Cache token count
        
        # Pre-compute token type sets for fast matching
        self._comparison_ops = (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE)
        self._equality_ops = (TokenType.EQ, TokenType.NEQ)
        self._addition_ops = (TokenType.PLUS, TokenType.MINUS)
        self._multiplication_ops = (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT)
        self._unary_ops = (TokenType.MINUS, TokenType.NOT)

    # ─── Helpers ───────────────────────────────────────────────

    def current(self) -> Token:
        """Return the current token."""
        return self.tokens[self.pos]

    def peek(self) -> Token:
        """Same as current — look at the token without consuming it."""
        return self.tokens[self.pos]

    def advance(self) -> Token:
        """Consume and return the current token, then move forward."""
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        """Consume the current token if it matches the expected type. Otherwise, raise an error."""
        token = self.current()
        if token.type != token_type:
            raise ParserError(f"Expected {token_type.name}, got {token.type.name} ('{token.value}')", token)
        return self.advance()

    def match(self, *types: TokenType) -> Token | None:
        """If the current token matches any of the given types, consume and return it."""
        if self.current().type in types:
            return self.advance()
        return None

    # ─── Program (top level) ───────────────────────────────────

    def parse(self) -> Program:
        """Parse the entire program: a list of function definitions."""
        functions = []
        while self.current().type != TokenType.EOF:
            functions.append(self.parse_function())
        return Program(functions=functions)

    # ─── Function ──────────────────────────────────────────────

    def parse_function(self) -> Function:
        """
        Parse a function definition:
            fn name(param: type, ...) -> return_type { body }
        """
        token = self.expect(TokenType.FN)
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value

        # Parameters
        self.expect(TokenType.LPAREN)
        params = []
        if self.current().type != TokenType.RPAREN:
            params = self.parse_param_list()
        self.expect(TokenType.RPAREN)

        # Return type (optional, defaults to void)
        return_type = "void"
        if self.match(TokenType.ARROW):
            type_token = self.advance()
            return_type = type_token.value

        # Body
        body = self.parse_block()

        return Function(
            name=name,
            params=params,
            return_type=return_type,
            body=body,
            line=token.line,
            col=token.column,
        )

    def parse_param_list(self) -> list[Parameter]:
        """Parse a comma-separated list of parameters: x: int, y: bool"""
        params = []
        params.append(self.parse_param())
        while self.match(TokenType.COMMA):
            params.append(self.parse_param())
        return params

    def parse_param(self) -> Parameter:
        """Parse a single parameter: name: type"""
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        type_name = self.advance().value
        return Parameter(name=name, type_name=type_name)

    # ─── Block ─────────────────────────────────────────────────

    def parse_block(self) -> list:
        """Parse a block of statements: { stmt; stmt; ... }"""
        self.expect(TokenType.LBRACE)
        statements = []
        while self.current().type != TokenType.RBRACE:
            statements.append(self.parse_statement())
        self.expect(TokenType.RBRACE)
        return statements

    # ─── Statements ────────────────────────────────────────────

    def parse_statement(self):
        """Parse a single statement based on the current token."""
        token = self.current()

        if token.type == TokenType.LET:
            return self.parse_let()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.WHILE:
            return self.parse_while()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        elif token.type == TokenType.BREAK:
            t = self.advance()
            self.expect(TokenType.SEMICOLON)
            return BreakStatement(line=t.line, col=t.column)
        elif token.type == TokenType.CONTINUE:
            t = self.advance()
            self.expect(TokenType.SEMICOLON)
            return ContinueStatement(line=t.line, col=t.column)
        else:
            return self.parse_expression_or_assign()

    def parse_let(self) -> LetStatement:
        """
        Parse a let statement:
            let name: type = value;
        """
        token = self.advance()  # consume 'let'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        type_name = self.advance().value
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        return LetStatement(name=name, type_name=type_name, value=value, line=token.line, col=token.column)

    def parse_return(self) -> ReturnStatement:
        """
        Parse a return statement:
            return;
            return expr;
        """
        token = self.advance()  # consume 'return'

        # Check for bare return (no value)
        if self.current().type == TokenType.SEMICOLON:
            self.advance()
            return ReturnStatement(value=None, line=token.line, col=token.column)

        value = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        return ReturnStatement(value=value, line=token.line, col=token.column)

    def parse_if(self) -> IfStatement:
        """
        Parse an if/else statement:
            if condition { body }
            if condition { body } else { body }
        """
        token = self.advance()  # consume 'if'
        condition = self.parse_expression()
        then_body = self.parse_block()

        else_body = []
        if self.match(TokenType.ELSE):
            if self.current().type == TokenType.IF:
                # else if → treat as a single if statement inside else
                else_body = [self.parse_if()]
            else:
                else_body = self.parse_block()

        return IfStatement(
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            line=token.line,
            col=token.column,
        )

    def parse_while(self) -> WhileStatement:
        """
        Parse a while loop:
            while condition { body }
        """
        token = self.advance()  # consume 'while'
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(condition=condition, body=body, line=token.line, col=token.column)

    def parse_for(self) -> ForStatement:
        """
        Parse a for loop:
            for init; condition; update { body }

        Example:
            for let i: int = 0; i < 10; i = i + 1 { ... }
        """
        token = self.advance()  # consume 'for'

        # Init: either a let statement or an assignment
        if self.current().type == TokenType.LET:
            init = self.parse_let()  # let already consumes semicolon
        else:
            init = self.parse_expression_or_assign()  # consumes semicolon

        # Condition
        condition = self.parse_expression()
        self.expect(TokenType.SEMICOLON)

        # Update (assignment, no semicolon — block follows)
        update_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        update_value = self.parse_expression()
        update = AssignStatement(name=update_name, value=update_value)

        # Body
        body = self.parse_block()

        return ForStatement(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=token.line,
            col=token.column,
        )

    def parse_expression_or_assign(self):
        """
        Parse either:
            - assignment:  x = expr;
            - expression statement:  print(x);
        """
        # Check if it's an assignment: IDENTIFIER followed by =
        if (self.current().type == TokenType.IDENTIFIER
                and self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TokenType.ASSIGN):
            token = self.advance()  # consume identifier
            self.advance()  # consume =
            value = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return AssignStatement(name=token.value, value=value, line=token.line, col=token.column)

        # Otherwise it's an expression statement (like a function call)
        expr = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        return ExpressionStatement(expression=expr, line=expr.line if hasattr(expr, 'line') else 0,
                                   col=expr.col if hasattr(expr, 'col') else 0)

    # ─── Expressions (with operator precedence) ────────────────

    def parse_expression(self):
        """Entry point for expression parsing. Starts at the lowest precedence."""
        return self.parse_or()

    def parse_or(self):
        """Parse || (lowest precedence)."""
        left = self.parse_and()
        while self.current().type == TokenType.OR:
            op_token = self.advance()
            right = self.parse_and()
            left = BinaryOp(left=left, op="||", right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_and(self):
        """Parse && """
        left = self.parse_equality()
        while self.current().type == TokenType.AND:
            op_token = self.advance()
            right = self.parse_equality()
            left = BinaryOp(left=left, op="&&", right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_equality(self):
        """Parse == and != """
        left = self.parse_comparison()
        while self.current().type in self._equality_ops:
            op_token = self.advance()
            right = self.parse_comparison()
            left = BinaryOp(left=left, op=op_token.value, right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_comparison(self):
        """Parse <, >, <=, >= """
        left = self.parse_addition()
        while self.current().type in self._comparison_ops:
            op_token = self.advance()
            right = self.parse_addition()
            left = BinaryOp(left=left, op=op_token.value, right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_addition(self):
        """Parse + and - """
        left = self.parse_multiplication()
        while self.current().type in self._addition_ops:
            op_token = self.advance()
            right = self.parse_multiplication()
            left = BinaryOp(left=left, op=op_token.value, right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_multiplication(self):
        """Parse *, /, % """
        left = self.parse_unary()
        while self.current().type in self._multiplication_ops:
            op_token = self.advance()
            right = self.parse_unary()
            left = BinaryOp(left=left, op=op_token.value, right=right, line=op_token.line, col=op_token.column)
        return left

    def parse_unary(self):
        """Parse unary operators: -x, !flag"""
        if self.current().type in self._unary_ops:
            op_token = self.advance()
            operand = self.parse_unary()  # right-recursive for chaining: --x, !!flag
            return UnaryOp(op=op_token.value, operand=operand, line=op_token.line, col=op_token.column)
        return self.parse_primary()

    def parse_primary(self):
        """
        Parse primary (highest precedence) expressions:
            - integer literals
            - string literals
            - boolean literals
            - identifiers
            - function calls
            - parenthesized expressions
        """
        token = self.current()

        # Integer literal
        if token.type == TokenType.INT_LITERAL:
            self.advance()
            return IntLiteral(value=int(token.value), line=token.line, col=token.column)

        # String literal
        if token.type == TokenType.STRING_LITERAL:
            self.advance()
            return StringLiteral(value=token.value, line=token.line, col=token.column)

        # Boolean literals
        if token.type in (TokenType.TRUE, TokenType.FALSE):
            self.advance()
            return BoolLiteral(value=(token.type == TokenType.TRUE), line=token.line, col=token.column)

        # Identifier or function call
        if token.type == TokenType.IDENTIFIER or token.type == TokenType.PRINT:
            self.advance()
            # Check if it's a function call: name(...)
            if self.current().type == TokenType.LPAREN:
                return self.parse_call(token)
            return Identifier(name=token.value, line=token.line, col=token.column)

        # Parenthesized expression: (expr)
        if token.type == TokenType.LPAREN:
            self.advance()  # consume (
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        raise ParserError(f"Unexpected token: {token.type.name} ('{token.value}')", token)

    def parse_call(self, name_token: Token) -> FunctionCall:
        """Parse a function call: name(arg1, arg2, ...)"""
        self.advance()  # consume (
        args = []
        if self.current().type != TokenType.RPAREN:
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())
        self.expect(TokenType.RPAREN)
        return FunctionCall(name=name_token.value, args=args, line=name_token.line, col=name_token.column)


# ─── Pretty Printer (for debugging) ───────────────────────────

def print_ast(node, indent=0):
    """Recursively print the AST in a readable tree format."""
    pad = "  " * indent

    if isinstance(node, Program):
        print(f"{pad}Program")
        for fn in node.functions:
            print_ast(fn, indent + 1)

    elif isinstance(node, Function):
        params_str = ", ".join(f"{p.name}: {p.type_name}" for p in node.params)
        print(f"{pad}Function '{node.name}({params_str}) -> {node.return_type}'")
        for stmt in node.body:
            print_ast(stmt, indent + 1)

    elif isinstance(node, LetStatement):
        print(f"{pad}Let {node.name}: {node.type_name} =")
        print_ast(node.value, indent + 1)

    elif isinstance(node, AssignStatement):
        print(f"{pad}Assign {node.name} =")
        print_ast(node.value, indent + 1)

    elif isinstance(node, ReturnStatement):
        if node.value:
            print(f"{pad}Return")
            print_ast(node.value, indent + 1)
        else:
            print(f"{pad}Return (void)")

    elif isinstance(node, IfStatement):
        print(f"{pad}If")
        print(f"{pad}  condition:")
        print_ast(node.condition, indent + 2)
        print(f"{pad}  then:")
        for stmt in node.then_body:
            print_ast(stmt, indent + 2)
        if node.else_body:
            print(f"{pad}  else:")
            for stmt in node.else_body:
                print_ast(stmt, indent + 2)

    elif isinstance(node, WhileStatement):
        print(f"{pad}While")
        print(f"{pad}  condition:")
        print_ast(node.condition, indent + 2)
        print(f"{pad}  body:")
        for stmt in node.body:
            print_ast(stmt, indent + 2)

    elif isinstance(node, ForStatement):
        print(f"{pad}For")
        print(f"{pad}  init:")
        print_ast(node.init, indent + 2)
        print(f"{pad}  condition:")
        print_ast(node.condition, indent + 2)
        print(f"{pad}  update:")
        print_ast(node.update, indent + 2)
        print(f"{pad}  body:")
        for stmt in node.body:
            print_ast(stmt, indent + 2)

    elif isinstance(node, ExpressionStatement):
        print(f"{pad}ExprStmt")
        print_ast(node.expression, indent + 1)

    elif isinstance(node, BreakStatement):
        print(f"{pad}Break")

    elif isinstance(node, ContinueStatement):
        print(f"{pad}Continue")

    elif isinstance(node, BinaryOp):
        print(f"{pad}BinaryOp '{node.op}'")
        print_ast(node.left, indent + 1)
        print_ast(node.right, indent + 1)

    elif isinstance(node, UnaryOp):
        print(f"{pad}UnaryOp '{node.op}'")
        print_ast(node.operand, indent + 1)

    elif isinstance(node, FunctionCall):
        print(f"{pad}Call '{node.name}'")
        for arg in node.args:
            print_ast(arg, indent + 1)

    elif isinstance(node, IntLiteral):
        print(f"{pad}Int({node.value})")

    elif isinstance(node, StringLiteral):
        print(f"{pad}String(\"{node.value}\")")

    elif isinstance(node, BoolLiteral):
        print(f"{pad}Bool({node.value})")

    elif isinstance(node, Identifier):
        print(f"{pad}Ident({node.name})")

    else:
        print(f"{pad}Unknown node: {type(node).__name__}")


# ─── Quick test ────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import Lexer

    test_code = """
fn main() -> int {
    let x: int = 42;
    let name: string = "hello";

    if x >= 10 {
        print(x);
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

fn add(a: int, b: int) -> int {
    return a + b;
}
"""

    print("=== ZIP Parser Output ===\n")

    lexer = Lexer(test_code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    print_ast(ast)
