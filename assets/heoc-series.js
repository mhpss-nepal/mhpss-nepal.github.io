/* =====================================================================
   MHPSS in the Ministry's situation reports -- Flood Response, section 2
   ---------------------------------------------------------------------
   The figures below are the ones the Ministry of Health and Food Safety
   prints in the "Mental Health and Psychosocial Support" section of its
   Situation Report on the Health Sector Response to the Flash Flood in
   Rasuwa (Health Emergency Operation Centre). Each row is one report, read
   on its own page; nothing here is computed, estimated or added up.

   Why the series starts at #21: up to report #12 the headline figure was
   "total people reached"; from #21 it is "PFA / MHPSS services till date",
   a count of services, not of people. The two units are not drawn on one
   line and are never compared.

   Reports #23, #25, #27 and #29 are listed on the Ministry's dashboard but
   their files could not be opened (1 October 2026); the line joins the
   reports that could, at their own dates.

   TO ADD A REPORT: append its row, with the date printed on page 1 and the
   four numbers as printed. Nothing else changes.
   ===================================================================== */
window.HEOC_SERIES = {
  read: "2026-10-01",
  source: "https://heoc.mohp.gov.np/flashflood/",
  rows: [
    /* report, date printed, services till date, personnel in field,
       services in 24 h (null where the report has no such column),
       helpline calls as printed */
    { n: 21, d: "2026-09-15", svc: 9858,  staff: 137, day: null, calls: 4 },
    { n: 22, d: "2026-09-16", svc: 10382, staff: 147, day: null, calls: 0 },
    { n: 24, d: "2026-09-18", svc: 11251, staff: 129, day: null, calls: 3 },
    { n: 26, d: "2026-09-20", svc: 11781, staff: 91,  day: null, calls: 3 },
    { n: 28, d: "2026-09-22", svc: 12634, staff: 91,  day: null, calls: 5 },
    { n: 30, d: "2026-09-24", svc: 13559, staff: 91,  day: 590,  calls: 5 },
    { n: 31, d: "2026-09-25", svc: 13703, staff: 73,  day: 144,  calls: 3 },
    { n: 32, d: "2026-09-26", svc: 13761, staff: 46,  day: 58,   calls: 4 },
    { n: 33, d: "2026-09-27", svc: 13829, staff: 54,  day: 68,   calls: 2 },
    { n: 34, d: "2026-09-28", svc: 13997, staff: 57,  day: 168,  calls: 3 },
    { n: 35, d: "2026-09-29", svc: 14243, staff: 57,  day: 246,  calls: 1 },
    { n: 36, d: "2026-09-30", svc: 14427, staff: 57,  day: 184,  calls: 2 }
  ]
};

(function () {
  "use strict";
  var S = window.HEOC_SERIES;
  var root = document.querySelector("[data-heoc]");
  if (!S || !root) return;

  function t(k, vars) { return window.I18N ? window.I18N.t(k, vars) : k; }
  function nf(x) { return x == null ? "—" : x.toLocaleString("en-US"); }
  function dlong(iso) {
    var d = new Date(iso + "T00:00:00Z");
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).replace(/ /g, " ");
  }
  function dshort(iso) {
    var d = new Date(iso + "T00:00:00Z");
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).replace(/ /g, " ");
  }
  var NS = "http://www.w3.org/2000/svg";
  function sv(tag, attrs, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  function niceMax(v) {
    var p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p;
    var s = m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10;
    return s * p;
  }

  var rows = S.rows.slice();
  var last = rows[rows.length - 1];
  var t0 = Date.parse(rows[0].d), t1 = Date.parse(last.d);

  /* one line, one measure, one axis. Two measures of different size are two
     charts, never one chart with two scales. */
  function chart(host, field, titleKey, unitKey) {
    host.innerHTML = "";
    /* drawn at the width it is shown at, so the axis text stays at reading
       size on a phone instead of shrinking with a fixed drawing */
    var W = Math.max(300, Math.round(host.clientWidth || 560)), H = W < 460 ? 210 : 230, L = 48, R = 16, T = 18, B = 34;
    var max = niceMax(Math.max.apply(null, rows.map(function (r) { return r[field]; })) * 1.05);
    function x(r) { return L + (Date.parse(r.d) - t0) / (t1 - t0) * (W - L - R); }
    function y(v) { return T + (1 - v / max) * (H - T - B); }

    var h = document.createElement("h4"); h.textContent = t(titleKey); host.appendChild(h);
    var wrap = document.createElement("div"); wrap.className = "hc-plot"; host.appendChild(wrap);
    var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": t(titleKey) + ": " + nf(rows[0][field]) + " → " + nf(last[field]) });
    wrap.appendChild(svg);

    var g = sv("g", { "font-family": "Mukta,sans-serif", "font-size": "12", fill: "#5c5c5a" });
    svg.appendChild(g);
    for (var i = 0; i <= 4; i++) {
      var v = max * i / 4, yy = y(v);
      g.appendChild(sv("line", { x1: L, x2: W - R, y1: yy, y2: yy, stroke: "#e6e6e4", "stroke-width": 1 }));
      g.appendChild(sv("text", { x: L - 8, y: yy + 4, "text-anchor": "end" }, nf(Math.round(v))));
    }
    [rows[0], rows[Math.floor(rows.length / 2)], last].forEach(function (r) {
      g.appendChild(sv("text", { x: x(r), y: H - 10, "text-anchor": "middle" }, dshort(r.d)));
    });
    var d = rows.map(function (r, i) { return (i ? "L" : "M") + x(r).toFixed(1) + " " + y(r[field]).toFixed(1); }).join(" ");
    svg.appendChild(sv("path", { d: d, fill: "none", stroke: "#006996", "stroke-width": 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" }));

    var tip = document.createElement("div"); tip.className = "hc-tip"; tip.hidden = true; wrap.appendChild(tip);
    rows.forEach(function (r) {
      var cx = x(r), cy = y(r[field]);
      svg.appendChild(sv("circle", { cx: cx, cy: cy, r: 4.5, fill: "#006996", stroke: "#fff", "stroke-width": 2 }));
      var hit = sv("circle", { cx: cx, cy: cy, r: 14, fill: "transparent", tabindex: 0,
        "aria-label": t("flood.heoc.report", { n: r.n }) + ", " + dlong(r.d) + ": " + nf(r[field]) });
      function show() {
        tip.innerHTML = "<b>" + nf(r[field]) + "</b> " + t(unitKey) + "<br>" +
          t("flood.heoc.report", { n: r.n }) + " · " + dlong(r.d);
        tip.hidden = false;
        var px = cx / W * 100, py = cy / H * 100;
        tip.style.left = Math.min(Math.max(px, 18), 82) + "%";
        tip.style.top = py + "%";
      }
      hit.addEventListener("mouseenter", show); hit.addEventListener("focus", show);
      hit.addEventListener("mouseleave", function () { tip.hidden = true; });
      hit.addEventListener("blur", function () { tip.hidden = true; });
      svg.appendChild(hit);
    });
    /* the end value, labelled once -- not a number on every point */
    svg.appendChild(sv("text", { x: x(last) - 8, y: y(last[field]) - 10, "text-anchor": "end",
      "font-family": "Mukta,sans-serif", "font-size": "13", "font-weight": "700", fill: "#153f4c" }, nf(last[field])));
  }

  function table(host) {
    var head = "<thead><tr><th>" + t("flood.heoc.col.report") + "</th><th>" + t("flood.heoc.col.date") +
      "</th><th class=\"n\">" + t("flood.heoc.col.svc") + "</th><th class=\"n\">" + t("flood.heoc.col.staff") +
      "</th><th class=\"n\">" + t("flood.heoc.col.day") + "</th><th class=\"n\">" + t("flood.heoc.col.calls") + "</th></tr></thead>";
    var body = rows.slice().reverse().map(function (r) {
      return "<tr><td>#" + r.n + "</td><td>" + dlong(r.d) + "</td><td class=\"n\">" + nf(r.svc) +
        "</td><td class=\"n\">" + nf(r.staff) + "</td><td class=\"n\">" + nf(r.day) + "</td><td class=\"n\">" + nf(r.calls) + "</td></tr>";
    }).join("");
    host.innerHTML = "<table class=\"t2\">" + head + "<tbody>" + body + "</tbody></table>";
  }

  function render() {
    var k = root.querySelectorAll("[data-heoc-k]");
    for (var i = 0; i < k.length; i++) {
      var f = k[i].getAttribute("data-heoc-k");
      k[i].textContent = nf(last[f]);
    }
    var asof = root.querySelector("[data-heoc-asof]");
    if (asof) asof.textContent = t("flood.heoc.asof", { n: last.n, date: dlong(last.d) });
    chart(root.querySelector("[data-heoc-chart=svc]"), "svc", "flood.heoc.ch.svc", "flood.heoc.unit.svc");
    chart(root.querySelector("[data-heoc-chart=staff]"), "staff", "flood.heoc.ch.staff", "flood.heoc.unit.staff");
    table(root.querySelector("[data-heoc-table]"));
  }
  if (window.I18N) render(); else document.addEventListener("DOMContentLoaded", render);
  document.addEventListener("i18n:changed", render);
  var lastW = 0, timer = null;
  window.addEventListener("resize", function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var w = root.clientWidth;
      if (Math.abs(w - lastW) > 40) { lastW = w; render(); }
    }, 200);
  });
})();
