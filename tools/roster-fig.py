#!/usr/bin/env python3
"""
MHPSS Nepal -- the site unit chart: build it, and keep it true
---------------------------------------------------------------------
The figure in section 1 of index.html draws ONE SQUARE PER SITE CODE.
That is only worth drawing if the squares are the real list, so the
squares are generated from assets/codes.js rather than typed, and this
same script is run by the deploy guard to refuse a deploy where the
drawn figure and the code list have drifted apart.

  build   print the <div> rows, to paste into index.html
  apply   rewrite the rows and the marker inside index.html in place
  check   recount codes.js, compare with the numbers marked in
          index.html, and exit non-zero if they differ

Counted groups, all from `source` and `district` in codes.js:
  roster    on the proposed holding-centre roster, Rasuwa and Nuwakot
  govlist   on the DAO Nuwakot list of 29 Bhadra 2083, not on that roster
            (source "gov-list"; whether these join the denominator is the
            open question D-S14, so they are drawn apart)
  offlist   reported by partners, not on either list, same two districts
  outside   reported in any other district
Two kinds of entry are not sites and are excluded from every group: the
`escape` entry ("Other -- not on this list") and `retired` codes, which
stay in the list only so that old records still resolve.
"""
import re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESPONSE = ("RAS", "NUW")
NOT_SITES = ("escape", "retired")

def sites():
    s = open(os.path.join(ROOT, "assets/codes.js"), encoding="utf-8").read()
    m = re.search(r"const SITES\s*=\s*\[(.*?)\n\];", s, re.S)
    if not m:
        print("cannot find SITES in assets/codes.js"); sys.exit(2)
    out = []
    for line in m.group(1).splitlines():
        c = re.search(r'code:\s*"([^"]+)"', line)
        d = re.search(r'district:\s*"([^"]+)"', line)
        src = re.search(r'source:\s*"([^"]+)"', line)
        if c and d and src:
            out.append((c.group(1), d.group(1), src.group(1)))
    return out

def districts():
    """district code -> name, for the note under the 'outside' row"""
    s = open(os.path.join(ROOT, "assets/codes.js"), encoding="utf-8").read()
    m = re.search(r"const DISTRICTS\s*=\s*\[(.*?)\n\];", s, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        c = re.search(r'code:\s*"([^"]+)"', line)
        n = re.search(r'name:\s*"([^"]+)"', line)
        if c and n:
            out[c.group(1)] = n.group(1)
    return out

def counts():
    g = {"roster": [], "govlist": [], "offlist": [], "outside": []}
    for code, dist, src in sites():
        if src in NOT_SITES:
            continue
        if src == "roster" and dist in RESPONSE:
            g["roster"].append(code)
        elif src == "gov-list" and dist in RESPONSE:
            g["govlist"].append(code)
        elif dist in RESPONSE:
            g["offlist"].append(code)
        else:
            g["outside"].append(code)
    return g

def outside_note(g):
    names = districts()
    seen = []
    for code, dist, src in sites():
        if code in g["outside"] and dist not in seen:
            seen.append(dist)
    return ", ".join(names.get(d, d) for d in seen)

# ---------------------------------------------------------------- build
def rows(g):
    return [
        ("roster",  "On the proposed holding-centre roster",
         "the denominator every coverage figure is measured against"),
        ("govlist", "On the district administration's list, not on that roster",
         "DAO Nuwakot, 29 Bhadra 2083 · whether they join the denominator is an open question"),
        ("offlist", "Reported by partners, on neither list",
         "shown apart, and never counted as a gap"),
        ("outside", "Reported outside Rasuwa and Nuwakot",
         outside_note(g)),
    ]

def marker(g):
    return "%d,%d,%d,%d" % (len(g["roster"]), len(g["govlist"]),
                            len(g["offlist"]), len(g["outside"]))

def build():
    """HTML, not SVG, on purpose.

    An SVG figure with a fixed viewBox scales its own text down with the
    container, so a 12px label on a 860-wide drawing renders at 5px on a
    phone -- unreadable, which is the one screen the field actually uses.
    Squares that are elements reflow instead: fewer per row on a narrow
    screen, and the words stay the size they were set in.
    """
    g = counts()
    parts = []
    for key, title, note in rows(g):
        n = len(g[key])
        parts.append('      <div class="urow">')
        parts.append('        <p class="ulab"><b>%d</b> %s <span>%s</span></p>'
                     % (n, title, note))
        parts.append('        <div class="units">' +
                     ('<i class="u %s"></i>' % key) * n + '</div>')
        parts.append('      </div>')
    return "\n".join(parts), g

# ---------------------------------------------------------------- apply
ROWS_RE = re.compile(r'(      <div class="urow">\n.*?\n      </div>\n)+', re.S)

def apply():
    """Rewrite the generated rows and the marker inside index.html.
    Everything else on the page -- the lede, the key, the insight -- is
    written by hand and left alone."""
    path = os.path.join(ROOT, "index.html")
    page = open(path, encoding="utf-8").read()
    html, g = build()
    if not ROWS_RE.search(page) or 'data-sitefig="' not in page:
        print("index.html carries no generated rows or no marker; paste the build output by hand")
        return 1
    page = ROWS_RE.sub(html + "\n", page, count=1)
    page = re.sub(r'data-sitefig="[^"]*"', 'data-sitefig="%s"' % marker(g), page, count=1)
    open(path, "w", encoding="utf-8").write(page)
    print("index.html rewritten: marker %s" % marker(g))
    return 0

# ---------------------------------------------------------------- check
def check():
    g = counts()
    page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'data-sitefig="([^"]+)"', page)
    print("MHPSS Nepal -- the site unit chart")
    print("  codes.js:  roster=%d  gov-list=%d  off-roster=%d  outside=%d"
          % (len(g["roster"]), len(g["govlist"]), len(g["offlist"]), len(g["outside"])))
    if not m:
        print("\n  index.html carries no data-sitefig marker. The figure cannot be")
        print("  checked, so it must not ship. Regenerate it with: roster-fig.py apply")
        return 1
    want = marker(g)
    print("  index.html: %s" % m.group(1))
    if m.group(1) != want:
        print("\n  DRIFTED -- the drawn figure no longer matches the site list.")
        print("  Regenerate it: tools/roster-fig.py apply")
        return 1
    # the squares themselves, not only the marker
    for key in g:
        drawn = len(re.findall(r'<i class="u %s"></i>' % key, page))
        if drawn != len(g[key]):
            print("\n  DRIFTED -- %d %s squares are drawn, the list holds %d."
                  % (drawn, key, len(g[key])))
            return 1
    print("\n  True: every site code in the list is drawn once, and only once.")
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "build":
        html, g = build()
        print(html)
        sys.stderr.write('\nmarker: data-sitefig="%s"\n' % marker(g))
    elif mode == "apply":
        sys.exit(apply())
    else:
        sys.exit(check())
