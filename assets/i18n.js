/* =====================================================================
   MHPSS Nepal — the bilingual engine
   ---------------------------------------------------------------------
   One page, two languages, one copy of every sentence. The HTML holds
   structure and keys; assets/i18n-strings.js holds the text. Change the
   English in one place and both versions change together, because there
   is only one place.

   WHY KEYS AND A DICTIONARY, NOT TWO BLOCKS WITH .lang-en / .lang-ne
   The show/hide-by-class pattern has a silent failure that has already
   been hit on another project: an element that nobody remembered to tag
   shows in BOTH languages, so a forgotten translation appears in English
   inside the Nepali page and nothing reports it. With keys, a missing
   translation is a missing dictionary entry -- countable, reportable,
   and blockable at deploy.

   WHAT IS AUTOMATIC AND WHAT IS NOT, stated plainly
   Translation is not automatic; a person writes the Nepali. What IS
   automatic is that a missing translation cannot hide FROM US:
   tools/i18n-check.py fails the deploy when a page marked enforced has a
   gap, and ?i18n=marks paints every gap on the page for whoever is
   writing the Nepali.
   What a READER is told is different, and deliberately so: a notice at the
   top of the Nepali page, saying it was translated automatically and that
   English is the authoritative version. Not ninety dotted underlines and a
   "90 to do" counter -- those are our instruments, and a Ministry reader
   who sees them reads the page as broken rather than as honest.

   MARKUP
     <h1 data-i18n="hub.title"></h1>            text content
     <input data-i18n-ph="form.namePlaceholder">  placeholder
     <a data-i18n-aria="nav.hubAria">             aria-label
     <img data-i18n-alt="logo.whoAlt">            alt text
     <span data-i18n="x.y" data-i18n-html>        trusted inline markup,
                                                   for a string that must
                                                   carry <b> or <br>
     <span data-i18n-skip>mhpss-nepal.github.io</span>
                                                   the same in every
                                                   language -- a domain, a
                                                   code, a proper noun. It
                                                   must be declared, not
                                                   assumed: unmarked text is
                                                   what the gate catches.
   ===================================================================== */
(function () {
  "use strict";

  var S = window.I18N_STRINGS || { _meta: { langs: [] }, en: {}, ne: {} };
  var LANGS = (S._meta && S._meta.langs) || [];
  var PRO = (S._meta && S._meta.professionalOnly) || [];
  var SRC = (S._meta && S._meta.source) || { machine: [], human: [] };

  /* A key whose clinical meaning lives in its exact wording. It is shown in
     English even on the Nepali page: a machine-rendered PHQ-9 is not the
     PHQ-9, and consent given to different words is not consent. */
  function isProtected(key) {
    for (var i = 0; i < PRO.length; i++) {
      if (key.indexOf(PRO[i]) === 0) return true;
    }
    return false;
  }
  function provenance(key) {
    if ((SRC.human || []).indexOf(key) > -1) return "human";
    if ((SRC.machine || []).indexOf(key) > -1) return "machine";
    return null;
  }
  var KEY = "mhpss-np-lang";
  var DEFAULT = "en";

  /* ---------- which language ------------------------------------------
     The URL wins, so a link can be shared in either language and the
     Ministry can bookmark the Nepali one. Then the remembered choice.
     Then the browser's own preference. Then English. */
  function pick() {
    var codes = LANGS.map(function (l) { return l.code; });
    try {
      var q = new URLSearchParams(window.location.search).get("lang");
      if (q && codes.indexOf(q) > -1) return q;
    } catch (e) { /* ignore */ }
    try {
      var saved = localStorage.getItem(KEY);
      if (saved && codes.indexOf(saved) > -1) return saved;
    } catch (e) { /* ignore */ }
    var nav = (navigator.language || "").toLowerCase();
    if (nav.indexOf("ne") === 0 && codes.indexOf("ne") > -1) return "ne";
    return codes.indexOf(DEFAULT) > -1 ? DEFAULT : (codes[0] || DEFAULT);
  }

  var lang = pick();

  /* ---------- reader view vs translator view --------------------------
     The provenance marks and the coverage count below are working
     instruments: they tell whoever is writing the Nepali which sentences
     are still English and which are only a machine draft. They are not
     for a reader. Left on by default they put a dotted rule under almost
     every line of a part-translated page and print "90 to do" beside the
     language buttons -- a Ministry reader opens that and sees a broken
     page, not an honest one.

     So the marks are off unless asked for:
       ?i18n=marks   turn them on (kept for the rest of the browser
                     session, so following links through the site keeps
                     them on while a translator works)
       ?i18n=clean   turn them off again
     What a reader is still told, always, is the notice at the top of the
     page: this was translated automatically and English is the
     authoritative version. That is the honest part, and it does not
     depend on this flag. */
  var MKEY = "mhpss-np-i18n-marks";
  function marksOn() {
    var q = null;
    try { q = new URLSearchParams(window.location.search).get("i18n"); } catch (e) { /* ignore */ }
    if (q === "marks" || q === "1") {
      try { sessionStorage.setItem(MKEY, "1"); } catch (e) { /* ignore */ }
      return true;
    }
    if (q === "clean" || q === "0") {
      try { sessionStorage.removeItem(MKEY); } catch (e) { /* ignore */ }
      return false;
    }
    try { return sessionStorage.getItem(MKEY) === "1"; } catch (e) { return false; }
  }
  var MARKS = marksOn();

  /* ---------- lookup ---------------------------------------------------
     Returns the string and whether it was actually translated, so the
     caller can mark the ones that were not. */
  function look(key) {
    var en = (S.en || {})[key];
    var tr = (S[lang] || {})[key];
    if (lang === "en") return { text: en, translated: en != null, missing: en == null, kept: false };
    /* Protected keys stay English whatever the dictionary holds, so a
       machine draft cannot reach a clinical instrument even by accident. */
    if (isProtected(key)) {
      return { text: en, translated: true, missing: en == null, kept: true, prov: "en" };
    }
    if (tr != null && String(tr).trim() !== "") {
      return { text: tr, translated: true, missing: false, kept: false, prov: provenance(key) };
    }
    return { text: en, translated: false, missing: en == null, kept: false };
  }

  /* A date is one unit: "7 September 2026" never breaks after the 7 or
     before the year. In justified text a date split across two lines leaves
     a stranded "7" and a line of wide gaps above it (17 Sep 2026). */
  var MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December";
  var DATE3 = new RegExp("(\\d{1,2}) (" + MONTHS + ") (\\d{4})", "g");
  var DATE2 = new RegExp("(\\d{1,2}) (" + MONTHS + ")(?![\\u00a0\\w])", "g");
  function bindDates(s) {
    if (typeof s !== "string" || s.indexOf(" ") < 0) return s;
    return s.replace(DATE3, "$1\u00a0$2\u00a0$3").replace(DATE2, "$1\u00a0$2");
  }

  function t(key, vars) {
    var r = look(key);
    var s = r.text == null ? "" : String(r.text);
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        s = s.replace(new RegExp("\\{" + k + "\\}", "g"), vars[k]);
      });
    }
    s = bindDates(s);
    return s;
  }

  /* ---------- apply ---------------------------------------------------- */
  var ATTRS = [
    ["data-i18n-ph", "placeholder"],
    ["data-i18n-aria", "aria-label"],
    ["data-i18n-alt", "alt"],
    ["data-i18n-title", "title"]
  ];

  function apply(root) {
    root = root || document;
    var missing = [], untranslated = [], total = 0;

    root.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      var r = look(key);
      total++;
      if (r.missing) { missing.push(key); }
      else if (!r.translated) { untranslated.push(key); }
      if (r.text == null) {
        /* No English either: show the key rather than an empty gap, so a
           typo in a key is obvious on the page instead of invisible. */
        el.textContent = "[" + key + "]";
        el.classList.add("i18n-missing");
        return;
      }
      if (el.hasAttribute("data-i18n-html")) el.innerHTML = bindDates(r.text);
      else el.textContent = bindDates(r.text);
      el.classList.toggle("i18n-todo", !r.translated && lang !== "en");
      el.classList.toggle("i18n-kept", !!r.kept && lang !== "en");
      el.classList.toggle("i18n-machine", r.prov === "machine" && lang !== "en");
      if (lang !== "en" && MARKS) {
        if (r.kept) el.setAttribute("title", t("i18n.keptTitle"));
        else if (!r.translated) el.setAttribute("title", t("i18n.todoTitle"));
      } else if (el.hasAttribute("title")) {
        el.removeAttribute("title");
      }
    });

    ATTRS.forEach(function (pair) {
      root.querySelectorAll("[" + pair[0] + "]").forEach(function (el) {
        var r = look(el.getAttribute(pair[0]));
        total++;
        if (r.missing) missing.push(el.getAttribute(pair[0]));
        else if (!r.translated) untranslated.push(el.getAttribute(pair[0]));
        if (r.text != null) el.setAttribute(pair[1], r.text);
      });
    });

    var L = LANGS.filter(function (l) { return l.code === lang; })[0];
    document.documentElement.setAttribute("lang", (L && L.html) || lang);
    document.documentElement.setAttribute("data-lang", lang);
    if (MARKS) document.documentElement.setAttribute("data-i18n-marks", "on");
    else document.documentElement.removeAttribute("data-i18n-marks");

    var kept = 0, machine = 0, human = 0;
    root.querySelectorAll("[data-i18n]").forEach(function (el) {
      var r = look(el.getAttribute("data-i18n"));
      if (r.kept) kept++;
      else if (r.prov === "machine") machine++;
      else if (r.prov === "human") human++;
    });
    return { total: total, missing: missing, untranslated: untranslated,
             translated: total - untranslated.length,
             kept: kept, machine: machine, human: human };
  }

  function setLang(next) {
    if (next === lang) return;
    lang = next;
    try { localStorage.setItem(KEY, next); } catch (e) { /* ignore */ }
    try {
      var u = new URL(window.location.href);
      u.searchParams.set("lang", next);
      window.history.replaceState({}, "", u);
    } catch (e) { /* ignore */ }
    var r = apply(document);
    paintToggle(r);
    if (lang === "en") { var nn = document.getElementById("mtnote"); if (nn) nn.remove(); }
    else mountNotice(r);
    document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lang: lang, coverage: r } }));
  }

  /* ---------- the toggle ----------------------------------------------
     Injected into the page's top bar so no page has to build it, which
     also means no page can forget it. */
  function mountToggle(cov) {
    if (LANGS.length < 2 || document.getElementById("i18nbar")) return;
    /* Three places to land, in order of preference:
         [data-i18n-toggle]  a slot a page has chosen deliberately
         .top                a page with a dark header bar -- sits inline
         nothing             the landing page has no header bar, so the
                             control floats top-right rather than not
                             appearing at all. It went missing there on the
                             first build, on the one page the Ministry opens
                             first, because mounting depended on .top. */
    /* A deliberate slot wins over a .top bar. It was the other way round, which
       is why the hub pages put the switch in their dark bar and ignored the
       slot in the rail -- landing it on top of the synthetic-data banner. */
    var bar = document.querySelector("[data-i18n-toggle]") || document.querySelector(".top");
    var floating = !bar;

    var css = document.createElement("style");
    css.textContent =
      "#i18nbar{display:inline-flex;align-items:stretch;border:1px solid rgba(255,255,255,.35);" +
      "border-radius:5px;overflow:hidden;margin-left:4px;flex:0 0 auto}" +
      "#i18nbar button{font:700 11.5px/1 'Noto Sans',system-ui,sans-serif;letter-spacing:.05em;" +
      "padding:6px 9px;border:0;background:transparent;color:#cfe6f2;cursor:pointer}" +
      "#i18nbar button[aria-pressed=true]{background:#cfe6f2;color:#20313b}" +
      "#i18nbar button:focus-visible{outline:2px solid #fff;outline-offset:-2px}" +
      /* the floating variant, for a page with no header bar */
      "#i18nwrap.float{position:fixed;z-index:60;top:calc(var(--i18n-float-top,10px) + env(safe-area-inset-top,0px));" +
      "right:12px;display:flex;align-items:center;gap:6px;background:rgba(32,49,59,.94);" +
      "padding:5px 7px;border-radius:7px;box-shadow:0 1px 6px rgba(0,0,0,.22)}" +
      "#i18nwrap.float #i18nbar{margin:0}" +
      "#i18nwrap.float #i18nprog{margin:0 2px 0 4px}" +
      "@media (max-width:480px){#i18nwrap.float{top:auto;bottom:calc(10px + env(safe-area-inset-bottom,0px))}}" +
      /* Untranslated text is shown, not hidden -- with a mark, so a
         half-done page is never mistaken for a finished one. */
      /* The three provenance rules apply only in the translator view
         (?i18n=marks). The classes are always on the elements, so the
         worksheet tooling and any DOM check still find them -- it is only
         their appearance that is gated. */
      ':root[data-i18n-marks="on"] .i18n-todo{border-bottom:1px dotted currentColor;opacity:.92}' +
      /* kept in English on purpose -- a solid rule, not the dotted "missing"
         one, because it is a decision rather than a gap */
      ':root[data-i18n-marks="on"] .i18n-kept{border-bottom:1px solid rgba(180,84,31,.45)}' +
      ':root[data-i18n-marks="on"] .i18n-machine{border-bottom:1px dashed rgba(0,126,180,.5)}' +
      ".i18n-missing{background:#fdeeee;color:#9b2c2c;font-family:ui-monospace,monospace;font-size:.9em}" +
      "#i18nprog{font:600 10.5px/1.3 'Noto Sans',system-ui,sans-serif;color:#a9bcc7;" +
      "margin-left:8px;flex:0 0 auto}" +
      /* Devanagari sits taller than Latin and its matras run above and below
         the baseline, so the same line-height that looks right in English
         crowds it. The face is switched here too, so no page has to remember. */
      ':root[data-lang="ne"] body{line-height:1.74;' +
      /* Mukta FIRST: it carries Devanagari and Latin in one family, which is
         the whole reason it was chosen. Naming another face here made the
         Nepali view a different typeface from the English one -- two
         typefaces on one site, which is exactly what Mukta avoids. The
         others stay as fallbacks in case Mukta has not loaded. */
      "font-family:'Mukta','Noto Sans Devanagari','Noto Sans',system-ui,sans-serif}" +
      ':root[data-lang="ne"] h1,:root[data-lang="ne"] h2,:root[data-lang="ne"] h3{line-height:1.35}' +
      "@media print{#i18nbar,#i18nprog{display:none}}";
    document.head.appendChild(css);

    var wrap = document.createElement("div");
    wrap.id = "i18nbar";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", t("lang.select"));
    LANGS.forEach(function (l) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = l.label;
      b.setAttribute("data-lang", l.code);
      b.setAttribute("aria-pressed", String(l.code === lang));
      b.setAttribute("lang", l.html);
      b.title = l.name;
      b.addEventListener("click", function () { setLang(l.code); });
      wrap.appendChild(b);
    });

    var prog = document.createElement("span");
    prog.id = "i18nprog";

    if (floating) {
      var host = document.createElement("div");
      host.id = "i18nwrap";
      host.className = "float";
      host.appendChild(wrap);
      host.appendChild(prog);
      document.body.appendChild(host);
    } else {
      var spacer = bar.querySelector(".spacer");
      if (spacer) { bar.insertBefore(wrap, spacer.nextSibling); }
      else { bar.appendChild(wrap); }
      wrap.parentNode.insertBefore(prog, wrap.nextSibling);
    }
    paintToggle(cov);
  }

  function paintToggle(cov) {
    var wrap = document.getElementById("i18nbar");
    if (wrap) {
      wrap.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-lang") === lang));
      });
    }
    var prog = document.getElementById("i18nprog");
    if (!prog) return;
    /* The count is shown only where it means something: on the Nepali
       view, where a gap is a gap. */
    if (lang === "en" || !MARKS || !cov || !cov.total) { prog.textContent = ""; return; }
    /* Strings kept in English on purpose are not gaps, so they are not
       counted as missing. A machine draft is counted separately from text a
       person has checked -- "38 machine" and "38 reviewed" are very
       different states and the page should not blur them. */
    var parts = [];
    if (cov.human) parts.push(cov.human + " reviewed");
    if (cov.machine) parts.push(cov.machine + " machine");
    if (cov.untranslated.length) parts.push(cov.untranslated.length + " to do");
    if (cov.kept) parts.push(cov.kept + " kept in English");
    prog.textContent = parts.join(" · ");
  }


  /* ---------- the machine-translation notice --------------------------
     Modelled on the browser's own offer -- a thin bar, not a modal, and
     dismissible. Two differences that matter here:

       it is bilingual, because a notice about translation quality cannot
       be allowed to depend on translation quality; and

       it says which version is authoritative, because a Ministry reader
       needs to know how much weight to give the page in front of them.

     Dismissal is remembered per revision: change the English and the
     notice returns, because the Nepali is now a draft of something older. */
  function mountNotice(cov) {
    if (lang === "en" || document.getElementById("mtnote")) return;
    var rev = (S._meta && S._meta.revision) || "0";
    var dkey = "mhpss-np-mtnote-" + rev;
    try { if (localStorage.getItem(dkey) === "1") return; } catch (e) { /* ignore */ }

    var css = document.createElement("style");
    css.textContent =
      "#mtnote{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;" +
      "padding:9px 14px;padding-top:calc(9px + env(safe-area-inset-top,0px));" +
      "background:#fdf6e9;border-bottom:1px solid #e6d5ae;color:#6b4d16;" +
      "font:400 12.5px/1.5 'Mukta','Noto Sans Devanagari','Noto Sans',system-ui,sans-serif}" +
      "#mtnote .m{flex:1 1 300px;min-width:0}" +
      "#mtnote .np{display:block;font-weight:600}" +
      "#mtnote .en{display:block;opacity:.85;font-family:'Noto Sans',system-ui,sans-serif}" +
      "#mtnote .acts{display:flex;gap:7px;flex:0 0 auto;align-items:center}" +
      "#mtnote button,#mtnote a{font:700 11.5px/1.2 'Noto Sans',system-ui,sans-serif;" +
      "border:1px solid #c9a94f;background:#fff;color:#6b4d16;border-radius:5px;" +
      "padding:6px 10px;cursor:pointer;text-decoration:none}" +
      "@media print{#mtnote{display:none}}";
    document.head.appendChild(css);

    /* Two honest wordings, chosen by what is actually translated on THIS
       page. A page with no keys is one we have not keyed up yet: its prose
       is still English and only the dropdown choices are Nepali, so saying
       "this page was translated automatically" would be false. A false
       notice is worse than none -- it is the kind of thing a Ministry
       reader checks once and then stops trusting the rest. */
    var keyed = !!(cov && cov.total);
    var hasLists = !!document.querySelector("select");
    var kind = keyed ? "full" : (hasLists ? "partial" : "notyet");
    var WORDS = {
      /* The "clinical wording is kept in English" sentence is added only
         when this page actually HAS a string kept in English. Claiming it
         on a page with none is a promise with no mechanism behind it, and
         a Ministry reader who checks one claim and finds it hollow stops
         trusting the others. cov.kept is that count. */
      full:    [["mt.notice.ne", "mt.authoritative.ne"].concat(
                  (cov && cov.kept) ? ["mt.clinicalKept.ne"] : []),
                ["mt.notice.en", "mt.authoritative.en"].concat(
                  (cov && cov.kept) ? ["mt.clinicalKept.en"] : [])],
      partial: [["mt.partial.ne", "mt.partial.auth.ne"],
                ["mt.partial.en", "mt.partial.auth.en"]],
      notyet:  [["mt.notyet.ne", "mt.notyet.auth.ne"],
                ["mt.notyet.en", "mt.notyet.auth.en"]]
    };
    var ne = WORDS[kind][0].map(t);
    var en = WORDS[kind][1].map(t);
    var partial = kind !== "full";

    var n = document.createElement("div");
    n.id = "mtnote";
    n.setAttribute("role", "status");
    n.setAttribute("data-mt", kind);
    n.innerHTML =
      '<span class="m">' +
        '<span class="np" lang="ne">' + esc(ne.join(" ")) + "</span>" +
        '<span class="en" lang="en">' + esc(en.join(" ")) + "</span>" +
      "</span>";
    var acts = document.createElement("span");
    acts.className = "acts";
    var enBtn = document.createElement("button");
    enBtn.type = "button";
    enBtn.textContent = t("mt.readEnglish");
    enBtn.addEventListener("click", function () { setLang("en"); });
    var x = document.createElement("button");
    x.type = "button";
    x.textContent = t("mt.dismiss");
    x.addEventListener("click", function () {
      try { localStorage.setItem(dkey, "1"); } catch (e) { /* ignore */ }
      n.remove();
    });
    acts.appendChild(enBtn); acts.appendChild(x);
    n.appendChild(acts);
    document.body.insertBefore(n, document.body.firstChild);

    /* Keep a floating toggle clear of the notice. The notice is in flow at
       the top of the page; the toggle is fixed in the same corner, so on a
       wide screen it landed on top of the notice's own "Read in English"
       button. Measured rather than guessed, because the notice wraps to two
       or three lines depending on width and language. */
    function clearNotice() {
      var wrap = document.getElementById("i18nwrap");
      if (!wrap || !wrap.classList.contains("float")) return;
      var h = n.getBoundingClientRect().height;
      document.documentElement.style.setProperty(
        "--i18n-float-top", (h > 0 ? Math.round(h) + 8 : 10) + "px");
    }
    clearNotice();
    window.addEventListener("resize", clearNotice);
    /* and put it back when the notice is dismissed */
    x.addEventListener("click", function () {
      document.documentElement.style.setProperty("--i18n-float-top", "10px");
    });
  }

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function start() {
    var cov = apply(document);
    mountToggle(cov);
    mountNotice(cov);
    if (cov.missing.length) {
      console.warn("[i18n] keys used on this page with no English string:", cov.missing);
    }
    window.I18N.coverage = cov;
    /* Announce the language on FIRST LOAD too, not only when the toggle is
       pressed.
       The forms fill their dropdowns from the code lists in a script that
       runs before this one -- so on a page opened directly at ?lang=ne the
       options were already built, in English, by the time the language was
       known. Pressing NEP fixed them, which meant the Nepali words only
       appeared for someone who happened to toggle. A field worker opening
       a Nepali link saw an English form and no reason to think otherwise.
       Firing the same event here lets every listener rebuild once, before
       anyone has typed anything. */
    document.dispatchEvent(new CustomEvent("i18n:changed", {
      detail: { lang: lang, coverage: cov, initial: true }
    }));
  }

  window.I18N = {
    t: t,
    apply: apply,
    setLang: setLang,
    lang: function () { return lang; },
    langs: LANGS,
    coverage: null
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
