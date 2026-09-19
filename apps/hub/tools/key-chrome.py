#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key the shared chrome on a page: the trial banner, the header bar and the
navigation links.

This exists because the chrome is identical on every page, so it should be
keyed identically on every page -- by a script, not by hand fifteen times.
The keys already live in the dictionary (banner.*, nav.*), so pages share
one copy of each string and a change to "Field inbox" lands everywhere.

  python3 tools/key-chrome.py form/index.html coordination/inbox.html ...
"""
import io
import re
import sys

NAV = {
    "hub": "nav.hub", "field forms": "nav.forms", "form list": "nav.forms",
    "coordination view": "nav.coordination", "field inbox": "nav.inbox",
    "access": "nav.access", "method": "nav.method",
    "who can see what": "nav.whoSees",
}


def key_page(path):
    s = io.open(path, encoding="utf-8").read()
    orig = s
    hits = []

    # ---- the red trial banner: its two spans, or a bare text node ----
    def banner(m):
        inner = m.group(2)
        # split the strong lead from the lighter tail, however it is marked up
        lead = re.match(r'\s*([^<]+)', inner)
        tail = re.search(r'<span[^>]*>(.*?)</span>', inner, re.S)
        parts = []
        if lead and lead.group(1).strip():
            parts.append('<span data-i18n="banner.trial"></span>')
            hits.append("banner.trial")
        if tail:
            parts.append('<span data-i18n="banner.trialSub"></span>')
            hits.append("banner.trialSub")
        return m.group(1) + "".join(parts) + m.group(3) if parts else m.group(0)

    s = re.sub(r'(<div[^>]*(?:class="(?:trial|synth)"|background:#d03b3b)[^>]*>)(.*?)(</div>)',
               banner, s, count=1, flags=re.S)

    # ---- the header bar ----
    m = re.search(r'<div class="brand">(.*?)</div>', s, re.S)
    if m and "data-i18n" not in m.group(0):
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
        k = NAV.get(txt.lower())
        if k:
            s = s.replace(m.group(0), '<div class="brand" data-i18n="%s"></div>' % k, 1)
            hits.append(k)
        else:
            # page-specific title: give it a key derived from the page
            base = "page." + re.sub(r"[^a-z0-9]+", "", path.split("/")[-1].replace(".html", "").lower())
            s = s.replace(m.group(0), '<div class="brand" data-i18n="%s.brand"></div>' % base, 1)
            hits.append(base + ".brand  [NEW: " + txt + "]")

    m = re.search(r'<div class="sub">(.*?)</div>', s, re.S)
    if m and "data-i18n" not in m.group(0):
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
        base = "page." + re.sub(r"[^a-z0-9]+", "", path.split("/")[-1].replace(".html", "").lower())
        s = s.replace(m.group(0), '<div class="sub" data-i18n="%s.sub"></div>' % base, 1)
        hits.append(base + ".sub  [NEW: " + txt + "]")

    # ---- nav links in the header ----
    def nav(m):
        opening, label = m.group(1), m.group(2)
        if "data-i18n" in opening:
            return m.group(0)
        clean = label.replace("←", "").replace("→", "").strip()
        k = NAV.get(clean.lower())
        if not k:
            return m.group(0)
        hits.append(k)
        arrow = "← " if "←" in label else ""
        return "%s%s<span data-i18n=\"%s\"></span>%s" % (
            opening, arrow, k, m.group(3))

    top = re.search(r'(<div class="top">)(.*?)(</div>\s*\n)', s, re.S)
    if top:
        block = re.sub(r'(<a\b[^>]*>)([^<]+)(</a>)', nav, top.group(2))
        s = s[:top.start(2)] + block + s[top.end(2):]

    if s != orig:
        io.open(path, "w", encoding="utf-8").write(s)
    return hits


if __name__ == "__main__":
    for p in sys.argv[1:]:
        h = key_page(p)
        print("  %-28s %s" % (p, ", ".join(h) if h else "nothing to key"))
