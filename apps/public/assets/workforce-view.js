/* =====================================================================
   MHPSS Nepal -- "Staff deployed, by district and palika"
   (referral-directory.html, section 5)
   ---------------------------------------------------------------------
   Layer 3. Draws window.WORKFORCE (assets/workforce.js, built by
   tools/workforce-build.py from the de-identified workforce roster):
     - four headline numbers and the people on the lists by cadre
     - a map that shades each palika by how many staff name it as their place
       of work, with the number on it; a district carries the people whose
       place of work names no palika. A person is never a point.
     - a table of districts by cadre, and for each district its palikas by
       cadre and the organisations with staff listed there
   A number of one or two people arrives as "lt3" and is written "<3"; a
   number hidden so that a smaller one beside it cannot be worked out arrives
   as "ge3" and is written "3+". Nothing here can show more than the file holds.
   ===================================================================== */
(function () {
  "use strict";
  var W = window.WORKFORCE, G = window.REFERRAL_GEO;
  var root = document.getElementById("wf");
  if (!root || !W || !G) return;

  function t(key, vars) { return window.I18N ? window.I18N.t(key, vars) : key; }
  function isNe() { return (document.documentElement.getAttribute("lang") || "").slice(0, 2) === "ne"; }
  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var $ = function (id) { return document.getElementById(id); };

  var DIST = {}, PAL = {};
  (G.dist || []).forEach(function (x) { DIST[x.d] = x; });
  (G.pal || []).forEach(function (x) { if (x.r !== "pin") PAL[x.p] = x; });
  /* a district the map has no Nepali name for takes the code list's */
  var ADM2_CODE = { NP0327: "KTM", NP0328: "NUW", NP0329: "RAS", NP0330: "DHA", NP0335: "CHT",
                    NP0436: "GOR", NP0440: "TAN", NP0447: "NAW" };
  function distName(code) {
    if (code === "outside") return t("wf.row.outside");
    if (code === "none") return t("wf.row.none");
    var x = DIST[code];
    if (!x) return code;
    if (isNe() && x.ne) return x.ne;
    if (isNe()) {
      var C = window.CODES;
      try { var o = C && C.districtByCode[ADM2_CODE[code]]; if (o && C.label) return C.label(o); } catch (e) { /* the English name stands */ }
    }
    return x.n;
  }
  function palName(code) {
    if (code === "unnamed") return t("wf.row.unnamed");
    var x = PAL[code]; return x ? (isNe() && x.ne ? x.ne : x.n) : code;
  }

  var CAD = Array.isArray(W.cadre_order) ? W.cadre_order :
    ["PSYT", "CPSY", "PSY", "PNUR", "MO", "HW", "PSC", "CPSW", "SW", "FCHV", "VOL", "OTH", "NS"];

  /* a count as written on the page */
  function show(v) { return v === "lt3" ? "<3" : v === "ge3" ? "3+" : String(v); }
  function isNum(v) { return typeof v === "number"; }
  function cellHtml(v) {
    if (v === "lt3") return '<td class="n s" title="' + esc(t("wf.lt3")) + '">&lt;3</td>';
    if (v === "ge3") return '<td class="n s" title="' + esc(t("wf.ge3")) + '">3+</td>';
    return '<td class="n' + (v === 0 ? " z" : "") + '">' + esc(v) + "</td>";
  }

  var districts = (W.districts || []).filter(function (r) { return DIST[r.d]; });
  var extra = (W.districts || []).filter(function (r) { return !DIST[r.d]; });
  var palRows = {};
  Object.keys(W.palikas || {}).forEach(function (d) {
    (W.palikas[d] || []).forEach(function (r) { if (r.p !== "unnamed") palRows[r.p] = r; });
  });

  /* ------------------------------------------------------------ headline */
  function kpis() {
    var box = $("wfKpis"); if (!box) return;
    var named = Object.keys(palRows).length;
    box.innerHTML =
      '<div class="kpi lead"><span class="n">' + esc(show(W.people)) + '</span><span class="l">' + esc(t("wf.kpi.people")) + "</span></div>" +
      '<div class="kpi"><span class="n">' + esc(districts.length) + '</span><span class="l">' + esc(t("wf.kpi.districts")) + "</span></div>" +
      '<div class="kpi"><span class="n">' + esc(named) + '</span><span class="l">' + esc(t("wf.kpi.palikas")) + "</span></div>" +
      '<div class="kpi"><span class="n">' + esc(show(W.placed && W.placed.none)) + '</span><span class="l">' + esc(t("wf.kpi.none")) + "</span></div>";
  }

  function cadres() {
    var ul = $("wfCadres"); if (!ul) return;
    var max = 0;
    CAD.forEach(function (c) { var v = W.cadres && W.cadres[c]; if (isNum(v) && v > max) max = v; });
    ul.innerHTML = CAD.map(function (c) {
      var v = W.cadres ? W.cadres[c] : 0;
      var w = isNum(v) && max ? Math.max(1, Math.round(100 * v / max)) : 0;
      return '<li><span class="hl3">' + esc(t("wf.cad." + c)) + '</span><span class="track">' +
        (w ? '<span class="bar3" style="width:' + w + '%"></span>' : "") +
        '<span class="val">' + esc(show(v)) + "</span></span></li>";
    }).join("");
  }

  /* ------------------------------------------------------------ tables */
  function head(firstKey) {
    return "<thead><tr><th>" + esc(t(firstKey)) + "</th>" +
      CAD.map(function (c) { return '<th class="n">' + esc(t("wf.cad." + c)) + "</th>"; }).join("") +
      '<th class="n">' + esc(t("wf.col.total")) + "</th></tr></thead>";
  }
  function row(label, r, attrs) {
    var h = "<tr" + (attrs || "") + '><td class="k">' + esc(label) + "</td>";
    if (r.c) h += CAD.map(function (c) { return cellHtml(r.c[c]); }).join("");
    else h += '<td class="pend" colspan="' + CAD.length + '">' + esc(t("wf.row.small")) + "</td>";
    return h + cellHtml(r.n) + "</tr>";
  }
  function table() {
    var tb = $("wfTable"); if (!tb) return;
    var body = districts.concat(extra).map(function (r) {
      return row(distName(r.d), r, ' data-dist="' + esc(r.d) + '"');
    }).join("");
    var foot = '<tfoot><tr><td class="k">' + esc(t("wf.row.all")) + "</td>" +
      CAD.map(function (c) { return cellHtml(W.cadres ? W.cadres[c] : 0); }).join("") + cellHtml(W.people) + "</tr></tfoot>";
    tb.innerHTML = "<caption>" + esc(t("wf.table.caption")) + "</caption>" + head("wf.col.district") + "<tbody>" + body + "</tbody>" + foot;
  }

  function orgLine(d) {
    var items = (W.organisations || {})[d] || [];
    if (!items.length) return "";
    return '<p class="wforgs"><b>' + esc(t("wf.orgs")) + "</b> " + items.map(function (it) {
      var name = it[0] ? it[0] : t("wf.org.notStated");
      return '<span class="wforg">' + esc(name) + (it[2] ? " " + esc(t("wf.org.written")) : "") +
        ' <b>' + esc(show(it[1])) + "</b></span>";
    }).join(" · ") + "</p>";
  }
  function details() {
    var box = $("wfDistricts"); if (!box) return;
    var open = {};
    box.querySelectorAll("details[open]").forEach(function (d) { open[d.getAttribute("data-dist")] = true; });
    box.innerHTML = districts.filter(function (r) { return (W.palikas || {})[r.d]; }).map(function (r) {
      var rows = W.palikas[r.d] || [];
      return '<details class="wfd" data-dist="' + esc(r.d) + '"' + (open[r.d] ? " open" : "") + "><summary>" +
        esc(t("wf.district.summary", { district: distName(r.d), n: show(r.n) })) + '</summary><div class="in">' +
        '<div class="tscroll"><table class="t2 wft">' + head("wf.col.palika") + "<tbody>" +
        rows.map(function (p) { return row(palName(p.p), p, ' data-pcode="' + esc(p.p) + '"'); }).join("") +
        "</tbody></table></div>" + orgLine(r.d) + "</div></details>";
    }).join("");
  }

  /* ------------------------------------------------------------ the map */
  var M = null;
  function shade(v) {
    if (v == null) return null;
    if (v === "lt3") return { color: "#006996", opacity: 0.16 };
    if (v === "ge3") return { color: "#006996", opacity: 0.32 };
    if (v >= 25) return { color: "#006996", opacity: 0.74 };
    if (v >= 10) return { color: "#006996", opacity: 0.52 };
    if (v >= 3) return { color: "#006996", opacity: 0.32 };
    return null;
  }
  function openDistrict(code, pcode) {
    var d = document.querySelector('.wfd[data-dist="' + code + '"]');
    if (!d) return;
    d.open = true;
    document.querySelectorAll(".wft tr.on").forEach(function (tr) { tr.classList.remove("on"); });
    var target = pcode ? d.querySelector('tr[data-pcode="' + pcode + '"]') : d;
    if (target && target.classList) target.classList.add("on");
    (target || d).scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function drawMap() {
    var el = $("wfMap");
    if (!el || !window.REFERRAL_MAP || !window.L) { if (el) el.hidden = true; return; }
    try {
      M = window.REFERRAL_MAP.create(el, {
        ariaKey: "wf.maparia",
        fill: function (p) { var r = palRows[p]; return r ? shade(r.n) : null; },
        tip: function (p) {
          var r = palRows[p];
          if (!r) return t("wf.tip.none");
          return r.n === "lt3" ? t("wf.tip.lt3") : r.n === "ge3" ? t("wf.tip.ge3") : t("wf.tip.n", { n: r.n });
        },
        badge: show,
        badgeTitle: function (kind, x, n) {
          var name = isNe() && x.ne ? x.ne : x.n;
          return t(kind === "palika" ? "wf.badge.palika" : "wf.badge.district", { place: name, n: show(n) });
        },
        onPalika: function (p) { var r = palRows[p]; if (r) openDistrict(p.slice(0, 6), p); },
        onDistrict: function (code) { openDistrict(code); }
      });
    } catch (e) {
      M = null;
      if (window.console) console.warn("staff map not drawn:", e && e.message);
    }
    if (!M) { el.hidden = true; return; }
    var palCounts = {}, distCounts = {}, hit = {};
    Object.keys(palRows).forEach(function (p) { palCounts[p] = palRows[p].n; hit[p] = true; });
    Object.keys(W.palikas || {}).forEach(function (d) {
      (W.palikas[d] || []).forEach(function (r) { if (r.p === "unnamed") distCounts[d] = r.n; });
    });
    mapData = { pins: [], palCounts: palCounts, distCounts: distCounts, hit: hit, pal: "", dist: "" };
    M.update(mapData);
    M.invalidate(); frame();
  }
  var mapData = null;
  /* frame the districts whose palikas are drawn with staff, not the whole map */
  function frame() {
    if (!M) return;
    var withPalikas = Object.keys(W.palikas || {}).filter(function (d) { return DIST[d]; });
    if (M.fitDistricts) M.fitDistricts(withPalikas); else M.fitAll();
  }

  function all() { kpis(); cadres(); table(); details(); }
  all();
  drawMap();
  /* the counts' titles and the hover lines are written in the page's language */
  document.addEventListener("i18n:changed", function () {
    all();
    if (M) { M.relabel(); if (mapData) M.update(mapData); }
  });
})();
