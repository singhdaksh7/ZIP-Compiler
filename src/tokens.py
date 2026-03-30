"""
Token types for the ZIP language.
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Literals
    INT_LITERAL = auto()      # 42, 0, 100
    STRING_LITERAL = auto()   # "hello"
    BOOL_LITERAL = auto()     # true, false

    # Identifiers
    IDENTIFIER = auto()       # variable/function names

    # Keywords
    FN = auto()               # fn
    LET = auto()              # let
    RETURN = auto()           # return
    IF = auto()               # if
    ELSE = auto()             # else
    WHILE = auto()            # while
    FOR = auto()              # for
    TRUE = auto()             # true
    FALSE = auto()            # false
    INT = auto()              # int (type)
    BOOL = auto()             # bool (type)
    STRING = auto()           # string (type)
    VOID = auto()             # void (type)
    PRINT = auto()            # print

    # Operators
    PLUS = auto()             # +
    MINUS = auto()            # -
    STAR = auto()             # *
    SLASH = auto()            # /
    PERCENT = auto()          # %
    ASSIGN = auto()           # =
    EQ = auto()               # ==
    NEQ = auto()              # !=
    LT = auto()               # <
    GT = auto()               # >
    LTE = auto()              # <=
    GTE = auto()              # >=
    AND = auto()              # &&
    OR = auto()               # ||
    NOT = auto()              # !

    # Delimiters
    LPAREN = auto()           # (
    RPAREN = auto()           # )
    LBRACE = auto()           # {
    RBRACE = auto()           # }
    SEMICOLON = auto()        # ;
    COLON = auto()            # :
    COMMA = auto()            # ,
    ARROW = auto()            # ->

    # Special
    EOF = auto()              # End of file
    NEWLINE = auto()          # \n (tracked for line counting)


# Keyword lookup table
KEYWORDS = {
    "fn": TokenType.FN,
    "let": TokenType.LET,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "int": TokenType.INT,
    "bool": TokenType.BOOL,
    "string": TokenType.STRING,
    "void": TokenType.VOID,
    "print": TokenType.PRINT,
}


@dataclass
class Token:
    """Represents a single token produced by the lexer."""
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"
