"""
Lexer for the ZIP language.

Converts raw source code into a stream of tokens.

Usage:
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
"""

from io import StringIO
from tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    """Raised when the lexer encounters an unexpected character."""
    def __init__(self, message, line, column):
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at line {line}, col {column}: {message}")


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.source_len = len(source)  # Cache source length to avoid repeated len() calls
        self.pos = 0         
        self.line = 1         
        self.column = 1     
        self.tokens = []

    def peek(self) -> str | None:
        """Look at the current character without consuming it."""
        if self.pos >= self.source_len:
            return None
        return self.source[self.pos]

    def advance(self) -> str:
        """Consume and return the current character."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def match(self, expected: str) -> bool:
        """Consume the next character if it matches expected."""
        if self.pos < self.source_len and self.source[self.pos] == expected:
            self.advance()
            return True
        return False

    def skip_whitespace(self):
        """Skip spaces, tabs, and carriage returns (but not newlines)."""
        while self.pos < self.source_len and self.source[self.pos] in (' ', '\t', '\r', '\n'):
            self.advance()

    def skip_comment(self):
        """Skip single-line comments starting with //."""
        while self.pos < self.source_len and self.source[self.pos] != '\n':
            self.advance()

    def read_string(self) -> Token:
        """Read a string literal enclosed in double quotes."""
        start_line = self.line
        start_col = self.column
        self.advance()  

        result = StringIO()
        while self.pos < self.source_len:
            ch = self.source[self.pos]

            if ch == '"':
                self.advance()  
                return Token(TokenType.STRING_LITERAL, result.getvalue(), start_line, start_col)

            if ch == '\\':
                self.advance()
                escaped = self.peek()
                if escaped is None:
                    raise LexerError("Unexpected end of file in string", self.line, self.column)
                escape_map = {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}
                if escaped in escape_map:
                    result.write(escape_map[escaped])
                    self.advance()
                else:
                    raise LexerError(f"Unknown escape sequence: \\{escaped}", self.line, self.column)
            elif ch == '\n':
                raise LexerError("Unterminated string (newline in string)", self.line, self.column)
            else:
                result.write(ch)
                self.advance()

        raise LexerError("Unterminated string literal", start_line, start_col)

    def read_number(self) -> Token:
        """Read an integer literal."""
        start_line = self.line
        start_col = self.column
        result = StringIO()

        while self.pos < self.source_len and self.source[self.pos].isdigit():
            result.write(self.advance())

        return Token(TokenType.INT_LITERAL, result.getvalue(), start_line, start_col)

    def read_identifier(self) -> Token:
        """Read an identifier or keyword."""
        start_line = self.line
        start_col = self.column
        result = StringIO()

        while self.pos < self.source_len and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            result.write(self.advance())

        word = result.getvalue()
        token_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
        return Token(token_type, word, start_line, start_col)

    def make_token(self, token_type: TokenType, value: str, line: int, col: int) -> Token:
        """Helper to create a token."""
        return Token(token_type, value, line, col)

    def tokenize(self) -> list[Token]:
        """Tokenize the entire source string and return a list of tokens."""
        # Pre-compute single-char token set for fast lookups
        single_char_set = {'+', '-', '*', '/', '%', '=', '<', '>', '!', '(', ')', '{', '}', ';', ':', ','}
        
        while self.pos < self.source_len:
            self.skip_whitespace()

            if self.pos >= self.source_len:
                break

            ch = self.source[self.pos]
            start_line = self.line
            start_col = self.column

          
            if ch == '/' and self.pos + 1 < self.source_len and self.source[self.pos + 1] == '/':
                self.skip_comment()
                continue

            
            if ch == '"':
                self.tokens.append(self.read_string())
                continue

            
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
                continue

            
            if ch == '=' and self.match_ahead('='):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.EQ, "==", start_line, start_col))
                continue
            if ch == '!' and self.match_ahead('='):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.NEQ, "!=", start_line, start_col))
                continue
            if ch == '<' and self.match_ahead('='):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.LTE, "<=", start_line, start_col))
                continue
            if ch == '>' and self.match_ahead('='):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.GTE, ">=", start_line, start_col))
                continue
            if ch == '-' and self.match_ahead('>'):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.ARROW, "->", start_line, start_col))
                continue
            if ch == '&' and self.match_ahead('&'):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.AND, "&&", start_line, start_col))
                continue
            if ch == '|' and self.match_ahead('|'):
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenType.OR, "||", start_line, start_col))
                continue

            
            single_char_tokens = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '=': TokenType.ASSIGN,
                '<': TokenType.LT,
                '>': TokenType.GT,
                '!': TokenType.NOT,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                ';': TokenType.SEMICOLON,
                ':': TokenType.COLON,
                ',': TokenType.COMMA,
            }

            if ch in single_char_tokens:
                self.advance()
                self.tokens.append(self.make_token(single_char_tokens[ch], ch, start_line, start_col))
                continue

            
            raise LexerError(f"Unexpected character: {ch!r}", start_line, start_col)

        
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def match_ahead(self, expected: str) -> bool:
        """Check if the next character (pos+1) matches expected, without consuming."""
        return self.pos + 1 < self.source_len and self.source[self.pos + 1] == expected


if __name__ == "__main__":
    test_code = """
fn main() -> int {
    let x: int = 42;
    let name: string = "hello";
    // this is a comment
    if x >= 10 {
        print(x);
    }
    return 0;
}
"""
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()

    print("=== ZIP Lexer Output ===\n")
    for token in tokens:
        print(token)
