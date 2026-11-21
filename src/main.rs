use std::io::{Read, Write};
use std::process::exit;

use ts_subset_check::{process_input, DEFAULT_MAX_BYTES};

const USAGE: &str = "Usage: ts_subset_check [--max-bytes N] [--help]\n\
Reads TypeScript-subset source from stdin and prints one JSON document.\n\
Exit codes: 0 no diagnostics, 1 diagnostics, 2 usage error / invalid UTF-8 / input over cap.\n";

fn usage_error(msg: &str) -> ! {
    eprintln!("ts_subset_check: {}", msg);
    eprint!("{}", USAGE);
    exit(2);
}

fn main() {
    let mut max_bytes = DEFAULT_MAX_BYTES;
    let mut args = std::env::args_os().skip(1);
    while let Some(arg) = args.next() {
        match arg.to_str() {
            Some("--help") => {
                // Help is the only case where usage goes to stdout (exit 0).
                print!("{}", USAGE);
                exit(0);
            }
            Some("--max-bytes") => {
                let value = match args.next() {
                    Some(v) => v,
                    None => usage_error("--max-bytes requires a value"),
                };
                max_bytes = match value.to_str().and_then(|v| v.parse::<usize>().ok()) {
                    Some(n) => n,
                    None => usage_error("--max-bytes requires a non-negative integer"),
                };
            }
            _ => usage_error("unknown argument"),
        }
    }

    // Bounded read: never buffer more than max_bytes + 1 bytes.
    let limit = (max_bytes as u64).saturating_add(1);
    let mut buf = Vec::new();
    if let Err(e) = std::io::stdin().lock().take(limit).read_to_end(&mut buf) {
        eprintln!("ts_subset_check: failed to read stdin: {}", e);
        exit(2);
    }

    let outcome = process_input(&buf, max_bytes);
    let mut out = std::io::stdout().lock();
    let _ = out.write_all(outcome.stdout.as_bytes());
    let _ = out.flush();
    exit(outcome.exit_code);
}
