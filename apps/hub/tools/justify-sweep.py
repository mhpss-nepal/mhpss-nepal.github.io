#!/usr/bin/env python3
"""
MHPSS Nepal -- text-setting sweep.

The check from the project's text-setting rules, run over every page at two
widths. It reports any GENUINELY MULTI-LINE block of running text that is
not justified, or that has hyphenation turned on.

One-line blocks are exempt by construction, not by a line counter in the
page: a last line never justifies, so a single-line block is untouched by
the rule anyway. The exemption here is in the CHECK, so that a two-line
paragraph -- the case that was got wrong before -- is still required to be
flush.

Needs Playwright, so it runs cloud-side before a deploy and is not one of
the Mac gates. tools/text-setting-check.py is the static gate that does
run there.
"""
import subprocess, sys, time, json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

PORT = 9071
APP_ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "forms.html", "access.html"]

# Deliberately ragged, per the rules doc: labels, numerals, monospace.
# A selector here means "this element is set, not justified", and the sweep
# says so rather than passing over it in silence.
EXEMPT = ("th", ".mono", "code", "kbd", "samp", ".chip", ".badge", ".tag",
          ".num", ".eyebrow", ".blabel", ".ulab", ".pill", ".tagpill",
          ".hint", ".opt", ".n", ".rt")

def wait_for_server(srv):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urlopen("http://127.0.0.1:%d/" % PORT, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            if srv.poll() is not None:
                raise RuntimeError("local QA server failed to start")
        time.sleep(0.05)
    raise RuntimeError("local QA server was not ready in time")

JS = """() => {
  const EX = %s;
  const out = [];
  const nodes = document.querySelectorAll('p, li, td, blockquote, dd, figcaption');
  nodes.forEach(el => {
    if (!el.offsetParent && el.tagName !== 'BODY') return;      /* not rendered */
    const txt = (el.textContent || '').trim();
    if (txt.length < 2) return;
    /* Count VISUAL LINES, not rects. Range.getClientRects() returns a rect
       per contained element as well as per line box, so a one-line cell
       holding <b>0-4</b> reports two rects and looked multi-line. Dedupe
       by rounded top edge: two rects on the same top are one line. */
    const r = document.createRange(); r.selectNodeContents(el);
    const tops = new Set();
    for (const rect of r.getClientRects()) {
      if (rect.width < 0.5 && rect.height < 0.5) continue;
      tops.add(Math.round(rect.top));
    }
    if (tops.size < 2) return;                                  /* one line: exempt */
    const cs = getComputedStyle(el);
    const ok = cs.textAlign === 'justify' && cs.hyphens !== 'auto';
    const exempt = EX.some(s => s.startsWith('.') ? el.classList.contains(s.slice(1))
                                                  : el.tagName.toLowerCase() === s);
    out.push({ ok: ok, exempt: exempt, align: cs.textAlign, hy: cs.hyphens,
               tag: el.tagName.toLowerCase(),
               cls: (el.className || '').toString().split(' ').filter(Boolean).slice(0,2).join('.'),
               txt: txt.slice(0, 46).replace(/\\s+/g, ' ') });
  });
  return out;
}""" % json.dumps(list(EXEMPT))

def local_only(route):
    if route.request.url.startswith("http://127.0.0.1:"):
        route.continue_()
    else:
        route.abort()


def main():
    srv = subprocess.Popen([
        sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
        "--directory", str(APP_ROOT),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total = multi = bad = 0
    problems = []
    try:
        wait_for_server(srv)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            for w in (1440, 390):
                ctx = b.new_context(viewport={"width": w, "height": 1200})
                ctx.route("**/*", local_only)
                pg = ctx.new_page()
                for path in PAGES:
                    url = "http://127.0.0.1:%d/%s" % (PORT, path)
                    pg.goto(url, wait_until="load")
                    pg.wait_for_timeout(700)
                    if pg.url != url:
                        print("    NOTE  %s redirected to %s -- not a page of its own"
                              % (path, pg.url))
                        continue
                    rows = pg.evaluate(JS)
                    multi += len(rows)
                    for r in rows:
                        if r["ok"] or r["exempt"]:
                            continue
                        bad += 1
                        problems.append((w, path, r))
                pg.close(); ctx.close()
            b.close()
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(timeout=5)

    print("MHPSS Nepal -- text setting")
    print("  pages: %d x 2 widths   multi-line text blocks checked: %d" % (len(PAGES), multi))
    if problems:
        print("  NOT FLUSH: %d" % bad)
        seen = set()
        for w, path, r in problems:
            key = (path, r["tag"], r["cls"], r["txt"])
            if key in seen: continue
            seen.add(key)
            print("    %-24s %4dpx  %-14s align=%-8s  %s"
                  % (path, w, (r["tag"] + "." + r["cls"]).rstrip("."), r["align"], r["txt"]))
        print("\n  Not flush yet: %d block(s) above are multi-line and not justified." % bad)
        return 1
    print("  Flush: every multi-line block of running text is justified, and")
    print("  nothing on the site has hyphens:auto.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
