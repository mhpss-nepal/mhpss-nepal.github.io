#!/usr/bin/env python3
"""
MHPSS Nepal -- the site's navigation, written once and generated into every page
-------------------------------------------------------------------------------
Two shapes, on purpose, because they are two different things and should not be
mistaken for each other at a glance:

  TOP BAND   the public website (the Layer 3 page and the reference pages).
             A masthead and a solid bilingual nav band across the top.
  SIDE RAIL  the Layer 2 coordination hub. A dark rail down the left.

Before this, the nav band's seven items were all anchors into one page, so the
whole site looked like a single scrolling document; and the four hub pages each
had a different hand-written bar. Both are now generated from the tables below,
so a link added here appears on every page and cannot drift.

  apply    rewrite the block between the markers in every page
  check    fail if any page's block differs from what apply would write
           (the deploy guard runs this)

Markers, written once into each page by hand:
  <!--NAV:top KEY-->  ... <!--/NAV-->
  <!--NAV:rail KEY--> ... <!--/NAV-->
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------- the website
# np labels are DRAFT, like every other Nepali string on this site, and are
# listed in the translation worksheet for a Nepali speaker to confirm.
NAV = [
    ("overview",     "Overview",              "समग्र विवरण",     "./"),
    ("forms",        "Field forms",           "फिल्ड फारम",      "form/"),
    ("dashboard",    "Coordination dashboard","ड्यासबोर्ड",       "hub/"),
    ("method",       "Method",                "विधि",            "method.html"),
    ("architecture", "Architecture",          "संरचना",          "architecture.html"),
    ("access",       "Who sees what",         "पहुँच",            "access-explained.html"),
]
# layer3.html is deliberately NOT in this table, as of 16 September 2026.
# The whole site is the public-facing thing, so a nav item labelled "Public
# layer" read as a contradiction -- a reader could not tell what was public and
# what was not. The page itself is a HANDOVER argument: what may be published,
# what blocks submission into the national 5W, and who owns the permanent
# public page after this deployment ends. It is linked from architecture.html,
# where that argument belongs, and its own marker points at `architecture` so
# the nav shows a reader where they are rather than highlighting nothing.

# the sections of the Layer 3 page, offered as a jump strip under the band
SECTIONS = [
    ("#coverage", "§1 What is measured"), ("#pyramid", "§2 Where it sits"),
    ("#members", "§3 Who takes part"),    ("#work", "§4 What the group does"),
    ("#tools", "§5 Forms & dashboard"),   ("#method", "§6 Three layers"),
]

MAST = '''<header class="gov">
  <div class="in">
    <a class="id" href="{home}">
      <span data-mark="44"></span>
      <span style="min-width:0">
        <span class="who-line">Health Cluster &middot; Nepal</span>
        <b>MHPSS Technical Working Group</b>
        <span class="place">Rasuwa &middot; Nuwakot &middot; flood response</span>
      </span>
    </a>
    <div class="mid">
      <b>Mental Health &amp; Psychosocial Support</b>
      <span>मानसिक स्वास्थ्य र मनोसामाजिक सहयोग</span>
    </div>
    <div class="right">
      <!-- i18n.js mounts the language switch into [data-i18n-toggle] when it
           finds one, instead of floating it top-right over these buttons. -->
      <span data-i18n-toggle class="langslot"></span>
      <a class="gbtn out" href="{hub}">Coordination hub</a>
      <a class="gbtn crimson" href="{forms}">Field forms</a>
    </div>
  </div>
</header>'''

def top_block(key):
    out = [MAST.format(home="./", hub="hub/", forms="form/")]
    out.append('<nav class="navband" aria-label="Sections of this site">')
    out.append('  <div class="in">')
    for k, en, np, href in NAV:
        on = ' class="on" aria-current="page"' if k == key else ''
        out.append('    <a%s href="%s"><b>%s</b><i>%s</i></a>' % (on, href, en, np))
    out.append('  </div>')
    out.append('</nav>')
    if key == "overview":
        out.append('<div class="jump" aria-label="Sections of this page">')
        out.append('  <div class="in"><span class="lab">On this page</span>')
        for href, label in SECTIONS:
            out.append('    <a href="%s">%s</a>' % (href, label))
        out.append('  </div>')
        out.append('</div>')
    return "\n".join(out)

# ------------------------------------------------------------------- the hub
RAIL = [
    ("group", "Dashboard", None),
    ("hubindex",    "Coordination view",   "./"),
    ("hubcoverage", "Coverage &amp; 4Ws",  "coverage.html"),
    ("hubinbox",    "Field inbox",         "inbox.html"),
    ("hubaccess",   "Access",              "access.html"),
    ("group", "Elsewhere", None),
    ("outforms",  "Field forms",   "../form/"),
    ("outpublic", "Public page",   "../"),
    ("outmethod", "Method",        "../method.html"),
]
# the sections of the coordination view itself, shown only on that page
HUBSECTIONS = [
    ("#coverage", "Coverage"), ("#who", "Who is doing what"), ("#when", "Over time"),
    ("#what", "Activities"),   ("#people", "Workforce"),      ("#helpline", "Helplines"),
    ("#layers", "Architecture"),
]

def rail_block(key):
    out = ['<aside class="rail" aria-label="Coordination hub">',
           '  <a class="railid" href="./">',
           '    <span data-mark="30"></span>',
           '    <span><b>MHPSS Nepal</b><i>Layer 2 &middot; coordination</i></span>',
           '  </a>',
           '  <nav>']
    for k, label, href in RAIL:
        if k == "group":
            out.append('    <span class="rgrp">%s</span>' % label)
            continue
        on = ' class="on" aria-current="page"' if k == key else ''
        out.append('    <a%s href="%s">%s</a>' % (on, href, label))
        if k == "hubindex" and key == "hubindex":
            out.append('    <span class="rsub">')
            for h, l in HUBSECTIONS:
                out.append('      <a href="%s">%s</a>' % (h, l))
            out.append('    </span>')
    out.append('  </nav>')
    # i18n.js mounts the language switch here. Without a slot it floats top
    # right, where on these pages it lands on top of the synthetic-data banner.
    out.append('  <span data-i18n-toggle class="railtoggle"></span>')
    out.append('  <p class="rfoot">Draft. Synthetic data only.</p>')
    out.append('</aside>')
    return "\n".join(out)

# ------------------------------------------------------------------- machinery
MARK = re.compile(r'<!--NAV:(top|rail) ([a-z0-9]+)-->.*?<!--/NAV-->', re.S)

def pages():
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "tools", "node_modules")]
        for fn in sorted(filenames):
            if not fn.endswith(".html"):
                continue
            p = os.path.join(dirpath, fn)
            s = open(p, encoding="utf-8").read()
            if MARK.search(s):
                found.append((os.path.relpath(p, ROOT), s))
    return found

def render(kind, key):
    return top_block(key) if kind == "top" else rail_block(key)

def run(apply_it):
    rows, bad = [], 0
    for rel, s in pages():
        def sub(m):
            kind, key = m.group(1), m.group(2)
            return '<!--NAV:%s %s-->\n%s\n<!--/NAV-->' % (kind, key, render(kind, key))
        new = MARK.sub(sub, s)
        m = MARK.search(s)
        kind, key = m.group(1), m.group(2)
        same = (new == s)
        rows.append((rel, kind, key, same))
        if not same:
            bad += 1
            if apply_it:
                open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(new)
    print("MHPSS Nepal -- navigation")
    for rel, kind, key, same in rows:
        print("  %-26s %-5s %-12s %s" % (rel, kind, key,
              "ok" if same else ("rewritten" if apply_it else "DIFFERS")))
    if not rows:
        print("\n  No page carries a NAV marker. Nothing is generated, so nothing is")
        print("  guaranteed: add the markers or remove this gate.")
        return 1
    if apply_it:
        print("\n  %d page(s) rewritten from tools/nav.py." % bad)
        return 0
    if bad:
        print("\n  DRIFTED -- %d page(s) carry navigation that tools/nav.py did not"
              " write.\n  Run: tools/nav.py apply" % bad)
        return 1
    print("\n  True: every page's navigation is the one written in tools/nav.py.")
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit(run(mode == "apply"))
