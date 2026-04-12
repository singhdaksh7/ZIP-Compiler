"""
Token types for the ZIP language.
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Literals
    INT_LITERAL = auto()      
    STRING_LITERAL = auto()   
    BOOL_LITERAL = auto()     

    # Identifiers
    IDENTIFIER = auto()       

    # Keywords
    FN = auto()               
    LET = auto()              
    RETURN = auto()           
    IF = auto()              
    ELSE = auto()             
    WHILE = auto()           
    FOR = auto()             
    TRUE = auto()             
    FALSE = auto()            
    INT = auto()             
    BOOL = auto()             
    STRING = auto()           
    VOID = auto()             
    PRINT = auto()            

    
    PLUS = auto()            
    MINUS = auto()            
    STAR = auto()             
    SLASH = auto()           
    PERCENT = auto()          
    ASSIGN = auto()           
    EQ = auto()               
    NEQ = auto()             
    LT = auto()              
    GT = auto()               
    LTE = auto()             
    GTE = auto()            
    AND = auto()              
    OR = auto()               
    NOT = auto()            


    LPAREN = auto()        
    RPAREN = auto()          
    LBRACE = auto()           
    RBRACE = auto()          
    SEMICOLON = auto()       
    COLON = auto()           
    COMMA = auto()           
    ARROW = auto()

    BREAK = auto()
    CONTINUE = auto()


    EOF = auto()
    NEWLINE = auto()

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
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
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
