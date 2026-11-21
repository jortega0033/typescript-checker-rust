//! Minimal hand-written JSON serialization (no dependencies).
//! Output is compact with a fixed key order.

use crate::checker::Report;

pub fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Section 4.1 check result (no trailing newline).
pub fn report_to_json(report: &Report) -> String {
    let mut out = String::new();
    out.push_str("{\"schema_version\":1,\"ok\":");
    out.push_str(if report.ok() { "true" } else { "false" });
    out.push_str(&format!(
        ",\"summary\":{{\"declarations\":{},\"diagnostics\":{}}},\"diagnostics\":[",
        report.declarations,
        report.diagnostics.len()
    ));
    for (i, d) in report.diagnostics.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        out.push_str(&format!(
            "{{\"code\":{},\"severity\":\"error\",\"message\":{},\"span\":{{\"start\":{{\"line\":{},\"column\":{}}},\"end\":{{\"line\":{},\"column\":{}}}}}}}",
            escape(d.code),
            escape(&d.message),
            d.span.start.line,
            d.span.start.column,
            d.span.end.line,
            d.span.end.column
        ));
    }
    out.push_str("]}");
    out
}

/// Section 4.2 tool error (no trailing newline).
pub fn error_to_json(code: &str, message: &str) -> String {
    format!(
        "{{\"schema_version\":1,\"ok\":false,\"error\":{{\"code\":{},\"message\":{}}}}}",
        escape(code),
        escape(message)
    )
}
