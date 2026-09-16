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
   automatic is that a missing translation cannot hide: it renders with a
   visible marker, it is counted on the page, and tools/i18n-check.py
   fails the deploy when a migrated page has gaps.

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

  /* ---------- lookup ---------------------------------------------------
     Returns the string and whether it was actually translated, so the
     caller can mark the ones that were not. */
  function look(key) {
    var en = (S.en || {})[key];
    var tr = (S[lang] || {})[key];
    if (lang === "en") return { text: en, translated: en != null, missing: en == null };
    if (tr != null && String(tr).trim() !== "") return { text: tr, translated: true, missing: false };
    return { text: en, translated: false, missing: en == null };
  }

  function t(key, vars) {
    var r = look(key);
    var s = r.text == null ? "" : String(r.text);
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        s = s.replace(new RegExp("\\{" + k + "\\}", "g"), vars[k]);
      });
    }
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
      if (el.hasAttribute("data-i18n-html")) el.innerHTML = r.text;
      else el.textContent = r.text;
      el.classList.toggle("i18n-todo", !r.translated && lang !== "en");
      if (!r.translated && lang !== "en") el.setAttribute("title", t("i18n.todoTitle"));
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

    return { total: total, missing: missing, untranslated: untranslated,
             translated: total - untranslated.length };
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
    document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lang: lang, coverage: r } }));
  }

  /* ---------- the toggle ----------------------------------------------
     Injected into the page's top bar so no page has to build it, which
     also means no page can forget it. */
  function mountToggle(cov) {
    if (LANGS.length < 2 || document.getElementById("i18nbar")) return;
    /* Three places to land, in order of preference:
         .top                a page with a dark header bar -- sits inline
         [data-i18n-toggle]  a slot a page has chosen deliberately
         nothing             the landing page has no header bar, so the
                             control floats top-right rather than not
                             appearing at all. It went missing there on the
                             first build, on the one page the Ministry opens
                             first, because mounting depended on .top. */
    var bar = document.querySelector(".top") || document.querySelector("[data-i18n-toggle]");
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
      "#i18nwrap.float{position:fixed;z-index:60;top:calc(10px + env(safe-area-inset-top,0px));" +
      "right:12px;display:flex;align-items:center;gap:6px;background:rgba(32,49,59,.94);" +
      "padding:5px 7px;border-radius:7px;box-shadow:0 1px 6px rgba(0,0,0,.22)}" +
      "#i18nwrap.float #i18nbar{margin:0}" +
      "#i18nwrap.float #i18nprog{margin:0 2px 0 4px}" +
      "@media (max-width:480px){#i18nwrap.float{top:auto;bottom:calc(10px + env(safe-area-inset-bottom,0px))}}" +
      /* Untranslated text is shown, not hidden -- with a mark, so a
         half-done page is never mistaken for a finished one. */
      ".i18n-todo{border-bottom:1px dotted currentColor;opacity:.92}" +
      ".i18n-missing{background:#fdeeee;color:#9b2c2c;font-family:ui-monospace,monospace;font-size:.9em}" +
      "#i18nprog{font:600 10.5px/1.3 'Noto Sans',system-ui,sans-serif;color:#a9bcc7;" +
      "margin-left:8px;flex:0 0 auto}" +
      /* Devanagari sits taller than Latin and its matras run above and below
         the baseline, so the same line-height that looks right in English
         crowds it. The face is switched here too, so no page has to remember. */
      ':root[data-lang="ne"] body{line-height:1.74;' +
      "font-family:'Noto Sans Devanagari','Noto Sans',system-ui,sans-serif}" +
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
    if (lang === "en" || !cov || !cov.total) { prog.textContent = ""; return; }
    prog.textContent = cov.untranslated.length
      ? t("i18n.progress", { done: cov.translated, total: cov.total })
      : "";
  }

  function start() {
    var cov = apply(document);
    mountToggle(cov);
    if (cov.missing.length) {
      console.warn("[i18n] keys used on this page with no English string:", cov.missing);
    }
    window.I18N.coverage = cov;
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
