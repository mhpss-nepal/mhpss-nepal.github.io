/* =====================================================================
   MHPSS Nepal -- the media gallery on Resources (Layer 3)
   ---------------------------------------------------------------------
   Every resource the page already lists, shown as a thumbnail as well as a
   line of text: a small cover, the body that published it, its language and
   its format, with the actions beside it.

   WHY IT READS THE PAGE INSTEAD OF HOLDING ITS OWN LIST
   The sources are already written into resources.html as a definition
   list. Making a second copy here would give the site two places to change
   the same fact, and the day they disagree is the day one of them is wrong.
   So this script reads the authored list, builds the grid from it, and then
   hides the list. With scripts off the list stands on its own, complete: the
   grid is an enhancement, never the only copy.

   WHY THE PUBLISHER LINE IS COPIED, NOT BUILT
   The publisher and the language are translations, and the dictionary is
   applied to the page at DOMContentLoaded -- after this script runs. Read at
   build time they are empty, which is how every card once shipped with a
   blank publisher. They are therefore read AFTER the language is applied and
   copied across on every change (syncBy).

   WHY THERE IS NO "PREVIEW"
   A preview has to be honest. These are landing pages and one PDF; the
   site has no rendered first page for any of them, so a preview button would
   open something invented. Each item instead offers the one action that is
   real -- its source -- and Download only where a file is actually served
   (it is, for the code of conduct). A Preview action belongs here the day
   there is a real thing to preview.

   WHAT IT DOES NOT DO
   No data is invented: title, publisher, language, year and link all come
   from the authored list. Nepali titles are already written in Nepali in the
   list and are left exactly as they are.
   ===================================================================== */
(function () {
  "use strict";

  var root = document.querySelector("[data-media-gallery]");
  var src = document.querySelector("[data-media-source]");
  if (!root || !src) return;

  /* ---------- read the authored list ------------------------------- */
  var items = [];
  src.querySelectorAll(".resgroup").forEach(function (group) {
    var title = group.querySelector("h3");
    group.querySelectorAll(".srclist li").forEach(function (li) {
      var a = li.querySelector(".t a");
      if (!a) return;
      var by = li.querySelector(".by");
      var lang = li.querySelector(".lang");
      /* The dictionary is applied to the page later, at DOMContentLoaded, so
         at this moment these two spans are still empty. Read their KEYS and
         keep the elements, so the text can be filled in when the language is
         actually applied (syncBy, below). Reading .textContent here would put
         an empty publisher on every card. */
      var langKey = lang ? (lang.getAttribute("data-i18n") || "") : "";
      items.push({
        topic: title ? title.textContent.trim() : "",
        // the link text is the document's own title, in its own language
        title: a.textContent.trim(),
        href: a.getAttribute("href") || "",
        by: labelOf(by),
        lang: labelOf(lang),
        byEl: by,
        langEl: lang,
        isNepali: (a.getAttribute("lang") === "ne") ||
                  langKey === "res.p023" || langKey === "res.p025"
      });
    });
  });
  if (!items.length) return;

  /* Language is whatever the list says; "NEPALI" or "ENGLISH" in the row. */
  function langCode(it) { return it.isNepali ? "ne" : "en"; }

  /* Format: a file the site serves directly and that ends in .pdf is a PDF;
     the journal articles are articles; the rest are pages to read. */
  function formatOf(it) {
    if (/\.pdf(\?|#|$)/i.test(it.href)) return "pdf";
    if (/pubmed|biomedcentral|ijmhs|ncbi/i.test(it.href)) return "article";
    return "web";
  }

  /* Download only where a file is really served. The WHO document is the one
     item whose host serves the PDF itself; a landing page is not a file. */
  function downloadable(it) { return formatOf(it) === "pdf"; }

  /* The cover carries a short form of the REAL title, never a different one.
     Cut at a word boundary and add an ellipsis. The cap suits the NARROWEST
     card, which is a two-column grid on a phone: 30 characters is about three
     lines there and about two on a desktop card. The full title is on the
     card below and in the list above, so nothing is lost. */
  function coverTitle(title) {
    var t = String(title).trim();
    if (t.length <= 30) return t;
    var cut = t.slice(0, 30);
    var sp = cut.lastIndexOf(" ");
    if (sp > 14) cut = cut.slice(0, sp);
    return cut.replace(/[\s,;:.\u2013\u2014-]+$/, "") + "\u2026";
  }

  /* What a label element says right now. The dictionary may not have been
     applied yet, in which case the element still holds its key and not its
     text -- so hold the key back rather than showing an empty line. */
  function labelOf(el) {
    if (!el) return "";
    var s = (el.textContent || "").trim();
    return s || (el.getAttribute("data-i18n") || "");
  }

  /* ---------- build the grid --------------------------------------- */
  function t(key, vars) {
    var s = "";
    try {
      var d = window.I18N_STRINGS || {};
      var cur = d[document.documentElement.getAttribute("data-lang") || "en"] || {};
      s = cur[key] != null ? cur[key] : (d.en || {})[key];
    } catch (e) { /* fall through */ }
    if (s == null) s = "";
    if (vars) Object.keys(vars).forEach(function (k) {
      s = s.split("{" + k + "}").join(vars[k]);
    });
    return s;
  }

  var grid = document.createElement("ul");
  grid.className = "mgrid";
  grid.setAttribute("role", "list");

  items.forEach(function (it) {
    var fmt = formatOf(it), lc = langCode(it);
    var li = document.createElement("li");
    li.className = "mgcard-item";
    li.setAttribute("data-format", fmt);
    li.setAttribute("data-lang", lc);
    li.setAttribute("data-search", (it.title + " " + it.by + " " + it.topic).toLowerCase());

    var card = document.createElement("article");
    card.className = "mgcard";

    // cover: a short form of the REAL title on a sheet of the page's own
    // palette, with a rule under it, the way a report cover carries a title
    // block. Nothing invented: no made-up page image, no fake logo.
    var thumb = document.createElement("div");
    thumb.className = "mg-thumb";
    var badge = document.createElement("span");
    badge.className = "mg-format";
    badge.setAttribute("data-i18n", "res.gallery.type." + fmt);
    badge.textContent = t("res.gallery.type." + fmt) || fmt.toUpperCase();
    var sheet = document.createElement("div");
    sheet.className = "mg-sheet" + (lc === "ne" ? " ne" : "");
    if (lc === "ne") sheet.setAttribute("lang", "ne");
    var st = document.createElement("span");
    st.className = "t";
    st.textContent = coverTitle(it.title);
    var sr = document.createElement("span");
    sr.className = "r";
    sr.setAttribute("aria-hidden", "true");
    sheet.appendChild(st); sheet.appendChild(sr);
    thumb.appendChild(badge); thumb.appendChild(sheet);

    // body
    var body = document.createElement("div");
    body.className = "mg-body";
    var h3 = document.createElement("h3");
    if (lc === "ne") h3.setAttribute("lang", "ne");
    h3.textContent = it.title;
    var by = document.createElement("p");
    by.className = "mg-by";
    by.textContent = it.by;
    var meta = document.createElement("div");
    meta.className = "mg-meta";
    [["res.gallery.format." + fmt, fmt],
     ["res.gallery.lang." + lc, lc === "ne" ? "Nepali" : "English"]].forEach(function (pair) {
      var s = document.createElement("span");
      s.setAttribute("data-i18n", pair[0]);
      s.textContent = t(pair[0]) || pair[1];
      meta.appendChild(s);
    });

    var actions = document.createElement("div");
    actions.className = "mg-actions";
    var read = document.createElement("a");
    read.href = it.href;
    read.target = "_blank";
    read.rel = "noopener";
    read.setAttribute("data-i18n", "res.gallery.act.read");
    read.textContent = t("res.gallery.act.read") || "Read at source";
    actions.appendChild(read);
    if (downloadable(it)) {
      var dl = document.createElement("a");
      dl.href = it.href;
      dl.setAttribute("download", "");
      dl.setAttribute("data-i18n", "res.gallery.act.download");
      dl.textContent = t("res.gallery.act.download") || "Download";
      actions.appendChild(dl);
    }

    body.appendChild(h3); body.appendChild(by); body.appendChild(meta); body.appendChild(actions);
    card.appendChild(thumb); card.appendChild(body);
    li.appendChild(card);
    grid.appendChild(li);
  });

  /* The publisher and the language line on a card are translations of text the
     page already carries in its authored list. Copy them across every time
     the language changes, so a card never shows a blank publisher and never
     keeps the previous language after the switch. */
  function syncBy() {
    var nodes = grid.querySelectorAll(".mgcard .mg-by");
    for (var i = 0; i < nodes.length && i < items.length; i++) {
      var src = items[i].byEl;
      if (src) nodes[i].textContent = (src.textContent || "").trim();
    }
  }

  /* ---------- the toolbar ------------------------------------------ */
  var tools = document.createElement("div");
  tools.className = "mg-tools";

  var fSearch = document.createElement("label");
  fSearch.className = "field";
  fSearch.innerHTML =
    '<span class="fl" data-i18n="res.gallery.search"></span>' +
    '<input type="search" data-mg-search>';
  fSearch.querySelector(".fl").textContent = t("res.gallery.search");

  function selectField(labelKey, id, options) {
    var l = document.createElement("label");
    l.className = "field";
    var sp = document.createElement("span");
    sp.className = "fl";
    sp.setAttribute("data-i18n", labelKey);
    sp.textContent = t(labelKey);
    var sel = document.createElement("select");
    sel.id = id;
    options.forEach(function (o) {
      var op = document.createElement("option");
      op.value = o[0];
      op.setAttribute("data-i18n", o[1]);
      op.textContent = t(o[1]) || o[2];
      sel.appendChild(op);
    });
    l.appendChild(sp); l.appendChild(sel);
    // the caller keeps the element itself: it is not in the document until
    // the section is mounted, so document.getElementById would find null
    return { label: l, select: sel };
  }

  tools.appendChild(fSearch);
  var typeField = selectField("res.gallery.filterType", "mgType", [
    ["", "res.gallery.filterType.all", "All formats"],
    ["pdf", "res.gallery.format.pdf", "PDF"],
    ["web", "res.gallery.format.web", "Web page"],
    ["article", "res.gallery.format.article", "Journal article"]
  ]);
  var langField = selectField("res.gallery.filterLang", "mgLang", [
    ["", "res.gallery.filterLang.all", "All languages"],
    ["en", "res.gallery.filterLang.en", "English"],
    ["ne", "res.gallery.filterLang.ne", "Nepali"]
  ]);
  tools.appendChild(typeField.label);
  tools.appendChild(langField.label);

  var head = document.createElement("h2");
  head.className = "mg-head";
  head.setAttribute("data-i18n", "res.gallery.heading");
  head.textContent = t("res.gallery.heading") || "Browse the collection";

  var count = document.createElement("p");
  count.className = "mg-count";

  var empty = document.createElement("p");
  empty.className = "mg-empty";
  empty.hidden = true;
  empty.setAttribute("data-i18n", "res.gallery.empty");
  empty.textContent = t("res.gallery.empty");

  /* ---------- filtering -------------------------------------------- */
  function apply() {
    var q = (fSearch.querySelector("input").value || "").trim().toLowerCase();
    var tf = typeField.select.value;
    var lf = langField.select.value;
    var shown = 0;
    grid.querySelectorAll("li").forEach(function (li) {
      var ok = (!q || li.getAttribute("data-search").indexOf(q) > -1) &&
               (!tf || li.getAttribute("data-format") === tf) &&
               (!lf || li.getAttribute("data-lang") === lf);
      li.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = t("res.gallery.count", { n: shown }) ||
                        (shown + " items, each at the body that published it");
    empty.hidden = shown !== 0;
    grid.hidden = shown === 0;
  }
  fSearch.querySelector("input").addEventListener("input", apply);
  typeField.select.addEventListener("change", apply);
  langField.select.addEventListener("change", apply);
  // the language switch rewrites every [data-i18n] on the page; the count and
  // the empty state are built by this script, so they are refreshed on the
  // event i18n.js actually fires (assets/i18n.js), as referral-find.js does
  document.addEventListener("i18n:changed", apply);
  document.addEventListener("i18n:changed", syncBy);

  /* ---------- mount ------------------------------------------------ */
  var section = document.createElement("section");
  section.className = "mg";
  section.appendChild(head);
  section.appendChild(tools);
  section.appendChild(count);
  section.appendChild(grid);
  section.appendChild(empty);
  root.appendChild(section);

  apply();
  syncBy();
  // the authored list has done its job once the grid exists
  src.setAttribute("hidden", "");
  src.classList.add("mg-src");
})();
