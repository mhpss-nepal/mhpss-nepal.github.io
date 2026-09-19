#!/usr/bin/env python3
"""
MHPSS Nepal -- staff deployed, by district and palika (Referral Directory, section 5).

    python3 tools/workforce-build.py build <de-identified roster .xlsx>
    python3 tools/workforce-build.py check

WHAT IT READS. The de-identified workforce roster the data workstream built from
the four staff lists of the flood-response workbook: one row per person, with a
cadre code, the cadre labels as written, the organisation(s), the district(s)
derived from the lists and the place(s) of work as written. The roster holds no
name, telephone number or e-mail address, and it stays where it is kept: this
script is run where the roster is, and only its output -- counts -- comes out.

WHAT IT WRITES. assets/workforce.js: people per district and per palika, by
cadre, and the organisations per district. Nothing smaller than a district or a
palika, and no person, place of work or list row.

HOW IT PROTECTS A SMALL NUMBER. The Coordinator's decision of 17 September 2026:
the site shows where staff are by district and palika, and a number of one or two
people is written "fewer than 3". A single hidden number beside a total could
still be worked out by subtraction, so in any row or column whose total is shown,
a hidden number never stands alone: the smallest other number in that line is
hidden too and written "3 or more" (or "fewer than 3" when it is 0, which is true).

HOW A PLACE BECOMES A PALIKA. Only where the place of work, as written, names the
palika in a common spelling (Belkotgadi, Gosainkunda, Galchi ...), or names
Trishuli Hospital, whose printed address is in Bidur (assets/referral-facilities.js).
A holding centre or a school named without its palika counts in its district,
"palika not stated". Palika codes are COD-AB's, as assets/referral-geo.js draws them.

CADRES follow the list agreed with EDCD on 17 September 2026 (codes.js 0.3.0) and
the twelve codes approved that afternoon: senior psychosocial counsellors are
counted with psychosocial counsellors, a psychologist whose label as written says
clinical psychologist is CPSY, and a person the roster filed as Other or not stated
whose label names a psychiatric nurse, a community psychosocial worker, an mhGAP
medical officer, an FCHV, a social worker or a health worker takes that code.
"""
import io, json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "workforce.js")
GEO = os.path.join(ROOT, "assets", "referral-geo.js")
FLOOR = 3
# codes.js CADRE_RANK (the twelve codes approved on 17 Sep 2026), then "not stated";
# a cadre nobody on the lists holds is left out of the table rather than drawn as zeros
CADRES = ["PSYT", "CPSY", "PSY", "PNUR", "MO", "HW", "PSC", "CPSW", "SW", "FCHV", "VOL", "OTH", "NS"]
# a person the roster could only file as Other or not stated, whose label as written
# names one of the codes added on 17 Sep 2026
LABELLED = [
    (r"psychiatric\s*nurs|mental\s*health\s*nurs", "PNUR"),
    (r"\bcpsw\b|community\s*psycho\s*-?\s*social\s*worker", "CPSW"),
    (r"mhgap|medical\s*officer", "MO"),
    (r"\bfchv\b|female\s*community\s*health\s*volunteer", "FCHV"),
    (r"social\s*worker", "SW"),
    (r"health\s*worker|\banm\b|\bahw\b", "HW"),
]

DISTRICT = {                      # districts as the roster derives them -> COD-AB
    "Nuwakot": "NP0328", "Rasuwa": "NP0329", "Dhading": "NP0330", "Kathmandu": "NP0327",
    "Nawalparasi (Bardaghat Susta East)": "NP0447", "Chitwan": "NP0335", "Gorkha": "NP0436",
    "Tanahun": "NP0440",
}
ORDER = ["NP0328", "NP0329", "NP0330", "NP0327", "NP0335", "NP0436", "NP0440", "NP0447"]

# (district, pattern on the place of work as written, COD-AB palika code)
PALIKA = [
    ("NP0328", r"\bbidur\b", "NP0328301"),
    ("NP0328", r"tris?h?uli\s*hospi", "NP0328301"),     # Trishuli Hospital, Bidur
    ("NP0328", r"belkot", "NP0328302"),
    ("NP0328", r"kispang", "NP0328402"),
    ("NP0329", r"uttargaya", "NP0329403"),
    ("NP0329", r"gosa(?:i|in)kunda", "NP0329402"),
    ("NP0329", r"\bkalika\s*(?:rm\b|rural)", "NP0329404"),
    ("NP0329", r"aamachhod", "NP0329401"),
    ("NP0330", r"nilk(?:h)?antha\s*(?:mun|municipality)", "NP0330301"),
    ("NP0330", r"dhunibe(?:n)?s", "NP0330302"),
    ("NP0330", r"\bgalch", "NP0330410"),
    ("NP0330", r"gajuri", "NP0330409"),
    ("NP0330", r"benighat", "NP0330408"),
    ("NP0330", r"siddhalek", "NP0330407"),
    ("NP0327", r"nagarjun", "NP0327305"),
    ("NP0327", r"kathmandu\s*metropoli", "NP0327101"),
]
OUTSIDE = [r"s(?:h)?urkhet", r"rupandehi|lumbini\s*provincial"]


def geo_codes():
    raw = io.open(GEO, encoding="utf-8").read()
    return set(re.findall(r'"p"\s*:\s*"(NP\d{7})"', raw)), set(re.findall(r'"d"\s*:\s*"(NP\d{4})"', raw))


def cadre_of(code, written):
    code = (code or "").strip().upper()
    if code == "SPSC":
        return "PSC"
    if code == "PSY" and re.search(r"clinical", written or "", re.I) and re.search(r"p(?:s)?ycholog", written or "", re.I):
        return "CPSY"
    if code in ("OTH", "NOT STATED", ""):
        for pat, new in LABELLED:
            if re.search(pat, written or "", re.I):
                return new
    if code in ("PSYT", "PSY", "PSC", "VOL", "OTH"):
        return code
    return "NS"


# ------------------------------------------------------------------ protection
def determined(cells, total):
    """cells: list of (mark, value). Can a reader work out a hidden number?
    Along a row the numbers add up to the row's total (one cadre per person), so
    a reader who takes "fewer than 3" as 1 or 2 and "3 or more" as 3 to the rest
    can bound each hidden number. It is determined when only one value fits."""
    shown = sum(v for m, v in cells if m is None)
    rest = total - shown
    hid = [m for m, v in cells if m in ("lt3", "ge3")]
    if not hid:
        return False
    lo = [1 if m == "lt3" else 3 for m in hid]
    hi = [2 if m == "lt3" else max(3, rest) for m in hid]
    for i in range(len(hid)):
        a = max(lo[i], rest - (sum(hi) - hi[i]))
        b = min(hi[i], rest - (sum(lo) - lo[i]))
        if a == b:
            return True
    return False


def protect(vals, rows, cols, row_total, col_shown):
    """vals[r][c] -> int. Returns marks[(r, c)] in {None, 'lt3', 'ge3', 'hide'},
    the rows whose total is itself under FLOOR, and the rows whose total had to
    be hidden as well.
    Rows add up (a person has one cadre): no hidden number in a row may be
    determined from the row total. Columns do not add up (a person can be counted
    in two districts or palikas): a hidden number may not stand alone in one."""
    val = lambda x: vals[x[0]].get(x[1], 0)
    hidden = {r for r in rows if 0 < row_total[r] < FLOOR}
    tot_hidden = set()
    mark = {}
    for r in rows:
        for c in cols:
            v = vals[r].get(c, 0)
            mark[(r, c)] = "hide" if r in hidden else ("lt3" if 0 < v < FLOOR else None)

    def add_one(keys):
        cand = [x for x in keys if mark[x] is None and val(x) > 0]
        if cand:
            x = min(cand, key=lambda k: (val(k) < 4, val(k)))   # prefer a number of 4 or more
            mark[x] = "ge3" if val(x) >= FLOOR else "lt3"
            return True
        zeros = [x for x in keys if mark[x] is None]
        if zeros:
            mark[zeros[0]] = "lt3"                               # "fewer than 3" is true of 0
            return True
        return False

    changed = True
    while changed:
        changed = False
        for r in rows:
            if r in hidden or r in tot_hidden:
                continue
            keys = [(r, c) for c in cols]
            while determined([(mark[x], val(x)) for x in keys], row_total[r]):
                if not add_one(keys):
                    tot_hidden.add(r)
                    break
                changed = True
        for c in cols:
            if not col_shown.get(c):
                continue
            keys = [(r, c) for r in rows]
            unknown = [x for x in keys if mark[x] in ("lt3", "ge3", "hide")]
            if len(unknown) == 1 and add_one(keys):
                changed = True
    return mark, hidden, tot_hidden


def orgs_protect(names, keys):
    """organisations in a district: a person can work for two, so the line does
    not add up to the district's total; a hidden number may not stand alone."""
    mark = {("_", k): ("lt3" if 0 < names[k] < FLOOR else None) for k in keys}
    if sum(1 for k in keys if mark[("_", k)]) == 1:
        cand = [k for k in keys if mark[("_", k)] is None]
        if cand:
            k = min(cand, key=lambda k: (names[k] < 4, names[k]))
            mark[("_", k)] = "ge3"
    return mark


def cell(mark, v):
    if mark == "lt3":
        return "lt3"
    if mark == "ge3":
        return "ge3"
    return v


def total(n):
    return n if (n == 0 or n >= FLOOR) else "lt3"


# ------------------------------------------------------------------ build
def build(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Roster"]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h) if h is not None else "" for h in next(it)]
    H = {h: i for i, h in enumerate(hdr)}
    need = ["Person ID", "Cadre code", "Cadre as written", "Organisation(s)", "District(s), derived",
            "Place(s) of work as written"]
    for n in need:
        if n not in H:
            sys.exit("roster: column %r not found" % n)
    pal_codes, dist_codes = geo_codes()
    for _, _, p in PALIKA:
        assert p in pal_codes, p
    people = []
    for r in it:
        if not r or not r[H["Person ID"]]:
            continue
        g = lambda k: "" if r[H[k]] is None else str(r[H[k]])
        cad = cadre_of(g("Cadre code"), g("Cadre as written"))
        orgs = []
        for o in g("Organisation(s)").split(" | "):
            o = o.strip()
            if not o:
                continue
            written = o.endswith("(as written)")
            name = re.sub(r"\s*\(as written\)$", "", o)
            if name.lower() == "not stated":
                name, written = "", False
            orgs.append((name, written))
        dists, outside = set(), False
        for d in g("District(s), derived").split(" | "):
            d = d.strip()
            if d in DISTRICT:
                dists.add(DISTRICT[d])
            elif d.startswith("Rupandehi"):
                outside = True
        places = [p.strip() for p in g("Place(s) of work as written").split(" | ") if p.strip()]
        pals = set()
        for p in places:
            for dist, pat, code in PALIKA:
                if re.search(pat, p, re.I):
                    pals.add(code)
                    dists.add(dist)
            for pat in OUTSIDE:
                if re.search(pat, p, re.I):
                    outside = True
        people.append({"c": cad, "orgs": orgs or [("", False)], "d": dists, "p": pals, "out": outside})

    n_people = len(people)
    ctot = {c: sum(1 for x in people if x["c"] == c) for c in CADRES}
    CAD = [c for c in CADRES if ctot[c] > 0]     # the columns the page draws
    rows = [d for d in ORDER if any(d in x["d"] for x in people)]
    has_out = any(x["out"] for x in people)
    none_row = [x for x in people if not x["d"] and not x["out"]]

    # district table
    vals, rtot = {}, {}
    for d in rows:
        grp = [x for x in people if d in x["d"]]
        vals[d] = {c: sum(1 for x in grp if x["c"] == c) for c in CAD}
        rtot[d] = len(grp)
    if has_out:
        grp = [x for x in people if x["out"]]
        vals["outside"] = {c: sum(1 for x in grp if x["c"] == c) for c in CAD}
        rtot["outside"] = len(grp)
    if none_row:
        vals["none"] = {c: sum(1 for x in none_row if x["c"] == c) for c in CAD}
        rtot["none"] = len(none_row)
    trows = rows + (["outside"] if has_out else []) + (["none"] if none_row else [])
    col_shown = {c: ctot[c] >= FLOOR or ctot[c] == 0 for c in CAD}
    mark, hidden, thid = protect(vals, trows, CAD, rtot, col_shown)
    dtable = []
    for r in trows:
        row = {"d": r, "n": "ge3" if r in thid else total(rtot[r])}
        if r not in hidden:
            row["c"] = {c: cell(mark[(r, c)], vals[r][c]) for c in CAD}
        dtable.append(row)
    dmark = {r: {c: mark[(r, c)] for c in CAD} for r in trows}

    # palika blocks, one per district on the map
    blocks = {}
    for d in rows:
        if d in hidden:
            continue
        grp = [x for x in people if d in x["d"]]
        pcs = sorted({p for x in grp for p in x["p"] if p[:6] == d})
        prow_vals, prtot = {}, {}
        for p in pcs:
            g2 = [x for x in grp if p in x["p"]]
            prow_vals[p] = {c: sum(1 for x in g2 if x["c"] == c) for c in CAD}
            prtot[p] = len(g2)
        un = [x for x in grp if not any(p[:6] == d for p in x["p"])]
        if un:
            prow_vals["unnamed"] = {c: sum(1 for x in un if x["c"] == c) for c in CAD}
            prtot["unnamed"] = len(un)
        prows = pcs + (["unnamed"] if un else [])
        pshown = {c: (d not in hidden and dmark[d][c] is None) for c in CAD}
        pm, phidden, pthid = protect(prow_vals, prows, CAD, prtot, pshown)
        out = []
        for p in prows:
            row = {"p": p, "n": "ge3" if p in pthid else total(prtot[p])}
            if p not in phidden:
                row["c"] = {c: cell(pm[(p, c)], prow_vals[p][c]) for c in CAD}
            out.append(row)
        blocks[d] = out

    # organisations per district: one line each, total = the district's people
    orgs = {}
    for d in rows:
        if d in hidden:
            continue
        grp = [x for x in people if d in x["d"]]
        names = {}
        for x in grp:
            for name, written in x["orgs"]:
                k = (name, written)
                names[k] = names.get(k, 0) + 1
        keys = sorted(names, key=lambda k: (k[0] == "", -names[k], k[0]))
        ov = {"_": {k: names[k] for k in keys}}
        om = orgs_protect(names, keys)
        orgs[d] = [[k[0], cell(om[("_", k)], names[k]), k[1]] for k in keys]

    data = {
        "schema": 1,
        "exported": "2026-09-14",
        "built": datetime.date.today().isoformat(),
        "floor": FLOOR,
        "people": n_people,
        "cadre_order": CAD,
        "cadres": {c: total(ctot[c]) for c in CAD},
        "districts": dtable,
        "palikas": blocks,
        "organisations": orgs,
        "placed": {
            "palika": total(sum(1 for x in people if x["p"])),
            "district_only": total(sum(1 for x in people if x["d"] and not x["p"])),
            "none": total(len(none_row)),
        },
    }
    head = ("/* MHPSS Nepal -- staff deployed, by district and palika. Built by\n"
            "   tools/workforce-build.py from the de-identified workforce roster; counts only,\n"
            "   no person, no place of work, nothing below a palika. A number of one or two\n"
            "   is \"lt3\"; a number hidden so that a neighbour cannot be worked out is \"ge3\".\n"
            "   Do not edit by hand: rebuild, then run tools/workforce-build.py check. */\n")
    io.open(OUT, "w", encoding="utf-8").write(head + "window.WORKFORCE = " +
                                              json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print("  wrote assets/workforce.js: %d people, %d districts, %d palikas named, %d bytes"
          % (n_people, len(rows), sum(len([r for r in b if r["p"] != "unnamed"]) for b in blocks.values()),
             os.path.getsize(OUT)))
    return check()


# ------------------------------------------------------------------ check
def check():
    fails = []
    if not os.path.exists(OUT):
        print("  assets/workforce.js is missing")
        return 1
    raw = io.open(OUT, encoding="utf-8").read()
    m = re.search(r"window\.WORKFORCE\s*=\s*(\{.*\})\s*;\s*$", raw, re.S)
    if not m:
        print("  assets/workforce.js: not one JSON object after window.WORKFORCE =")
        return 1
    d = json.loads(m.group(1))
    pal_codes, dist_codes = geo_codes()
    floor = d.get("floor")
    if floor != FLOOR:
        fails.append("floor is %r, not %d" % (floor, FLOOR))

    def ok_val(v, where):
        if isinstance(v, bool) or not (isinstance(v, int) or v in ("lt3", "ge3")):
            fails.append("%s: %r is neither a count nor lt3/ge3" % (where, v))
        elif isinstance(v, int) and 0 < v < FLOOR:
            fails.append("%s: a count of %d is shown -- anything under %d is lt3" % (where, v, FLOOR))

    def lines_ok(rows, cols, where, col_shown=None):
        for r in rows:
            if "c" not in r or not isinstance(r["n"], int):
                continue
            cells = [((r["c"].get(c) if r["c"].get(c) in ("lt3", "ge3") else None),
                      (r["c"].get(c) if isinstance(r["c"].get(c), int) else 0)) for c in cols]
            if determined(cells, r["n"]):
                fails.append("%s %s: a hidden number can be worked out from the row total"
                             % (where, r.get("d") or r.get("p")))
        for c in cols:
            if col_shown is not None and not col_shown.get(c):
                continue
            unknown = [r for r in rows if "c" not in r or r["c"].get(c) in ("lt3", "ge3")]
            if len(unknown) == 1 and col_shown is not None:
                fails.append("%s column %s: one hidden number stands alone beside a shown total" % (where, c))

    ok_val(d.get("people"), "people")
    for c, v in d.get("cadres", {}).items():
        ok_val(v, "cadres." + c)
    dt = d.get("districts", [])
    for r in dt:
        if r["d"] not in dist_codes and r["d"] not in ("outside", "none"):
            fails.append("district %r is not a COD-AB district the map draws" % r["d"])
        ok_val(r["n"], "district %s" % r["d"])
        for c, v in r.get("c", {}).items():
            ok_val(v, "district %s %s" % (r["d"], c))
        if r["n"] == "lt3" and "c" in r:
            fails.append("district %s: a total under %d still shows its breakdown" % (r["d"], FLOOR))
    cols = d.get("cadre_order", CADRES)
    lines_ok(dt, cols, "district table", {c: isinstance(d["cadres"].get(c), int) for c in cols})
    for dist, rows in d.get("palikas", {}).items():
        drow = next((r for r in dt if r["d"] == dist), None)
        for r in rows:
            if r["p"] != "unnamed" and (r["p"] not in pal_codes or r["p"][:6] != dist):
                fails.append("palika %r is not a COD-AB palika of %s" % (r["p"], dist))
            ok_val(r["n"], "palika %s" % r["p"])
            for c, v in r.get("c", {}).items():
                ok_val(v, "palika %s %s" % (r["p"], c))
            if r["n"] == "lt3" and "c" in r:
                fails.append("palika %s: a total under %d still shows its breakdown" % (r["p"], FLOOR))
        shown = {c: bool(drow and "c" in drow and isinstance(drow["c"].get(c), int)) for c in cols}
        lines_ok(rows, cols, "palikas of " + dist, shown)
    for dist, items in d.get("organisations", {}).items():
        unknown = [it for it in items if it[1] in ("lt3", "ge3")]
        if len(unknown) == 1:
            fails.append("organisations of %s: one hidden number stands alone" % dist)
        for name, v, written in items:
            ok_val(v, "organisation in %s" % dist)
            if re.search(r"\d{7,}|@|https?://", name or ""):
                fails.append("organisation name in %s looks like a number, address or link" % dist)
    text = json.dumps(d, ensure_ascii=False)
    for bad, why in ((r"\bP\d{3}\b", "a person ID"), (r"(?<![\d-])\+?\d(?:[\s-]?\d){8,}(?![\d-])", "a telephone number"),
                     (r"[\w.+-]+@[\w-]+\.", "an e-mail address"), (r"![A-Z]?\d+", "a sheet!row key")):
        if re.search(bad, text):
            fails.append("the file carries what looks like %s" % why)
    print("MHPSS Nepal -- staff deployed, by district and palika")
    if fails:
        for f in fails:
            print("  FAIL  %s" % f)
        return 1
    print("  True: counts only, nothing under %d shown, no hidden number alone beside a total," % FLOOR)
    print("  every palika and district a COD-AB unit the map draws, no person, number or address.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        sys.exit(build(sys.argv[2]))
    if len(sys.argv) >= 2 and sys.argv[1] == "check":
        sys.exit(check())
    print(__doc__)
    sys.exit(2)
