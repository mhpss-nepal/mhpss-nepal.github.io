#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final sweep: key any element that holds prose and no block-level children.

Why a sweep rather than keying element by element: a paragraph containing
<b> or <em> must be keyed as ONE string including its markup. Keying the
text nodes around the markup splits a sentence into fragments, and a
translator handed "before" and "anything is collected for real" cannot
reassemble them -- Nepali word order is not English word order, so the
fragments cannot even be put back in the same sequence.

So the unit of translation is the smallest element that contains a whole
sentence, and it is keyed with data-i18n-html.

  python3 tools/key-prose.py <page> <key-prefix>
"""
import io
import json
import re
import sys

BLOCK = r"div|section|ul|ol|table|form|header|footer|nav|main|aside|h1|h2|h3|p|li|figure"
INLINE_OK = r"b|i|em|strong|code|br|a|span|small|sup|sub|abbr"


def sweep(path, prefix):
    raw = io.open(path, encoding="utf-8").read()

    # Mask <script> and <style> before touching anything. A script can contain
    # HTML inside a string literal -- '<div class="x">' + d.url + '</div>' --
    # and a sweep that does not mask them will "key" the inside of a JavaScript
    # expression and break the page. That happened on 16 Sep: a key landed
    # around ' + d.url + '.
    masked, vault = [], []
    pos = 0
    for m in re.finditer(r"<(script|style)\b[\s\S]*?</\1>", raw, re.I):
        masked.append(raw[pos:m.start()])
        masked.append("\x00VAULT%d\x00" % len(vault))
        vault.append(m.group(0))
        pos = m.end()
    masked.append(raw[pos:])
    s = "".join(masked)

    added = {}
    n = 0

    # elements that can hold a sentence
    # OUTERMOST FIRST. A banner like
    #     <div class="banner"><b>Lead.</b> Body sentence.</div>
    # is one message and must be one key. Keying the <b> first leaves the div
    # holding a keyed child, the sweep then skips the div, and the body
    # sentence is left loose -- which is exactly what happened on the first
    # attempt. Keying the div first empties it, so the inline pass finds
    # nothing left to key and cannot split the message.
    for tag in ("div", "label", "summary", "p", "li", "h1", "h2", "h3", "h4",
                "th", "td", "button", "b", "span"):
        # REVERSE order: a replacement changes the string length, so applying
        # matches front-to-back invalidates every later offset. Doing it
        # back-to-front keeps them all valid. Getting this wrong corrupted a
        # page on 16 Sep -- an insert landed inside an HTML comment and then
        # inside a <script> block.
        for m in reversed(list(re.finditer(r'<%s(\s[^>]*)?>((?:(?!<%s\b)[\s\S])*?)</%s>' % (tag, tag, tag), s))):
            opening, inner = m.group(1) or "", m.group(2)
            if "data-i18n" in opening:
                continue
            # skip if it contains a block-level child -- key the child instead
            if re.search(r"<(%s)\b" % BLOCK, inner):
                continue
            # and never key a container that holds interactive elements. Doing
            # so hands the translator a string full of onclick handlers and
            # data-url attributes, which they can silently break, and the whole
            # row gets rebuilt from the dictionary on every language switch.
            # Their LABELS are keyed individually by the later passes instead.
            # The exclusion applies to generic CONTAINERS -- a row of buttons
            # must not become one string. But a sentence with a link inside it
            # ("drop it into the <a>field inbox</a>, which turns...") IS one
            # translatable unit: Nepali word order moves the link, so the
            # sentence cannot be keyed in fragments around it.
            PROSE = ("p", "li", "td", "th", "h1", "h2", "h3", "h4", "b", "summary")

            # RULE 1, and it applies to EVERY tag, not a list of them.
            # An element that contains a form control can never become one
            # string: the engine fills the element, which destroys the
            # control inside it.
            #   This was written as two tag-specific rules and <label> was
            # in neither. The result: seventeen radio labels on the
            # self-report form were swept WITH their <input>, which would
            # have shipped a form for displaced people showing the markup
            # as text and with no radio buttons to press. Caught by filling
            # the form, not by reading the code. The gate now refuses it
            # too (see i18n-check.py), so there are two nets, and this is
            # the one that stops it being created.
            if re.search(r"<(input|select|textarea|button)\b", inner):
                continue

            # RULE 2: a link is different. A row of links is furniture and
            # must stay in fragments; a SENTENCE containing a link is one
            # translatable unit, because Nepali word order moves the link
            # and the sentence cannot be keyed in pieces around it.
            if tag not in PROSE and re.search(r"<a\b", inner):
                continue
            text = re.sub(r"<[^>]+>", "", inner).strip()
            if len(text) < 4 or not re.search(r"[A-Za-z]{3}", text):
                continue
            # skip anything already covered by a child key
            if "data-i18n" in inner:
                continue
            n += 1
            key = "%s.p%03d" % (prefix, n)
            added[key] = re.sub(r"\s+", " ", inner).strip()
            ish = " data-i18n-html" if re.search(r"<(%s)\b" % INLINE_OK, inner) else ""
            s = (s[:m.start()]
                 + "<%s%s data-i18n=\"%s\"%s></%s>" % (tag, opening, key, ish, tag)
                 + s[m.end():])

    for i, block in enumerate(vault):
        s = s.replace("\x00VAULT%d\x00" % i, block, 1)
    assert "\x00VAULT" not in s, "a masked script block was lost -- refusing to write"
    io.open(path, "w", encoding="utf-8").write(s)
    return added


if __name__ == "__main__":
    path, prefix = sys.argv[1], sys.argv[2]
    added = sweep(path, prefix)
    d = io.open("assets/i18n-strings.js", encoding="utf-8").read()
    block = "\n".join('    %s: %s,' % (json.dumps(k, ensure_ascii=False),
                                       json.dumps(v, ensure_ascii=False))
                      for k, v in sorted(added.items()))
    anchor = "    /* ---- the machine-translation notice ----"
    d = d.replace(anchor, "    /* ---- swept prose: %s ---- */\n%s\n\n%s" % (prefix, block, anchor), 1)
    io.open("assets/i18n-strings.js", "w", encoding="utf-8").write(d)
    print("  %s: %d prose blocks keyed" % (path, len(added)))
    for k in sorted(added)[:6]:
        print("    %-18s %s" % (k, added[k][:70]))
