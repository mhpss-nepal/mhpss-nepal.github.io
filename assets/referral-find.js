/* =====================================================================
   MHPSS Nepal -- "Find a service" on the Referral Directory
   ---------------------------------------------------------------------
   Layer 3. Four filters -- service, provider, how to access, place -- over
   three tiers of entries that are never merged into one count:

     official  hospitals and helplines, in the words of their own websites
               (assets/referral-facilities.js, every tag quoted and dated)
     provider  individual providers from the Epidemiology and Disease Control
               Division's provider list, or registered by a partner and marked
               as not yet checked (public_stats/provider_directory; a row is
               shown only when it says the provider agreed to be listed, and
               which of the two it came from)
     partner   organisations as partners report them, published by the
               Technical Working Group (public_stats/referral_directory,
               read by assets/public-read.js; nothing until published)

   The map (assets/referral-map.js) shows each matching hospital as a pin at
   its own location; providers and partner organisations are a count on a
   palika -- or on a district when no palika was given. A person is never a point.
   A row whose place lies outside the districts the map draws is listed under
   "Outside the affected districts", by the name the row gives, and not counted.

   Filters live in the address (?svc=SPEC&cadre=PSYT), so a worker can send
   a colleague "where are the psychiatrists" as a link.
   ===================================================================== */
(function () {
  "use strict";

  var C = window.CODES || {};
  var F = window.REFERRAL_FACILITIES || { entries: [], not_listed: [] };
  var G = window.REFERRAL_GEO || { pal: [], dist: [] };

  /* the districts drawn on the map, in the order tools/map-build.py reads
     them; map-build.py check compares this list with its own */
  var DIST = [
    ["NP0329", "Rasuwa"], ["NP0328", "Nuwakot"], ["NP0330", "Dhading"],
    ["NP0436", "Gorkha"], ["NP0440", "Tanahun"], ["NP0335", "Chitwan"],
    ["NP0327", "Kathmandu"], ["NP0447", "Nawalparasi East"]
  ];
  var DIST_NAME = {};
  DIST.forEach(function (d) { DIST_NAME[d[0]] = d[1]; });
  var DIST_NE = {};
  (G.dist || []).forEach(function (x) { if (x.ne) DIST_NE[x.d] = x.ne; });
  /* partner rows carry the codes.js district code; the map speaks COD-AB.
     GOR and TAN joined codes.js on 17 Sep 2026 (0.3.0); their COD-AB codes
     are the ones assets/referral-geo.js draws for Gorkha and Tanahun */
  var CODE_TO_ADM2 = { RAS: "NP0329", NUW: "NP0328", DHA: "NP0330", KTM: "NP0327", CHT: "NP0335", NAW: "NP0447",
    GOR: "NP0436", TAN: "NP0440" };

  /* what a person can go to; assessment, coordination, training and IEC
     distribution are activities, not services someone is referred to */
  var SVC = ["PFA", "CNS-I", "CNS-G", "SPEC", "MEDS", "PSED", "RECR", "CFS", "REF", "HELP", "STAFF"];
  /* the cadres and the four service settings agreed with EDCD on 17 Sep 2026
     (assets/codes.js 0.3.0), in the hub's order -- CADRE_RANK without Other;
     the twelve-code cadre list was approved the same afternoon */
  var CADRE = ["PSYT", "CPSY", "PSY", "PNUR", "MO", "HW", "PSC", "CPSW", "SW", "FCHV", "VOL"];
  var MODE = ["HC", "COM", "FAC", "TEL"];
  /* codes retired that day still arrive on rows filed before it. One that was
     merged into a single code is read as that code. INP -- "in person, at a
     site" -- was a holding centre or a facility and the row cannot say which:
     it answers to both filters and is shown as neither. */
  var WAS = { SPSC: "PSC", OUT: "COM" };
  var WAS_EITHER = { INP: ["HC", "FAC"] };
  function today(list) {
    var out = [];
    (Array.isArray(list) ? list : []).forEach(function (c) {
      c = String(c); c = WAS[c] || c;
      if (out.indexOf(c) < 0) out.push(c);
    });
    return out;
  }

  var $ = function (id) { return document.getElementById(id); };
  function t(key, vars) { return window.I18N ? window.I18N.t(key, vars) : key; }
  function isNe() { return (document.documentElement.getAttribute("lang") || "").slice(0, 2) === "ne"; }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function byCode(list, code) {
    for (var i = 0; list && i < list.length; i++) if (list[i] && list[i].code === code) return list[i];
    return null;
  }
  function codeLabel(list, code) {
    var it = byCode(list, code);
    return it && C.label ? C.label(it) : code;
  }
  function when(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(iso || ""))) return String(iso || "");
    var d = new Date(iso + "T00:00:00Z");
    try { return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }); }
    catch (e) { return iso; }
  }
  function distName(code) { return isNe() && DIST_NE[code] ? DIST_NE[code] : (DIST_NAME[code] || ""); }

  /* ------------------------------------------------------------ places */
  var PAL = {};      // pcode -> {name, ne, adm2}, the palikas drawn on the map
  (G.pal || []).forEach(function (x) {
    if (x.r !== "pin") PAL[x.p] = { name: x.n, ne: x.ne || null, adm2: x.d };
  });
  function palName(code) { var p = PAL[code]; return p ? (isNe() && p.ne ? p.ne : p.name) : code; }

  /* where a published row sits: a palika the map draws; a district it draws,
     palika not given; or outside the districts drawn, by the name the row
     gives (district_name) -- never a district left without a name. A district
     is its COD-AB pcode (NP0328) or its codes.js code (NUW). */
  function placeOf(r) {
    var pc = /^NP\d{7}$/.test(String(r.pcode || "")) ? String(r.pcode) : null;
    var dist = String(r.district || "");
    var adm2 = pc ? pc.slice(0, 6) : (/^NP\d{4}$/.test(dist) ? dist : (CODE_TO_ADM2[dist] || null));
    if (adm2 && DIST_NAME[adm2]) return { adm2: adm2, pcode: pc && PAL[pc] ? pc : null, outside: "" };
    var named = String(r.district_name || "").trim();
    if (adm2 || named) return { adm2: "outside", pcode: null, outside: named };
    return { adm2: null, pcode: null, outside: "" };
  }

  /* ------------------------------------------------------------ entries */
  var partnerRows = [];     // normalised, from the published document
  var partnerDoc = undefined;
  var providerRows = [];    // normalised, from public_stats/provider_directory
  var providerDoc = undefined, providerErr = "";

  function officialEntries() {
    return (F.entries || []).map(function (e) {
      return {
        tier: e.kind === "helpline" ? "phone" : "official",
        id: e.id,
        src: e,
        name: e.name || {},
        adm2: e.district === "outside" ? "outside" : (e.district || null),
        outside: e.outside || "",
        pcode: e.pcode && PAL[e.pcode] ? e.pcode : null,
        pin: e.pin && typeof e.pin.lat === "number" ? e.pin : null,
        services: Object.keys(e.services || {}),
        cadres: today(Object.keys(e.cadres || {})),
        modes: today(Object.keys(e.modes || {}))
      };
    });
  }
  function normalisePartner(d) {
    var rows = d && Array.isArray(d.rows) ? d.rows : [];
    return rows.map(function (r) {
      var at = placeOf(r);
      var org = r.org_name || (C.orgByCode && C.orgByCode[r.org] && C.label ? C.label(C.orgByCode[r.org]) : r.org);
      return {
        tier: "partner",
        src: r,
        name: { en: String(org || "") },
        adm2: at.adm2,
        outside: at.outside,
        pcode: at.pcode,
        palika: String(r.palika || ""),
        services: Array.isArray(r.activities) ? r.activities.map(String) : [],
        cadres: today(r.cadres),
        modes: today(r.modalities),
        last: r.last_report || ""
      };
    });
  }
  /* A provider row is shown only when it says, in so many words, that the
     provider agreed to be listed: a public page with a person's name and
     number on it is a decision each person takes, not the list's owner.
     It must also say where it came from -- the provider list, or a partner's
     registration -- so the page never calls a row "on the provider list"
     that nobody said was. */
  function normaliseProvider(d) {
    if (!d || d.schema !== 1) return [];
    var rows = Array.isArray(d.rows) ? d.rows : [];
    return rows.filter(function (r) { return r && r.consent === true && String(r.name || "").trim() && (r.source === "list" || r.source === "registration"); }).map(function (r, i) {
      var at = placeOf(r);
      return {
        tier: "provider",
        id: "pv-" + (String(r.id || i).replace(/[^\w-]/g, "") || i),
        src: r,
        name: { en: String(r.name || "") },
        qualification: String(r.qualification || ""),
        org: String(r.organisation || ""),
        phone: String(r.phone || ""),
        adm2: at.adm2,
        outside: at.outside,
        pcode: at.pcode,
        services: Array.isArray(r.services) ? r.services.map(String) : [],
        cadres: today(r.cadre ? [r.cadre] : []),
        modes: today(r.modalities),
        checked: /^\d{4}-\d{2}-\d{2}$/.test(String(r.checked || "")) ? String(r.checked) : "",
        via: r.source
      };
    });
  }

  /* the palika an entry sits in, for the map: the hospital's pin, else the
     palika it was reported with */
  function palikaOf(e) {
    if (e.pin && PAL[e.pin.pcode]) return e.pin.pcode;
    return e.pcode;
  }

  /* ------------------------------------------------------------ filters */
  var sel = { svc: $("fSvc"), cadre: $("fCadre"), mode: $("fMode"), dist: $("fDist"), pal: $("fPal") };
  var state = { svc: "", cadre: "", mode: "", dist: "", pal: "" };

  function readUrl() {
    try {
      var q = new URLSearchParams(location.search);
      ["svc", "cadre", "mode", "dist", "pal"].forEach(function (k) { state[k] = q.get(k) || ""; });
    } catch (e) { /* old browser: start with nothing selected */ }
    if (state.svc && SVC.indexOf(state.svc) < 0) state.svc = "";
    if (state.cadre && CADRE.indexOf(state.cadre) < 0) state.cadre = WAS[state.cadre] || "";
    if (state.mode && MODE.indexOf(state.mode) < 0) state.mode = WAS[state.mode] || "";
    if (state.dist && state.dist !== "outside" && !DIST_NAME[state.dist]) state.dist = "";
    if (state.pal && !PAL[state.pal]) state.pal = "";
    if (state.pal) state.dist = PAL[state.pal].adm2;
  }
  function writeUrl() {
    try {
      var q = new URLSearchParams(location.search);
      ["svc", "cadre", "mode", "dist", "pal"].forEach(function (k) {
        if (state[k]) q.set(k, state[k]); else q.delete(k);
      });
      var s = q.toString();
      history.replaceState(null, "", location.pathname + (s ? "?" + s : "") + location.hash);
    } catch (e) { /* the filters still work; only the link does not carry them */ }
  }

  function fill(select, anyKey, items) {
    if (!select) return;
    select.textContent = "";
    var o = el("option", null, t(anyKey)); o.value = ""; select.appendChild(o);
    items.forEach(function (it) {
      var op = el("option", null, it[1]); op.value = it[0]; select.appendChild(op);
    });
  }
  /* the label names the place outside the affected districts that the
     hospitals list reaches; once a published row sits anywhere else outside,
     the label drops the name rather than name only some of the places */
  function outsideLabel() {
    var own = {}, other = false;
    officialEntries().forEach(function (e) { if (e.adm2 === "outside" && e.outside) own[e.outside] = true; });
    providerRows.concat(partnerRows).forEach(function (e) { if (e.adm2 === "outside" && !own[e.outside]) other = true; });
    return t(other ? "refdir.find.outsideAll" : "refdir.find.outside");
  }
  function fillAll() {
    fill(sel.svc, "refdir.find.any.svc", SVC.map(function (c) { return [c, codeLabel(C.ACTIVITIES, c)]; }));
    fill(sel.cadre, "refdir.find.any.cadre", CADRE.map(function (c) { return [c, codeLabel(C.CADRES, c)]; }));
    fill(sel.mode, "refdir.find.any.mode", MODE.map(function (c) { return [c, codeLabel(C.MODALITIES, c)]; }));
    fill(sel.dist, "refdir.find.any.dist", DIST.map(function (d) { return [d[0], distName(d[0])]; })
      .concat([["outside", outsideLabel()]]));
    fillPalikas();
    ["svc", "cadre", "mode", "dist"].forEach(function (k) { if (sel[k]) sel[k].value = state[k]; });
  }
  function fillPalikas() {
    var items = [];
    if (state.dist && state.dist !== "outside") {
      Object.keys(PAL).forEach(function (pc) { if (PAL[pc].adm2 === state.dist) items.push([pc, palName(pc)]); });
      items.sort(function (a, b) { return a[1].localeCompare(b[1]); });
    }
    fill(sel.pal, "refdir.find.any.pal", items);
    if (sel.pal) {
      sel.pal.disabled = !items.length;
      sel.pal.value = state.pal;
    }
  }

  function has(list, code) { return list.indexOf(code) > -1; }
  function matchesWhat(e) {
    if (state.svc && !has(e.services, state.svc)) return false;
    if (state.cadre && !has(e.cadres, state.cadre)) return false;
    if (state.mode && !has(e.modes, state.mode) &&
        !e.modes.some(function (c) { return (WAS_EITHER[c] || []).indexOf(state.mode) > -1; })) return false;
    return true;
  }
  /* a helpline is reachable from every place, so place never removes it */
  function matchesWhere(e) {
    if (e.tier === "phone") return true;
    if (!state.dist) return true;
    if (state.dist === "outside") return e.adm2 === "outside";
    if (e.adm2 !== state.dist) return false;
    var p = palikaOf(e);
    if (state.pal && p && p !== state.pal) return false;
    return true;
  }

  /* ------------------------------------------------------------ render */
  function placeText(e) {
    if (e.tier === "phone") return "";
    if (e.adm2 === "outside") return e.outside ? t("refdir.find.place.outside", { district: e.outside }) : t("refdir.find.outsideAll");
    if (!e.adm2) return t("refdir.find.place.none");
    var dn = distName(e.adm2);
    if (e.pcode) return t("refdir.find.place.palika", { palika: palName(e.pcode), district: dn });
    if (e.tier === "partner" || e.tier === "provider") return t("refdir.find.place.districtPartner", { district: dn });
    return t("refdir.find.place.district", { district: dn });
  }

  function chips(codes, list) {
    var ul = el("ul", "fchips");
    codes.forEach(function (c) { ul.appendChild(el("li", null, codeLabel(list, c))); });
    return ul;
  }

  function card(e) {
    var li = el("li", "fcard");
    if (e.id) li.id = "fc-" + e.id;
    var h = el("div", "fc-h");
    var b = el("b", null, e.name.en || ""); b.setAttribute("data-i18n-skip", "");
    h.appendChild(b);
    if (e.name.ne) {
      var np = el("span", "np", e.name.ne); np.setAttribute("lang", "ne"); np.setAttribute("data-i18n-skip", "");
      h.appendChild(np);
    }
    li.appendChild(h);
    if (e.tier === "provider") {
      if (e.qualification) li.appendChild(el("p", "fc-qual", e.qualification));
      if (e.org) {
        var og = el("p", "fc-org"); og.appendChild(el("span", "lab", t("refdir.find.org") + " "));
        var ob = el("span", null, e.org); ob.setAttribute("data-i18n-skip", ""); og.appendChild(ob);
        li.appendChild(og);
      }
    }
    var place = placeText(e);
    if (place) li.appendChild(el("p", "fc-place", place));

    var svc = e.services.filter(function (c) { return SVC.indexOf(c) > -1; });
    if (svc.length) li.appendChild(chips(svc, C.ACTIVITIES));
    var who = e.cadres.filter(function (c) { return CADRE.indexOf(c) > -1; });
    var how = e.modes.filter(function (c) { return MODE.indexOf(c) > -1; });
    if (who.length || how.length) {
      var meta = el("p", "fc-meta");
      if (who.length) meta.appendChild(el("span", null, who.map(function (c) { return codeLabel(C.CADRES, c); }).join(" · ")));
      if (who.length && how.length) meta.appendChild(document.createTextNode("  —  "));
      if (how.length) meta.appendChild(el("span", "how", how.map(function (c) { return codeLabel(C.MODALITIES, c); }).join(" · ")));
      li.appendChild(meta);
    }

    var s = e.src || {};
    /* a number is shown only when it looks like one: digits and the usual separators */
    if (e.tier === "provider" && /^[+\d\s().\/\u2013-]+$/.test(e.phone) && e.phone.replace(/\D/g, "").length >= 4) {
      var pp = el("p", "fc-tel");
      var pa = el("a", null, e.phone); pa.href = "tel:" + e.phone.replace(/[^\d+]/g, "");
      pa.setAttribute("data-i18n-skip", "");
      pp.appendChild(pa);
      li.appendChild(pp);
    }
    if (Array.isArray(s.phones) && s.phones.length) {
      var ph = el("p", "fc-tel");
      s.phones.forEach(function (p, i) {
        if (i) ph.appendChild(document.createTextNode("  ·  "));
        if (p.label === "toll") ph.appendChild(el("span", "lab", t("refdir.find.toll") + " "));
        var a = el("a", null, p.text); a.href = "tel:" + String(p.tel || "").replace(/[^\d+]/g, "");
        a.setAttribute("data-i18n-skip", "");
        ph.appendChild(a);
      });
      li.appendChild(ph);
    }

    if (e.pin && M) {
      var go = el("button", "fc-map", t("refdir.find.onmap"));
      go.type = "button";
      go.addEventListener("click", function () {
        var wrap = $("find") && $("find").querySelector(".findmap");
        if (wrap && wrap.scrollIntoView) wrap.scrollIntoView({ behavior: "smooth", block: "start" });
        M.openPin(e.id);
      });
      li.appendChild(go);
    }

    if (e.tier === "provider") {
      li.appendChild(el("p", "fc-src", e.via === "registration" ? t("refdir.find.selfreg")
        : (e.checked ? t("refdir.find.checked", { date: when(e.checked) }) : t("refdir.find.fromlist"))));
    } else if (e.tier === "partner") {
      if (e.last) li.appendChild(el("p", "fc-src", t("refdir.find.last", { date: when(e.last) })));
    } else if (Array.isArray(s.quotes) && s.quotes.length) {
      var det = el("details", "fc-says");
      det.appendChild(el("summary", null, t("refdir.find.says")));
      /* the quotes, under the page each one is on */
      (s.sources || []).forEach(function (src, si) {
        var qs = s.quotes.filter(function (q) { return q.src === si; });
        if (!qs.length) return;
        var a = el("a", "fc-page", src.title || src.url || ""); a.href = src.url || "#";
        a.setAttribute("data-i18n-skip", ""); a.rel = "noopener";
        det.appendChild(a);
        var ul = el("ul");
        qs.forEach(function (q) {
          var qi = el("li");
          var qt = el("q", null, q.text); qt.setAttribute("data-i18n-skip", "");
          if (/[ऀ-ॿ]/.test(q.text)) qt.setAttribute("lang", "ne");
          qi.appendChild(qt);
          if (q.context) qi.appendChild(el("span", "ctx", " " + t("refdir.find.ctx." + q.context)));
          ul.appendChild(qi);
        });
        det.appendChild(ul);
      });
      det.appendChild(el("p", "fc-read", t("refdir.find.read", { date: when(F.read) })));
      if (e.pin) {
        var pl = el("p", "fc-read");
        pl.appendChild(document.createTextNode(t("refdir.find.pinsrc", { date: when(e.pin.read) }) + " "));
        var oa = el("a", null, "OpenStreetMap " + e.pin.osm);
        oa.href = "https://www.openstreetmap.org/" + e.pin.osm; oa.rel = "noopener"; oa.setAttribute("data-i18n-skip", "");
        pl.appendChild(oa);
        if (e.pin.site_map) pl.appendChild(document.createTextNode(". " + t("refdir.find.pinsite")));
        det.appendChild(pl);
      }
      li.appendChild(det);
    }
    return li;
  }

  function group(tier, list, emptyNode) {
    var g = el("div", "fgroup");
    g.setAttribute("data-tier", tier);
    var h = el("h3", null, t("refdir.find.tier." + tier));
    if ((tier === "partner" && partnerDoc && partnerDoc.mode === "demonstration") ||
        (tier === "provider" && providerDoc && providerDoc.mode === "demonstration")) {
      h.appendChild(el("span", "fdemo", t("refdir.find.demo")));
    }
    var n = el("span", "n", String(list.length));
    h.appendChild(n);
    g.appendChild(h);
    if (list.length) {
      var ul = el("ul", "fcards");
      list.forEach(function (e) { ul.appendChild(card(e)); });
      g.appendChild(ul);
    } else if (emptyNode) {
      g.appendChild(emptyNode);
    }
    return g;
  }

  function partnerState() {
    var s = $("dirState");
    var key = s && s.getAttribute("data-i18n-live");
    if (partnerDoc === null || key === "live.nonePublished") return t("live.nonePublished");
    if (key && key !== "live.published" && key !== "live.publishedDemo") return t(key);
    return "";
  }

  function providerState() {
    if (providerErr) return t("live.error");
    if (providerDoc === undefined) return t("live.checking");
    if (providerDoc === null) return t("refdir.find.none.providerUnpublished");
    if (providerDoc.schema !== 1) return t("live.schema");
    return t("refdir.find.none.provider");
  }

  function count(kind, n) {
    return t("refdir.find.count." + kind + "." + (n === 0 ? "none" : n === 1 ? "one" : "many"), { n: n });
  }

  function render() {
    var oo = sel.dist && sel.dist.querySelector('option[value="outside"]');
    if (oo) oo.textContent = outsideLabel();
    var all = officialEntries().concat(providerRows, partnerRows);
    var what = all.filter(matchesWhat);
    var shown = what.filter(matchesWhere);
    var official = shown.filter(function (e) { return e.tier === "official"; });
    var provider = shown.filter(function (e) { return e.tier === "provider"; });
    var partner = shown.filter(function (e) { return e.tier === "partner"; });
    var phone = shown.filter(function (e) { return e.tier === "phone"; });

    /* the summary line, read aloud when it changes */
    var sum = $("fSum");
    if (sum) {
      /* hospitals and partner organisations are places; a provider is a person */
      var places = official.length + partner.length;
      if (!places && !provider.length && !phone.length) {
        sum.textContent = t("refdir.find.sum0");
      } else if (providerRows.length) {
        sum.textContent = t("refdir.find.sumProviders", { places: count("place", places),
          providers: count("provider", provider.length), phones: count("phone", phone.length) });
      } else {
        sum.textContent = t("refdir.find.sum", { places: count("place", places), phones: count("phone", phone.length) });
      }
    }

    /* the list */
    var res = $("fRes");
    if (res) {
      res.textContent = "";
      res.appendChild(group("official", official, el("p", "fempty", t("refdir.find.none.official"))));
      var pe = el("p", "fempty", providerState());
      /* until the provider list is published, point to where the staff are */
      if (providerDoc === null && window.WORKFORCE && document.getElementById("staff")) {
        pe.appendChild(document.createTextNode(" "));
        var sa = el("a", null, t("refdir.find.seeStaff")); sa.href = "#staff";
        pe.appendChild(sa);
      }
      res.appendChild(group("provider", provider, pe));
      var pstate = partnerState();
      res.appendChild(group("partner", partner, el("p", "fempty", partner.length ? "" :
        (pstate || t("refdir.find.none.partner")))));
      res.appendChild(group("phone", phone, el("p", "fempty", t("refdir.find.none.phone"))));
      var nl = F.not_listed || [];
      if (nl.length) {
        var np = nl.filter(function (x) { return x.why === "no-psychiatry"; }).map(function (x) { return x.name; });
        var un = nl.filter(function (x) { return x.why === "unreachable"; }).map(function (x) { return x.name; });
        var p = el("p", "fnot");
        if (np.length) p.appendChild(document.createTextNode(t("refdir.find.not.nopsy", { names: np.join(", ") }) + " "));
        if (un.length) p.appendChild(document.createTextNode(t("refdir.find.not.unreach", { names: un.join(", "), date: when(F.read) })));
        res.appendChild(p);
      }
    }

    drawMap(shown);
  }

  /* ------------------------------------------------------------ the map */
  var M = null;
  var framed = { dist: null, pal: null };
  function drawMap(shown) {
    if (!M) return;
    var pins = [], palCounts = {}, distCounts = {}, hit = {};
    shown.forEach(function (e) {
      if (e.tier === "phone") return;
      var p = palikaOf(e);
      if (e.tier === "official") {
        if (e.pin) pins.push({ id: e.id, name: e.name, lat: e.pin.lat, lon: e.pin.lon, place: placeText(e), outside: e.adm2 === "outside" });
        if (p) hit[p] = true;
        return;
      }
      if (e.pcode) { palCounts[e.pcode] = (palCounts[e.pcode] || 0) + 1; hit[e.pcode] = true; }
      else if (e.adm2 && DIST_NAME[e.adm2]) distCounts[e.adm2] = (distCounts[e.adm2] || 0) + 1;
    });
    M.update({ pins: pins, palCounts: palCounts, distCounts: distCounts, hit: hit, pal: state.pal, dist: state.dist });

    /* frame the map on what was chosen -- only when the choice changed, so a
       filter on service or provider does not throw away a hand-made view */
    if (framed.dist !== state.dist || framed.pal !== state.pal) {
      if (state.pal) M.fitPalika(state.pal);
      else if (state.dist) M.fitDistrict(state.dist);
      else if (framed.dist !== null) M.fitAll();
      framed.dist = state.dist; framed.pal = state.pal;
    }

    var bar = $("fZoom");
    if (bar) {
      var on = !!state.dist;
      bar.hidden = !on;
      bar.textContent = "";
      if (on) {
        bar.appendChild(el("b", null, state.dist === "outside" ? outsideLabel() : distName(state.dist)));
        var back = el("button", "fback", t("refdir.find.zoom.back"));
        back.type = "button";
        back.addEventListener("click", function () { chooseDistrict(""); });
        bar.appendChild(back);
        if (distCounts[state.dist]) {
          var withPalikas = Object.keys(palCounts).some(function (c) { return PAL[c] && PAL[c].adm2 === state.dist; });
          bar.appendChild(el("span", "fdl", t(withPalikas ? "refdir.find.zoom.districtLevel" : "refdir.find.zoom.districtOnly",
            { n: distCounts[state.dist] })));
        }
      }
    }
    var k = $("keyHit"); if (k) k.hidden = !Object.keys(palCounts).length;
    var kd = $("keyDhit"); if (kd) kd.hidden = !Object.keys(distCounts).length;
    var kp = $("keyPin"); if (kp) kp.hidden = !pins.length;
  }

  function chooseDistrict(code) {
    state.dist = code; state.pal = "";
    if (sel.dist) sel.dist.value = code;
    fillPalikas(); writeUrl(); render();
  }
  function choosePalika(code) {
    if (!PAL[code]) return;
    if (state.pal === code) { state.pal = ""; }
    else { state.pal = code; state.dist = PAL[code].adm2; }
    if (sel.dist) sel.dist.value = state.dist;
    fillPalikas(); writeUrl(); render();
  }
  function countAt(code) {
    var n = 0;
    officialEntries().concat(providerRows, partnerRows).filter(matchesWhat).forEach(function (e) {
      if (e.tier !== "phone" && palikaOf(e) === code) n++;
    });
    return n;
  }

  /* ------------------------------------------------------------ wiring */
  ["svc", "cadre", "mode"].forEach(function (k) {
    if (!sel[k]) return;
    sel[k].addEventListener("change", function () { state[k] = this.value; writeUrl(); render(); });
  });
  if (sel.dist) sel.dist.addEventListener("change", function () {
    state.dist = this.value; state.pal = ""; fillPalikas(); writeUrl(); render();
  });
  if (sel.pal) sel.pal.addEventListener("change", function () {
    state.pal = this.value; writeUrl(); render();
  });
  var clear = $("fClear");
  if (clear) clear.addEventListener("click", function () {
    state = { svc: "", cadre: "", mode: "", dist: "", pal: "" };
    fillAll(); writeUrl(); render();
  });

  var mapBox = $("fMap");
  /* the map's box has to be visible before Leaflet measures it: a map made in
     a hidden box frames itself on a size of nought and draws nothing */
  var wrap = $("find") && $("find").querySelector(".map");
  if (wrap && window.L && window.REFERRAL_GEO) wrap.classList.add("live");
  try {
    M = window.REFERRAL_MAP ? window.REFERRAL_MAP.create(mapBox, {
      onPalika: choosePalika,
      onDistrict: chooseDistrict,
      countAt: countAt,
      onPinDetails: function (id) {
        var c = $("fc-" + id);
        if (!c) return;
        var d = c.querySelector("details"); if (d) d.open = true;
        c.scrollIntoView({ behavior: "smooth", block: "center" });
        c.classList.add("flash");
        setTimeout(function () { c.classList.remove("flash"); }, 1600);
        var b = c.querySelector("summary"); if (b) b.focus({ preventScroll: true });
      }
    }) : null;
  } catch (err) {
    M = null;
    if (window.console) console.warn("map not drawn:", err && err.message);
  }
  if (wrap) wrap.classList.toggle("live", !!M);
  if (M) { M.invalidate(); M.fitAll(); }

  /* a larger map, for a room or a projector; the list stays below it */
  var big = $("fBig");
  if (big) {
    big.hidden = !M;
    big.addEventListener("click", function () {
      var fm = $("find").querySelector(".findmap");
      var on = !fm.classList.contains("big");
      fm.classList.toggle("big", on);
      big.textContent = t(on ? "refdir.find.smaller" : "refdir.find.bigger");
      big.setAttribute("aria-pressed", on ? "true" : "false");
      setTimeout(function () {
        if (!M) return;
        M.invalidate();
        if (state.pal) M.fitPalika(state.pal); else if (state.dist) M.fitDistrict(state.dist); else M.fitAll();
        if (on && fm.scrollIntoView) fm.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 60);
    });
  }

  /* the partner tier arrives when public_stats answers -- or never, which
     the partner group then says in the words of the live strip */
  var previewing = false;
  document.addEventListener("publicstats:referral_directory", function (ev) {
    if (previewing) return;
    partnerDoc = ev.detail;
    partnerRows = normalisePartner(ev.detail);
    render();
  });
  /* individual providers: their own document, read the same way */
  var previewingProviders = false;
  if (window.PUBLIC_STATS && window.PUBLIC_STATS.configured) {
    window.PUBLIC_STATS.watch("provider_directory", function (data) {
      if (previewingProviders) return;
      providerDoc = data; providerErr = ""; providerRows = normaliseProvider(data); render();
    }, function (msg) {
      if (previewingProviders) return;
      providerErr = msg || "error"; render();
    });
  } else {
    providerErr = "not configured";
  }
  var ds = $("dirState");
  if (ds && window.MutationObserver) {
    new MutationObserver(function () { render(); }).observe(ds, { attributes: true, attributeFilter: ["data-i18n-live"] });
  }
  document.addEventListener("i18n:changed", function () {
    if (M) M.relabel();
    if (big) big.textContent = t($("find").querySelector(".findmap").classList.contains("big") ? "refdir.find.smaller" : "refdir.find.bigger");
    fillAll(); render();
  });

  readUrl();
  fillAll();
  if (big) big.textContent = t("refdir.find.bigger");
  render();

  /* for whoever builds the publish step: paint a partner document that has
     not been published, with no network, to see what the filters will do */
  window.REFERRAL_FIND = {
    preview: function (doc) { previewing = true; partnerDoc = doc; partnerRows = normalisePartner(doc); render(); },
    previewProviders: function (doc) {
      previewingProviders = true; providerErr = ""; providerDoc = doc; providerRows = normaliseProvider(doc); render();
    }
  };
})();
