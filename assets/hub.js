/* MHPSS Nepal Hub — rendering. Classic script, no dependencies, no network.
   All charts are inline SVG built here so the page works from a file:// URL. */
(function () {
  'use strict';
  var C = window.CODES, D = window.DEMO;
  if (!C || !D) { document.body.insertAdjacentHTML('afterbegin',
      '<p style="padding:20px;color:#d03b3b">Data did not load. Open index.html from the repository folder so that assets/ and data/ sit beside it.</p>'); return; }

  var recs = D.records;
  var siteBy = {}; C.SITES.forEach(function (s) { siteBy[s.code] = s; });
  var orgBy  = {}; C.ORGS.forEach(function (o) { orgBy[o.code] = o; });
  var actBy  = {}; C.ACTIVITIES.forEach(function (a) { actBy[a.code] = a; });
  var distBy = {}; C.DISTRICTS.forEach(function (d) { distBy[d.code] = d; });
  var cadBy  = {}; C.CADRES.forEach(function (c) { cadBy[c.code] = c; });
  var roster = C.SITES.filter(function (s) { return s.source === 'roster'; });
  /* Short forms for chart axes; the full registered name stays in tables and tooltips. */
  var SHORT = { TPO:'TPO Nepal', CMC:'CMC-Nepal', CWIN:'CWIN Nepal', NRCS:'Nepal Red Cross',
                KOS:'KOSHISH', SAMI:'SaMi · palika PSC', VID:'Vidushi', GOVPSC:'Government PSC' };

  var fmt = function (n) { return (n == null ? '—' : n.toLocaleString('en-GB')); };
  var el  = function (id) { return document.getElementById(id); };
  var SVGNS = 'http://www.w3.org/2000/svg';
  function mk(tag, attrs, text) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    return n;
  }
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  /* ── theme toggle ───────────────────────────────────────────────── */
  var root = document.documentElement;
  try { var t = localStorage.getItem('mhpss-theme'); if (t) root.setAttribute('data-theme', t); } catch (e) {}
  el('themeBtn').addEventListener('click', function () {
    var cur = root.getAttribute('data-theme');
    var sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var next = cur ? (cur === 'dark' ? 'light' : 'dark') : (sysDark ? 'light' : 'dark');
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('mhpss-theme', next); } catch (e) {}
    redraw();
  });

  /* ── tooltip ────────────────────────────────────────────────────── */
  var tip = el('tip');
  function showTip(evt, html) {
    tip.innerHTML = html; tip.classList.add('on'); tip.setAttribute('aria-hidden', 'false');
    var r = tip.getBoundingClientRect();
    var x = Math.min(Math.max(8, evt.clientX + 14), window.innerWidth - r.width - 8);
    var y = evt.clientY - r.height - 12; if (y < 8) y = evt.clientY + 18;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hideTip() { tip.classList.remove('on'); tip.setAttribute('aria-hidden', 'true'); }
  function bindTip(node, html) {
    node.addEventListener('mousemove', function (e) { showTip(e, html); });
    node.addEventListener('mouseleave', hideTip);
  }
  document.addEventListener('scroll', hideTip, { passive: true });

  /* ── aggregate ──────────────────────────────────────────────────── */
  var bySite = {}, byOrg = {}, byDay = {}, byDist = {}, byAct = {};
  recs.forEach(function (r) {
    (bySite[r.site] = bySite[r.site] || { reach: 0, days: {}, orgs: {}, n: 0 });
    bySite[r.site].reach += r.reachedTotal; bySite[r.site].days[r.dateBS] = 1;
    bySite[r.site].orgs[r.org] = 1; bySite[r.site].n++;
    (byOrg[r.org] = byOrg[r.org] || { reach: 0, n: 0, sites: {}, days: {}, dist: {} });
    byOrg[r.org].reach += r.reachedTotal; byOrg[r.org].n++;
    byOrg[r.org].sites[r.site] = 1; byOrg[r.org].days[r.dateBS] = 1; byOrg[r.org].dist[r.district] = 1;
    (byDay[r.dateBS] = byDay[r.dateBS] || { reach: 0, sites: {}, orgs: {} });
    byDay[r.dateBS].reach += r.reachedTotal; byDay[r.dateBS].sites[r.site] = 1; byDay[r.dateBS].orgs[r.org] = 1;
    (byDist[r.district] = byDist[r.district] || { reach: 0, n: 0, sites: {} });
    byDist[r.district].reach += r.reachedTotal; byDist[r.district].n++; byDist[r.district].sites[r.site] = 1;
    byAct[r.activity] = (byAct[r.activity] || 0) + r.reachedTotal;
  });
  var totalReach = recs.reduce(function (a, r) { return a + r.reachedTotal; }, 0);
  var days = Object.keys(byDay).sort();
  var gaps = roster.filter(function (s) { return !bySite[s.code]; });
  var thin = roster.filter(function (s) { return bySite[s.code] && Object.keys(bySite[s.code].days).length <= 3; });
  /* A record counts as disaggregated in either shape: the four bands as
     collected since 16 Sep 2026, or the two the form carried before it.
     store.js owns the fold; this page owns no copy of the band list. */
  var SS = window.STORE;
  var disagg = recs.filter(function (r) { return SS ? SS.disaggTotal(r) > 0 : r.f18 != null; });
  var disReach = disagg.reduce(function (a, r) { return a + r.reachedTotal; }, 0);

  /* ── hero + KPIs ────────────────────────────────────────────────── */
  el('heroLine').textContent = gaps.length + ' of ' + roster.length +
    ' holding centres on the roster have received no MHPSS service at all.';
  var POP = D.sitePop || {};
  var gapPop = gaps.reduce(function (a, s) { return a + (POP[s.code] || 0); }, 0);
  el('kpis').innerHTML = [
    ['bad',  gaps.length + '<small> of ' + roster.length + '</small>', 'Roster sites with<br>no service reported'],
    ['bad',  fmt(gapPop),                       'People at those<br>sites (synthetic)'],
    ['warn', thin.length,                       'Sites reported on<br>3 days or fewer'],
    ['',     fmt(totalReach),                   'Service contacts<br>not unique people'],
    ['',     recs.length,                       'Activity records<br>submitted'],
    ['',     Object.keys(byOrg).length,         'Organisations<br>reporting'],
    ['',     days.length,                       'Days with<br>any report'],
    ['',     Math.round(100 * disReach / totalReach) + '<small>%</small>', 'Of reach carrying<br>sex and age detail']
  ].map(function (k) {
    return '<div class="kpi ' + k[0] + '"><div class="v">' + k[1] + '</div><div class="k">' + k[2] + '</div></div>';
  }).join('');

  /* ── coverage grid ──────────────────────────────────────────────── */
  var covOrder = roster.slice().sort(function (a, b) {
    return a.district === b.district ? a.code.localeCompare(b.code) : (a.district === 'RAS' ? -1 : 1);
  });
  var grid = el('covGrid');
  covOrder.forEach(function (s) {
    var d = bySite[s.code], nd = d ? Object.keys(d.days).length : 0;
    var cls = nd === 0 ? 'g0' : nd <= 3 ? 'g1' : 'g2';
    var mark = nd === 0 ? '✕ no service' : (nd <= 3 ? '△ ' : '● ') + nd + ' day' + (nd === 1 ? '' : 's');
    var c = document.createElement('div');
    c.className = 'cell ' + cls;
    c.innerHTML = '<div class="c">' + s.code + ' · ' + distBy[s.district].name + '</div>' +
                  '<div class="n">' + esc(s.name) + '</div><div class="m">' + mark + '</div>';
    var orgs = d ? Object.keys(d.orgs).map(function (o) { return orgBy[o].name; }).join(', ') : '—';
    bindTip(c, '<b>' + esc(s.name) + '</b><br><span style="opacity:.75">' + esc(s.np || '') + '</span>' +
      '<div class="r"><span>Roster population</span><span>' + fmt(POP[s.code]) + '</span></div>' +
      '<div class="r"><span>Days reported</span><span>' + nd + '</span></div>' +
      '<div class="r"><span>Contacts</span><span>' + fmt(d ? d.reach : 0) + '</span></div>' +
      '<div style="margin-top:5px;opacity:.8">' + esc(orgs) + '</div>');
    grid.appendChild(c);
  });

  /* ══ CHARTS ═══════════════════════════════════════════════════════ */
  function cssv(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

  /* A crop of a chart loses the page banner, so the word travels with the chart.
     Tiled diagonal text, drawn first so every mark sits above it. */
  function watermark(svg, W, H) {
    var g = mk('g', { 'aria-hidden': 'true', 'pointer-events': 'none', opacity: 0.06 });
    for (var y = 34; y < H; y += 150) {
      for (var x = 20; x < W - 130; x += 330) {
        var t = mk('text', { x: x, y: y, transform: 'rotate(-24 ' + x + ' ' + y + ')',
          fill: cssv('--ink'), 'font-size': 30, 'font-weight': 800, 'letter-spacing': '0.09em' }, 'SYNTHETIC');
        g.appendChild(t);
      }
    }
    svg.appendChild(g);
  }

  /* Reach by organisation — one measure, one colour, ranked. */
  function drawOrgs() {
    var svg = el('orgChart'); svg.innerHTML = '';
    var rows = Object.keys(byOrg).map(function (o) {
      return { code: o, name: orgBy[o].name, v: byOrg[o].reach, n: byOrg[o].n,
               sites: Object.keys(byOrg[o].sites).length, days: Object.keys(byOrg[o].days).length };
    }).sort(function (a, b) { return b.v - a.v; });
    var W = 900, padL = 168, padR = 78, rowH = 30, gap = 9, H = rows.length * (rowH + gap) + 26;
    if (window.innerWidth < 620) { padL = 104; }
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    watermark(svg, W, H);
    var max = Math.max.apply(null, rows.map(function (r) { return r.v; }));
    var scale = function (v) { return (v / max) * (W - padL - padR); };
    // recessive gridlines
    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      var x = padL + f * (W - padL - padR);
      svg.appendChild(mk('line', { x1: x, x2: x, y1: 0, y2: H - 22, stroke: cssv('--grid'), 'stroke-width': 1 }));
      svg.appendChild(mk('text', { x: x, y: H - 6, 'text-anchor': 'middle', class: 'axis' }, fmt(Math.round(max * f))))
         .setAttribute('fill', cssv('--slate'));
    });
    rows.forEach(function (r, i) {
      var y = i * (rowH + gap);
      var lab = mk('text', { x: padL - 12, y: y + rowH / 2 + 4, 'text-anchor': 'end', class: 'clabel' },
        window.innerWidth < 620 ? r.code : (SHORT[r.code] || r.name));
      lab.setAttribute('fill', cssv('--ink')); svg.appendChild(lab);
      var w = Math.max(3, scale(r.v));
      var bar = mk('rect', { x: padL, y: y, width: w, height: rowH, rx: 4, fill: cssv('--s1'), class: 'bar' });
      svg.appendChild(bar);
      var val = mk('text', { x: padL + w + 9, y: y + rowH / 2 + 4, class: 'vlabel' }, fmt(r.v));
      val.setAttribute('fill', cssv('--ink')); svg.appendChild(val);
      bindTip(bar, '<b>' + esc(r.name) + '</b>' +
        '<div class="r"><span>Contacts</span><span>' + fmt(r.v) + '</span></div>' +
        '<div class="r"><span>Records</span><span>' + r.n + '</span></div>' +
        '<div class="r"><span>Sites</span><span>' + r.sites + '</span></div>' +
        '<div class="r"><span>Days reported</span><span>' + r.days + '</span></div>');
    });
    el('whoTbl').innerHTML = table(
      ['Organisation', 'Donor tag', 'Records', 'Sites', 'Days', 'Contacts'],
      rows.map(function (r) {
        return [orgBy[r.code].name, (orgBy[r.code].donors[0] || 'Not specified'),
                r.n, r.sites, r.days, fmt(r.v)];
      }), [0, 0, 1, 1, 1, 1]);
  }

  /* Contacts per day — single series area + line. */
  function drawDays() {
    var svg = el('dayChart'); svg.innerHTML = '';
    var W = 900, H = 260, padL = 46, padR = 12, padT = 12, padB = 34;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    watermark(svg, W, H);
    var max = Math.max.apply(null, days.map(function (d) { return byDay[d].reach; }));
    var nice = Math.ceil(max / 100) * 100;
    var X = function (i) { return padL + (i / (days.length - 1)) * (W - padL - padR); };
    var Y = function (v) { return padT + (1 - v / nice) * (H - padT - padB); };
    [0, 0.5, 1].forEach(function (f) {
      var y = Y(nice * f);
      svg.appendChild(mk('line', { x1: padL, x2: W - padR, y1: y, y2: y, stroke: cssv('--grid'), 'stroke-width': 1 }));
      var t = mk('text', { x: padL - 9, y: y + 4, 'text-anchor': 'end', class: 'axis' }, fmt(Math.round(nice * f)));
      t.setAttribute('fill', cssv('--slate')); svg.appendChild(t);
    });
    var dpts = days.map(function (d, i) { return [X(i), Y(byDay[d].reach)]; });
    svg.appendChild(mk('path', {
      d: 'M' + padL + ',' + Y(0) + 'L' + dpts.map(function (p) { return p[0] + ',' + p[1]; }).join('L') +
         'L' + X(days.length - 1) + ',' + Y(0) + 'Z',
      fill: cssv('--s1'), opacity: 0.12 }));
    svg.appendChild(mk('path', { d: 'M' + dpts.map(function (p) { return p[0] + ',' + p[1]; }).join('L'),
      fill: 'none', stroke: cssv('--s1'), 'stroke-width': 2, 'stroke-linejoin': 'round' }));
    days.forEach(function (d, i) {
      var hit = mk('rect', { x: X(i) - (W - padL - padR) / (days.length * 2), y: padT,
        width: (W - padL - padR) / days.length, height: H - padT - padB, fill: 'transparent' });
      svg.appendChild(hit);
      svg.appendChild(mk('circle', { cx: X(i), cy: Y(byDay[d].reach), r: 3.2, fill: cssv('--s1'),
        stroke: cssv('--surface'), 'stroke-width': 2 }));
      bindTip(hit, '<b>' + d + '</b>' +
        '<div class="r"><span>Contacts</span><span>' + fmt(byDay[d].reach) + '</span></div>' +
        '<div class="r"><span>Sites reporting</span><span>' + Object.keys(byDay[d].sites).length + '</span></div>' +
        '<div class="r"><span>Organisations</span><span>' + Object.keys(byDay[d].orgs).length + '</span></div>');
      if (i === 0 || i === days.length - 1 || i === Math.floor(days.length / 2)) {
        var t = mk('text', { x: X(i), y: H - 10, 'text-anchor': i === 0 ? 'start' : i === days.length - 1 ? 'end' : 'middle', class: 'axis' }, d);
        t.setAttribute('fill', cssv('--slate')); svg.appendChild(t);
      }
    });
    el('whenTbl').innerHTML = table(['Date (BS)', 'Contacts', 'Sites reporting', 'Organisations'],
      days.map(function (d) { return [d, fmt(byDay[d].reach), Object.keys(byDay[d].sites).length, Object.keys(byDay[d].orgs).length]; }),
      [0, 1, 1, 1]);
  }

  /* Activity mix — VERTICAL columns, GROUPED, one bar per activity family.
     It was horizontal bars, then vertical stacked ones; Adib asked for each
     family to stand beside the others rather than be piled into one bar. That
     is the better chart anyway: every family now starts from the baseline, so a
     small family is compared against the axis instead of being read off the top
     of whatever is beneath it.

     What this had to solve:
       · the totals span 26x (4,756 against 185), so the smallest bars are a
         couple of pixels. The value therefore sits ABOVE each bar, in ink,
         never inside it — a label inside a two-pixel bar is unreadable at any
         contrast. And a 100% MIX STRIP under each group carries the composition
         at full length whatever the district's size, without a second y-scale.
       · the viewBox takes the container's own width, so one unit is one CSS
         pixel and a 10px label is 10px on a phone. With a fixed 900-wide
         viewBox it rendered at about 4px. Six bars per district cannot be read
         at 320px either, so the figure has a min-width and swipes.
       · colour is a SEQUENTIAL ramp, not six hues — the reasoning is in
         hub.css. Palest is the broadest, least specialised support; darkest the
         most specialised. "Other" is hatched, because it is a remainder.
     The family order is fixed and runs with the ramp, in every group and in the
     legend. It is never sorted by size, or position and shading would both
     stop meaning anything. */
  var FAM = [
    { key: 'COMM', label: 'Community & children',     codes: ['PSED', 'RECR', 'CFS', 'IEC'], v: '--a1' },
    { key: 'REM',  label: 'Remote & assessment',      codes: ['HELP', 'ASMT', 'STAFF'],      v: '--a2' },
    { key: 'PFA',  label: 'Psychological first aid',  codes: ['PFA'],                        v: '--a3' },
    { key: 'CNS',  label: 'Counselling',              codes: ['CNS-I', 'CNS-G'],             v: '--a4' },
    { key: 'SPEC', label: 'Specialised & referral',   codes: ['SPEC', 'MEDS', 'REF'],        v: '--a5' }
  ];
  var famOf = {}; FAM.forEach(function (f) { f.codes.forEach(function (c) { famOf[c] = f.key; }); });

  /* A label's colour is computed against the fill it sits on, not chosen, because
     the ramp runs pale to dark and reverses between light and dark mode. */
  function relLum(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || ''); if (!m) return 0;
    var n = parseInt(m[1], 16);
    var c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (v) {
      v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function ratio(a, b) {
    var x = relLum(a), y = relLum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }
  function inkOn(bg) {
    var dark = cssv('--ink') || '#1d1d1b';
    return ratio('#ffffff', bg) >= ratio(dark, bg) ? '#ffffff' : dark;
  }

  /* the hatch for the residual, rebuilt each draw so a theme change repaints it */
  function hatch(svg, id) {
    var defs = mk('defs', {});
    var pat = mk('pattern', { id: id, width: 6, height: 6,
      patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' });
    pat.appendChild(mk('rect', { width: 6, height: 6, fill: cssv('--surface') || '#fff' }));
    pat.appendChild(mk('rect', { width: 2.4, height: 6, fill: cssv('--a0') || '#9a9a98' }));
    defs.appendChild(pat); svg.appendChild(defs);
    return 'url(#' + id + ')';
  }

  function drawActs() {
    var svg = el('actChart'); svg.innerHTML = '';
    var dm = {};
    recs.forEach(function (r) {
      var k = famOf[r.activity] || 'OTH';
      (dm[r.district] = dm[r.district] || {})[k] = (dm[r.district][k] || 0) + r.reachedTotal;
    });
    var rows = Object.keys(dm).map(function (d) {
      var tot = FAM.reduce(function (a, f) { return a + (dm[d][f.key] || 0); }, 0) + (dm[d].OTH || 0);
      return { d: d, name: distBy[d].name, parts: dm[d], tot: tot };
    }).sort(function (a, b) { return b.tot - a.tot; });
    if (!rows.length) return;

    /* the viewBox takes the container's own width, so one unit is one CSS pixel
       and a 10px label is 10px on every screen. The container has a min-width
       and scrolls: six bars per district cannot be read at 320px, and shrinking
       the type until they fit is not reading them either. */
    var W = Math.max(720, Math.round(svg.getBoundingClientRect().width || 900));
    var padL = 54, padR = 14, padT = 26, padB = 74;
    var plotH = 232, H = padT + plotH + padB;
    var band = (W - padL - padR) / rows.length;
    var groupW = band * 0.84;
    var cells = FAM.concat([{ key: 'OTH', label: 'Other / unclassified', v: null }]);
    var barW = Math.max(6, groupW / cells.length - 2);   /* 2px surface gap between bars */
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    watermark(svg, W, H);
    var resFill = hatch(svg, 'actHatch');

    var biggest = 0;
    rows.forEach(function (r) { cells.forEach(function (f) {
      biggest = Math.max(biggest, r.parts[f.key] || 0); }); });
    var stepU = Math.pow(10, Math.floor(Math.log(biggest) / Math.LN10)) / 2;
    var top = Math.max(stepU, Math.ceil(biggest / stepU) * stepU);
    var y0 = padT + plotH;

    var grid = mk('g', { 'aria-hidden': 'true' });
    for (var t = 0; t <= 4; t++) {
      var val = top * t / 4, gy = Math.round(y0 - (val / top) * plotH) + 0.5;
      grid.appendChild(mk('line', { x1: padL, x2: W - padR, y1: gy, y2: gy,
        stroke: cssv('--grid') || '#e7ecf0', 'stroke-width': 1 }));
      var al = mk('text', { x: padL - 9, y: gy + 3.5, 'text-anchor': 'end', class: 'alabel' }, fmt(val));
      al.setAttribute('fill', cssv('--muted')); grid.appendChild(al);
    }
    svg.appendChild(grid);

    /* a column with a 4px rounded top and square feet on the baseline */
    function col(x, y, w, h) {
      var r = Math.min(4, w / 2, h);
      return 'M' + x + ' ' + (y + h) + ' L' + x + ' ' + (y + r) +
             ' Q' + x + ' ' + y + ' ' + (x + r) + ' ' + y +
             ' L' + (x + w - r) + ' ' + y + ' Q' + (x + w) + ' ' + y + ' ' + (x + w) + ' ' + (y + r) +
             ' L' + (x + w) + ' ' + (y + h) + ' Z';
    }

    var stripY = y0 + 15, stripH = 12;
    var grand = rows.reduce(function (a, q) { return a + q.tot; }, 0);

    rows.forEach(function (r, i) {
      var gx = padL + band * i + (band - groupW) / 2, cx = gx + groupW / 2;

      cells.forEach(function (f, fi) {
        var v = r.parts[f.key] || 0;
        var bx = gx + fi * (barW + 2), h = (v / top) * plotH;
        if (v > 0) {
          var bar = mk('path', { d: col(bx, y0 - h, barW, h),
            fill: f.v ? cssv(f.v) : resFill, class: 'bar' });
          svg.appendChild(bar);
          bindTip(bar, '<b>' + esc(f.label) + '</b><br><span style="opacity:.8">' + esc(r.name) + '</span>' +
            '<div class="r"><span>Contacts</span><span>' + fmt(v) + '</span></div>' +
            '<div class="r"><span>Share of district</span><span>' + Math.round(100 * v / r.tot) + '%</span></div>');
          /* the value sits ABOVE the bar, in ink, never inside it: at this range
             the smallest bars are two pixels tall and a label inside them is
             unreadable however good the contrast is (Adib's rule 10). */
          if (barW >= 16) {
            var vl = mk('text', { x: bx + barW / 2, y: y0 - h - 5, 'text-anchor': 'middle',
              class: 'blabel' }, fmt(v));
            vl.setAttribute('fill', cssv('--ink')); svg.appendChild(vl);
          }
        } else {
          /* an empty family is drawn as a hairline on the baseline, so the six
             positions stay in the same order in every group and a gap reads as
             a nought rather than as a missing category */
          var z = mk('rect', { x: bx, y: y0 - 1.5, width: barW, height: 1.5,
            fill: cssv('--grid') || '#e7ecf0' });
          svg.appendChild(z);
        }
      });

      var dl = mk('text', { x: cx, y: y0 + 48, 'text-anchor': 'middle', class: 'clabel' }, r.name);
      dl.setAttribute('fill', cssv('--ink')); svg.appendChild(dl);
      var pl = mk('text', { x: cx, y: y0 + 62, 'text-anchor': 'middle', class: 'alabel' },
        fmt(r.tot) + ' · ' + Math.round(100 * r.tot / grand) + '% of all reach');
      pl.setAttribute('fill', cssv('--muted')); svg.appendChild(pl);

      /* the mix strip: the district's six families normalised to 100%, so the
         composition is readable even where the tallest bar is three pixels */
      var run = 0;
      cells.forEach(function (f) {
        var v = r.parts[f.key] || 0; if (!v) return;
        var w = (v / r.tot) * groupW;
        var sg = mk('rect', { x: gx + run, y: stripY, width: Math.max(1, w - 1.5), height: stripH,
          fill: f.v ? cssv(f.v) : resFill, class: 'bar' });
        svg.appendChild(sg);
        bindTip(sg, '<b>' + esc(f.label) + '</b><br><span style="opacity:.8">' + esc(r.name) +
          ' &middot; share of district</span>' +
          '<div class="r"><span>Share</span><span>' + Math.round(100 * v / r.tot) + '%</span></div>' +
          '<div class="r"><span>Contacts</span><span>' + fmt(v) + '</span></div>');
        run += w;
      });
    });

    var sl = mk('text', { x: padL - 9, y: stripY + 9, 'text-anchor': 'end', class: 'alabel' }, 'mix');
    sl.setAttribute('fill', cssv('--muted')); svg.appendChild(sl);
    svg.setAttribute('aria-label', 'Activity mix by district, as grouped columns. ' +
      rows.map(function (r) { return r.name + ' ' + fmt(r.tot); }).join(', ') +
      '. Within each district the six activity families stand side by side in a fixed order, ' +
      'palest to darkest. The strip under each group is the same six normalised to 100 per cent.');

    el('actKeys').innerHTML = cells.map(function (f) {
      var bg = f.v ? 'background:var(' + f.v + ')' :
        'background:repeating-linear-gradient(45deg,var(--a0) 0 2px,transparent 2px 5px);' +
        'border:1px solid var(--a0)';
      return '<b><span class="sw" style="' + bg + '"></span>' + f.label + '</b>';
    }).join('');
    el('whatTbl').innerHTML = table(['District'].concat(cells.map(function (f) { return f.label; })).concat(['Total']),
      rows.map(function (r) {
        return [r.name].concat(cells.map(function (f) { return fmt(r.parts[f.key] || 0); })).concat([fmt(r.tot)]);
      }), [0, 1, 1, 1, 1, 1, 1, 1]);
  }

  /* ── plain tables ───────────────────────────────────────────────── */
  function table(head, rows, numeric) {
    return '<table class="tbl"><thead><tr>' + head.map(function (h, i) {
        return '<th' + (numeric && numeric[i] ? ' class="n"' : '') + '>' + esc(h) + '</th>'; }).join('') +
      '</tr></thead><tbody>' + rows.map(function (r) {
        return '<tr>' + r.map(function (c, i) {
          return '<td' + (numeric && numeric[i] ? ' class="n"' : '') + '>' + esc(c) + '</td>'; }).join('') + '</tr>';
      }).join('') + '</tbody></table>';
  }

  /* workforce by cadre × district */
  (function () {
    var dists = [], m = {};
    D.workforce.forEach(function (p) {
      if (dists.indexOf(p.district) < 0) dists.push(p.district);
      (m[p.cadre] = m[p.cadre] || {})[p.district] = (m[p.cadre][p.district] || 0) + 1;
      m[p.cadre]._t = (m[p.cadre]._t || 0) + 1;
    });
    dists.sort();
    var order = C.CADRES.map(function (c) { return c.code; }).filter(function (c) { return m[c]; });
    var rows = order.map(function (c) {
      return [cadBy[c].name].concat(dists.map(function (d) { return m[c][d] || 0; })).concat([m[c]._t]);
    });
    rows.push(['All cadres'].concat(dists.map(function (d) {
      return order.reduce(function (a, c) { return a + (m[c][d] || 0); }, 0); })).concat([D.workforce.length]));
    el('cadreTbl').innerHTML = table(['Cadre'].concat(dists.map(function (d) { return distBy[d].name; })).concat(['Total']),
      rows, [0].concat(dists.map(function () { return 1; })).concat([1]));
  })();

  /* helpline */
  (function () {
    var tot = {}, dayn = {};
    D.helpline.forEach(function (row) {
      D.lines.forEach(function (L) {
        if (row[L.code] == null) return;
        tot[L.code] = (tot[L.code] || 0) + row[L.code];
        if (row[L.code] > 0) dayn[L.code] = (dayn[L.code] || 0) + 1;
      });
    });
    var rows = D.lines.map(function (L) {
      var reported = tot[L.code] != null;
      return [L.name, reported ? fmt(tot[L.code]) : '— never reported',
              reported ? (dayn[L.code] || 0) : '—',
              reported ? (Math.round(10 * tot[L.code] / D.helpline.length) / 10) : '—'];
    });
    el('helpTbl').innerHTML = table(['Helpline', 'Contacts', 'Days with a call', 'Mean per day'], rows, [0, 1, 1, 1]);
  })();

  /* ── table toggles ──────────────────────────────────────────────── */
  Array.prototype.forEach.call(document.querySelectorAll('[data-toggle]'), function (b) {
    b.addEventListener('click', function () {
      var t = el(b.getAttribute('data-toggle'));
      t.hidden = !t.hidden;
      b.textContent = t.hidden ? 'Show table' : 'Hide table';
    });
  });

  /* ── nav highlight ──────────────────────────────────────────────── */
  var links = Array.prototype.slice.call(document.querySelectorAll('nav.tabs a[href^="#"]'));
  var secs = links.map(function (a) { return el(a.getAttribute('href').slice(1)); });
  window.addEventListener('scroll', function () {
    var y = window.scrollY + 150, k = 0;
    secs.forEach(function (s, i) { if (s && s.offsetTop <= y) k = i; });
    links.forEach(function (a, i) { if (i === k) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  }, { passive: true });

  /* ── draw / redraw ──────────────────────────────────────────────── */
  function redraw() { drawOrgs(); drawDays(); drawActs(); }
  redraw();
  var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(redraw, 160); });
})();
