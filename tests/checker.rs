//! Library-level tests for the checker: golden example, fixtures, every
//! stable code, recovery, truncation, column counting and line endings.

use std::fs;
use std::path::PathBuf;

use ts_subset_check::json::{escape, report_to_json};
use ts_subset_check::{check, process_input};

type D = (&'static str, usize, usize, usize, usize);

/// (code, start line, start col, end line, end col) for each diagnostic.
fn d(src: &str) -> Vec<D> {
    check(src)
        .diagnostics
        .iter()
        .map(|x| {
            (
                x.code,
                x.span.start.line,
                x.span.start.column,
                x.span.end.line,
                x.span.end.column,
            )
        })
        .collect()
}

fn msgs(src: &str) -> Vec<String> {
    check(src).diagnostics.into_iter().map(|x| x.message).collect()
}

const GOLDEN: &str = "const attempts: number = 3;\nconst ready: boolean = 2;\nconst title: string = \"Map\";\n";

#[test]
fn golden_example() {
    let r = check(GOLDEN);
    assert!(!r.ok());
    assert_eq!(r.declarations, 3);
    assert_eq!(r.diagnostics.len(), 1);
    let diag = &r.diagnostics[0];
    assert_eq!(diag.code, "SC2001");
    assert_eq!(diag.message, "Type 'number' is not assignable to type 'boolean'.");
    assert_eq!(d(GOLDEN), vec![("SC2001", 2, 24, 2, 25)]);

    let out = process_input(GOLDEN.as_bytes(), 65536);
    assert_eq!(out.exit_code, 1);
    assert!(out.stdout.starts_with("{\"schema_version\":1,\"ok\":false,\"summary\":{\"declarations\":3,\"diagnostics\":1},\"diagnostics\":[{\"code\":\"SC2001\",\"severity\":\"error\","));
    assert!(out.stdout.ends_with("\n"));
}

#[test]
fn valid_fixture_has_no_diagnostics() {
    let src = "let count: number = 42;\nconst name: string = \"Ada\";\nconst done: boolean = false;\n";
    let r = check(src);
    assert!(r.ok());
    assert_eq!(r.declarations, 3);
    assert!(r.diagnostics.is_empty());
    let out = process_input(src.as_bytes(), 65536);
    assert_eq!(out.exit_code, 0);
    assert_eq!(
        out.stdout,
        "{\"schema_version\":1,\"ok\":true,\"summary\":{\"declarations\":3,\"diagnostics\":0},\"diagnostics\":[]}\n"
    );
}

#[test]
fn empty_and_whitespace_only_inputs_are_valid() {
    for src in ["", "   \n\t\r\n  ", "\n\n"] {
        let r = check(src);
        assert!(r.ok(), "{:?}", src);
        assert_eq!(r.declarations, 0);
    }
}

#[test]
fn valid_literal_forms() {
    let src = concat!(
        "let a: number = -5.25;\n",
        "let b: number = 007;\n",
        "const s1: string = 'it\\'s \\\"ok\\\" \\\\ \\n\\t\\r';\n",
        "const s2: string = \"\";\n",
        "let $x_1: boolean = true;\n",
        "let _y: boolean = false;\n",
        "let   z  :  number  =  0  ;\n",
    );
    let r = check(src);
    assert_eq!(r.diagnostics, vec![], "{:?}", r.diagnostics);
    assert_eq!(r.declarations, 7);
}

#[test]
fn fixtures_match_expected_output() {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests").join("fixtures");
    let mut seen = 0;
    for entry in fs::read_dir(&dir).expect("fixtures dir") {
        let path = entry.unwrap().path();
        if path.extension().and_then(|e| e.to_str()) != Some("ts") {
            continue;
        }
        let expected_path = path.with_extension("expected.json");
        let src = fs::read_to_string(&path).unwrap();
        let expected = fs::read_to_string(&expected_path)
            .unwrap_or_else(|_| panic!("missing {}", expected_path.display()));
        let actual = report_to_json(&check(&src));
        assert_eq!(actual, expected.trim_end(), "fixture {}", path.display());
        seen += 1;
    }
    assert!(seen >= 4, "expected at least 4 fixtures, saw {}", seen);
}

// ---- SC1xxx: lexical and syntax codes ----

#[test]
fn sc1001_invalid_character() {
    // `@` is skipped through the `;`, then the next statement parses.
    let r = check("@;\nlet ok: number = 1;\n");
    assert_eq!(d("@;\nlet ok: number = 1;\n"), vec![("SC1001", 1, 1, 1, 2)]);
    assert_eq!(r.declarations, 1);
    // Invalid char where `;` was expected.
    assert_eq!(d("let x: number = 1 @;"), vec![("SC1001", 1, 19, 1, 20)]);
    // Backslash and a NUL are invalid too; BOM and NBSP are not whitespace.
    assert_eq!(d("\\;")[0].0, "SC1001");
    assert_eq!(d("\u{0};")[0].0, "SC1001");
    assert_eq!(d("\u{feff}let a: number = 1;")[0], ("SC1001", 1, 1, 1, 2));
}

#[test]
fn sc1002_unterminated_string() {
    // Span: opening quote to end of line; recovery swallows the next `;`.
    let src = "let s: string = \"abc;\nlet t: number = 1;\n";
    assert_eq!(d(src), vec![("SC1002", 1, 17, 1, 22)]);
    assert_eq!(check(src).declarations, 0);
    // Trailing backslash at end of line, and a lone quote at EOF.
    assert_eq!(d("let s: string = 'a\\\n;")[0].0, "SC1002");
    assert_eq!(d("let s: string = '"), vec![("SC1002", 1, 17, 1, 18)]);
}

#[test]
fn sc1003_expected_token_messages() {
    assert_eq!(d("let : number = 1;"), vec![("SC1003", 1, 5, 1, 6)]);
    assert_eq!(msgs("let : number = 1;"), vec!["Expected identifier."]);
    assert_eq!(d("let 1 2 3;"), vec![("SC1003", 1, 5, 1, 6)]);
    assert_eq!(d("let string: number = 1;"), vec![("SC1003", 1, 5, 1, 11)]);

    assert_eq!(d("let x number = 1;"), vec![("SC1003", 1, 7, 1, 13)]);
    assert_eq!(msgs("let x number = 1;"), vec!["Expected ':'."]);
    assert_eq!(msgs("let x = 1;"), vec!["Expected ':'."]);

    assert_eq!(d("let x: number 1;"), vec![("SC1003", 1, 15, 1, 16)]);
    assert_eq!(msgs("let x: number 1;"), vec!["Expected '='."]);
    assert_eq!(msgs("let x: number;"), vec!["Expected '='."]);

    assert_eq!(d("let x: number = ;"), vec![("SC1003", 1, 17, 1, 18)]);
    assert_eq!(msgs("let x: number = ;"), vec!["Expected a literal."]);
    assert_eq!(msgs("let x: number = foo;"), vec!["Expected a literal."]);
    assert_eq!(msgs("let x: number = -;"), vec!["Expected a literal."]);

    assert_eq!(msgs("let x: number = 1 let"), vec!["Expected ';'."]);
}

#[test]
fn sc1003_at_eof_has_width_one() {
    // No trailing newline: just after the last character.
    assert_eq!(d("let x: number = 1"), vec![("SC1003", 1, 18, 1, 19)]);
    // Trailing newline: the span sits on the newline, staying on the last line.
    assert_eq!(d("let x: number = 1\n"), vec![("SC1003", 1, 18, 1, 19)]);
    assert_eq!(d("let x: number = 1\r\n"), vec![("SC1003", 1, 19, 1, 20)]);
    // Type position at EOF.
    assert_eq!(d("let x:"), vec![("SC1005", 1, 7, 1, 8)]);
    // Statement truncated after the keyword on a later line.
    assert_eq!(d("let a: number = 1;\nlet"), vec![("SC1003", 2, 4, 2, 5)]);
}

#[test]
fn sc1004_unsupported_syntax() {
    assert_eq!(d("var x = 1;"), vec![("SC1004", 1, 1, 1, 4)]);
    assert_eq!(d("function f() {}"), vec![("SC1004", 1, 1, 1, 9)]);
    assert_eq!(d(";"), vec![("SC1004", 1, 1, 1, 2)]);
    assert_eq!(d("// comment\n"), vec![("SC1004", 1, 1, 1, 2)]);
    assert_eq!(d("/* c */ let a: number = 1;"), vec![("SC1004", 1, 1, 1, 2)]);
    assert_eq!(d("let var: number = 1;"), vec![("SC1004", 1, 5, 1, 8)]);
    assert_eq!(d("42;"), vec![("SC1004", 1, 1, 1, 3)]);
    assert_eq!(msgs("x = 1;"), vec!["Unsupported syntax."]);
}

#[test]
fn sc1005_unsupported_type() {
    assert_eq!(d("let x: bigint = 1;"), vec![("SC1005", 1, 8, 1, 14)]);
    assert_eq!(d("let x: any = 1;")[0].0, "SC1005");
    assert_eq!(d("let x: Array<number> = 1;")[0].0, "SC1005");
    assert_eq!(d("let x: = 1;"), vec![("SC1005", 1, 8, 1, 9)]);
    assert_eq!(d("let x: \"a\" = 1;")[0].0, "SC1005");
    // Element-type arrays: `string` is a valid type, then `[` is unexpected.
    assert_eq!(msgs("let x: string[] = 1;"), vec!["Expected '='."]);
}

#[test]
fn sc1006_unsupported_literal() {
    assert_eq!(d("let x: number = null;"), vec![("SC1006", 1, 17, 1, 21)]);
    assert_eq!(d("let x: number = undefined;"), vec![("SC1006", 1, 17, 1, 26)]);
    assert_eq!(d("let x: number = 1e3;"), vec![("SC1006", 1, 17, 1, 20)]);
    assert_eq!(d("let x: number = 1e-3;"), vec![("SC1006", 1, 17, 1, 21)]);
    assert_eq!(d("let x: number = 0x1F;"), vec![("SC1006", 1, 17, 1, 21)]);
    assert_eq!(d("let x: number = 1_000;"), vec![("SC1006", 1, 17, 1, 22)]);
    assert_eq!(d("let x: number = 10n;"), vec![("SC1006", 1, 17, 1, 20)]);
    assert_eq!(d("let x: number = .5;"), vec![("SC1006", 1, 17, 1, 19)]);
    assert_eq!(d("let x: number = 5.;"), vec![("SC1006", 1, 17, 1, 19)]);
    assert_eq!(d("let x: number = 1.2.3;"), vec![("SC1006", 1, 17, 1, 22)]);
    assert_eq!(d("let s: string = \"a\\q\";"), vec![("SC1006", 1, 17, 1, 22)]);
    assert_eq!(d("let s: string = `a`;"), vec![("SC1006", 1, 17, 1, 20)]);
    assert_eq!(msgs("let x: number = null;"), vec!["Unsupported literal."]);
}

// ---- SC2xxx ----

#[test]
fn sc2001_type_mismatch_all_pairs() {
    let cases = [
        ("let x: string = 1;", "number", "string", 17, 18),
        ("let x: string = true;", "boolean", "string", 17, 21),
        ("let x: number = \"s\";", "string", "number", 17, 20),
        ("let x: number = false;", "boolean", "number", 17, 22),
        ("let x: boolean = 'b';", "string", "boolean", 18, 21),
        ("let x: boolean = -1.5;", "number", "boolean", 18, 22),
    ];
    for (src, lit, ann, c0, c1) in cases {
        let r = check(src);
        assert_eq!(r.declarations, 1, "{}", src);
        assert_eq!(r.diagnostics.len(), 1, "{}", src);
        assert_eq!(r.diagnostics[0].code, "SC2001");
        assert_eq!(
            r.diagnostics[0].message,
            format!("Type '{}' is not assignable to type '{}'.", lit, ann)
        );
        assert_eq!(d(src), vec![("SC2001", 1, c0, 1, c1)], "{}", src);
    }
}

#[test]
fn sc2002_duplicate_declaration_and_sorting() {
    let src = "let a: number = 1;\nconst a: string = \"x\";\n";
    assert_eq!(d(src), vec![("SC2002", 2, 7, 2, 8)]);
    assert_eq!(msgs(src), vec!["Cannot redeclare block-scoped variable 'a'."]);
    assert_eq!(check(src).declarations, 2);
    // Both semantic errors on one statement, sorted by column.
    let src = "let a: number = 1;\nlet a: string = 2;";
    assert_eq!(d(src), vec![("SC2002", 2, 5, 2, 6), ("SC2001", 2, 17, 2, 18)]);
    // A statement that failed to parse does not declare its name.
    assert_eq!(d("let a: bigint = 1;\nlet a: number = 1;")[0].0, "SC1005");
    assert_eq!(d("let a: bigint = 1;\nlet a: number = 1;").len(), 1);
    // Third redeclaration reported too.
    assert_eq!(d("let a: number = 1;\nlet a: number = 1;\nlet a: number = 1;").len(), 2);
}

// ---- Recovery ----

#[test]
fn recovery_continues_with_next_statement() {
    let src = "let a: number = ;\nlet b: boolean = 1;\nconst c = 2;\nconst d: string = \"x\";\n";
    assert_eq!(
        d(src),
        vec![
            ("SC1003", 1, 17, 1, 18),
            ("SC2001", 2, 18, 2, 19),
            ("SC1003", 3, 9, 3, 10),
        ]
    );
    assert_eq!(check(src).declarations, 2);
}

#[test]
fn one_syntax_diagnostic_per_statement() {
    let r = check("let 1 2 3 @ \"x ;");
    assert_eq!(r.diagnostics.len(), 1);
    let r = check("const x: string[] = [1, 2, 3];\nconst y: number = null;\n");
    assert_eq!(r.diagnostics.len(), 2);
}

#[test]
fn missing_semicolon_swallows_through_next_semicolon() {
    let src = "let a: number = 1\nlet b: number = 2;\nlet c: number = 3;\n";
    assert_eq!(d(src), vec![("SC1003", 2, 1, 2, 4)]);
    assert_eq!(check(src).declarations, 1);
}

#[test]
fn recovered_region_is_silent() {
    // The comment contains an apostrophe and an invalid char; neither is reported.
    let src = "// don't @ stop\nlet a: number = 1;\nlet b: number = 2;\n";
    assert_eq!(d(src), vec![("SC1004", 1, 1, 1, 2)]);
    assert_eq!(check(src).declarations, 1);
}

// ---- Truncation ----

fn many(n: usize) -> String {
    (0..n).map(|i| format!("let v{}: number = true;\n", i)).collect()
}

#[test]
fn truncates_at_fifty_with_sc9001() {
    let r = check(&many(60));
    assert_eq!(r.declarations, 60);
    assert_eq!(r.diagnostics.len(), 51);
    assert!(r.diagnostics[..50].iter().all(|x| x.code == "SC2001"));
    let last = &r.diagnostics[50];
    assert_eq!(last.code, "SC9001");
    assert_eq!(last.message, "Too many diagnostics; output truncated.");
    let fiftieth = &r.diagnostics[49];
    assert_eq!(last.span.start, fiftieth.span.end);
    assert_eq!(last.span.end.line, last.span.start.line);
    assert_eq!(last.span.end.column, last.span.start.column + 1);
    // Kept diagnostics are the first fifty in position order.
    assert_eq!(fiftieth.span.start.line, 50);
    let json = report_to_json(&r);
    assert!(json.contains("\"summary\":{\"declarations\":60,\"diagnostics\":51}"));
    assert!(json.contains("\"code\":\"SC9001\""));
}

#[test]
fn exactly_fifty_is_not_truncated() {
    let r = check(&many(50));
    assert_eq!(r.diagnostics.len(), 50);
    assert!(r.diagnostics.iter().all(|x| x.code != "SC9001"));
    let r = check(&many(51));
    assert_eq!(r.diagnostics.len(), 51);
    assert_eq!(r.diagnostics[50].code, "SC9001");
}

// ---- Columns and line endings ----

#[test]
fn columns_count_unicode_scalar_values() {
    // The string holds a 4-byte astral char and a 2-byte char: bytes and
    // UTF-16 units would both give a different column than scalars.
    let src = "const s: string = \"\u{1F600}\u{e9}\"; const n: boolean = 1;";
    assert_eq!(d(src), vec![("SC2001", 1, 44, 1, 45)]);
    // Non-ASCII outside a string is an invalid single character.
    assert_eq!(d("\u{1F600};"), vec![("SC1001", 1, 1, 1, 2)]);
    assert_eq!(d("let caf\u{e9}: number = 1;"), vec![("SC1001", 1, 8, 1, 9)]);
    // Non-ASCII in an unterminated string: span ends after the last scalar.
    assert_eq!(d("let s: string = \"\u{e9}\u{e9}"), vec![("SC1002", 1, 17, 1, 20)]);
}

#[test]
fn crlf_is_one_line_break() {
    let src = GOLDEN.replace('\n', "\r\n");
    assert_eq!(d(&src), vec![("SC2001", 2, 24, 2, 25)]);
    assert_eq!(check(&src).declarations, 3);
    // Unterminated string ends before the CR of its CRLF.
    let src = "let s: string = \"abc\r\nlet t: number = 1;\r\n";
    assert_eq!(d(src), vec![("SC1002", 1, 17, 1, 21)]);
}

#[test]
fn lone_cr_is_whitespace_not_a_line_break() {
    let src = "const a: number = 1;\rconst b: boolean = 2;";
    assert_eq!(d(src), vec![("SC2001", 1, 41, 1, 42)]);
    assert_eq!(check(src).declarations, 2);
}

// ---- Output ----

#[test]
fn output_is_deterministic_and_escaped() {
    let a = process_input(GOLDEN.as_bytes(), 65536);
    let b = process_input(GOLDEN.as_bytes(), 65536);
    assert_eq!(a, b);
    assert_eq!(escape("a\"b\\c\n\u{1}"), "\"a\\\"b\\\\c\\n\\u0001\"");
}

#[test]
fn process_input_error_documents() {
    let out = process_input(&[b'l', 0xff, 0xfe], 65536);
    assert_eq!(out.exit_code, 2);
    assert_eq!(
        out.stdout,
        "{\"schema_version\":1,\"ok\":false,\"error\":{\"code\":\"SC0002\",\"message\":\"Input is not valid UTF-8.\"}}\n"
    );
    let out = process_input(b"12345678901", 10);
    assert_eq!(out.exit_code, 2);
    assert!(out.stdout.contains("\"code\":\"SC0001\""));
    // Over cap wins over invalid UTF-8.
    let out = process_input(&[0xff; 11], 10);
    assert!(out.stdout.contains("SC0001"));
    // Exactly at the cap is accepted.
    assert_eq!(process_input(b"          ", 10).exit_code, 0);
}
