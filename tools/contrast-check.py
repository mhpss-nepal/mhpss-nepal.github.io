#!/usr/bin/env python3
"""
MHPSS Nepal -- the contrast gate
---------------------------------------------------------------------
On 16 September 2026 a sweep over every text element on every page, in
light and dark, found 109 that did not clear WCAG AA. Most were one of
three token mistakes repeated everywhere:

  · --muted was #8497A2, which is 3.03:1 on white, so every caption,
    table header and eyebrow set in it failed
  · design.css forced a white body over page.css and hub.css, whose dark
    modes still coloured their own text light -- so the hub and the
    reference pages rendered near-white text on white
  · a brand blue that carries text on white (#006996) was used as a FILL
    under white text, where it is 2.97:1, and the reverse

All three are token-level, so they are checkable without a browser: read
the declared tokens out of each stylesheet's :root blocks, pair each with
the surface of its own block, and compute. That is what this does, and it
runs in the deploy guard.

It does NOT replace looking at the pages. A cascade can still land a
passing colour on an unexpected background, and only a real browser sees
that; the DOM sweep lives beside this file as contrast-sweep.py and is
run before a deploy from a machine that has Playwright.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def lum(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

HEX = re.compile(r"#[0-9a-fA-F]{3,6}\b")

def blocks(path):
    """Every :root-ish block in a stylesheet, as (label, {token: hex})."""
    src = open(os.path.join(ROOT, path), encoding="utf-8").read()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)       # comments first
    out = []
    for m in re.finditer(r"(:root[^{]*)\{([^}]*)\}", src):
        sel, body = m.group(1).strip(), m.group(2)
        toks = {}
        for d in re.finditer(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body):
            v = d.group(2).strip()
            if HEX.fullmatch(v):
                toks[d.group(1)] = v
        if toks:
            dark = "data-theme=\"dark\"" in sel or ":not([data-theme" in sel
            out.append(("%s %s" % (path, "dark" if dark else "light"), toks))
    # merge blocks with the same label: later declarations win, as in CSS
    merged = {}
    for label, toks in out:
        merged.setdefault(label, {}).update(toks)
    return list(merged.items())

# what each token is FOR, and what it therefore has to clear.
#   text  : the token colours text sitting on the block's surface
#   fill  : the token is a background under WHITE text
TEXT = ["--ink", "--slate", "--muted", "--mute", "--brand-d", "--wh-tx",
        "--good", "--warning", "--critical", "--serious", "--hc-ink", "--hc-mute"]
FILL = ["--l1", "--l2", "--l3", "--wh-d", "--wh-dd", "--brand-d-fill"]
SURFACE = ["--paper", "--surface", "--bg"]
FIXED = [("the demonstration banner", "#ffffff", "#a3201f", 4.5)]

def main():
    rows, bad = [], 0
    # hub.css moved to the hub repository on 17 Sep 2026 and is checked there
    for path in ("assets/design.css", "assets/app.css", "assets/page.css", "assets/site.css"):
        for label, toks in blocks(path):
            surface = next((toks[s] for s in SURFACE if s in toks), "#ffffff")
            for t in TEXT:
                if t in toks:
                    r = ratio(toks[t], surface)
                    rows.append((label, t + " on the surface", toks[t], surface, r, 4.5))
            for t in FILL:
                if t in toks:
                    r = ratio("#ffffff", toks[t])
                    rows.append((label, "white on " + t, "#ffffff", toks[t], r, 4.5))
    for name, fg, bg, need in FIXED:
        rows.append(("fixed", name, fg, bg, ratio(fg, bg), need))

    print("MHPSS Nepal -- declared colour tokens against their own surfaces")
    print("  %-26s %-24s %-9s %-9s %6s" % ("block", "pair", "fg", "bg", "ratio"))
    for label, pair, fg, bg, r, need in rows:
        ok = r >= need
        if not ok:
            bad += 1
        print("  %-26s %-24s %-9s %-9s %6.2f  %s" % (label, pair, fg, bg, r,
              "ok" if ok else "FAILS %.1f" % need))
    print()
    if not rows:
        print("  No tokens were read. The gate is checking nothing, so it fails.")
        return 1
    if bad:
        print("  %d declared pair(s) below WCAG AA. A caption or a heading set in one" % bad)
        print("  of these cannot be read. Fix the token, do not remove the check.")
        return 1
    print("  True: every declared token clears AA against the surface of its own block.")
    print("  (%d pairs checked. The live DOM sweep is a separate step -- see the header.)" % len(rows))
    return 0

if __name__ == "__main__":
    sys.exit(main())
