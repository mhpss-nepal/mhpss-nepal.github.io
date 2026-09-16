#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MHPSS Nepal -- the affected-area map: build it, and keep it true
---------------------------------------------------------------------
The map on referral-directory.html and the list of declared palikas on
flood-response.html are generated from ONE list, below, and checked against
it by the deploy guard. A palika drawn as declared that is not on the
Government's list -- or one on the list and not drawn -- is exactly the kind
of public error nobody notices by looking.

  build <npl_admin3.geojson>   regenerate both blocks from OCHA COD-AB
                               (cloud-side: needs mapshaper on PATH)
  check                        parse the two pages and compare them with
                               the list (runs anywhere, no GIS libraries)

WHAT "AFFECTED AREA" MEANS HERE -- decided 16 September 2026
  Declared palikas: the Government's declaration of disaster crisis areas.
    Decision of the Ministry of Home Affairs, published in the Nepal Gazette
    on 13 Bhadra 2083, under section 32(1) of the Disaster Risk Reduction and
    Management Act 2074, for three months: fifteen local levels in five
    districts. Read from the reports of that notice in Prasashan and
    Onlinekhabar (29 Aug 2026); the Gazette notice itself was not reachable.
    The Nepali names below are as those reports print them.
  Affected districts: the six in which the declaration falls plus Chitwan,
    which NDRRMA Situation Report #01 (1 Sep 2026) lists as moderately
    affected, and which UNDP (citing the Flash Appeal) counts among six
    districts and 17 municipalities. The two municipalities beyond the
    Gazette's fifteen are not named in any source read, so none is drawn.
  Context districts: Kathmandu and Nawalparasi (Bardaghat Susta East), where
    the response's own site list (assets/codes.js) records MHPSS activity
    outside the declared area. Drawn with a dashed boundary, never as
    affected. Sindhupalchok is NOT drawn: its one reported site carries the
    open question D-S23 in codes.js -- whether that record belongs to the flood
    response at all -- and a map should not answer an open question.

Boundaries: OCHA COD-AB Nepal v02 (Survey Department of Nepal, UN RCO
Nepal), valid from 2024-03-14, via HDX dataset cod-ab-npl, CC BY-IGO.
Palika level only -- never a point, never a site (claude/access-model.md).
"""
import io, json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REFPAGE = os.path.join(ROOT, "referral-directory.html")
FLOODPAGE = os.path.join(ROOT, "flood-response.html")

# (COD-AB adm3_pcode, COD-AB name, Nepali name as printed in the reports of the Gazette notice)
DECLARED = [
    ("NP0329401", "Aamachhodingmo",  "आमाछोदिङमो गाउँपालिका"),
    ("NP0329402", "Gosaikunda",      "गोसाइँकुण्ड गाउँपालिका"),
    ("NP0329404", "Kalika",          "कालिका गाउँपालिका"),
    ("NP0329403", "Uttargaya",       "उत्तरगया गाउँपालिका"),
    ("NP0328302", "Belkotgadhi",     "बेलकोटगढी नगरपालिका"),
    ("NP0328301", "Bidur",           "विदुर नगरपालिका"),
    ("NP0328402", "Kispang",         "किस्पाङ गाउँपालिका"),
    ("NP0328403", "Tarakeshwor",     "तारकेश्वर गाउँपालिका"),
    ("NP0330408", "Benighat Rorang", "बेनीघाट रोराङ गाउँपालिका"),
    ("NP0330409", "Gajuri",          "गजुरी गाउँपालिका"),
    ("NP0330410", "Galchhi",         "गल्छी गाउँपालिका"),
    ("NP0330407", "Siddhalek",       "सिद्धलेक गाउँपालिका"),
    ("NP0436409", "Gandaki",         "गण्डकी गाउँपालिका"),
    ("NP0440405", "Aanbu Khaireni",  "आँबुखैरेनी गाउँपालिका"),
    ("NP0440406", "Devghat",         "देवघाट गाउँपालिका"),
]
# (adm2_pcode, label, role) in the order the list is read
DISTRICTS = [
    ("NP0329", "Rasuwa",           "affected"),
    ("NP0328", "Nuwakot",          "affected"),
    ("NP0330", "Dhading",          "affected"),
    ("NP0436", "Gorkha",           "affected"),
    ("NP0440", "Tanahun",          "affected"),
    ("NP0335", "Chitwan",          "affected"),
    ("NP0327", "Kathmandu",        "context"),
    ("NP0447", "Nawalparasi East", "context"),
]
# Label nudges, in percent of the drawing, where two district centres sit so
# close that the names collide on a phone (measured at 390px, 16 Sep 2026).
NUDGE = {"NP0328": (3.5, -2.5), "NP0330": (-4.0, 1.5)}
W = 1000  # viewBox width; the height follows the shape

def district_of(pcode):
    return pcode[:6]

# ---------------------------------------------------------------- check
def check():
    fails = []
    print("MHPSS Nepal -- the affected-area map")
    codes = [p for p, _, _ in DECLARED]
    dists = set(district_of(p) for p in codes)
    print("  declared list: %d palikas in %d districts" % (len(codes), len(dists)))
    if len(codes) != 15 or len(set(codes)) != 15:
        fails.append("the declared list must hold 15 distinct palikas (Gazette, 13 Bhadra 2083)")
    if len(dists) != 5:
        fails.append("the declared palikas must fall in 5 districts")
    affected = set(d for d, _, r in DISTRICTS if r == "affected")
    for p in codes:
        if district_of(p) not in affected:
            fails.append("%s is declared but its district is not drawn as affected" % p)
    # the Gazette's own word for each palika must agree with COD-AB's code:
    # municipalities are 3xx, rural municipalities 4xx
    for p, en, np in DECLARED:
        kind = p[6]
        if ("नगरपालिका" in np) != (kind == "3"):
            fails.append("%s %s: Gazette type and COD-AB code disagree" % (p, en))

    for path, label, pat in (
        (REFPAGE, "referral-directory.html map", r'<path class="pal decl"[^>]*data-pcode="(NP\d{7})"'),
        (REFPAGE, "referral-directory.html list", r'<li class="decl" data-pcode="(NP\d{7})"'),
        (FLOODPAGE, "flood-response.html list", r'<li data-pcode="(NP\d{7})"'),
    ):
        if not os.path.exists(path):
            fails.append("%s is missing" % os.path.basename(path))
            continue
        page = io.open(path, encoding="utf-8").read()
        block = re.search(r"<!--MAP:(svg|list|chips)-->(.*?)<!--/MAP-->", page, re.S)
        found = re.findall(pat, page)
        if not found:
            fails.append("%s: no declared palikas found -- the block is missing or was hand-edited" % label)
            continue
        if sorted(found) != sorted(codes):
            extra = sorted(set(found) - set(codes)); miss = sorted(set(codes) - set(found))
            fails.append("%s: drawn %d, list %d (extra %s, missing %s)"
                         % (label, len(found), len(codes), extra, miss))
        else:
            print("  %-32s %d declared palikas, all on the list" % (label, len(found)))
    if fails:
        print("\n  DRIFTED:")
        for f in fails:
            print("    " + f)
        print("\n  Regenerate with: tools/map-build.py build <npl_admin3.geojson>")
        return 1
    print("\n  True: the map and the list draw exactly the Government's declared palikas.")
    return 0

# ---------------------------------------------------------------- build
def mapshaper(src, outdir):
    keep = ",".join('"%s"' % d for d, _, _ in DISTRICTS)
    pal = os.path.join(outdir, "pal.geojson"); dist = os.path.join(outdir, "dist.geojson")
    cmd = ["mapshaper", src,
           "-filter", "[%s].indexOf(adm2_pcode) > -1" % keep,
           "-filter-fields", "adm3_pcode,adm3_name,adm2_pcode,adm2_name",
           "-simplify", "4%", "keep-shapes", "-clean",
           "-o", "format=geojson", "precision=0.00001", pal,
           "-dissolve", "adm2_pcode", "copy-fields=adm2_name",
           "-o", "format=geojson", "precision=0.00001", dist]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.load(open(pal)), json.load(open(dist))

def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return geom["coordinates"]

def build(src):
    tmp = tempfile.mkdtemp()
    pal, dist = mapshaper(src, tmp)
    xs, ys = [], []
    for f in dist["features"]:
        for poly in rings(f["geometry"]):
            for ring in poly:
                for x, y in ring:
                    xs.append(x); ys.append(y)
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    pad = 8
    sx = (W - 2 * pad) / ((lon1 - lon0) * k)
    H = int(round((lat1 - lat0) * sx + 2 * pad))
    def P(x, y):
        return ((x - lon0) * k * sx + pad, (lat1 - y) * sx + pad)
    def d_of(geom):
        # Whole units in a 1000-wide box are under half a pixel at any size
        # the page draws it, and relative moves keep the page light: the
        # absolute points are rounded first and the moves taken between the
        # rounded points, so rounding error cannot accumulate along a border.
        out = []
        for poly in rings(geom):
            for ring in poly:
                pts = []
                for x, y in ring[:-1]:
                    q = tuple(int(round(v)) for v in P(x, y))
                    if not pts or q != pts[-1]:
                        pts.append(q)
                if len(pts) < 3:
                    continue
                seg = ["M%d %d" % pts[0]]
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    seg.append("l%d %d" % (x1 - x0, y1 - y0))
                out.append("".join(seg).replace(" -", "-") + "z")
        return "".join(out)
    declared = {p: (en, np) for p, en, np in DECLARED}
    role = {d: r for d, _, r in DISTRICTS}
    label = {d: l for d, l, _ in DISTRICTS}

    svg = ['<svg viewBox="0 0 %d %d" role="img" data-i18n-aria="map.aria" aria-label="Map of the affected districts">' % (W, H),
           '  <g class="pals">']
    for f in sorted(pal["features"], key=lambda f: f["properties"]["adm3_pcode"]):
        p = f["properties"]["adm3_pcode"]; dcode = f["properties"]["adm2_pcode"]
        cls = "pal decl" if p in declared else ("pal ctx" if role.get(dcode) == "context" else "pal")
        svg.append('    <path class="%s" data-pcode="%s" d="%s"><title>%s</title></path>'
                   % (cls, p, d_of(f["geometry"]), f["properties"]["adm3_name"]))
    svg.append('  </g>')
    svg.append('  <g class="dists">')
    cent = {}
    for f in sorted(dist["features"], key=lambda f: f["properties"]["adm2_pcode"]):
        dcode = f["properties"]["adm2_pcode"]
        cls = "dist ctx" if role.get(dcode) == "context" else "dist"
        svg.append('    <path class="%s" data-dcode="%s" d="%s"/>' % (cls, dcode, d_of(f["geometry"])))
        # label at the area-weighted centre of the largest ring, in percent of the box
        best = max((poly for poly in rings(f["geometry"])), key=lambda poly: len(poly[0]))
        pts = [P(x, y) for x, y in best[0]]
        a = cx = cy = 0.0
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
        a *= 0.5
        cent[dcode] = (cx / (6 * a), cy / (6 * a)) if a else pts[0]
    svg.append('  </g>')
    svg.append('</svg>')
    labs = []
    for dcode, (x, y) in sorted(cent.items()):
        cls = "dlab ctx" if role.get(dcode) == "context" else "dlab"
        nx, ny = NUDGE.get(dcode, (0, 0))
        labs.append('<span class="%s" style="left:%.1f%%;top:%.1f%%" data-i18n-skip>%s</span>'
                    % (cls, 100 * x / W + nx, 100 * y / H + ny, label[dcode]))
    svg_block = ('<div class="mapwrap">\n' + "\n".join(svg) + "\n" + "\n".join(labs) + "\n</div>")

    # the list beside the map, grouped by district
    li = ['<ul class="palist">']
    for dcode, dl, r in DISTRICTS:
        rows = [(p, en, np) for p, en, np in DECLARED if district_of(p) == dcode]
        if not rows:
            continue
        li.append('  <li class="dhrow"><span class="dh" data-i18n-skip>%s</span></li>' % dl)
        for p, en, np in rows:
            ty = "map.type.mun" if p[6] == "3" else "map.type.rm"
            li.append('  <li class="decl" data-pcode="%s"><span class="en" data-i18n-skip>%s</span>'
                      '<span class="ty" data-i18n="%s"></span>'
                      '<span class="np" lang="ne" data-i18n-skip>%s</span></li>' % (p, en, ty, np))
    li.append('</ul>')
    list_block = "\n".join(li)

    # the compact list on Flood Response
    ch = ['<ul class="declist">']
    for dcode, dl, r in DISTRICTS:
        rows = [(p, en, np) for p, en, np in DECLARED if district_of(p) == dcode]
        if not rows:
            continue
        ch.append('  <li class="dg"><b data-i18n-skip>%s</b><ul>' % dl)
        for p, en, np in rows:
            ch.append('    <li data-pcode="%s"><span data-i18n-skip>%s</span> <span class="np" lang="ne" data-i18n-skip>%s</span></li>'
                      % (p, en, np))
        ch.append('  </ul></li>')
    ch.append('</ul>')
    chips_block = "\n".join(ch)

    def put(path, name, block):
        s = io.open(path, encoding="utf-8").read()
        pat = re.compile(r"<!--MAP:%s-->.*?<!--/MAP-->" % name, re.S)
        if not pat.search(s):
            raise SystemExit("%s has no <!--MAP:%s--> marker" % (os.path.basename(path), name))
        s = pat.sub(lambda m: "<!--MAP:%s-->\n%s\n<!--/MAP-->" % (name, block), s)
        io.open(path, "w", encoding="utf-8").write(s)
    put(REFPAGE, "svg", svg_block)
    put(REFPAGE, "list", list_block)
    put(FLOODPAGE, "chips", chips_block)
    print("map: %dx%d, %d palikas drawn, %d declared; path data %d bytes"
          % (W, H, len(pal["features"]), len(DECLARED), len("".join(svg))))
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "build":
        sys.exit(build(sys.argv[2]))
    sys.exit(check())
