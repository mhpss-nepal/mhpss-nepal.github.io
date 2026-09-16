#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 Bilingual gate — MHPSS Nepal hub
================================================================================
Translation is not automatic; a person writes the Nepali. What this makes
automatic is that a gap cannot ship quietly.

It reports four things and fails the build on the first two:

  1. a key used in a page with no English string           -> FAIL
  2. a migrated page with any untranslated key             -> FAIL
  3. visible text on a migrated page that carries no key   -> FAIL
     (this is the one that stops the two versions drifting: new English
      prose cannot be added to a finished page without a key)
  4. pages not yet migrated, with a word count             -> report only

  --worksheet   also writes tools/i18n-worksheet.csv: every key, the
                English, and an empty Nepali column, for the translator.
                Existing Nepali is carried through so nobody retypes it.
  --import FILE reads that worksheet back and rewrites the `ne` block of
                assets/i18n-strings.js. Refuses to touch English.

Which pages are enforced is listed in tools/i18n-pages.txt, so migration
can be incremental without turning the gate off.

Run from the repository root:  python3 tools/i18n-check.py
================================================================================
"""
import csv
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRINGS = os.path.join(ROOT, "assets", "i18n-strings.js")
PAGELIST = os.path.join(ROOT, "tools", "i18n-pages.txt")
WORKSHEET = os.path.join(ROOT, "tools", "i18n-worksheet.csv")

KEY_ATTRS = ["data-i18n", "data-i18n-ph", "data-i18n-aria",
             "data-i18n-alt", "data-i18n-title"]

# Text that is the same in every language -- a domain, a code, a proper noun --
# must SAY SO with data-i18n-skip. It is not assumed: text nobody has thought
# about is exactly what the gate exists to catch.
SKIP_ATTR = "data-i18n-skip"


# ---------------------------------------------------------------- strings
def load_strings():
    """Read the en/ne dictionaries out of the JS file without running it."""
    src = open(STRINGS, encoding="utf-8").read()
    out = {}
    for lang in ("en", "ne"):
        m = re.search(r"\n  " + lang + r":\s*\{(.*?)\n  \}", src, re.S)
        if not m:
            out[lang] = {}
            continue
        body = m.group(1)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        body = re.sub(r"^\s*//.*$", "", body, flags=re.M)
        d = {}
        for mm in re.finditer(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', body):
            d[unescape(mm.group(1))] = unescape(mm.group(2))
        out[lang] = d
    return out


def unescape(s):
    """Undo JS string escapes without touching UTF-8.

    The obvious .encode().decode("unicode_escape") reads UTF-8 bytes as
    Latin-1, so an em-dash comes out as three mojibake characters -- and
    this text goes to a human translator, so that would be handed over as
    if it were the English.
    """
    out, i = [], 0
    simple = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t",
              "r": "\r", "b": "\b", "f": "\f", "'": "'", "`": "`"}
    while i < len(s):
        c = s[i]
        if c != "\\":
            out.append(c); i += 1; continue
        if i + 1 >= len(s):
            out.append(c); break
        n = s[i + 1]
        if n == "u" and i + 5 < len(s) + 1:
            try:
                out.append(chr(int(s[i + 2:i + 6], 16))); i += 6; continue
            except ValueError:
                pass
        if n == "x" and i + 3 < len(s) + 1:
            try:
                out.append(chr(int(s[i + 2:i + 4], 16))); i += 4; continue
            except ValueError:
                pass
        out.append(simple.get(n, n)); i += 2
    return "".join(out)


# ------------------------------------------------------------------ pages
def load_pages():
    """{relpath: 'enforced'|'pending'}; anything unlisted counts as pending."""
    state = {}
    if os.path.exists(PAGELIST):
        for line in open(PAGELIST, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            state[parts[0]] = parts[1] if len(parts) > 1 else "enforced"
    found = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "tools")]
        for f in files:
            if f.endswith(".html"):
                found.append(os.path.relpath(os.path.join(base, f), ROOT))
    return {p: state.get(p, "pending") for p in sorted(found)}


class Scan(HTMLParser):
    """Collect the keys a page uses, and any visible text not under a key."""
    SKIP = {"script", "style", "template", "noscript", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.keys = []
        self.loose = []
        self._skip = 0
        self._covered = 0
        self._stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        has_key = any(k in a for k in KEY_ATTRS) or SKIP_ATTR in a
        for k in KEY_ATTRS:
            if k in a and a[k]:
                self.keys.append(a[k])
        void = tag in ("br", "img", "input", "hr", "meta", "link", "source", "area")
        if not void:
            self._stack.append((tag, has_key, tag in self.SKIP))
            if tag in self.SKIP:
                self._skip += 1
            if has_key:
                self._covered += 1

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                _, has_key, skipped = self._stack.pop(i)
                if skipped:
                    self._skip = max(0, self._skip - 1)
                if has_key:
                    self._covered = max(0, self._covered - 1)
                break

    def handle_data(self, data):
        if self._skip or self._covered:
            return
        t = data.strip()
        if not t or len(t) < 3:
            return
        # punctuation, separators and bare numbers are not prose
        if re.fullmatch(r"[\W\d\s·—–|/•:,.()\[\]{}+\-*=<>&;#%'\"]+", t):
            return
        self.loose.append(re.sub(r"\s+", " ", t)[:90])


def scan(path):
    s = open(os.path.join(ROOT, path), encoding="utf-8").read()
    p = Scan()
    try:
        p.feed(s)
    except Exception:
        pass
    words = len(re.sub(r"\s+", " ", re.sub(
        r"<[^>]+>", " ",
        re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S))).split())
    return p.keys, p.loose, words


# ------------------------------------------------------------- worksheet
def write_worksheet(d):
    rows = []
    for k in sorted(d["en"]):
        rows.append({"key": k, "english": d["en"][k], "nepali": d["ne"].get(k, "")})
    with open(WORKSHEET, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["key", "english", "nepali"])
        w.writeheader()
        w.writerows(rows)
    done = sum(1 for r in rows if r["nepali"].strip())
    print("  worksheet written: tools/i18n-worksheet.csv")
    print("    %d strings, %d already translated, %d to do"
          % (len(rows), done, len(rows) - done))
    print("    Give this file to the translator. Only the 'nepali' column is filled in.")
    return 0


def import_worksheet(path, d):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    ne, skipped = {}, 0
    for r in rows:
        k = (r.get("key") or "").strip()
        v = (r.get("nepali") or "").strip()
        if not k:
            continue
        if k not in d["en"]:
            skipped += 1
            continue
        if v:
            ne[k] = v
    src = open(STRINGS, encoding="utf-8").read()
    block = ",\n".join('    %s: %s' % (json.dumps(k, ensure_ascii=False),
                                       json.dumps(ne[k], ensure_ascii=False))
                       for k in sorted(ne))
    new = re.sub(r"(\n  ne:\s*\{)(.*?)(\n  \})",
                 lambda m: m.group(1) + ("\n" + block + "\n" if block else "\n") + m.group(3),
                 src, count=1, flags=re.S)
    if new == src:
        print("  could not find the `ne` block to rewrite — nothing changed")
        return 1
    open(STRINGS, "w", encoding="utf-8").write(new)
    print("  imported %d Nepali strings into assets/i18n-strings.js" % len(ne))
    if skipped:
        print("  %d rows ignored: their key is not in the English dictionary" % skipped)
    print("  English was not touched.")
    return 0


# ------------------------------------------------------------------- main
def main(argv):
    d = load_strings()
    if "--worksheet" in argv:
        return write_worksheet(d)
    if "--import" in argv:
        i = argv.index("--import")
        if i + 1 >= len(argv):
            print("  --import needs a file path")
            return 2
        return import_worksheet(argv[i + 1], d)

    pages = load_pages()
    fail = []
    print("MHPSS Nepal — bilingual gate")
    print("  English strings: %d   Nepali strings: %d" % (len(d["en"]), len(d["ne"])))
    print()

    enforced = [p for p, st in pages.items() if st == "enforced"]
    keyed = [p for p, st in pages.items() if st == "keyed"]
    pending = [p for p, st in pages.items() if st not in ("enforced", "keyed")]

    def check(p, require_nepali):
        keys, loose, words = scan(p)
        no_en = [k for k in keys if k not in d["en"]]
        no_ne = [k for k in keys if k in d["en"] and not d["ne"].get(k, "").strip()]
        bad = bool(no_en) or bool(loose) or (require_nepali and bool(no_ne))
        note = ""
        if no_ne and not require_nepali:
            note = "  (%d awaiting Nepali)" % len(set(no_ne))
        print("    %-34s %s  %d keys%s"
              % (p, "FAIL" if bad else "OK  ", len(set(keys)), note))
        if no_en:
            fail.append((p, "keys used here with no English string", sorted(set(no_en))[:8]))
        if loose:
            fail.append((p, "visible text carrying no key -- add one or the two "
                            "versions will drift", loose[:8]))
        if require_nepali and no_ne:
            fail.append((p, "keys with no Nepali string", sorted(set(no_ne))[:8]))

    print("  ENFORCED — keyed and fully translated")
    if not enforced:
        print("    (none yet)")
    for p in enforced:
        check(p, True)

    print()
    print("  KEYED — no loose English allowed; Nepali still awaited")
    if not keyed:
        print("    (none yet)")
    for p in keyed:
        check(p, False)

    print()
    print("  NOT YET MIGRATED")
    tot = 0
    for p in pending:
        _, _, words = scan(p)
        tot += words
        print("    %-34s %5d words" % (p, words))
    print("    %-34s %5d words to key up" % ("TOTAL", tot))

    if fail:
        print()
        print("  " + "-" * 66)
        for p, what, items in fail:
            print("  FAIL  %s" % p)
            print("        %s:" % what)
            for it in items:
                print("          - %s" % it)
        print("  " + "-" * 66)
        print("  The gate is closed. Nothing is published until these are resolved.")
        return 1

    print()
    print("  Gate open: every enforced page is fully keyed and fully translated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
