/* =====================================================================
   MHPSS Nepal -- "Find a service" on the Referral Directory
   ---------------------------------------------------------------------
   Layer 3. Four filters -- service, provider, how to access, place -- over
   two tiers of entries that are never merged into one count:

     official  hospitals and helplines, in the words of their own websites
               (assets/referral-facilities.js, every tag quoted and dated)
     partner   organisations as partners report them, published by the
               Technical Working Group (public_stats/referral_directory,
               read by assets/public-read.js; nothing until published)

   The map below the filters shows, for whatever is selected, how many
   entries sit in each palika -- or in a district, when a hospital's printed
   address names no palika. Never a point: a count on a palika, as the
   partner directory has always been drawn.

   Filters live in the address (?svc=SPEC&cadre=PSYT), so a worker can send
   a colleague "where are the psychiatrists" as a link.
   ===================================================================== */
(function () {
  "use strict";

  var C = window.CODES || {};
  var F = window.REFERRAL_FACILITIES || { entries: [], not_listed: [] };

  /* the districts drawn on the map, in the order tools/map-build.py reads
     them; map-build.py check compares this list with its own */
  var DIST = [
    ["NP0329", "Rasuwa"], ["NP0328", "Nuwakot"], ["NP0330", "Dhading"],
    ["NP0436", "Gorkha"], ["NP0440", "Tanahun"], ["NP0335", "Chitwan"],
    ["NP0327", "Kathmandu"], ["NP0447", "Nawalparasi East"]
  ];
  var DIST_NAME = {};
  DIST.forEach(function (d) { DIST_NAME[d[0]] = d[1]; });
  /* partner rows carry the codes.js district code; the map speaks COD-AB */
  var CODE_TO_ADM2 = { RAS: "NP0329", NUW: "NP0328", DHA: "NP0330", KTM: "NP0327", CHT: "NP0335", NAW: "NP0447" };

  /* what a person can go to; assessment, coordination, training and IEC
     distribution are activities, not services someone is referred to */
  var SVC = ["PFA", "CNS-I", "CNS-G", "SPEC", "MEDS", "PSED", "RECR", "CFS", "REF", "HELP", "STAFF"];
  var CADRE = ["PSYT", "PSY", "PSC", "SPSC", "SW", "HW", "VOL"];
  var MODE = ["INP", "OUT", "TEL"];

  var $ = function (id) { return document.getElementById(id); };
  function t(key, vars) { return window.I18N ? window.I18N.t(key, vars) : key; }
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

  /* ------------------------------------------------------------ the map */
  var map = document.querySelector("#find .map");
  var svg = map && map.querySelector("svg");
  var stage = map && map.querySelector(".mapstage");
  var badges = $("fBadges"), tip = $("fTip");
  var PAL = {};      // pcode -> {path, name, adm2}
  var DPATH = {};    // adm2  -> path
  if (svg) {
    svg.querySelectorAll(".pal[data-pcode]").forEach(function (p) {
      var code = p.getAttribute("data-pcode");
      var title = p.querySelector("title");
      var name = title ? title.textContent : code;
      /* the drawn title would pop a second, unstyled tooltip over ours */
      if (title) p.removeChild(title);
      PAL[code] = { path: p, name: name, adm2: code.slice(0, 6) };
    });
    svg.querySelectorAll(".dist[data-dcode]").forEach(function (p) {
      DPATH[p.getAttribute("data-dcode")] = p;
    });
  }
  var FULL = (function () {
    var v = svg ? svg.viewBox.baseVal : null;
    return v && v.width ? { x: v.x, y: v.y, w: v.width, h: v.height } : { x: 0, y: 0, w: 1000, h: 751 };
  })();
  var view = { x: FULL.x, y: FULL.y, w: FULL.w, h: FULL.h };
  function setView(v) {
    view = v;
    if (svg) svg.setAttribute("viewBox", [v.x, v.y, v.w, v.h].map(function (n) { return Math.round(n * 10) / 10; }).join(" "));
  }
  /* A count belongs inside its palika. The middle of a palika's box can fall
     outside a crooked palika, so the point is searched for once, in map
     units, and kept: the nearest point to the middle that is in the shape. */
  var INSIDE = {};
  function inside(code) {
    if (INSIDE[code]) return INSIDE[code];
    var path = PAL[code] && PAL[code].path;
    if (!path) return null;
    var b;
    try { b = path.getBBox(); } catch (e) { return null; }
    var cx = b.x + b.width / 2, cy = b.y + b.height / 2, best = { x: cx, y: cy }, bestD = Infinity;
    var test = function (x, y) {
      try {
        if (path.isPointInFill) {
          var pt = svg.createSVGPoint(); pt.x = x; pt.y = y;
          return path.isPointInFill(pt);
        }
      } catch (e) { /* older engines: take the middle */ }
      return null;
    };
    var first = test(cx, cy);
    if (first !== false) {
      INSIDE[code] = best;
      return best;
    }
    for (var i = 0; i <= 12; i++) for (var j = 0; j <= 12; j++) {
      var x = b.x + b.width * i / 12, y = b.y + b.height * j / 12;
      var d = (x - cx) * (x - cx) + (y - cy) * (y - cy);
      if (d < bestD && test(x, y)) { bestD = d; best = { x: x, y: y }; }
    }
    INSIDE[code] = best;
    return best;
  }
  /* map units -> percent of the drawing as it is currently framed */
  function pct(pt) {
    return { x: 100 * (pt.x - view.x) / view.w, y: 100 * (pt.y - view.y) / view.h };
  }
  /* the frame for one district: its box, padded, widened to the map's own
     proportions so the drawing does not change height as it zooms */
  function districtView(code) {
    var p = DPATH[code];
    if (!p) return null;
    var b;
    try { b = p.getBBox(); } catch (e) { return null; }
    var pad = 0.08, w = b.width * (1 + 2 * pad), h = b.height * (1 + 2 * pad);
    var ratio = FULL.w / FULL.h;
    if (w / h > ratio) h = w / ratio; else w = h * ratio;
    var x = b.x + b.width / 2 - w / 2, y = b.y + b.height / 2 - h / 2;
    return { x: x, y: y, w: w, h: h };
  }

  /* ------------------------------------------------------------ entries */
  var partnerRows = [];     // normalised, from the published document
  var partnerDoc = undefined;

  function officialEntries() {
    return (F.entries || []).map(function (e) {
      return {
        tier: e.kind === "helpline" ? "phone" : "official",
        src: e,
        name: e.name || {},
        adm2: e.district === "outside" ? "outside" : (e.district || null),
        outside: e.outside || "",
        pcode: e.pcode && PAL[e.pcode] ? e.pcode : null,
        services: Object.keys(e.services || {}),
        cadres: Object.keys(e.cadres || {}),
        modes: Object.keys(e.modes || {})
      };
    });
  }
  function normalisePartner(d) {
    var rows = d && Array.isArray(d.rows) ? d.rows : [];
    return rows.map(function (r) {
      var pc = /^NP\d{7}$/.test(String(r.pcode || "")) ? String(r.pcode) : null;
      var adm2 = pc ? pc.slice(0, 6) : (CODE_TO_ADM2[r.district] || null);
      var org = r.org_name || (C.orgByCode && C.orgByCode[r.org] && C.label ? C.label(C.orgByCode[r.org]) : r.org);
      return {
        tier: "partner",
        src: r,
        name: { en: String(org || "") },
        adm2: adm2,
        pcode: pc && PAL[pc] ? pc : null,
        palika: String(r.palika || ""),
        services: Array.isArray(r.activities) ? r.activities.map(String) : [],
        cadres: Array.isArray(r.cadres) ? r.cadres.map(String) : [],
        modes: Array.isArray(r.modalities) ? r.modalities.map(String) : [],
        last: r.last_report || ""
      };
    });
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
    if (state.cadre && CADRE.indexOf(state.cadre) < 0) state.cadre = "";
    if (state.mode && MODE.indexOf(state.mode) < 0) state.mode = "";
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
  function fillAll() {
    fill(sel.svc, "refdir.find.any.svc", SVC.map(function (c) { return [c, codeLabel(C.ACTIVITIES, c)]; }));
    fill(sel.cadre, "refdir.find.any.cadre", CADRE.map(function (c) { return [c, codeLabel(C.CADRES, c)]; }));
    fill(sel.mode, "refdir.find.any.mode", MODE.map(function (c) { return [c, codeLabel(C.MODALITIES, c)]; }));
    fill(sel.dist, "refdir.find.any.dist", DIST.concat([["outside", t("refdir.find.outside")]]));
    fillPalikas();
    ["svc", "cadre", "mode", "dist"].forEach(function (k) { if (sel[k]) sel[k].value = state[k]; });
  }
  function fillPalikas() {
    var items = [];
    if (state.dist && state.dist !== "outside") {
      Object.keys(PAL).forEach(function (pc) { if (PAL[pc].adm2 === state.dist) items.push([pc, PAL[pc].name]); });
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
    if (state.cadre) {
      var ok = has(e.cadres, state.cadre) || (state.cadre === "PSC" && has(e.cadres, "SPSC"));
      if (!ok) return false;
    }
    if (state.mode && !has(e.modes, state.mode)) return false;
    return true;
  }
  /* a helpline is reachable from every place, so place never removes it */
  function matchesWhere(e) {
    if (e.tier === "phone") return true;
    if (!state.dist) return true;
    if (state.dist === "outside") return e.adm2 === "outside";
    if (e.adm2 !== state.dist) return false;
    if (state.pal && e.pcode && e.pcode !== state.pal) return false;
    return true;
  }

  /* ------------------------------------------------------------ render */
  function placeText(e) {
    if (e.tier === "phone") return "";
    if (e.adm2 === "outside") return t("refdir.find.place.outside", { district: e.outside });
    var dn = DIST_NAME[e.adm2] || "";
    if (e.pcode) return t("refdir.find.place.palika", { palika: PAL[e.pcode].name, district: dn });
    if (e.tier === "partner") return t("refdir.find.place.districtPartner", { district: dn });
    return t("refdir.find.place.district", { district: dn });
  }

  function chips(codes, list) {
    var ul = el("ul", "fchips");
    codes.forEach(function (c) { ul.appendChild(el("li", null, codeLabel(list, c))); });
    return ul;
  }

  function card(e) {
    var li = el("li", "fcard");
    var h = el("div", "fc-h");
    var b = el("b", null, e.name.en || ""); b.setAttribute("data-i18n-skip", "");
    h.appendChild(b);
    if (e.name.ne) {
      var np = el("span", "np", e.name.ne); np.setAttribute("lang", "ne"); np.setAttribute("data-i18n-skip", "");
      h.appendChild(np);
    }
    li.appendChild(h);
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

    if (e.tier === "partner") {
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
      li.appendChild(det);
    }
    return li;
  }

  function group(tier, list, emptyNode) {
    var g = el("div", "fgroup");
    g.setAttribute("data-tier", tier);
    var h = el("h3", null, t("refdir.find.tier." + tier));
    if (tier === "partner" && partnerDoc && partnerDoc.mode === "demonstration") {
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
    if (key && key !== "live.published") return t(key);
    return "";
  }

  function count(kind, n) {
    return t("refdir.find.count." + kind + "." + (n === 0 ? "none" : n === 1 ? "one" : "many"), { n: n });
  }

  function render() {
    var all = officialEntries().concat(partnerRows);
    var what = all.filter(matchesWhat);
    var shown = what.filter(matchesWhere);
    var official = shown.filter(function (e) { return e.tier === "official"; });
    var partner = shown.filter(function (e) { return e.tier === "partner"; });
    var phone = shown.filter(function (e) { return e.tier === "phone"; });

    /* the summary line, read aloud when it changes */
    var sum = $("fSum");
    if (sum) {
      var places = official.length + partner.length;
      if (!places && !phone.length) {
        sum.textContent = t("refdir.find.sum0");
      } else {
        sum.textContent = t("refdir.find.sum", { places: count("place", places), phones: count("phone", phone.length) });
      }
    }

    /* the list */
    var res = $("fRes");
    if (res) {
      res.textContent = "";
      res.appendChild(group("official", official, el("p", "fempty", t("refdir.find.none.official"))));
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

  function drawMap(shown) {
    if (!svg) return;
    var pc = {}, dc = {};
    shown.forEach(function (e) {
      if (e.tier === "phone" || !e.adm2 || e.adm2 === "outside") return;
      if (e.pcode) pc[e.pcode] = (pc[e.pcode] || 0) + 1;
      else if (DPATH[e.adm2]) dc[e.adm2] = (dc[e.adm2] || 0) + 1;
    });
    Object.keys(PAL).forEach(function (code) {
      var p = PAL[code].path;
      p.classList.toggle("hit", !!pc[code]);
      p.classList.toggle("sel", code === state.pal);
    });
    Object.keys(DPATH).forEach(function (code) {
      DPATH[code].classList.toggle("hit", !!dc[code]);
      DPATH[code].classList.toggle("sel", code === state.dist);
    });
    if (map) map.classList.toggle("filtering", !!(state.svc || state.cadre || state.mode || state.dist));
    if (!badges || !stage) return;

    /* Choosing a district frames the map on it, so its palikas are big enough
       to point at on a phone. The district names are laid over the whole
       map and would sit in the wrong places, so they step aside while zoomed;
       the bar at the top says where the map is and leads back. */
    var zoom = state.dist && DPATH[state.dist] ? districtView(state.dist) : null;
    setView(zoom || FULL);
    stage.classList.toggle("zoomed", !!zoom);
    var bar = $("fZoom");
    if (bar) {
      bar.hidden = !zoom;
      bar.textContent = "";
      if (zoom) {
        bar.appendChild(el("b", null, DIST_NAME[state.dist]));
        var back = el("button", "fback", t("refdir.find.zoom.back"));
        back.type = "button";
        back.addEventListener("click", function () { chooseDistrict(""); });
        bar.appendChild(back);
        if (dc[state.dist]) {
          var withPalikas = Object.keys(pc).some(function (c) { return PAL[c].adm2 === state.dist; });
          bar.appendChild(el("span", "fdl", t(withPalikas ? "refdir.find.zoom.districtLevel" : "refdir.find.zoom.districtOnly",
            { n: dc[state.dist] })));
        }
      }
    }

    /* a keyboard user who pressed a count keeps their place on the new one */
    var act = document.activeElement;
    var had = act && act.classList && (act.classList.contains("fbadge") || act.classList.contains("dcount"))
      ? act.getAttribute("data-code") : null;
    badges.textContent = "";
    stage.querySelectorAll(".dlab .dcount").forEach(function (c) { c.parentNode.removeChild(c); });

    function button(cls, n, code, label, onClick) {
      var bt = el("button", cls, String(n));
      bt.type = "button";
      bt.setAttribute("data-code", code);
      bt.setAttribute("aria-label", label);
      bt.addEventListener("click", onClick);
      return bt;
    }

    /* On the whole map, a phone shows one total per district, riding inside
       the district's name (which the map already places clear of the others),
       and a wider screen a count per palika. A count without a palika -- a
       hospital whose address names none -- always rides in the name. */
    var narrow = stage.clientWidth < 560;
    var perDist = {};
    var items = [];
    if (!zoom) {
      Object.keys(pc).forEach(function (code) {
        if (narrow) { var d = PAL[code].adm2; perDist[d] = (perDist[d] || 0) + pc[code]; }
      });
      Object.keys(dc).forEach(function (d) { perDist[d] = (perDist[d] || 0) + dc[d]; });
      var labs = [].slice.call(stage.querySelectorAll(".dlab"));
      Object.keys(perDist).forEach(function (code) {
        var lab = labs.filter(function (l) { return l.firstChild && l.firstChild.nodeValue === DIST_NAME[code]; })[0];
        if (!lab) return;
        var key = dc[code] === perDist[code] ? "refdir.find.badge.district" : "refdir.find.badge.districtAll";
        lab.appendChild(button("dcount", perDist[code], code,
          t(key, { place: DIST_NAME[code], n: perDist[code] }),
          function () { chooseDistrict(code); }));
      });
    }
    Object.keys(pc).forEach(function (code) {
      if (!zoom && narrow) return;
      var at = inside(code);
      if (!at) return;
      var q = pct(at);
      var bt = button("fbadge", pc[code], code,
        t("refdir.find.badge", { place: PAL[code].name, n: pc[code] }),
        function () { choosePalika(code); });
      bt.style.left = q.x.toFixed(2) + "%";
      bt.style.top = q.y.toFixed(2) + "%";
      badges.appendChild(bt);
      items.push({ el: bt, px: q.x, py: q.y });
    });

    /* Where two counts, or a count and a district's name, still overlap they
       are nudged apart -- never by more than half a count, so a count cannot
       wander into a palika it does not describe. */
    var sr = stage.getBoundingClientRect();
    if (sr.width && items.length > 0) {
      var h = items[0].el.offsetHeight || 24;
      items.forEach(function (it) {
        it.x0 = it.x = it.px * sr.width / 100; it.y0 = it.y = it.py * sr.height / 100;
        it.w = it.el.offsetWidth || h;
      });
      var walls = zoom ? [] : [].slice.call(stage.querySelectorAll(".dlab")).map(function (l) {
        var r = l.getBoundingClientRect();
        return { x: r.left - sr.left + r.width / 2, y: r.top - sr.top + r.height / 2, w: r.width, h: r.height };
      });
      var limit = h / 2;
      for (var round = 0; round < 30; round++) {
        var moved = false;
        items.forEach(function (a, i) {
          var fx = 0, fy = 0;
          function push(bx, by, bw, bh) {
            var ox = (a.w + bw) / 2 + 2 - Math.abs(a.x - bx);
            var oy = (h + bh) / 2 + 2 - Math.abs(a.y - by);
            if (ox > 0 && oy > 0) {
              if (ox < oy) fx += (a.x >= bx ? 1 : -1) * ox / 2;
              else fy += (a.y >= by ? 1 : -1) * oy / 2;
            }
          }
          items.forEach(function (b, j) { if (i !== j) push(b.x, b.y, b.w, h); });
          walls.forEach(function (b) { push(b.x, b.y, b.w, b.h); });
          if (fx || fy) {
            var nx = Math.max(a.w / 2, Math.min(sr.width - a.w / 2, a.x + fx));
            var ny = Math.max(h / 2, Math.min(sr.height - h / 2, a.y + fy));
            var dx = nx - a.x0, dy = ny - a.y0, dist = Math.sqrt(dx * dx + dy * dy);
            if (dist > limit) { nx = a.x0 + dx * limit / dist; ny = a.y0 + dy * limit / dist; }
            if (Math.abs(nx - a.x) > 0.3 || Math.abs(ny - a.y) > 0.3) moved = true;
            a.x = nx; a.y = ny;
          }
        });
        if (!moved) break;
      }
      items.forEach(function (it) {
        /* a nudge that carried the count out of its own palika is undone:
           covering a name is better than pointing at the wrong place */
        var mx = view.x + view.w * it.x / sr.width, my = view.y + view.h * it.y / sr.height;
        var path = PAL[it.el.getAttribute("data-code")].path;
        try {
          if (path.isPointInFill) {
            var pt = svg.createSVGPoint(); pt.x = mx; pt.y = my;
            if (!path.isPointInFill(pt)) { it.x = it.x0; it.y = it.y0; }
          }
        } catch (e) { /* keep the nudge */ }
        it.el.style.left = (100 * it.x / sr.width).toFixed(2) + "%";
        it.el.style.top = (100 * it.y / sr.height).toFixed(2) + "%";
      });
    }
    lastNarrow = narrow;

    if (had) {
      var again = stage.querySelector('.fbadge[data-code="' + had + '"], .dcount[data-code="' + had + '"]');
      if (again) again.focus();
    }
    var k = $("keyHit");
    if (k) k.hidden = !items.length;
    var kd = $("keyDhit");
    if (kd) kd.hidden = !Object.keys(perDist).length;
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

  /* the map: a palika can be chosen by clicking it; hovering names it */
  if (svg) {
    svg.addEventListener("click", function (ev) {
      var p = ev.target.closest && ev.target.closest(".pal[data-pcode]");
      if (p) choosePalika(p.getAttribute("data-pcode"));
    });
    svg.addEventListener("mousemove", function (ev) {
      var p = ev.target.closest && ev.target.closest(".pal[data-pcode]");
      if (!p || !tip || !stage) { if (tip) tip.hidden = true; return; }
      var code = p.getAttribute("data-pcode"), info = PAL[code];
      var n = 0;
      officialEntries().concat(partnerRows).filter(matchesWhat).forEach(function (e) {
        if (e.pcode === code) n++;
      });
      tip.textContent = "";
      tip.appendChild(el("b", null, info.name));
      tip.appendChild(el("span", null, DIST_NAME[info.adm2] || ""));
      tip.appendChild(el("span", "n", n ? t(n === 1 ? "refdir.find.tip.one" : "refdir.find.tip.many", { n: n })
                                        : t("refdir.find.tip.none")));
      var r = stage.getBoundingClientRect();
      var x = ev.clientX - r.left, y = ev.clientY - r.top;
      tip.style.left = Math.min(Math.max(x, 70), r.width - 70) + "px";
      tip.style.top = y + "px";
      tip.hidden = false;
    });
    svg.addEventListener("mouseleave", function () { if (tip) tip.hidden = true; });
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
  var ds = $("dirState");
  if (ds && window.MutationObserver) {
    new MutationObserver(function () { render(); }).observe(ds, { attributes: true, attributeFilter: ["data-i18n-live"] });
  }
  document.addEventListener("i18n:changed", function () { fillAll(); render(); });
  /* redraw only when the map crosses the phone width, where counts change form */
  var lastNarrow = null, resizeTimer = 0;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (stage && (stage.clientWidth < 560) !== lastNarrow) render();
    }, 150);
  });

  readUrl();
  fillAll();
  render();

  /* for whoever builds the publish step: paint a partner document that has
     not been published, with no network, to see what the filters will do */
  window.REFERRAL_FIND = {
    preview: function (doc) { previewing = true; partnerDoc = doc; partnerRows = normalisePartner(doc); render(); }
  };
})();
