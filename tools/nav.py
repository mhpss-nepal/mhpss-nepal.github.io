#!/usr/bin/env python3
"""
MHPSS Nepal -- the site's navigation, written once and generated into every page
-------------------------------------------------------------------------------
The public website's masthead and bilingual nav band, its footer and its
helplines block, generated into every page. The coordination hub's dark side
rail -- a deliberately different shape, so that the working dashboard is never
mistaken for the public site -- has been generated in the hub's own repository
since 17 September 2026.

Before this, the nav band's seven items were all anchors into one page, so the
whole site looked like a single scrolling document. The band is now generated
from the tables below, so a link added here appears on every page and cannot
drift.

  apply    rewrite the block between the markers in every page
  check    fail if any page's block differs from what apply would write
           (the deploy guard runs this)

Markers, written once into each page by hand:
  <!--NAV:top KEY-->  ... <!--/NAV-->
  <!--NAV:foot KEY--> ... <!--/NAV-->   the website footer
  <!--NAV:help KEY--> ... <!--/NAV-->   the helplines, on two public pages
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------- the website
# The public website follows mhpssmyanmar.org page for page (decided 16 Sep
# 2026; the model, and who reads each page, are recorded with the project
# documents). A public MHPSS site is for
# affected people and field partners -- materials, referral routes,
# resources, a way to make contact -- so these eight are the only items in
# the band. Pages with no Nepal content yet exist and say so plainly.
#
# np labels are DRAFT, like every other Nepali string on this site. Where the
# response's own documents use a word, that word is used: प्रतिकार्य,
# "IEC सामग्री" and रेफरल are the EDCD flood response report's own vocabulary.
# They reach the translation worksheet as nav.band.<key>, and the check below
# refuses a band whose words differ from the dictionary's.
NAV = [
    ("home",      "Home",               "गृहपृष्ठ",          "./"),
    ("flood",     "Flood Response",     "बाढी प्रतिकार्य",    "flood-response.html"),
    ("iec",       "IEC",                "IEC सामग्री",        "iec.html"),
    ("referral",  "Referral Directory", "रेफरल निर्देशिका",   "referral-directory.html"),
    ("resources", "Resources",          "स्रोत सामग्री",       "resources.html"),
    ("videos",    "Videos",             "भिडियो",             "videos.html"),
    ("contact",   "Contact",            "सम्पर्क",             "contact-us.html"),
]
PUBLIC = [k for k, _, _, _ in NAV]

# The design and method pages. They document the SYSTEM, not the response, so
# none of them is in the band -- putting them there is the mistake recorded in
# the Layer 3 handover. They hang off one footer link; on their own pages a
# thin strip under the band lets a reader move between the four and see where
# they are, without any of them posing as public content.
REFERENCE = [
    ("architecture", "architecture.html"),
    ("method",       "method.html"),
    ("access",       "access-explained.html"),
    ("layer3",       "layer3.html"),
]
REFKEYS = [k for k, _ in REFERENCE]

# In-page jump strips, only on pages long enough to need one. Labels are keys
# jump.<page>.<n> in the dictionary.
JUMP = {
    "flood":    ["#overview", "#summary", "#helplines", "#tools", "#guidance", "#coordination"],
    "referral": ["#helplines", "#find", "#map", "#directory", "#staff"],
}

# Every visible string in these blocks is a dictionary key (assets/i18n-strings.js)
# and the elements are written EMPTY, as on every keyed page: the dictionary is
# the only place page text lives, so a second English copy here could only drift.
# What is the same in every language -- the group's name, the bilingual pair in
# the middle, the stacked labels in the band -- is declared with data-i18n-skip.
MAST = '''<div class="topline">
  <div class="in">
    <span class="tl-l" data-i18n="mast.cluster"></span>
    <!-- i18n.js mounts the language switch into [data-i18n-toggle] when it
         finds one, instead of floating it top-right over the masthead. -->
    <span data-i18n-toggle class="langslot"></span>
  </div>
</div>
<header class="gov">
  <div class="in">
    <a class="id" href="{home}">
      <span data-mark="58"></span>
      <span style="min-width:0">
        <b data-i18n-skip>MHPSS Technical Working Group</b>
        <span class="place" data-i18n="mast.place"></span>
      </span>
    </a>
    <div class="mid" data-i18n-skip>
      <b>Mental Health &amp; Psychosocial Support</b>
      <span>मानसिक स्वास्थ्य र मनोसामाजिक सहयोग</span>
    </div>
    <div class="right">
      <a class="gbtn out" href="{hub}" data-i18n="mast.hub"></a>
      <a class="gbtn crimson" href="{forms}" data-i18n="nav.forms"></a>
    </div>
  </div>
</header>'''

# The demonstration band that stood above the masthead until 17 September
# 2026 is gone: the Ministry cleared the site to go live that day. What is
# still to be agreed is said where it applies -- a chip on the item itself --
# not in a red band over every page.

def top_block(key):
    out = []
    out.append(MAST.format(home="./", hub="hub/", forms="form/"))
    # the band's labels already carry both languages, stacked
    out.append('<nav class="navband" aria-label="Sections of this site" data-i18n-skip>')
    out.append('  <div class="in">')
    for k, en, np, href in NAV:
        on = ' class="on" aria-current="page"' if k == key else ''
        out.append('    <a%s href="%s"><b>%s</b><i>%s</i></a>' % (on, href, en, np))
    out.append('  </div>')
    out.append('</nav>')
    if key in REFKEYS:
        # The strip is white in both schemes, but page.css lifts --wh-tx for dark
        # mode, which left these links at 2.12:1 on the design pages
        # (tools/contrast-sweep.py, 16 Sep 2026). Pinned to the text-safe blue
        # on this strip only.
        out.append('<div class="jump ref" aria-label="How this system works" style="--wh-tx:#006996">')
        out.append('  <div class="in"><span class="lab" data-i18n="ref.strip"></span>')
        for k, href in REFERENCE:
            on = ' class="on" aria-current="page"' if k == key else ''
            out.append('    <a%s href="%s" data-i18n="ref.%s"></a>' % (on, href, k))
        out.append('  </div>')
        out.append('</div>')
    if key in JUMP:
        out.append('<div class="jump" aria-label="Sections of this page">')
        out.append('  <div class="in"><span class="lab" data-i18n="jump.label"></span>')
        for i, href in enumerate(JUMP[key]):
            out.append('    <a href="%s" data-i18n="jump.%s.%d"></a>' % (href, key, i + 1))
        out.append('  </div>')
        out.append('</div>')
    return "\n".join(out)

# ---------------------------------------------------------------- the footer
# One footer for the whole website, generated like the navigation, so a link
# cannot exist on four pages and not on the fifth. It carries no contact
# names: those belong on the Contact page, and are still to be confirmed.
FOOT = '''<footer class="gfoot">
  <div class="in">
    <div class="fid">
      <span data-mark="46" data-mark-mono></span>
      <span class="fid-t"><b data-i18n-skip>MHPSS Technical Working Group</b><span data-i18n="mast.cluster"></span></span>
    </div>
    <div class="cols">
      <div><h4 data-i18n="foot.site"></h4>
        <p><a href="flood-response.html" data-i18n="foot.flood"></a><br>
        <a href="referral-directory.html" data-i18n="foot.referral"></a><br>
        <a href="resources.html" data-i18n="foot.resources"></a><br>
        <a href="contact-us.html" data-i18n="foot.contact"></a></p></div>
      <div><h4 data-i18n="foot.tools"></h4>
        <p><a href="form/" data-i18n="nav.forms"></a><br>
        <a href="form/cards.html" data-i18n="foot.cards"></a><br>
        <a href="hub/" data-i18n="mast.hub"></a></p></div>
      <div><h4 data-i18n="ref.strip"></h4>
        <p><a href="architecture.html" data-i18n="ref.architecture"></a><br>
        <a href="method.html" data-i18n="ref.method"></a><br>
        <a href="access-explained.html" data-i18n="ref.access"></a><br>
        <a href="layer3.html" data-i18n="ref.layer3"></a></p></div>
    </div>
    <p data-i18n="foot.draft" data-i18n-html></p>
    <p data-i18n="foot.privacy"></p>
  </div>
</footer>'''

def foot_block(key):
    return FOOT

# ------------------------------------------------------------- the helplines
# The same three helplines stand on Flood Response and on Referral Directory.
# Typed twice, one copy would go stale the day a number changes, and a stale
# helpline number on a public MHPSS page is worse than none. So they are
# written once, here, and generated into both pages between
#   <!--NAV:help KEY--> ... <!--/NAV-->
# A number is listed only where the service itself, or the Ministry, prints
# it -- read on 16 Sep 2026, source beside each one. A number seen only in a
# news story (for example the child helpline 1098) is not listed until an
# official page carrying it has been read.
HELPLINES = [
    # (key, css, tel, shown number, official Nepali name or None)
    ("1166", "lead", "1166",        "1166",          "आत्महत्या रोकथाम हेल्पलाइन सेवा"),
    ("tpo",  "",     "16600102005", "1660 010 2005", None),
    ("1115", "",     "1115",        "1115",          None),
]

def help_block(key):
    if key == "home":
        # the home page carries the numbers only, and sends the reader on to
        # the full cards -- same data, so it cannot disagree with them
        out = ['<ul class="hlmini">']
        for k, css, tel, shown, np in HELPLINES:
            out.append('  <li%s><a class="num" href="tel:%s" data-i18n-skip>%s</a>'
                       '<span class="name" data-i18n="hl.%s.name"></span></li>'
                       % ((' class="%s"' % css) if css else "", tel, shown, k))
        out.append('</ul>')
        out.append('<p class="golinks"><a href="flood-response.html#helplines" data-i18n="hl.all"></a></p>')
        return "\n".join(out)
    out = ['<div class="hl">']
    for k, css, tel, shown, np in HELPLINES:
        out.append('  <div class="hlc%s">' % ((" " + css) if css else ""))
        out.append('    <span class="kind" data-i18n="hl.%s.kind"></span>' % k)
        out.append('    <a class="num" href="tel:%s" data-i18n-skip>%s</a>' % (tel, shown))
        out.append('    <span class="name" data-i18n="hl.%s.name"></span>' % k)
        if np:
            out.append('    <span class="np" lang="ne" data-i18n-skip>%s</span>' % np)
        out.append('    <p class="meta" data-i18n="hl.%s.meta"></p>' % k)
        out.append('    <p class="from" data-i18n="hl.%s.from" data-i18n-html></p>' % k)
        out.append('  </div>')
    out.append('</div>')
    out.append('<p class="hlnote" data-i18n="hl.note"></p>')
    return "\n".join(out)

# ------------------------------------------------------------------- machinery
MARK = re.compile(r'<!--NAV:(top|foot|help) ([a-z0-9]+)-->.*?<!--/NAV-->', re.S)

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
    if kind == "top":
        return top_block(key)
    if kind == "foot":
        return foot_block(key)
    if kind == "help":
        return help_block(key)
    raise ValueError("no navigation of kind %r" % kind)

def band_words():
    path = os.path.join(ROOT, "assets", "i18n-strings.js")
    strings = open(path, encoding="utf-8").read()
    ne_at = strings.index("\n  ne: {")
    out = []
    for k, en, np, href in NAV:
        for lang, want, block in (("en", en, strings[:ne_at]), ("ne", np, strings[ne_at:])):
            m = re.search(r'\n\s*"nav\.band\.%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % re.escape(k), block)
            got = json.loads('"%s"' % m.group(1)) if m else None
            if got != want:
                out.append("nav.band.%s [%s]  dictionary: %s   nav.py: %s"
                           % (k, lang, "missing" if got is None else got, want))
    return out

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
    # Every page in the band must exist and carry both the band and the footer.
    # A nav item that points at a missing page, or a public page with no footer,
    # is the kind of hole nobody sees until a reader falls into it.
    missing = []
    for k, en, np, href in NAV:
        rel = "index.html" if href == "./" else href
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            missing.append("%s -> %s does not exist" % (en, rel))
            continue
        txt = open(path, encoding="utf-8").read()
        for kind in ("top", "foot"):
            if "<!--NAV:%s %s-->" % (kind, k) not in txt:
                missing.append("%s carries no <!--NAV:%s %s--> marker" % (rel, kind, k))
    if missing:
        print("\n  INCOMPLETE -- the website band points at pages that are not whole:")
        for m in missing:
            print("    " + m)
        return 1
    # The band carries both languages at once, so its labels are written here
    # and not looked up at runtime. The words a Nepali speaker checks, though,
    # live in the dictionary and the translation worksheet, as nav.band.<key>.
    # The two must say the same thing: a label corrected in the worksheet and
    # not here would never reach the band, on every page of the site.
    words = band_words()
    if words:
        print("\n  WORDS DRIFTED -- the band and assets/i18n-strings.js disagree:")
        for w in words:
            print("    " + w)
        print("  Make NAV above say what the dictionary says, then run: tools/nav.py apply")
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
