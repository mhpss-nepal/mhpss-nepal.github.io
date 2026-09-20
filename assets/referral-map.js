/* =====================================================================
   MHPSS Nepal -- the interactive map of "Find a service"
   ---------------------------------------------------------------------
   Layer 3. Draws, over an OpenStreetMap background:
     - the palikas of the districts on the map, from OCHA COD-AB
       (assets/referral-geo.js, generated and checked by tools/map-build.py),
       with the fifteen declared disaster crisis areas filled in
     - each hospital as a pin at its own location (assets/referral-facilities.js:
       an OpenStreetMap feature, checked to lie in the palika its address names)
     - partner organisations as a COUNT on a palika, or on a district when no
       palika was reported -- never as a point
   It knows nothing about filters: assets/referral-find.js decides what is
   shown and calls update(); this file draws it and reports clicks back.
   A second map on the same page (section 5, assets/workforce-view.js) uses
   the same drawing with four options of its own: fill(pcode) shades a palika
   by its number, tip(pcode) writes the hover line, badge(n) and
   badgeTitle(kind, place, n) write the counts -- so a count can read "<3".

   Leaflet 1.9.4 is served from this repository (assets/vendor/leaflet, BSD-2).
   The background tiles come from tile.openstreetmap.org under the OSMF tile
   usage policy: attribution always visible, nothing prefetched. If the tiles
   cannot be reached the boundaries, pins and counts still draw.
   ===================================================================== */
(function () {
  "use strict";
  function t(key, vars) { return window.I18N ? window.I18N.t(key, vars) : key; }
  function lang() { return (document.documentElement.getAttribute("lang") || "en").slice(0, 2); }
  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* shared arcs -> Leaflet rings of [lat, lon] */
  function decoder(g) {
    var sx = g.transform.scale[0], sy = g.transform.scale[1];
    var tx = g.transform.translate[0], ty = g.transform.translate[1];
    var abs = g.arcs.map(function (arc) {
      var x = 0, y = 0;
      return arc.map(function (d) { x += d[0]; y += d[1]; return [y * sy + ty, x * sx + tx]; });
    });
    function arcPts(i) { return i >= 0 ? abs[i] : abs[~i].slice().reverse(); }
    function ring(ix) {
      var pts = [];
      ix.forEach(function (i) { var a = arcPts(i); pts = pts.length ? pts.concat(a.slice(1)) : a.slice(); });
      return pts;
    }
    return function (shape) {
      return shape.t === "Polygon" ? shape.a.map(ring) : shape.a.map(function (poly) { return poly.map(ring); });
    };
  }

  /* INK follows --hc-ink in assets/design.css: deep ocean #153f4c replaced
     Neutral Black C on 19 September 2026 (DEVIATION 1 there). Leaflet needs
     a literal, so it is repeated here and must be kept in step by hand. */
  var INK = "#153f4c", DEEP = "#006996", DEEPER = "#004969", GREY = "#939391";

  function create(el, opts) {
    var L = window.L, G = window.REFERRAL_GEO;
    if (!L || !G || !el) return null;
    var decode = decoder(G);
    var map = L.map(el, {
      zoomControl: false, scrollWheelZoom: false, zoomSnap: 0.25, zoomDelta: 0.5,
      minZoom: 6, maxZoom: 18, attributionControl: true, keyboard: true
    });
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · ' +
                   'boundaries: OCHA COD-AB (Survey Department of Nepal)'
    }).addTo(map);
    var zoom = L.control.zoom({ position: "bottomright", zoomInTitle: t("refdir.find.zoomin"), zoomOutTitle: t("refdir.find.zoomout") }).addTo(map);

    map.createPane("pals").style.zIndex = 400;
    map.createPane("dists").style.zIndex = 410;
    map.getPane("dists").style.pointerEvents = "none";

    /* ---------------------------------------------------- boundaries */
    var PAL = {}, DIST = {}, allBounds = null;
    G.pal.forEach(function (x) {
      if (x.r === "pin") return;          /* kept only so the check can place a pin */
      var layer = L.polygon(decode(x), { pane: "pals", smoothFactor: 0.6 });
      layer.on("click", function () { if (opts.onPalika) opts.onPalika(x.p); });
      layer.on("mouseover", function () { layer.setStyle({ weight: 2.6, color: INK }); showTip(x); });
      layer.on("mouseout", function () { restyle(x.p); });
      layer.addTo(map);
      PAL[x.p] = { x: x, layer: layer };
    });
    G.dist.forEach(function (x) {
      var layer = L.polygon(decode(x), {
        pane: "dists", interactive: false, fill: false, weight: x.r === "context" ? 1.6 : 2.2,
        color: x.r === "context" ? GREY : INK, dashArray: x.r === "context" ? "6 4" : null
      }).addTo(map);
      DIST[x.d] = { x: x, layer: layer };
      allBounds = allBounds ? allBounds.extend(layer.getBounds()) : L.latLngBounds(layer.getBounds().getSouthWest(), layer.getBounds().getNorthEast());
    });
    var labels = L.layerGroup().addTo(map);
    function drawLabels() {
      labels.clearLayers();
      G.dist.forEach(function (x) {
        var name = lang() === "ne" && x.ne ? x.ne : x.n;
        L.marker(x.lab, {
          interactive: false, keyboard: false,
          icon: L.divIcon({ className: "lm-dlab" + (x.r === "context" ? " ctx" : ""), html: "<span>" + esc(name) + "</span>", iconSize: null })
        }).addTo(labels);
      });
    }
    drawLabels();

    var state = { hit: {}, sel: "", dsel: "" };
    function palStyle(p) {
      var x = PAL[p].x, hit = !!state.hit[p], sel = state.sel === p;
      var s = { weight: 0.8, color: GREY, opacity: 0.9, fill: true, fillColor: "#ffffff", fillOpacity: 0.01 };
      if (x.r === "decl") { s.fillColor = DEEP; s.fillOpacity = 0.32; s.color = DEEP; s.weight = 1; }
      if (x.r === "ctx") { s.fillColor = "#f6f6f5"; s.fillOpacity = 0.18; }
      /* a map that shades palikas by a number of its own (section 5) passes
         opts.fill; the declared-area fill then gives way to it */
      if (opts.fill) {
        var f = opts.fill(p);
        s.fillColor = f ? f.color : "#ffffff"; s.fillOpacity = f ? f.opacity : 0.01;
        if (x.r === "decl") { s.color = GREY; s.weight = 0.8; }
      }
      if (hit) { s.color = INK; s.weight = 2.2; }
      if (sel) { s.color = INK; s.weight = 3.6; s.fillOpacity = Math.max(s.fillOpacity, 0.2); }
      return s;
    }
    function restyle(p) { PAL[p].layer.setStyle(palStyle(p)); }
    Object.keys(PAL).forEach(restyle);

    /* hover names the palika, its district and how many match there */
    function showTip(x) {
      var n = opts.countAt ? opts.countAt(x.p) : 0;
      var name = lang() === "ne" && x.ne ? x.ne : x.n;
      var dx = DIST[x.d] && DIST[x.d].x, dname = dx ? (lang() === "ne" && dx.ne ? dx.ne : dx.n) : "";
      var line = opts.tip ? opts.tip(x.p) :
        (n ? t(n === 1 ? "refdir.find.tip.one" : "refdir.find.tip.many", { n: n }) : t("refdir.find.tip.none"));
      PAL[x.p].layer.bindTooltip("<b>" + esc(name) + "</b><span>" + esc(dname) + "</span><span class='n'>" + esc(line) + "</span>",
        { sticky: true, direction: "top", className: "lm-tip", offset: [0, -8] }).openTooltip();
    }

    /* ---------------------------------------------------- pins and counts
       A count sits just below and to the right of its palika's inner point,
       so a hospital pin standing on that point (its tip is the location, its
       head rises above it) is never covered; counts stack above pins. */
    var pins = L.layerGroup().addTo(map), counts = L.layerGroup().addTo(map);
    var PIN = {};
    var pinSvg = '<svg viewBox="0 0 32 42" width="32" height="42" aria-hidden="true" focusable="false">' +
      '<path d="M16 41c-1.2-5.6-12-14.6-12-24a12 12 0 1 1 24 0c0 9.4-10.8 18.4-12 24z" fill="' + DEEPER + '" stroke="#fff" stroke-width="2"/>' +
      '<path d="M13.6 9.5h4.8v5.1h5.1v4.8h-5.1v5.1h-4.8v-5.1H8.5v-4.8h5.1z" fill="#fff"/></svg>';

    function popupHtml(e) {
      var ne = e.name.ne ? '<span class="np" lang="ne">' + esc(e.name.ne) + "</span>" : "";
      return '<div class="lm-pop"><b>' + esc(e.name.en) + "</b>" + ne +
        (e.place ? "<p>" + esc(e.place) + "</p>" : "") +
        '<button type="button" class="lm-inlist" data-id="' + esc(e.id) + '">' + esc(t("refdir.find.inlist")) + "</button></div>";
    }

    function update(d) {
      state.hit = d.hit || {}; state.sel = d.pal || ""; state.dsel = d.dist || "";
      Object.keys(PAL).forEach(restyle);
      Object.keys(DIST).forEach(function (code) {
        DIST[code].layer.setStyle({ weight: code === state.dsel ? 3.4 : (DIST[code].x.r === "context" ? 1.6 : 2.2) });
      });
      pins.clearLayers(); PIN = {};
      (d.pins || []).forEach(function (e) {
        var m = L.marker([e.lat, e.lon], {
          icon: L.divIcon({ className: "lm-pin", html: pinSvg, iconSize: [32, 42], iconAnchor: [16, 41], popupAnchor: [0, -36] }),
          title: e.name.en, alt: e.name.en, keyboard: true, riseOnHover: true, zIndexOffset: 1000
        });
        m.bindPopup(popupHtml(e), { className: "lm-popwrap", maxWidth: 260 });
        m.on("popupopen", function (ev) {
          var b = ev.popup.getElement() && ev.popup.getElement().querySelector(".lm-inlist");
          if (b) b.addEventListener("click", function () { if (opts.onPinDetails) opts.onPinDetails(e.id); });
        });
        m.addTo(pins);
        PIN[e.id] = { m: m, e: e };
      });
      counts.clearLayers();
      Object.keys(d.palCounts || {}).forEach(function (p) {
        if (!PAL[p]) return;
        var n = d.palCounts[p], x = PAL[p].x;
        var m = L.marker(x.lab, {
          icon: L.divIcon({ className: "lm-count", html: "<span>" + esc(opts.badge ? opts.badge(n) : n) + "</span>", iconSize: [30, 30], iconAnchor: [-4, -4] }),
          keyboard: true, title: opts.badgeTitle ? opts.badgeTitle("palika", x, n) : t("refdir.find.badge", { place: x.n, n: n }), zIndexOffset: 1500
        });
        m.on("click", function () { if (opts.onPalika) opts.onPalika(p); });
        m.addTo(counts);
      });
      Object.keys(d.distCounts || {}).forEach(function (code) {
        if (!DIST[code]) return;
        var n = d.distCounts[code], x = DIST[code].x;
        var m = L.marker(x.lab, {
          icon: L.divIcon({ className: "lm-count bydist", html: "<span>" + esc(opts.badge ? opts.badge(n) : n) + "</span>", iconSize: [30, 24], iconAnchor: [-10, 30] }),
          keyboard: true, title: opts.badgeTitle ? opts.badgeTitle("district", x, n) : t("refdir.find.badge.district", { place: x.n, n: n }), zIndexOffset: 1400
        });
        m.on("click", function () { if (opts.onDistrict) opts.onDistrict(code); });
        m.addTo(counts);
      });
    }

    /* ---------------------------------------------------- framing */
    var PAD = { padding: [18, 18] };
    function fitAll() { if (allBounds) map.fitBounds(allBounds, PAD); }
    function fitDistrict(code) {
      if (DIST[code]) map.fitBounds(DIST[code].layer.getBounds(), PAD);
      else if (code === "outside") {
        var b = null;
        Object.keys(PIN).forEach(function (id) {
          if (PIN[id].e.outside) b = b ? b.extend(PIN[id].m.getLatLng()) : L.latLngBounds(PIN[id].m.getLatLng(), PIN[id].m.getLatLng());
        });
        if (b) map.fitBounds(b.pad(0.6), { maxZoom: 15 });
      }
    }
    function fitPalika(p) { if (PAL[p]) map.fitBounds(PAL[p].layer.getBounds(), { padding: [30, 30], maxZoom: 14 }); }
    /* several districts at once -- section 5 frames the districts with staff */
    function fitDistricts(codes) {
      var b = null;
      (codes || []).forEach(function (code) {
        if (!DIST[code]) return;
        var lb = DIST[code].layer.getBounds();
        b = b ? b.extend(lb) : L.latLngBounds(lb.getSouthWest(), lb.getNorthEast());
      });
      if (b) map.fitBounds(b, PAD); else fitAll();
    }
    function openPin(id) {
      var it = PIN[id];
      if (!it) return false;
      map.setView(it.m.getLatLng(), Math.max(map.getZoom(), 14));
      it.m.openPopup();
      return true;
    }

    /* the wheel zooms only once the map has been chosen, so a page scroll
       that passes over the map keeps scrolling the page */
    map.on("click focus", function () { map.scrollWheelZoom.enable(); });
    el.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });

    function relabel() {
      drawLabels();
      var zi = el.querySelector(".leaflet-control-zoom-in"), zo = el.querySelector(".leaflet-control-zoom-out");
      if (zi) { zi.title = t("refdir.find.zoomin"); zi.setAttribute("aria-label", t("refdir.find.zoomin")); }
      if (zo) { zo.title = t("refdir.find.zoomout"); zo.setAttribute("aria-label", t("refdir.find.zoomout")); }
      el.setAttribute("aria-label", t(opts.ariaKey || "refdir.find.maparia"));
    }
    relabel();
    fitAll();

    return {
      map: map, update: update, fitAll: fitAll, fitDistrict: fitDistrict, fitPalika: fitPalika, fitDistricts: fitDistricts,
      openPin: openPin, relabel: relabel,
      invalidate: function () { map.invalidateSize(); },
      palikas: function () {
        return Object.keys(PAL).map(function (p) { var x = PAL[p].x; return { p: p, n: x.n, ne: x.ne, d: x.d }; });
      },
      districts: function () { return G.dist.map(function (x) { return { d: x.d, n: x.n, ne: x.ne, r: x.r }; }); }
    };
  }

  window.REFERRAL_MAP = { create: create };
})();
