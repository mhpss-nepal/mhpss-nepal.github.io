/* =====================================================================
   MHPSS Nepal -- the public website's only read from the register side
   ---------------------------------------------------------------------
   Client intent: Layer 3 reads public_stats aggregates rather than the raw
   register. Whether this read is authorized is a server decision. The
   authoritative Rules are not versioned here, so server enforcement is
   unverified and this branch must not be deployed.

   What this file does NOT do, on purpose:
     - no sign-in, no account, no queue, no sync strip (that is fb.js, for
       the field forms and the hub; a public page has no business showing
       "records reach coordination as you save them")
     - no read of `submissions`, ever
     - no number shown that was not published, and no count below the
       published floor (`suppressed_below`), even if a document carries one
       by mistake -- the floor is enforced here as well as by the publisher

   The document shapes are the contract with whoever publishes them. They
   are written down in full with the project documents; schema 1:

   public_stats/flood_response
     schema 1 · basis (string) · computed_at (server time) ·
     period_from, period_to ("YYYY-MM-DD") · suppressed_below (number) ·
     reports, contacts, organisations, palikas (numbers) ·
     districts [{code, reports, contacts, organisations}] ·
     families  [{family, contacts}]

   public_stats/referral_directory
     schema 1 · basis · computed_at · period_from, period_to ·
     rows [{district, pcode, palika, org, org_name, activities[], last_report}]

   The Firebase SDK version is kept in step with assets/fb.js.
   ===================================================================== */
(function () {
  "use strict";

  var SDK = "https://www.gstatic.com/firebasejs/10.13.0/";   /* same as fb.js */
  var cfg = window.FB_CONFIG || {};
  var configured = !!(cfg.projectId && cfg.apiKey);
  var dbPromise = null;
  var FLOOR = 10;   /* used only when a document does not declare its own */

  function t(key, vars) {
    return window.I18N ? window.I18N.t(key, vars) : key;
  }
  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function num(n) {
    return (typeof n === "number" && isFinite(n)) ? n.toLocaleString("en-GB") : "—";
  }
  /* A count below the floor, drawn on its own, is shown as "fewer than N" and
     never as itself. This is now only a last-ditch guard for a lone value:
     redaction is applied to the WHOLE document before anything is drawn (see
     `redact` below), so a suppressed ROW is dropped rather than labelled. */
  function safe(n, floor) {
    if (typeof n !== "number" || !isFinite(n)) return "—";
    if (n > 0 && n < floor) return t("live.fewer", { n: floor });
    return num(n);
  }
  /* ---------- analysis-wide redaction (defence in depth) ----------------
     The publisher drops a below-floor row and withholds the totals it fed.
     This page must never trust a document to have done that: a raw value
     already written to the collection is exposed to anyone who reads the
     document directly, so this renderer must not be the place that reveals it.

     The same decision is therefore computed here -- the SAME algorithm as the
     publisher's `redactPublicBody`, so that redacting an already-redacted
     document is a no-op and the page cannot depend on a withheld value:
       - a document may not declare a floor below this page's own floor;
       - a row carrying a below-floor count is dropped whole, never drawn as
         "fewer than N" with its category label intact;
       - when any row is dropped, every scalar count outside a row is withheld,
         so the hidden cell cannot be recovered by subtracting the published
         parts from a published total;
       - every count goes through the same floor (organisation and palika
         counts used to bypass it entirely). */
  var NOT_A_COUNT = {
    schema: 1, schema_version: 1, suppressed_below: 1,
    period_from: 1, period_to: 1, codes_version: 1
  };
  function isPlainObject(v) { return !!v && typeof v === "object" && !Array.isArray(v); }
  function isRowFamily(v) { return Array.isArray(v) && v.length > 0 && isPlainObject(v[0]); }
  /* a deep copy of the plain structure; a non-plain value (a Firestore
     Timestamp on computed_at, say) is kept by reference so its methods survive */
  function clone(node) {
    if (Array.isArray(node)) return node.map(clone);
    if (isPlainObject(node)) {
      var c = {};
      Object.keys(node).forEach(function (k) { c[k] = clone(node[k]); });
      return c;
    }
    return node;
  }
  function rowHasBelowFloor(row, floor) {
    var keys = Object.keys(row);
    for (var i = 0; i < keys.length; i++) {
      if (NOT_A_COUNT[keys[i]]) continue;
      var v = row[keys[i]];
      if (typeof v === "number" && isFinite(v) && v > 0 && v < floor) return true;
    }
    return false;
  }
  function redact(d) {
    var declared = (typeof d.suppressed_below === "number" && isFinite(d.suppressed_below))
      ? Math.floor(d.suppressed_below) : FLOOR;
    var floor = Math.max(FLOOR, declared);
    function small(n) { return typeof n === "number" && isFinite(n) && n > 0 && n < floor; }
    var state = { dropped: false };

    function dropRows(node) {
      if (Array.isArray(node)) {
        var rowFamily = isRowFamily(node);
        var kept = [];
        node.forEach(function (item) {
          if (rowFamily && isPlainObject(item)) {
            if (rowHasBelowFloor(item, floor)) { state.dropped = true; return; }
            kept.push(dropRows(item));
          } else {
            kept.push(dropRows(item));
          }
        });
        return kept;
      }
      if (isPlainObject(node)) {
        Object.keys(node).forEach(function (k) { node[k] = dropRows(node[k]); });
      }
      return node;
    }
    function nullAggregates(node, inRow) {
      if (Array.isArray(node)) {
        var rowFamily = isRowFamily(node);
        node.forEach(function (item) { nullAggregates(item, rowFamily); });
        return node;
      }
      if (isPlainObject(node)) {
        Object.keys(node).forEach(function (k) {
          if (NOT_A_COUNT[k]) return;
          var v = node[k];
          if (typeof v === "number") {
            if (small(v) || (state.dropped && !inRow)) node[k] = null;
          } else {
            nullAggregates(v, false);
          }
        });
      }
      return node;
    }

    var out = clone(d);
    out = dropRows(out);
    out.suppressed_below = floor;
    return nullAggregates(out, false);
  }
  /* the published basis is a coordinator's sentence; end it before the next one */
  function sentence(v) {
    var x = String(v == null ? "" : v).trim();
    return x && !/[.!?…]$/.test(x) ? x + "." : x;
  }
  function when(ts) {
    try {
      var d = ts && typeof ts.toDate === "function" ? ts.toDate() : null;
      if (!d) return "";
      return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) +
        ", " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    } catch (e) { return ""; }
  }

  function db() {
    if (!configured) return Promise.reject(new Error("not configured"));
    if (!dbPromise) {
      dbPromise = Promise.all([
        import(SDK + "firebase-app.js"),
        import(SDK + "firebase-firestore.js")
      ]).then(function (m) {
        /* a named app, so a page that one day also loads fb.js does not
           collide with the default one */
        var app;
        try { app = m[0].getApp("public3"); }
        catch (e) { app = m[0].initializeApp(cfg, "public3"); }
        return { fs: m[1], db: m[1].getFirestore(app) };
      });
    }
    return dbPromise;
  }

  /* watch(docId, onDoc(data|null), onErr(message)) -> unsubscribe */
  function watch(docId, onDoc, onErr) {
    var off = function () {};
    var stopped = false;
    db().then(function (h) {
      if (stopped) return;
      off = h.fs.onSnapshot(h.fs.doc(h.db, "public_stats", docId), function (snap) {
        onDoc(snap.exists() ? snap.data() : null);
      }, function (e) {
        onErr(e && e.message ? e.message : String(e));
      });
    }).catch(function (e) {
      onErr(e && e.message ? e.message : String(e));
    });
    return function () { stopped = true; off(); };
  }

  /* ---------------------------------------------------------- rendering */
  function setState(el, panel, key, vars, on) {
    if (!el) return;
    el.setAttribute("data-i18n-live", key);
    el.textContent = t(key, vars);
    if (panel) panel.classList.toggle("on", !!on);
  }

  function floodBody(d) {
    /* Defence in depth: the publisher refuses a declared floor below the
       policy minimum, but a document already in the collection must not be
       able to LOWER this page's floor either. `redact()` has already replaced
       a below-floor declaration, and this repeats the floor rule for the case
       where floodBody is reached directly. */
    var floor = (typeof d.suppressed_below === "number" && d.suppressed_below >= FLOOR)
      ? d.suppressed_below : FLOOR;
    var C = window.CODES;
    var h = [];
    /* Every published count goes through the same floor. The organisation and
       palika figures used to be drawn with a plain number formatter, so a
       below-floor count there was never suppressed at all. */
    h.push('<div class="kpis">' +
      '<div class="kpi lead"><span class="n">' + safe(d.contacts, floor) + '</span><span class="l">' +
        esc(t("live.flood.contacts")) + '</span></div>' +
      '<div class="kpi"><span class="n">' + safe(d.reports, floor) + '</span><span class="l">' +
        esc(t("live.flood.reports")) + '</span></div>' +
      '<div class="kpi"><span class="n">' + safe(d.organisations, floor) + '</span><span class="l">' +
        esc(t("live.flood.orgs")) + '</span></div>' +
      '<div class="kpi"><span class="n">' + safe(d.palikas, floor) + '</span><span class="l">' +
        esc(t("live.flood.palikas")) + '</span></div>' +
      '</div>');
    var fam = Array.isArray(d.families) ? d.families.slice() : [];
    if (fam.length) {
      /* the scale is computed over the rows that are actually drawn: a bar
         width must never be a function of a value this page withholds */
      var max = 0;
      fam.forEach(function (f) { if (typeof f.contacts === "number" && f.contacts > max) max = f.contacts; });
      h.push('<p>' + esc(t("live.flood.byFamily")) + '</p><ul class="hbars">');
      fam.forEach(function (f) {
        var small = typeof f.contacts === "number" && f.contacts > 0 && f.contacts < floor;
        var w = (!small && max > 0 && typeof f.contacts === "number") ? Math.max(1, Math.round(100 * f.contacts / max)) : 0;
        h.push('<li><span class="hl3">' + esc(f.family) + '</span><span class="track">' +
          (w ? '<span class="bar3" style="width:' + w + '%"></span>' : '') +
          '<span class="val">' + safe(f.contacts, floor) + '</span></span></li>');
      });
      h.push('</ul>');
    }
    var dist = Array.isArray(d.districts) ? d.districts.slice() : [];
    if (dist.length) {
      h.push('<div class="tscroll"><table class="t2"><thead><tr><th>' + esc(t("live.col.district")) +
        '</th><th class="n">' + esc(t("live.col.contacts")) + '</th><th class="n">' +
        esc(t("live.col.reports")) + '</th><th class="n">' + esc(t("live.col.orgs")) +
        '</th></tr></thead><tbody>');
      dist.forEach(function (r) {
        var name = r.code;
        try { var o = C && C.districtByCode[r.code]; if (o) name = C.label(o); } catch (e) { /* ignore */ }
        h.push('<tr><td class="k">' + esc(name) + '</td><td class="n">' + safe(r.contacts, floor) +
          '</td><td class="n">' + safe(r.reports, floor) + '</td><td class="n">' + safe(r.organisations, floor) +
          '</td></tr>');
      });
      h.push('</tbody></table></div>');
    }
    h.push('<p class="src"><b>' + esc(t("live.basis")) + '</b> — ' + esc(sentence(d.basis)) +
      (d.period_from || d.period_to ? ' ' + esc(t("live.period", { from: d.period_from || "…", to: d.period_to || "…" })) : '') +
      ' ' + esc(t("live.floor", { n: floor })) + '</p>');
    return h.join("");
  }

  /* the code lists are lookup OBJECTS in codes.js (CODES.districtByCode["RAS"]),
     not functions -- calling them threw inside the try and silently left the
     bare code on screen, found by rendering a sample document */
  function actName(code) {
    var C = window.CODES;
    try { var a = C && C.activityByCode[code]; if (a) return C.label(a); } catch (e) { /* ignore */ }
    return code;
  }

  function referralBody(d) {
    var C = window.CODES;
    var rows = Array.isArray(d.rows) ? d.rows.slice() : [];
    if (!rows.length) return '<p>' + esc(t("live.ref.empty")) + '</p>';
    rows.sort(function (a, b) {
      return String(a.district).localeCompare(String(b.district)) ||
             String(a.palika).localeCompare(String(b.palika)) ||
             String(a.org_name || a.org).localeCompare(String(b.org_name || b.org));
    });
    var h = ['<div class="tscroll"><table class="t2"><thead><tr><th>' + esc(t("live.col.district")) +
      '</th><th>' + esc(t("live.col.palika")) + '</th><th>' + esc(t("live.col.org")) + '</th><th>' +
      esc(t("live.col.services")) + '</th><th>' + esc(t("live.col.last")) + '</th></tr></thead><tbody>'];
    rows.forEach(function (r) {
      var dn = r.district;
      try { var o = C && C.districtByCode[r.district]; if (o) dn = C.label(o); } catch (e) { /* ignore */ }
      var on = r.org_name || r.org;
      try { var g = C && C.orgByCode[r.org]; if (g && !r.org_name) on = C.label(g); } catch (e) { /* ignore */ }
      var acts = (Array.isArray(r.activities) ? r.activities : []).map(actName).join(", ");
      h.push('<tr><td class="k">' + esc(dn) + '</td><td>' + esc(r.palika) + '</td><td>' + esc(on) +
        '</td><td>' + esc(acts) + '</td><td>' + esc(r.last_report || "—") + '</td></tr>');
    });
    h.push('</tbody></table></div>');
    h.push('<p class="src"><b>' + esc(t("live.basis")) + '</b> — ' + esc(sentence(d.basis)) +
      (d.period_from || d.period_to ? ' ' + esc(t("live.period", { from: d.period_from || "…", to: d.period_to || "…" })) : '') + '</p>');
    return h.join("");
  }

  /* render(docId, {state, body, panel, kind}) */
  function render(docId, o) {
    var last = { data: undefined, err: null };
    var noneHTML = o.body ? o.body.innerHTML : "";

    function paint() {
      if (!configured) {
        setState(o.state, o.panel, "live.noconfig");
        return;
      }
      if (last.err) {
        setState(o.state, o.panel, "live.error");
        return;
      }
      if (last.data === undefined) {
        setState(o.state, o.panel, "live.checking");
        return;
      }
      var d = last.data;
      if (d === null) {
        setState(o.state, o.panel, "live.nonePublished");
        if (o.body) { o.body.innerHTML = noneHTML; if (window.I18N) window.I18N.apply(o.body); }
        document.dispatchEvent(new CustomEvent("publicstats:" + docId, { detail: null }));
        return;
      }
      if (d.schema !== 1) {
        setState(o.state, o.panel, "live.schema");
        return;
      }
      /* ONE redaction for the whole document, before a single value is drawn. */
      d = redact(d);
      /* The hub can publish in demonstration mode (small numbers not
         suppressed, for review). Whatever the page shows then says so. */
      setState(o.state, o.panel, d.mode === "demonstration" ? "live.publishedDemo" : "live.published",
               { when: when(d.computed_at) }, true);
      if (o.body) o.body.innerHTML = o.kind === "referral" ? referralBody(d) : floodBody(d);
      document.dispatchEvent(new CustomEvent("publicstats:" + docId, { detail: d }));
    }

    paint();
    if (configured) {
      watch(docId, function (data) { last.data = data; last.err = null; paint(); },
                   function (msg) { last.err = msg; paint(); });
    }
    /* a language switch repaints what this file wrote, in the new language */
    document.addEventListener("i18n:changed", function (e) {
      if (e && e.detail && e.detail.initial) return;
      paint();
    });
  }

  /* preview(o, data) paints a document that has NOT been published into a
     panel, with no network at all. For whoever builds the publish step in the
     hub, to show a coordinator exactly what the public page will show before
     pressing publish -- and for testing this file against a sample document. */
  function preview(o, d) {
    if (!d || d.schema !== 1) { setState(o.state, o.panel, "live.schema"); return; }
    setState(o.state, o.panel, "live.preview", null, true);
    d = redact(d);
    if (o.body) o.body.innerHTML = o.kind === "referral" ? referralBody(d) : floodBody(d);
  }

  window.PUBLIC_STATS = { watch: watch, render: render, preview: preview, redact: redact, configured: configured };
})();
