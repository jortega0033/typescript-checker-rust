//! Tokenizer for the supported TypeScript subset.
//!
//! The lexer never fails: anything it cannot classify becomes an error token
//! (`Invalid`, `UnterminatedString`, `BadLiteral`) and the parser decides
//! whether to report it, so skipped (recovered) regions stay silent.
//!
//! Positions are 1-based; columns count Unicode scalar values; only `\n`
//! starts a new line (`\r` is plain whitespace and occupies a column).

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Pos {
    pub line: usize,
    pub column: usize,
}

/// `end` is exclusive. Spans are never zero-width.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Span {
    pub start: Pos,
    pub end: Pos,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum TokenKind {
    /// Identifier or keyword (keywords are classified by the parser).
    Ident(String),
    /// Well-formed string literal.
    Str,
    /// Well-formed number literal: `-?digits(.digits)?`.
    Num,
    /// Unsupported literal: exponent, hex, bigint, `_`, `.5`, `5.`, bad
    /// escape in a string, template string.
    BadLiteral,
    /// Recognised punctuation (unsupported unless the parser expects it).
    Punct(char),
    /// Character that is not valid anywhere (SC1001).
    Invalid,
    /// String literal that hits end of line first (SC1002).
    UnterminatedString,
    Eof,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Token {
    pub kind: TokenKind,
    pub span: Span,
}

fn is_ident_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_' || c == '$'
}

fn is_ident_continue(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_' || c == '$'
}

fn is_punct(c: char) -> bool {
    matches!(
        c,
        ':' | '='
            | ';'
            | '['
            | ']'
            | '('
            | ')'
            | '{'
            | '}'
            | '<'
            | '>'
            | ','
            | '.'
            | '+'
            | '-'
            | '*'
            | '/'
            | '%'
            | '&'
            | '|'
            | '^'
            | '!'
            | '?'
            | '~'
    )
}

struct Lexer {
    chars: Vec<char>,
    i: usize,
    line: usize,
    col: usize,
    /// Position of the most recently consumed `\n`.
    last_newline: Option<Pos>,
}

impl Lexer {
    fn pos(&self) -> Pos {
        Pos {
            line: self.line,
            column: self.col,
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.i).copied()
    }

    fn peek_at(&self, n: usize) -> Option<char> {
        self.chars.get(self.i + n).copied()
    }

    /// Character `n` positions before the cursor, or NUL.
    fn back(&self, n: usize) -> char {
        if self.i >= n {
            self.chars[self.i - n]
        } else {
            '\0'
        }
    }

    fn bump(&mut self) {
        if let Some(c) = self.chars.get(self.i).copied() {
            if c == '\n' {
                self.last_newline = Some(self.pos());
                self.line += 1;
                self.col = 1;
            } else {
                self.col += 1;
            }
            self.i += 1;
        }
    }

    fn at_line_end(&self) -> bool {
        match self.peek() {
            None | Some('\n') => true,
            Some('\r') => self.peek_at(1) == Some('\n'),
            _ => false,
        }
    }

    fn ident(&mut self) -> TokenKind {
        let mut s = String::new();
        while let Some(c) = self.peek() {
            if !is_ident_continue(c) {
                break;
            }
            s.push(c);
            self.bump();
        }
        TokenKind::Ident(s)
    }

    fn digits(&mut self) {
        while matches!(self.peek(), Some('0'..='9')) {
            self.bump();
        }
    }

    fn number_follows_minus(&self) -> bool {
        match self.peek_at(1) {
            Some('0'..='9') => true,
            Some('.') => matches!(self.peek_at(2), Some('0'..='9')),
            _ => false,
        }
    }

    fn number(&mut self) -> TokenKind {
        if self.peek() == Some('-') {
            self.bump();
        }
        if self.peek() == Some('.') {
            return self.bad_run();
        }
        self.digits();
        let mut bad = false;
        if self.peek() == Some('.') {
            if matches!(self.peek_at(1), Some('0'..='9')) {
                self.bump();
                self.digits();
            } else {
                bad = true;
            }
        }
        if bad || matches!(self.peek(), Some(c) if is_ident_continue(c) || c == '.') {
            return self.bad_run();
        }
        TokenKind::Num
    }

    /// Consume the rest of a malformed numeric literal as a single token.
    fn bad_run(&mut self) -> TokenKind {
        while let Some(c) = self.peek() {
            let exponent_sign = (c == '+' || c == '-')
                && matches!(self.back(1), 'e' | 'E')
                && (self.back(2).is_ascii_digit() || self.back(2) == '.')
                && matches!(self.peek_at(1), Some('0'..='9'));
            if is_ident_continue(c) || c == '.' || exponent_sign {
                self.bump();
            } else {
                break;
            }
        }
        TokenKind::BadLiteral
    }

    fn string(&mut self, quote: char) -> TokenKind {
        self.bump();
        let mut bad = false;
        loop {
            if self.at_line_end() {
                return TokenKind::UnterminatedString;
            }
            let c = match self.peek() {
                Some(c) => c,
                None => return TokenKind::UnterminatedString,
            };
            if c == quote {
                self.bump();
                break;
            }
            if c == '\\' {
                self.bump();
                if self.at_line_end() {
                    return TokenKind::UnterminatedString;
                }
                match self.peek() {
                    Some('\\') | Some('\'') | Some('"') | Some('n') | Some('t') | Some('r') => {}
                    _ => bad = true,
                }
                self.bump();
            } else {
                self.bump();
            }
        }
        if bad {
            TokenKind::BadLiteral
        } else {
            TokenKind::Str
        }
    }

    /// Template strings are unsupported; consume through the closing backtick
    /// (or end of line) as one token.
    fn template(&mut self) -> TokenKind {
        self.bump();
        while !self.at_line_end() {
            let c = self.peek();
            self.bump();
            if c == Some('`') {
                break;
            }
        }
        TokenKind::BadLiteral
    }
}

/// Tokenize `src`. The result always ends with exactly one `Eof` token.
///
/// The EOF span has width 1. If the input ends with `\n` it sits on that
/// newline character (so it stays on the last line); otherwise it sits just
/// after the last character.
pub fn tokenize(src: &str) -> Vec<Token> {
    let mut lx = Lexer {
        chars: src.chars().collect(),
        i: 0,
        line: 1,
        col: 1,
        last_newline: None,
    };
    let mut tokens = Vec::new();
    while let Some(c) = lx.peek() {
        let start = lx.pos();
        let kind = match c {
            ' ' | '\t' | '\n' | '\r' => {
                lx.bump();
                continue;
            }
            '"' | '\'' => lx.string(c),
            '`' => lx.template(),
            '0'..='9' => lx.number(),
            '-' if lx.number_follows_minus() => lx.number(),
            '.' if matches!(lx.peek_at(1), Some('0'..='9')) => lx.bad_run(),
            c if is_ident_start(c) => lx.ident(),
            c if is_punct(c) => {
                lx.bump();
                TokenKind::Punct(c)
            }
            _ => {
                lx.bump();
                TokenKind::Invalid
            }
        };
        tokens.push(Token {
            kind,
            span: Span {
                start,
                end: lx.pos(),
            },
        });
    }
    let eof_start = if lx.chars.last() == Some(&'\n') {
        lx.last_newline.unwrap_or_else(|| lx.pos())
    } else {
        lx.pos()
    };
    tokens.push(Token {
        kind: TokenKind::Eof,
        span: Span {
            start: eof_start,
            end: Pos {
                line: eof_start.line,
                column: eof_start.column + 1,
            },
        },
    });
    tokens
}
