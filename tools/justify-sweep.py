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

17 September 2026: the check now looks at what the reader sees, not only at
the computed style. A block passes when (a) every line but its last reaches
the right edge of the block -- a line holding a single word cannot be spread
and is not counted -- and (b) the block is as wide as the container it stands
in: running text is not held to a measure. It waits for the live panels to
draw, and it runs in English and in Nepali.
"""
import sys, subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 9071
# The real pages of this repository. coordination/* and dashboard/index.html are
# deliberately NOT here: they are redirect stubs that meta-refresh in 0s, so
# loading them measures their destination and reports it under the stub's
# name -- which is how this sweep first appeared to be checking twenty pages
# when four of them were the same four pages twice.
PAGES = ["index.html","flood-response.html","iec.html","referral-directory.html",
         "resources.html","videos.html","contact-us.html",
         "method.html","architecture.html","access-explained.html","layer3.html"]
# The hub and the field forms moved to their own repositories on 17 Sep 2026
# (hub, form) and are swept there.

# Deliberately ragged, per the rules doc: labels, numerals, monospace.
# A selector here means "this element is set, not justified", and the sweep
# says so rather than passing over it in silence.
EXEMPT = ("th", ".mono", "code", "kbd", "samp", ".chip", ".badge", ".tag",
          ".num", ".eyebrow", ".blabel", ".ulab", ".pill", ".tagpill",
          ".hint", ".opt", ".n", ".rt")

JS = r"""() => {
  const RUN = 'p, li, dd, td, blockquote, figcaption, .note, .callout, .lede, .subtitle, .help, .stand, .insight, .figsrc';
  const EX = ['th','.mono','code','kbd','samp','.chip','.badge','.tag','.num','.eyebrow','.blabel','.ulab','.units','.pill','.tagpill','.stamp','.hint','.opt','.n','.rt'];
  const isEx = el => EX.some(s => s.startsWith('.') ? el.classList.contains(s.slice(1)) : el.tagName.toLowerCase() === s);
  const out = [];
  const label = el => (el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.') : ''));
  const runs = [...document.querySelectorAll(RUN)];
  const runSet = new Set(runs);
  const owner = n => { let e = n.parentElement; while (e && !runSet.has(e)) e = e.parentElement; return e; };
  runs.forEach(el => {
    if (!el.getClientRects().length) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return;
    const txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (txt.length < 2 || isEx(el)) return;
    // line boxes from this element's own text nodes
    const lines = new Map();
    const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = tw.nextNode())) {
      if (!n.textContent.trim() || owner(n) !== el) continue;
      let nested = false;
      for (let a = n.parentElement; a && a !== el; a = a.parentElement) {
        const d = getComputedStyle(a).display;
        if (!/^inline$|^contents$/.test(d) || getComputedStyle(a).position === 'absolute') { nested = true; break; }
      }
      if (nested) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const rc of r.getClientRects()) {
        if (rc.width < 1) continue;
        const key = Math.round(rc.top / 3);
        const cur = lines.get(key) || {top: rc.top, right: -1e9, left: 1e9};
        cur.right = Math.max(cur.right, rc.right); cur.left = Math.min(cur.left, rc.left);
        lines.set(key, cur);
      }
    }
    const L = [...lines.values()].sort((a, b) => a.top - b.top);
    // merge keys that are within 4px (same visual line)
    const M = [];
    L.forEach(l => { const p = M[M.length - 1]; if (p && Math.abs(p.top - l.top) < 5) { p.right = Math.max(p.right, l.right); } else M.push({...l}); });
    const box = el.getBoundingClientRect();
    const contentRight = box.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
    const issues = [];
    const brs = el.querySelectorAll('br').length;
    if (M.length >= 2 && !/flex|grid/.test(cs.display) && brs < M.length - 1) {
      if (cs.textAlign !== 'justify') issues.push('align=' + cs.textAlign);
      if (cs.hyphens === 'auto') issues.push('hyphens:auto');
      let ragged = 0;
      const cand = [];
      for (let i = 0; i < M.length - 1; i++) if (contentRight - M[i].right > 3) cand.push(M[i]);
      if (cand.length) {
        /* a line holding one word cannot be spread: count words per line */
        const words = [];
        const tw2 = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let t;
        while ((t = tw2.nextNode())) {
          if (owner(t) !== el) continue;
          const re = /\S+/g; let m;
          while ((m = re.exec(t.textContent))) {
            const r2 = document.createRange(); r2.setStart(t, m.index); r2.setEnd(t, m.index + m[0].length);
            const rc = r2.getClientRects()[0]; if (rc) words.push(rc.top);
          }
        }
        cand.forEach(c => { const k = words.filter(tp => Math.abs(tp - c.top) < 5).length; if (k > 1) ragged++; });
      }
      if (ragged && cs.textAlign === 'justify') issues.push('ragged lines=' + ragged + '/' + (M.length - 1));
    }
    // width follows the container: no cap on running text blocks
    if (['block','list-item','flow-root'].includes(cs.display) && cs.float === 'none' && cs.position !== 'absolute' && !['TD'].includes(el.tagName)) {
      const par = el.parentElement; const pcs = getComputedStyle(par);
      if (['block','flow-root','list-item'].includes(pcs.display)) {
        const pbox = par.getBoundingClientRect();
        const pw = pbox.width - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight) - parseFloat(pcs.borderLeftWidth) - parseFloat(pcs.borderRightWidth);
        const ew = box.width + parseFloat(cs.marginLeft) + parseFloat(cs.marginRight);
        if (M.length >= 2 && pw - ew > 4) issues.push('narrower than container by ' + Math.round(pw - ew) + 'px (max-width ' + cs.maxWidth + ')');
      }
    }
    if (issues.length) out.push({el: label(el), txt: txt.slice(0, 60), issues: issues.join('; ')});
  });
  // lists and definition lists capped
  document.querySelectorAll('ul, ol, dl').forEach(el => {
    if (!el.getClientRects().length) return;
    const cs = getComputedStyle(el);
    if (cs.maxWidth !== 'none' && /px/.test(cs.maxWidth)) {
      const txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (txt.length > 40) out.push({el: label(el), txt: txt.slice(0, 60), issues: 'list max-width ' + cs.maxWidth});
    }
  });
  return out;
}"""

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    runs = bad = 0
    problems = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            for lang in ("en", "ne"):
                for w in (1440, 390):
                    ctx = b.new_context(viewport={"width": w, "height": 1200})
                    if lang == "ne":
                        ctx.add_init_script("try{localStorage.setItem('mhpss-np-lang','ne')}catch(e){}")
                    pg = ctx.new_page()
                    for path in PAGES:
                        pg.goto("http://127.0.0.1:%d/%s" % (PORT, path), wait_until="load")
                        pg.wait_for_timeout(2200)   # the live panels draw after load
                        landed = pg.url.split(str(PORT) + "/")[-1]
                        if landed != path:
                            print("    NOTE  %s redirected to %s -- not a page of its own" % (path, landed))
                            continue
                        runs += 1
                        for r in pg.evaluate(JS):
                            bad += 1
                            problems.append((lang, w, path, r))
                    pg.close(); ctx.close()
            b.close()
    finally:
        srv.terminate()

    print("MHPSS Nepal -- text setting")
    print("  pages: %d x 2 widths x 2 languages   page views checked: %d" % (len(PAGES), runs))
    if problems:
        seen = set()
        for lang, w, path, r in problems:
            key = (path, r["el"], r["txt"][:30], r["issues"].split(" by ")[0])
            if key in seen: continue
            seen.add(key)
            print("    %-2s %-24s %4dpx  %-20s %-44s %s" % (lang, path, w, r["el"][:20], r["txt"][:44], r["issues"]))
        print("\n  Not flush yet: %d finding(s) above." % bad)
        return 1
    print("  Flush: every multi-line block of running text is justified to the right")
    print("  edge, as wide as the container it stands in, and nothing is hyphenated.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
