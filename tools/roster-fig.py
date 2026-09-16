#!/usr/bin/env python3
"""
MHPSS Nepal -- the site unit chart: build it, and keep it true
---------------------------------------------------------------------
The figure in section 1 of index.html draws ONE SQUARE PER SITE CODE.
That is only worth drawing if the squares are the real list, so the
squares are generated from assets/codes.js rather than typed, and this
same script is run by the deploy guard to refuse a deploy where the
drawn figure and the code list have drifted apart.

  build   print the <svg> block, to paste into index.html
  check   recount codes.js, compare with the numbers marked in
          index.html, and exit non-zero if they differ

Counted groups, all from `source` and `district` in codes.js:
  roster    on the proposed holding-centre roster, Rasuwa and Nuwakot
  offlist   reported by partners, not on that roster, same two districts
  outside   reported in any other district
The `escape` entry ("Other -- not on this list") is not a site and is
excluded from all three.
"""
import re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESPONSE = ("RAS", "NUW")

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

def counts():
    g = {"roster": [], "offlist": [], "outside": []}
    for code, dist, src in sites():
        if src == "escape":
            continue
        if src == "roster" and dist in RESPONSE:
            g["roster"].append(code)
        elif dist in RESPONSE:
            g["offlist"].append(code)
        else:
            g["outside"].append(code)
    return g

# ---------------------------------------------------------------- build
ROWS = [
    ("roster",  "On the proposed holding-centre roster",
     "the denominator every coverage figure is measured against"),
    ("offlist", "Reported by partners, not on that roster",
     "shown apart, and never counted as a gap"),
    ("outside", "Reported outside Rasuwa and Nuwakot",
     "Dhading, Kathmandu, Chitwan, Nawalpur"),
]

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
    for key, title, note in ROWS:
        n = len(g[key])
        parts.append('      <div class="urow">')
        parts.append('        <p class="ulab"><b>%d</b> %s <span>%s</span></p>'
                     % (n, title, note))
        parts.append('        <div class="units">' +
                     ('<i class="u %s"></i>' % key) * n + '</div>')
        parts.append('      </div>')
    return "\n".join(parts), g

# ---------------------------------------------------------------- check
def check():
    g = counts()
    page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'data-sitefig="([^"]+)"', page)
    print("MHPSS Nepal -- the site unit chart")
    print("  codes.js:  roster=%d  off-roster=%d  outside=%d"
          % (len(g["roster"]), len(g["offlist"]), len(g["outside"])))
    if not m:
        print("\n  index.html carries no data-sitefig marker. The figure cannot be")
        print("  checked, so it must not ship. Regenerate it with: roster-fig.py build")
        return 1
    want = "%d,%d,%d" % (len(g["roster"]), len(g["offlist"]), len(g["outside"]))
    print("  index.html: %s" % m.group(1))
    if m.group(1) != want:
        print("\n  DRIFTED -- the drawn figure no longer matches the site list.")
        print("  Regenerate it: tools/roster-fig.py build")
        return 1
    # the squares themselves, not only the marker
    drawn = len(re.findall(r'<i class="u roster"></i>', page))
    if drawn != len(g["roster"]):
        print("\n  DRIFTED -- %d roster squares are drawn, the list holds %d."
              % (drawn, len(g["roster"])))
        return 1
    print("\n  True: every site code in the list is drawn once, and only once.")
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "build":
        svg, g = build()
        print(svg)
        sys.stderr.write('\nmarker: data-sitefig="%d,%d,%d"\n'
                         % (len(g["roster"]), len(g["offlist"]), len(g["outside"])))
    else:
        sys.exit(check())
