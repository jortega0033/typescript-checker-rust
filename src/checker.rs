//! Parser and type checker for the supported subset:
//!
//! ```text
//! statement := ("let" | "const") IDENT ":" type "=" literal ";"
//! ```
//!
//! Input is only tokenized and parsed. Nothing is ever evaluated.

use std::collections::HashSet;

use crate::lexer::{tokenize, Pos, Span, Token, TokenKind};

pub const MAX_DIAGNOSTICS: usize = 50;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub code: &'static str,
    pub message: String,
    pub span: Span,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Report {
    /// Syntactically complete, well-formed statements (type errors included).
    pub declarations: usize,
    /// Sorted, truncated to `MAX_DIAGNOSTICS` plus an optional trailing SC9001.
    pub diagnostics: Vec<Diagnostic>,
}

impl Report {
    pub fn ok(&self) -> bool {
        self.diagnostics.is_empty()
    }
}

/// Keywords that can never be identifiers (per the contract).
fn is_keyword(s: &str) -> bool {
    matches!(
        s,
        "let" | "const" | "string" | "number" | "boolean" | "true" | "false"
    )
}

/// Other JavaScript/TypeScript reserved words: unsupported syntax if used
/// as a name.
fn is_other_reserved(s: &str) -> bool {
    matches!(
        s,
        "var"
            | "function"
            | "class"
            | "interface"
            | "type"
            | "enum"
            | "if"
            | "else"
            | "for"
            | "while"
            | "do"
            | "return"
            | "import"
            | "export"
            | "new"
            | "delete"
            | "typeof"
            | "void"
            | "null"
            | "undefined"
            | "this"
            | "async"
            | "await"
    )
}

struct Parser<'a> {
    tokens: &'a [Token],
    i: usize,
    diags: Vec<Diagnostic>,
    declared: HashSet<String>,
    declarations: usize,
}

impl<'a> Parser<'a> {
    fn cur(&self) -> &'a Token {
        // The token list always ends with Eof and we never advance past it.
        &self.tokens[self.i.min(self.tokens.len() - 1)]
    }

    fn run(&mut self) {
        while !matches!(self.cur().kind, TokenKind::Eof) {
            let _ = self.declaration();
        }
    }

    /// Report one syntax diagnostic at the current token, then recover by
    /// skipping through the next `;` (or to EOF). Always returns `Err`.
    fn fail(&mut self, code: &'static str, message: &str) -> Result<(), ()> {
        let tok = self.cur();
        let (code, message) = match tok.kind {
            TokenKind::Invalid => ("SC1001", "Invalid or unsupported character.".to_string()),
            TokenKind::UnterminatedString => ("SC1002", "Unterminated string literal.".to_string()),
            _ => (code, message.to_string()),
        };
        self.diags.push(Diagnostic {
            code,
            message,
            span: tok.span,
        });
        loop {
            match &self.cur().kind {
                TokenKind::Eof => break,
                TokenKind::Punct(';') => {
                    self.i += 1;
                    break;
                }
                _ => self.i += 1,
            }
        }
        Err(())
    }

    fn expect_punct(&mut self, c: char, message: &str) -> Result<(), ()> {
        if self.cur().kind == TokenKind::Punct(c) {
            self.i += 1;
            Ok(())
        } else {
            self.fail("SC1003", message)
        }
    }

    fn declaration(&mut self) -> Result<(), ()> {
        match &self.cur().kind {
            TokenKind::Ident(s) if s == "let" || s == "const" => self.i += 1,
            _ => return self.fail("SC1004", "Unsupported syntax."),
        }

        let name_tok = self.cur();
        let name: &str = match &name_tok.kind {
            TokenKind::Ident(s) if is_keyword(s) => {
                return self.fail("SC1003", "Expected identifier.")
            }
            TokenKind::Ident(s) if is_other_reserved(s) => {
                return self.fail("SC1004", "Unsupported syntax.")
            }
            TokenKind::Ident(s) => s,
            _ => return self.fail("SC1003", "Expected identifier."),
        };
        self.i += 1;

        self.expect_punct(':', "Expected ':'.")?;

        let ty: &str = match &self.cur().kind {
            TokenKind::Ident(s) if matches!(s.as_str(), "string" | "number" | "boolean") => s,
            _ => {
                return self.fail(
                    "SC1005",
                    "Unsupported type annotation; expected string, number, or boolean.",
                )
            }
        };
        self.i += 1;

        self.expect_punct('=', "Expected '='.")?;

        let lit_tok = self.cur();
        let lit_kind: &'static str = match &lit_tok.kind {
            TokenKind::Str => "string",
            TokenKind::Num => "number",
            TokenKind::Ident(s) if s == "true" || s == "false" => "boolean",
            TokenKind::BadLiteral => return self.fail("SC1006", "Unsupported literal."),
            TokenKind::Ident(s) if matches!(s.as_str(), "null" | "undefined" | "NaN" | "Infinity") => {
                return self.fail("SC1006", "Unsupported literal.")
            }
            _ => return self.fail("SC1003", "Expected a literal."),
        };
        self.i += 1;

        self.expect_punct(';', "Expected ';'.")?;

        // Statement is complete and well-formed.
        self.declarations += 1;
        if !self.declared.insert(name.to_string()) {
            self.diags.push(Diagnostic {
                code: "SC2002",
                message: format!("Cannot redeclare block-scoped variable '{}'.", name),
                span: name_tok.span,
            });
        }
        if lit_kind != ty {
            self.diags.push(Diagnostic {
                code: "SC2001",
                message: format!(
                    "Type '{}' is not assignable to type '{}'.",
                    lit_kind, ty
                ),
                span: lit_tok.span,
            });
        }
        Ok(())
    }
}

/// Check TypeScript-subset source text.
pub fn check(src: &str) -> Report {
    let tokens = tokenize(src);
    let mut parser = Parser {
        tokens: &tokens,
        i: 0,
        diags: Vec::new(),
        declared: HashSet::new(),
        declarations: 0,
    };
    parser.run();

    let declarations = parser.declarations;
    let mut diagnostics = parser.diags;
    diagnostics.sort_by(|a, b| {
        (a.span.start.line, a.span.start.column, a.code)
            .cmp(&(b.span.start.line, b.span.start.column, b.code))
    });

    if diagnostics.len() > MAX_DIAGNOSTICS {
        diagnostics.truncate(MAX_DIAGNOSTICS);
        let after: Pos = diagnostics[MAX_DIAGNOSTICS - 1].span.end;
        diagnostics.push(Diagnostic {
            code: "SC9001",
            message: "Too many diagnostics; output truncated.".to_string(),
            span: Span {
                start: after,
                end: Pos {
                    line: after.line,
                    column: after.column + 1,
                },
            },
        });
    }

    Report {
        declarations,
        diagnostics,
    }
}
