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

  build <npl_admin3.geojson>   regenerate both blocks, and the interactive
                               map's boundaries (assets/referral-geo.js),
                               from OCHA COD-AB (cloud-side: needs mapshaper)
  geo <npl_admin3.geojson>     regenerate assets/referral-geo.js only
  check                        parse the two pages, the boundaries file and
                               the hospitals, and compare them with the list
                               (runs anywhere, no GIS libraries)

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
Palika level only -- never a point, never a site, as the access model says.
"""
import io, json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REFPAGE = os.path.join(ROOT, "referral-directory.html")
FACILITIES = os.path.join(ROOT, "assets", "referral-facilities.js")
FINDER = os.path.join(ROOT, "assets", "referral-find.js")
FLOODPAGE = os.path.join(ROOT, "flood-response.html")
GEO = os.path.join(ROOT, "assets", "referral-geo.js")

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
# District names in Nepali, as the Gazette notice's report (Prasashan, 29 Aug
# 2026), the Department of Health Services' flood report no. 19 and Bharatpur
# Hospital's own website print them. Nawalparasi East has no Nepali name in a
# source read, so it stays in English on the Nepali page.
DISTRICT_NE = {"NP0329": "रसुवा", "NP0328": "नुवाकोट", "NP0330": "धादिङ", "NP0436": "गोरखा",
               "NP0440": "तनहुँ", "NP0335": "चितवन", "NP0327": "काठमाडौं"}
GEO_SIMPLIFY_M = 30   # the interactive map: boundaries simplified to 30 metres

# Label nudges, in percent of the drawing, where two district centres sit so
# close that the names collide on a phone (measured at 390px, 16 Sep 2026).
NUDGE = {"NP0328": (3.5, -2.5), "NP0330": (-4.0, 1.5)}
W = 1000  # viewBox width; the height follows the shape

GEO_DATA = None

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
    global GEO_DATA
    geo = check_geo()
    if isinstance(geo, list):
        fails += geo
    else:
        fails += geo[0]
        GEO_DATA = (geo[1], geo[2])
    fails += check_facilities()
    if fails:
        print("\n  DRIFTED:")
        for f in fails:
            print("    " + f)
        print("\n  Regenerate with: tools/map-build.py build <npl_admin3.geojson>")
        return 1
    print("\n  True: the map and the list draw exactly the Government's declared palikas.")
    return 0

# ------------------------------------------------- the hospitals and helplines
# The Referral Directory's official-source tier (assets/referral-facilities.js)
# is drawn on this map, so it is checked with it. What the check holds it to:
# every tag quoted from a named page with a date; a place the map can draw, or
# "outside" said out loud; no person named; and the finder's own district
# table the same as this file's, so a district added here cannot be missing
# from the District filter.
ACTIVITY = {"PFA", "CNS-I", "CNS-G", "PSED", "RECR", "CFS", "SPEC", "MEDS", "REF", "HELP",
            "IEC", "ASMT", "COORD", "TRAIN", "STAFF"}          # assets/codes.js ACTIVITIES
# assets/codes.js 0.3.0 CADRES and MODALITIES, current codes only: a code
# retired on 17 Sep 2026 (SPSC, INP, OUT) still reads on an old record, but a
# hospital tagged today is tagged with the list as it stands
CADRE = {"PSYT", "CPSY", "PSY", "PSC", "SW", "HW", "VOL", "OTH"}
MODE = {"HC", "COM", "FAC", "TEL", "OTH"}

def check_facilities():
    fails = []
    if not os.path.exists(FACILITIES):
        return ["assets/referral-facilities.js is missing"]
    raw = io.open(FACILITIES, encoding="utf-8").read()
    m = re.search(r"window\.REFERRAL_FACILITIES\s*=\s*(\{.*\})\s*;\s*$", raw, re.S)
    if not m:
        return ["referral-facilities.js: not one JSON object after window.REFERRAL_FACILITIES ="]
    try:
        data = json.loads(m.group(1))
    except ValueError as e:
        return ["referral-facilities.js is not strict JSON: %s" % e]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("read", ""))):
        fails.append("referral-facilities.js: 'read' must be the date the pages were read, YYYY-MM-DD")
    page = io.open(REFPAGE, encoding="utf-8").read()
    drawn = set(re.findall(r'<path class="pal[^"]*" data-pcode="(NP\d{7})"', page))
    adm2 = set(d for d, _, _ in DISTRICTS)
    ids = set()
    person = re.compile(r"(?<![A-Za-z])(Dr|Prof)\.?\s+[A-Z]|डा\.\s*\S|प्रा\.\s*\S")
    for e in data.get("entries", []):
        eid = e.get("id", "?")
        where = "referral-facilities.js %s" % eid
        if eid in ids:
            fails.append("%s: id used twice" % where)
        ids.add(eid)
        if e.get("kind") not in ("hospital", "helpline"):
            fails.append("%s: kind must be hospital or helpline" % where)
        if not (e.get("name") or {}).get("en"):
            fails.append("%s: no English name" % where)
        srcs = e.get("sources") or []
        quotes = e.get("quotes") or []
        if not srcs:
            fails.append("%s: no source page" % where)
        for s in srcs:
            if not str(s.get("url", "")).startswith("https://"):
                fails.append("%s: a source is not an https address" % where)
        for q in quotes:
            if not isinstance(q.get("src"), int) or not (0 <= q["src"] < len(srcs)):
                fails.append("%s: a quote points at no source" % where)
            if not str(q.get("text", "")).strip():
                fails.append("%s: an empty quote" % where)
        for ph in e.get("phones") or []:
            if not isinstance(ph.get("src"), int) or not (0 <= ph["src"] < len(srcs)):
                fails.append("%s: a phone number points at no source" % where)
        for field, allowed in (("services", ACTIVITY), ("cadres", CADRE), ("modes", MODE)):
            for code, qi in (e.get(field) or {}).items():
                if code not in allowed:
                    fails.append("%s: %s code %s is not in codes.js" % (where, field, code))
                qis = qi if isinstance(qi, list) else [qi]
                if not qis or any(not isinstance(x, int) or not (0 <= x < len(quotes)) for x in qis):
                    fails.append("%s: %s %s is not backed by a quote" % (where, field, code))
        if not (e.get("services") or {}):
            fails.append("%s: lists no service" % where)
        dist, pc = e.get("district"), e.get("pcode")
        if e.get("kind") == "helpline":
            if dist or pc:
                fails.append("%s: a helpline has no place on the map" % where)
            if "TEL" not in (e.get("modes") or {}):
                fails.append("%s: a helpline is reached by telephone" % where)
        else:
            if dist == "outside":
                if not e.get("outside"):
                    fails.append("%s: outside the map, but not said where" % where)
                if pc:
                    fails.append("%s: outside the map cannot carry a palika drawn on it" % where)
            elif dist not in adm2:
                fails.append("%s: district %s is not drawn on the map" % (where, dist))
            if pc and pc not in drawn:
                fails.append("%s: palika %s is not drawn on the map" % (where, pc))
            if pc and dist and dist != "outside" and pc[:6] != dist:
                fails.append("%s: palika %s is not in district %s" % (where, pc, dist))
        pin = e.get("pin")
        if e.get("kind") == "hospital":
            if not isinstance(pin, dict):
                fails.append("%s: a hospital needs a pin (its location)" % where)
            else:
                la, lo = pin.get("lat"), pin.get("lon")
                if not all(isinstance(v, (int, float)) for v in (la, lo)) or not (26 < la < 31 and 80 < lo < 89):
                    fails.append("%s: pin is not a latitude/longitude in Nepal" % where)
                elif not re.match(r"^(node|way|relation)/\d+$", str(pin.get("osm", ""))):
                    fails.append("%s: pin has no OpenStreetMap feature it was read from" % where)
                elif not re.match(r"^\d{4}-\d{2}-\d{2}$", str(pin.get("read", ""))):
                    fails.append("%s: pin has no date it was read" % where)
                elif GEO_DATA is not None:
                    g, pal = GEO_DATA
                    pp = pin.get("pcode")
                    if pp not in pal:
                        fails.append("%s: pin palika %s has no boundary in referral-geo.js" % (where, pp))
                    elif not inside(g, pal[pp], lo, la):
                        fails.append("%s: the pin is not inside %s, the palika it names" % (where, pp))
                    elif pc and pp != pc:
                        fails.append("%s: the pin falls in %s but the address names %s" % (where, pp, pc))
                    elif dist not in (None, "outside") and pp[:6] != dist:
                        fails.append("%s: the pin falls outside district %s" % (where, dist))
                    elif dist == "outside" and pal[pp].get("dn") != e.get("outside"):
                        fails.append("%s: the pin falls in %s, not in %s" % (where, pal[pp].get("dn"), e.get("outside")))
                    sm = pin.get("site_map")
                    if sm:
                        dy = (la - sm["lat"]) * 111320
                        dx = (lo - sm["lon"]) * 111320 * math.cos(math.radians(la))
                        if math.hypot(dx, dy) > 30:
                            fails.append("%s: the pin is %.0f m from the map on the hospital's own website" % (where, math.hypot(dx, dy)))
        elif pin:
            fails.append("%s: a helpline has no pin" % where)
        text = json.dumps(e, ensure_ascii=False)
        if person.search(text):
            fails.append("%s: looks like a person is named (Dr/Prof) -- hospitals are listed, never people" % where)
    for n in data.get("not_listed", []):
        if n.get("why") not in ("no-psychiatry", "unreachable"):
            fails.append("referral-facilities.js not_listed %s: reason must be no-psychiatry or unreachable" % n.get("name"))
    if os.path.exists(FINDER):
        fj = io.open(FINDER, encoding="utf-8").read()
        table = re.findall(r'\["(NP\d{4})",\s*"([^"]+)"\]', fj.split("var DIST_NAME", 1)[0])
        if [(d, l) for d, l, _ in DISTRICTS] != table:
            fails.append("referral-find.js DIST table differs from DISTRICTS in tools/map-build.py")
    else:
        fails.append("assets/referral-find.js is missing")
    if not fails:
        print("  %-32s %d entries, every tag quoted, every place drawable, %d pins inside their palikas"
              % ("referral-facilities.js", len(data.get("entries", [])), sum(1 for e in data.get("entries", []) if e.get("pin"))))
    return fails

# ------------------------------------------------ the interactive map's data
def load_geo():
    raw = io.open(GEO, encoding="utf-8").read()
    m = re.search(r"window\.REFERRAL_GEO\s*=\s*(\{.*\})\s*;\s*$", raw, re.S)
    if not m:
        raise ValueError("not one JSON object after window.REFERRAL_GEO =")
    return json.loads(m.group(1))

def geo_rings(g, shape):
    """TopoJSON-style arcs -> [[ring of (lon, lat)], ...] per polygon."""
    if "_abs" not in g:
        sx, sy = g["transform"]["scale"]; tx, ty = g["transform"]["translate"]
        out = []
        for arc in g["arcs"]:
            x = y = 0; pts = []
            for dx, dy in arc:
                x += dx; y += dy
                pts.append((x * sx + tx, y * sy + ty))
            out.append(pts)
        g["_abs"] = out
    def arc(i):
        return g["_abs"][i] if i >= 0 else list(reversed(g["_abs"][~i]))
    def ring(ix):
        pts = []
        for i in ix:
            a = arc(i)
            pts.extend(a if not pts else a[1:])
        return pts
    polys = [shape["a"]] if shape["t"] == "Polygon" else shape["a"]
    return [[ring(r) for r in poly] for poly in polys]

def inside(g, shape, lon, lat):
    hit = False
    for poly in geo_rings(g, shape):
        for pts in poly:
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
                if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                    hit = not hit
    return hit

def check_geo():
    fails = []
    if not os.path.exists(GEO):
        return ["assets/referral-geo.js is missing -- run: tools/map-build.py geo <npl_admin3.geojson>"]
    try:
        g = load_geo()
    except ValueError as e:
        return ["referral-geo.js: %s" % e]
    pal = {x["p"]: x for x in g.get("pal", [])}
    dist = {x["d"]: x for x in g.get("dist", [])}
    decl = sorted(p for p, x in pal.items() if x.get("r") == "decl")
    if decl != sorted(p for p, _, _ in DECLARED):
        fails.append("referral-geo.js: declared palikas %d, list %d" % (len(decl), len(DECLARED)))
    if sorted(dist) != sorted(d for d, _, _ in DISTRICTS):
        fails.append("referral-geo.js: districts %s differ from DISTRICTS" % sorted(dist))
    for d, label, role in DISTRICTS:
        x = dist.get(d)
        if x and (x.get("n") != label or x.get("r") != role):
            fails.append("referral-geo.js: district %s is %s/%s, the list says %s/%s" % (d, x.get("n"), x.get("r"), label, role))
        if x and x.get("ne") != DISTRICT_NE.get(d):
            fails.append("referral-geo.js: Nepali name of %s differs from DISTRICT_NE" % d)
    for p, x in pal.items():
        if x.get("r") != "pin" and x.get("d") not in dist:
            fails.append("referral-geo.js: palika %s is drawn but its district is not" % p)
        lab = x.get("lab")
        if not lab or not inside(g, x, lab[1], lab[0]):
            fails.append("referral-geo.js: the count point of %s is not inside it" % p)
    if not fails:
        print("  %-32s %d palikas (%d declared), %d districts, simplified to %s m"
              % ("referral-geo.js", sum(1 for x in pal.values() if x.get("r") != "pin"), len(decl), len(dist), g.get("simplified_m")))
    return fails, g, pal

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

# ------------------------------------------------ the interactive map's data
def build_geo(src):
    """assets/referral-geo.js: the drawn districts' palikas and outlines, as
    shared arcs (quantised, delta-encoded, TopoJSON's scheme), simplified to
    GEO_SIMPLIFY_M metres, with a point inside every palika and district for
    its count; plus, not drawn, the palika of each hospital pin outside them,
    so the check can prove the pin is where its address says."""
    fac = io.open(FACILITIES, encoding="utf-8").read()
    data = json.loads(re.search(r"window\.REFERRAL_FACILITIES\s*=\s*(\{.*\})\s*;\s*$", fac, re.S).group(1))
    keep = [d for d, _, _ in DISTRICTS]
    pinpal = sorted(set((e.get("pin") or {}).get("pcode") for e in data["entries"] if e.get("pin")) - {None})
    extra = [p for p in pinpal if p[:6] not in keep]
    tmp = tempfile.mkdtemp(); out = os.path.join(tmp, "geo.json")
    cmd = ["mapshaper", src,
           "-filter", "%s.indexOf(adm2_pcode) > -1 || %s.indexOf(adm3_pcode) > -1" % (json.dumps(keep), json.dumps(extra)),
           "-filter-fields", "adm3_pcode,adm3_name,adm2_pcode,adm2_name",
           "-simplify", "interval=%d" % GEO_SIMPLIFY_M, "keep-shapes", "-clean",
           "-rename-layers", "pal",
           "-filter", "%s.indexOf(adm2_pcode) > -1" % json.dumps(keep), "+", "name=pal8", "target=pal",
           "-dissolve", "adm2_pcode", "copy-fields=adm2_name", "+", "name=dist", "target=pal8",
           "-points", "inner", "+", "name=labs", "target=pal",
           "-points", "inner", "+", "name=dlabs", "target=dist",
           "-o", "format=topojson", "quantization=100000", "target=pal,dist,labs,dlabs", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t = json.load(open(out))
    sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]
    def pt(c):
        return [round(c[1] * sy + ty, 5), round(c[0] * sx + tx, 5)]   # [lat, lon]
    labs = {gm["properties"]["adm3_pcode"]: pt(gm["coordinates"]) for gm in t["objects"]["labs"]["geometries"]}
    dlabs = {gm["properties"]["adm2_pcode"]: pt(gm["coordinates"]) for gm in t["objects"]["dlabs"]["geometries"]}
    declared = {p: np for p, _, np in DECLARED}
    role = {d: r for d, _, r in DISTRICTS}; label = {d: l for d, l, _ in DISTRICTS}
    pal = []
    for gm in sorted(t["objects"]["pal"]["geometries"], key=lambda x: x["properties"]["adm3_pcode"]):
        pr = gm["properties"]; p = pr["adm3_pcode"]; d = pr["adm2_pcode"]
        r = "pin" if d not in role else ("decl" if p in declared else ("ctx" if role[d] == "context" else "aff"))
        pal.append({"p": p, "n": pr["adm3_name"], "ne": declared.get(p), "d": d, "dn": pr["adm2_name"], "r": r,
                    "t": gm["type"], "a": gm["arcs"], "lab": labs[p]})
    dist = []
    for gm in sorted(t["objects"]["dist"]["geometries"], key=lambda x: x["properties"]["adm2_pcode"]):
        d = gm["properties"]["adm2_pcode"]
        dist.append({"d": d, "n": label[d], "ne": DISTRICT_NE.get(d), "r": role[d], "t": gm["type"], "a": gm["arcs"], "lab": dlabs[d]})
    doc = {"source": "OCHA COD-AB Nepal v02 (Survey Department of Nepal, UN RCO Nepal), valid from 2024-03-14, HDX dataset cod-ab-npl, CC BY-IGO",
           "simplified_m": GEO_SIMPLIFY_M, "transform": t["transform"], "arcs": t["arcs"], "pal": pal, "dist": dist}
    head = ("/* =====================================================================\n"
            "   MHPSS Nepal -- boundaries for the interactive map on the Referral Directory\n"
            "   ---------------------------------------------------------------------\n"
            "   GENERATED by tools/map-build.py geo from OCHA COD-AB Nepal v02. Do not\n"
            "   edit by hand: tools/map-build.py check compares it with the declared\n"
            "   list, the districts and every hospital pin.\n"
            "   Shared arcs, quantised and delta-encoded (TopoJSON's scheme); pal.r is\n"
            "   decl (declared disaster crisis area), aff (other palika of an affected\n"
            "   district), ctx (district with reported activity, not declared affected)\n"
            "   or pin (not drawn: the palika a hospital pin outside the drawn districts\n"
            "   falls in). lab is a point inside the shape, [lat, lon].\n"
            "   ===================================================================== */\n")
    io.open(GEO, "w", encoding="utf-8").write(head + "window.REFERRAL_GEO = " +
                                               json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("geo: %d palikas (%d not drawn), %d districts, %d arcs, %d bytes"
          % (len(pal), len(extra), len(dist), len(t["arcs"]), os.path.getsize(GEO)))
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "build":
        r = build(sys.argv[2])
        sys.exit(r or build_geo(sys.argv[2]))
    if mode == "geo":
        sys.exit(build_geo(sys.argv[2]))
    sys.exit(check())
