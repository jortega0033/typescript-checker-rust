(function () {
  "use strict";

  var src = document.getElementById("source");
  var checkBtn = document.getElementById("check-btn");
  var fixSel = document.getElementById("fixture-select");
  var loadBtn = document.getElementById("load-fixture");
  var undoBtn = document.getElementById("undo-load");
  var statusEl = document.getElementById("status");
  var list = document.getElementById("diagnostics");
  var emptyEl = document.getElementById("diagnostics-empty");
  var lineCount = document.getElementById("source-line-count");

  var fixtures = [];
  var pending = false;
  var previousText = null;

  var ERRORS = {
    checker_unavailable: "Checker unavailable. Build it with cargo build --release, then retry.",
    busy: "The checker is busy. Wait a moment and retry.",
    checker_timeout: "The checker took too long. Simplify the source and retry.",
    checker_failed: "The checker failed unexpectedly. Retry, and rebuild it if this continues.",
    too_large: "Source is too large. The limit is 64 KiB.",
    forbidden_origin: "Request rejected. Open this page at http://127.0.0.1 or localhost on the server port."
  };

  function setStatus(text, state) {
    statusEl.textContent = text;
    statusEl.setAttribute("data-state", state || "info");
  }

  function clearResults() {
    while (list.firstChild) list.removeChild(list.firstChild);
    list.hidden = true;
    emptyEl.textContent = "Run a check to see results here.";
    emptyEl.hidden = false;
  }

  function updateCount() {
    var n = src.value.split("\n").length;
    lineCount.textContent = n + (n === 1 ? " line" : " lines");
  }

  // Convert 1-based line and code-point column to a UTF-16 index.
  function toIndex(text, line, column) {
    var idx = 0;
    for (var l = 1; l < line; l++) {
      var nl = text.indexOf("\n", idx);
      if (nl === -1) return text.length;
      idx = nl + 1;
    }
    var cps = column - 1;
    while (cps > 0 && idx < text.length) {
      var c = text.charCodeAt(idx);
      if (text.charAt(idx) === "\n") break;
      idx += (c >= 0xd800 && c <= 0xdbff && idx + 1 < text.length) ? 2 : 1;
      cps--;
    }
    return idx;
  }

  function selectSpan(span) {
    var text = src.value;
    var a = toIndex(text, span.start.line, span.start.column);
    var b = toIndex(text, span.end.line, span.end.column);
    if (b <= a) b = Math.min(a + 1, text.length);
    src.focus();
    src.setSelectionRange(a, b);
  }

  function renderDiagnostics(diags) {
    clearResults();
    if (!diags.length) {
      emptyEl.textContent = "No diagnostics for this source.";
      return;
    }
    emptyEl.hidden = true;
    list.hidden = false;
    diags.forEach(function (d) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      var head = document.createElement("span");
      head.className = "d-head";
      var code = document.createElement("span");
      code.className = "d-code";
      code.textContent = String(d.code);
      var pos = document.createElement("span");
      pos.className = "d-pos";
      var s = d.span.start, e = d.span.end;
      pos.textContent = s.line + ":" + s.column + "–" + e.line + ":" + e.column;
      head.appendChild(code);
      head.appendChild(pos);
      var msg = document.createElement("span");
      msg.className = "d-msg";
      msg.textContent = String(d.message);
      btn.appendChild(head);
      btn.appendChild(msg);
      btn.addEventListener("click", function () { selectSpan(d.span); });
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  function setPending(on) {
    pending = on;
    checkBtn.disabled = on;
    if (on) checkBtn.setAttribute("aria-busy", "true");
    else checkBtn.removeAttribute("aria-busy");
  }

  function valid(r) {
    return r && r.schema_version === 1 && r.summary && Array.isArray(r.diagnostics);
  }

  function check() {
    if (pending) return;
    setPending(true);
    clearResults();
    setStatus("Checking…", "info");
    var ctl = new AbortController();
    var timedOut = false;
    var timer = setTimeout(function () { timedOut = true; ctl.abort(); }, 10000);
    var httpOk = false;
    fetch("/api/v1/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: src.value }),
      signal: ctl.signal,
      cache: "no-store"
    }).then(function (res) {
      httpOk = res.ok;
      return res.json().catch(function () { return null; });
    }).then(function (data) {
      if (httpOk && valid(data)) {
        renderDiagnostics(data.diagnostics);
        var n = data.diagnostics.length;
        if (n === 0) {
          var d = data.summary.declarations;
          setStatus("No issues (" + d + (d === 1 ? " declaration)" : " declarations)"), "ok");
        } else {
          setStatus(n === 1 ? "1 issue found" : n + " issues found", "issues");
        }
      } else {
        var c = data && data.error && data.error.code;
        setStatus(ERRORS[c] || "The check could not be completed. Retry.", "error");
      }
    }).catch(function () {
      setStatus(timedOut
        ? "The check timed out after 10 seconds. Retry."
        : "Network error. Check that the server is running, then retry.", "error");
    }).then(function () {
      clearTimeout(timer);
      setPending(false);
    });
  }

  checkBtn.addEventListener("click", check);
  src.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      check();
    }
  });
  src.addEventListener("input", updateCount);

  loadBtn.addEventListener("click", function () {
    var id = fixSel.value;
    var f = null;
    for (var i = 0; i < fixtures.length; i++) if (fixtures[i].id === id) f = fixtures[i];
    if (!f) return;
    if (previousText === null) previousText = src.value;
    src.value = f.source;
    updateCount();
    clearResults();
    undoBtn.hidden = false;
    setStatus("Loaded example: " + f.label + ". Press Check source.", "info");
    src.focus();
  });

  undoBtn.addEventListener("click", function () {
    if (previousText === null) return;
    src.value = previousText;
    previousText = null;
    undoBtn.hidden = true;
    updateCount();
    clearResults();
    setStatus("Previous text restored.", "info");
    src.focus();
  });

  function loadFixtures() {
    fetch("/static/fixtures.json", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("x"); return r.json(); })
      .then(function (data) {
        fixtures = (data && Array.isArray(data.fixtures)) ? data.fixtures : [];
        while (fixSel.firstChild) fixSel.removeChild(fixSel.firstChild);
        fixtures.forEach(function (f) {
          var o = document.createElement("option");
          o.value = String(f.id);
          o.textContent = String(f.label);
          fixSel.appendChild(o);
        });
        if (!fixtures.length) throw new Error("none");
        fixSel.disabled = false;
        loadBtn.disabled = false;
      })
      .catch(function () {
        while (fixSel.firstChild) fixSel.removeChild(fixSel.firstChild);
        var o = document.createElement("option");
        o.textContent = "Examples unavailable";
        fixSel.appendChild(o);
      });
  }

  updateCount();
  loadFixtures();
})();
