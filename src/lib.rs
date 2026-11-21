//! `ts_subset_check`: checker for a tiny, fixed subset of TypeScript
//! declarations. See the M1 contract for the exact grammar and schema.

pub mod checker;
pub mod json;
pub mod lexer;

pub use checker::{check, Diagnostic, Report};

pub const DEFAULT_MAX_BYTES: usize = 65536;

/// Result of processing one input: the full stdout text (JSON plus `\n`)
/// and the process exit code.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Outcome {
    pub stdout: String,
    pub exit_code: i32,
}

/// Process raw stdin bytes. `bytes` may hold at most `max_bytes + 1` bytes
/// (the reader stops past the cap); anything longer than `max_bytes` is
/// rejected with SC0001 before UTF-8 validation. Invalid UTF-8 is SC0002.
pub fn process_input(bytes: &[u8], max_bytes: usize) -> Outcome {
    if bytes.len() > max_bytes {
        return Outcome {
            stdout: format!(
                "{}\n",
                json::error_to_json(
                    "SC0001",
                    &format!("Input exceeds the maximum size of {} bytes.", max_bytes)
                )
            ),
            exit_code: 2,
        };
    }
    let text = match std::str::from_utf8(bytes) {
        Ok(t) => t,
        Err(_) => {
            return Outcome {
                stdout: format!(
                    "{}\n",
                    json::error_to_json("SC0002", "Input is not valid UTF-8.")
                ),
                exit_code: 2,
            }
        }
    };
    let report = check(text);
    Outcome {
        stdout: format!("{}\n", json::report_to_json(&report)),
        exit_code: if report.ok() { 0 } else { 1 },
    }
}
