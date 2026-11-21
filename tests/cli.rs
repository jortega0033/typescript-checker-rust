//! End-to-end tests that run the compiled binary: exit codes, stdout/stderr
//! contract, invalid UTF-8 and the input size cap.

use std::io::Write;
use std::process::{Command, Stdio};

const GOLDEN: &str = "const attempts: number = 3;\nconst ready: boolean = 2;\nconst title: string = \"Map\";\n";

const GOLDEN_JSON: &str = "{\"schema_version\":1,\"ok\":false,\"summary\":{\"declarations\":3,\"diagnostics\":1},\"diagnostics\":[{\"code\":\"SC2001\",\"severity\":\"error\",\"message\":\"Type 'number' is not assignable to type 'boolean'.\",\"span\":{\"start\":{\"line\":2,\"column\":24},\"end\":{\"line\":2,\"column\":25}}}]}\n";

/// Run the binary; returns (exit code, stdout, stderr).
fn run(args: &[&str], input: &[u8]) -> (i32, String, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_ts_subset_check"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn checker");
    let mut stdin = child.stdin.take().unwrap();
    let data = input.to_vec();
    // Write from a thread; the child may exit before reading everything.
    let writer = std::thread::spawn(move || {
        let _ = stdin.write_all(&data);
    });
    let out = child.wait_with_output().expect("wait");
    writer.join().unwrap();
    (
        out.status.code().expect("exit code"),
        String::from_utf8(out.stdout).expect("stdout is UTF-8"),
        String::from_utf8(out.stderr).expect("stderr is UTF-8"),
    )
}

#[test]
fn golden_exit_1_and_exact_json() {
    let (code, out, err) = run(&[], GOLDEN.as_bytes());
    assert_eq!(code, 1);
    assert_eq!(out, GOLDEN_JSON);
    assert_eq!(err, "");
}

#[test]
fn valid_input_exit_0() {
    let src = "let count: number = 42;\nconst name: string = \"Ada\";\nconst done: boolean = false;\n";
    let (code, out, err) = run(&[], src.as_bytes());
    assert_eq!(code, 0);
    assert_eq!(
        out,
        "{\"schema_version\":1,\"ok\":true,\"summary\":{\"declarations\":3,\"diagnostics\":0},\"diagnostics\":[]}\n"
    );
    assert_eq!(err, "");
}

#[test]
fn empty_input_exit_0() {
    let (code, out, _) = run(&[], b"");
    assert_eq!(code, 0);
    assert!(out.contains("\"ok\":true"));
}

#[test]
fn deterministic_output() {
    let a = run(&[], GOLDEN.as_bytes());
    let b = run(&[], GOLDEN.as_bytes());
    assert_eq!(a, b);
}

#[test]
fn crlf_input_through_binary() {
    let src = GOLDEN.replace('\n', "\r\n");
    let (code, out, _) = run(&[], src.as_bytes());
    assert_eq!(code, 1);
    assert_eq!(out, GOLDEN_JSON);
}

#[test]
fn invalid_utf8_exit_2_with_error_json() {
    let (code, out, err) = run(&[], &[b'l', b'e', b't', b' ', 0xff, 0xfe]);
    assert_eq!(code, 2);
    assert_eq!(
        out,
        "{\"schema_version\":1,\"ok\":false,\"error\":{\"code\":\"SC0002\",\"message\":\"Input is not valid UTF-8.\"}}\n"
    );
    assert_eq!(err, "");
}

#[test]
fn oversize_input_exit_2_with_error_json() {
    let (code, out, _) = run(&["--max-bytes", "10"], b"12345678901");
    assert_eq!(code, 2);
    assert_eq!(
        out,
        "{\"schema_version\":1,\"ok\":false,\"error\":{\"code\":\"SC0001\",\"message\":\"Input exceeds the maximum size of 10 bytes.\"}}\n"
    );
}

#[test]
fn exactly_at_cap_is_accepted() {
    let (code, _, _) = run(&["--max-bytes", "10"], b"          ");
    assert_eq!(code, 0);
}

#[test]
fn default_cap_is_65536() {
    let ok = vec![b' '; 65536];
    let (code, _, _) = run(&[], &ok);
    assert_eq!(code, 0);
    let big = vec![b' '; 65537];
    let (code, out, _) = run(&[], &big);
    assert_eq!(code, 2);
    assert!(out.contains("\"code\":\"SC0001\""));
}

#[test]
fn much_larger_than_cap_still_exit_2() {
    let big = vec![b'a'; 1_000_000];
    let (code, out, _) = run(&["--max-bytes", "100"], &big);
    assert_eq!(code, 2);
    assert!(out.contains("SC0001"));
}

#[test]
fn raised_cap_is_honored() {
    let mut src = String::new();
    while src.len() <= 70000 {
        src.push_str("let a: number = 1; ");
    }
    let (code, out, _) = run(&["--max-bytes", "100000"], src.as_bytes());
    // Duplicate names produce diagnostics (exit 1), but it is not a cap error.
    assert_eq!(code, 1);
    assert!(!out.contains("SC0001"));
}

#[test]
fn unknown_argument_exit_2_usage_on_stderr_no_stdout() {
    for args in [
        vec!["--bogus"],
        vec!["positional"],
        vec!["--max-bytes"],
        vec!["--max-bytes", "abc"],
        vec!["--max-bytes", "-5"],
        vec!["--max-bytes=10"],
    ] {
        let (code, out, err) = run(&args, GOLDEN.as_bytes());
        assert_eq!(code, 2, "{:?}", args);
        assert_eq!(out, "", "{:?}", args);
        assert!(err.contains("Usage:"), "{:?}", args);
    }
}

#[test]
fn help_exits_0() {
    let (code, out, _) = run(&["--help"], b"");
    assert_eq!(code, 0);
    assert!(out.contains("Usage:"));
}
