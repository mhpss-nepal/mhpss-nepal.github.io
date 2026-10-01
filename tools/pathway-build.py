#!/usr/bin/env python3
"""
MHPSS Nepal -- the GBV and child protection referral pathway, for the
Referral Directory's "Find a service"
-------------------------------------------------------------------------
The Nepal Protection Cluster keeps a referral pathway for GBV and child
protection response, one workbook per province plus a national one. Many of
its services carry mental health and psychosocial support. This tool reads
those workbooks and writes assets/referral-pathway.js: the rows that are
MHPSS-relevant, reduced to what a public page may show.

  build <folder>   read the workbooks in <folder> (never in this repository)
                   and write assets/referral-pathway.js
  check            fail if assets/referral-pathway.js carries anything a
                   public page must not: a field outside the allowed list,
                   an address, a phone number, an email, a shelter placed
                   below its district (the deploy guard runs this)

WHAT A ROW KEEPS
  province, district, palika (municipality), service category, service detail
  (only if it holds no number or address), days/hours, organisation, type of
  service point, languages, accessibility for persons with disabilities, who
  the service is open to, the month the row was last updated, and whether
  the service is a core MHPSS service or carries an MHPSS component.
WHAT A ROW NEVER KEEPS
  ward, address, the name of a holding centre, any provider or focal-point
  name, phone number or email. A safe house or shelter is shown by district
  only: where a shelter is, is not published.

MHPSS RELEVANCE (the screening rule of the extraction of 26 September 2026)
  core      the service category is Psycho Social Support (PSS) or
            Psychological First Aid (PFA)
  component any other category whose detail or organisation contains psych*,
            mental, PFA, PSS, PM+, grief, emotional, trauma or depress*; or
            counsel* in a category other than Legal Services, Local Judicial
            Committee or Safety and Security ("legal counselling" ignored)
  A screening rule, not a quality or standards check.
"""
import datetime, glob, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "referral-pathway.js")
SOURCE = {
    "name": "Nepal Protection Cluster — Referral Pathway, GBV & CP Response",
    "url": "https://sites.google.com/view/nepalprotectioncluster/",
}

def norm(s):
    if s is None:
        return ""
    if isinstance(s, float) and s.is_integer():
        s = int(s)
    return re.sub(r"\s+", " ", str(s)).strip()

CORE = ("psycho social support (pss)", "psychological first aid (pfa)")
KW = re.compile(r"psych|mental|\bpfa\b|\bpss\b|pm\+|grief|emotional|trauma|depress", re.I)
COUNSEL = re.compile(r"counsel", re.I)
LEGALISH = ("legal services", "local judicial comittee", "local judicial committee", "safety and secuirty", "safety and security")
SPEC = re.compile(r"psychiatr|mental health|pm\+|depress", re.I)
SHELTER = re.compile(r"shelter|safe house|rehabilitation", re.I)
UNSAFE = re.compile(r"\d{5,}|@|\bward\b|wada|tole|chowk|marg\b|road\b|\bmr\.|\bms\.|\bdr\.", re.I)
CAT_FIX = {"Safety and Secuirty": "Safety and Security", "Local Judicial Comittee": "Local Judicial Committee"}
GROUPS = [("woman age 18 +", "women"), ("men 18 +", "men"), ("girl 18 below", "girls"), ("boy 18 below", "boys"),
          ("senior citizen age 60+", "older"), ("lgbtqi persons", "lgbtqi")]
ALLOWED = {"prov", "dist", "pal", "cat", "det", "hrs", "org", "pt", "lang", "acc", "who", "upd", "mh", "spec", "shelter"}

def relevance(cat, det, org):
    c = cat.lower()
    if c in CORE:
        return "core"
    text = det + " " + org
    if KW.search(text):
        return "component"
    if COUNSEL.search(re.sub(r"legal counsel+ing", "", text, flags=re.I)) and c not in LEGALISH:
        return "component"
    return None

def hours(v):
    v = norm(v)
    if not v:
        return ""
    if re.fullmatch(r"\d{1,2}", v):
        return "%s hours" % v
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", v):
        return ""          # a date typed into the hours column
    if not re.search(r"\d|hour|hrs|24|continuous|always|sunday|monday|am|pm", v, re.I):
        return ""          # service text typed into the hours column
    return v

def month(v):
    v = norm(v)
    m = re.match(r"(\d{4})-(\d{2})", v)
    return "%s-%s" % (m.group(1), m.group(2)) if m else ""

def build(folder):
    import openpyxl
    rows, files = [], []
    for f in sorted(glob.glob(os.path.join(folder, "[1-8]*.xlsx"))):
        files.append(os.path.basename(f))
        ws = openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[1]
        R = list(ws.iter_rows(values_only=True))
        h = [norm(x).lower() for x in R[3]]
        for r in R[4:]:
            d = dict(zip(h, r))
            org, cat = norm(d.get("organization name")), norm(d.get("services"))
            if not org or not cat:
                continue
            det = norm(d.get("service detail (open text)"))
            mh = relevance(cat, det, org)
            if not mh:
                continue
            cat = CAT_FIX.get(cat, cat)
            pt = norm(d.get("institution/service point (ex: school, wgss, cfs)"))
            shelter = bool(SHELTER.search(cat) or SHELTER.search(pt))
            row = {
                "prov": norm(d.get("province")).replace("Madesh", "Madhesh"),
                "dist": norm(d.get("district")),
                "pal": "" if shelter else norm(d.get("municipality")),
                "cat": cat,
                "det": "" if (UNSAFE.search(det) or len(det) > 220) else det,
                "hrs": hours(d.get("days/hours of operation")),
                "org": "" if UNSAFE.search(org) else org,
                "pt": "" if shelter else pt,
                "lang": ", ".join(x for x in (["Nepali"] if norm(d.get("nepali")).lower() == "yes" else [])
                                  + [norm(d.get("other (please select all that apply)"))] if x),
                "acc": norm(d.get("persons with disability (please select all that apply)")),
                "who": [k2 for k1, k2 in GROUPS if norm(d.get(k1)).lower() == "yes"],
                "upd": month(d.get("last updated (month year)")),
                "mh": mh,
                "spec": bool(SPEC.search(det)),
            }
            if shelter:
                row["shelter"] = True
            if not row["org"]:
                continue
            rows.append(row)
    # the same service listed twice in one place is shown once
    seen, uniq = set(), []
    for r in rows:
        k = json.dumps(r, sort_keys=True)
        if k not in seen:
            seen.add(k); uniq.append(r)
    uniq.sort(key=lambda r: (r["prov"], r["dist"], r["pal"], r["mh"] != "core", r["cat"], r["org"]))
    doc = {"source": SOURCE, "read": datetime.date.today().isoformat(),
           "files": files, "rows": uniq}
    body = json.dumps(doc, ensure_ascii=False, indent=0)
    io.open(OUT, "w", encoding="utf-8").write(
        "/* Generated by tools/pathway-build.py from the Nepal Protection Cluster's\n"
        "   GBV & CP referral pathway workbooks. Do not edit by hand: rebuild, then\n"
        "   run tools/pathway-build.py check. No ward, address, name, phone number\n"
        "   or email is kept, and a shelter is placed by district only. */\n"
        "window.REFERRAL_PATHWAY = " + body + ";\n")
    print("  %d rows written (%d core MHPSS, %d with an MHPSS component) from %d workbooks"
          % (len(uniq), sum(r["mh"] == "core" for r in uniq), sum(r["mh"] == "component" for r in uniq), len(files)))
    return 0

def check():
    print("MHPSS Nepal -- the GBV & CP referral pathway on the public page")
    if not os.path.exists(OUT):
        print("  assets/referral-pathway.js is missing"); return 1
    s = io.open(OUT, encoding="utf-8").read()
    doc = json.loads(s[s.index("window.REFERRAL_PATHWAY = ") + len("window.REFERRAL_PATHWAY = "):].rstrip().rstrip(";"))
    fails = []
    for i, r in enumerate(doc.get("rows", [])):
        extra = set(r) - ALLOWED
        if extra:
            fails.append("row %d: a field a public page may not carry: %s" % (i, ", ".join(sorted(extra))))
        for k, v in r.items():
            if isinstance(v, str) and re.search(r"\d{5,}|@", v) and k not in ("upd",):
                fails.append("row %d: %s holds a number or an email" % (i, k))
        if r.get("shelter") and (r.get("pal") or r.get("pt")):
            fails.append("row %d: a shelter is placed below its district" % i)
        if r.get("mh") not in ("core", "component"):
            fails.append("row %d: not an MHPSS-relevant service" % i)
        if not r.get("org") or not r.get("cat"):
            fails.append("row %d: no organisation or service" % i)
    if fails:
        print("\n  REFUSED:"); [print("    " + f) for f in fails[:30]]
        return 1
    print("  %d rows; no address, number, email or person; shelters by district only"
          % len(doc.get("rows", [])))
    print("\n  True: the referral pathway carries only what a public page may show.")
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit(build(sys.argv[2]) if mode == "build" else check())
