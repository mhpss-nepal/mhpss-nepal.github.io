/* =====================================================================
   Contributing organisations — MHPSS Nepal, Contact page
   ---------------------------------------------------------------------
   The Ministry's review of 17 September 2026 asked for a
   "contributing-partners section" and for the Ministry logo. This builds
   the section it asked for, on the page it belongs on.

   THE RULE THIS FILE FOLLOWS
   An organisation is named here, and its emblem appears once it has
   supplied the file (or, for the two bodies the site already names in its
   own masthead and footer, once their use has been approved — see each
   entry's `basis`). Until a file is in hand the slot holds the name in
   writing and says the emblem is still awaited. It does not hold a
   logo-shaped gap, and it never holds a file fetched from somewhere else.

   WHY THE FILE IS TAKEN FROM THE SOURCE
   An emblem is taken from the organisation that owns it — whose.int for
   WHO, the Government of Nepal's own server for the state emblem — never
   from an image search, which returns the wrong file at the wrong
   resolution with no provenance. (EDCD's own site still serves the
   SUPERSEDED 1962–2006 coat of arms, which is why the Ministry slot uses
   the current emblem and says so.)

   TO ADD AN ORGANISATION
   1. Put the supplied file in assets/ (e.g. assets/logo-unfpa.png).
   2. Fill its entry below: set `logo` to that path and `basis` to where
      the file came from and on what authority it is shown.
   Nothing else changes; the slot renders as an emblem instead of a name.

   TO ADD AN ORGANISATION WHOSE FILE HAS NOT ARRIVED
   Add its entry with `logo: null`. It is named, and the slot says the
   emblem is awaited. Do not leave a blank slot for an organisation that
   has already agreed to be named.

   WHY THE SLOTS ARE IN A FILE AND NOT IN THE PAGE
   The names, the paths and the permission dates are facts about other
   organisations. Kept in one list they can be read and corrected in one
   place, and the page cannot drift from them.
   ===================================================================== */
window.CONTRIBUTING = [
  {
    /* The two bodies the site already names in its own footer and masthead,
       and the two the Ministry's review named. */
    key: "who",
    name: "WHO Nepal",
    nameNp: "विश्व स्वास्थ्य संगठन (WHO) नेपाल",
    role: "contact.contrib.role.who",
    logo: "assets/logo-who-nepal.png",
    /* Taken from who.int (the Organisation's own server). Approved by the
       project lead for this public page, 20 September 2026. */
    basis: "who.int official artwork; use approved for this page 2026-09-20"
  },
  {
    key: "mohp",
    name: "Ministry of Health and Food Safety — Epidemiology and Disease Control Division",
    nameNp: "स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय — इपिडिमियोलोजी तथा रोग नियन्त्रण महाशाखा",
    role: "contact.contrib.role.mohp",
    /* The Government of Nepal's current state emblem, from the Government's
       own server. EDCD's own site still serves the superseded 1962–2006
       coat of arms, so it is not used here; EDCD's own logo file can
       replace this the moment a current one is supplied. */
    logo: "assets/gon-emblem.png",
    basis: "Emblem of Nepal (current), from the Government of Nepal's server; use approved 2026-09-20"
  },
  {
    /* Open slots, unnamed on purpose. The decision that each organisation
       consents to be named by palika (D3, 17 September 2026) is still
       open, so no partner is named here before it has said yes. An
       organisation added here appears the moment its entry carries a
       name. */
    key: "open-1",
    name: null,
    role: "contact.contrib.role.partner",
    logo: null,
    basis: null
  },
  {
    key: "open-2",
    name: null,
    role: "contact.contrib.role.partner",
    logo: null,
    basis: null
  }
];

(function () {
  "use strict";

  var root = document.querySelector("[data-contributing]");
  if (!root || !window.CONTRIBUTING) return;

  /* Read a string from the dictionary the site already loaded, falling back
     to English, then to the caller's text. Same mechanism as the gallery. */
  function t(key, fallback) {
    var s = null;
    try {
      var d = window.I18N_STRINGS || {};
      var cur = d[document.documentElement.getAttribute("data-lang") || "en"] || {};
      s = cur[key] != null ? cur[key] : (d.en || {})[key];
    } catch (e) { /* fall through */ }
    return s == null ? (fallback || "") : s;
  }

  function isNp() {
    return (document.documentElement.getAttribute("data-lang") || "en") === "ne";
  }

  function slotHtml(org) {
    var role = t(org.role, "");
    var name = (isNp() && org.nameNp) ? org.nameNp : org.name;
    var inner;

    if (org.logo) {
      /* The file the organisation supplied. `alt` is the organisation's own
         name, so the emblem is never an unlabelled image. */
      inner =
        '<span class="cb-emblem"><img src="' + org.logo + '" alt="' + name +
        '" loading="lazy" decoding="async"></span>' +
        '<span class="cb-name">' + name + '</span>';
    } else if (name) {
      /* Named, logo awaited: said in words rather than shown as a gap. */
      inner =
        '<span class="cb-name">' + name + '</span>' +
        '<span class="cb-wait">' + t("contact.contrib.awaitingLogo",
          "Logo awaited from the organisation, with written permission.") + '</span>';
    } else {
      /* No organisation here yet. Stated plainly. */
      inner =
        '<span class="cb-name none">' + t("contact.contrib.openSlot",
          "Not yet named") + '</span>' +
        '<span class="cb-wait">' + t("contact.contrib.openSlotWhy",
          "Named once the organisation has agreed to be listed.") + '</span>';
    }

    var classAttr = org.logo ? "cb-slot" : (name ? "cb-slot pending" : "cb-slot open");
    return '<div class="' + classAttr + '">' +
             '<span class="cb-role">' + role + '</span>' +
             inner +
           '</div>';
  }

  function render() {
    var head = t("contact.contrib.h", "Contributing organisations");
    var body = t("contact.contrib.p",
      "The organisations below contribute to the mental health and psychosocial " +
      "support response. A logo is shown only where the organisation has supplied " +
      "the file and given written permission to use it; until then the organisation " +
      "is named in writing.");

    var out = '<h2 class="cb-h">' + head + '</h2><p class="cb-p">' + body + '</p><div class="cb-grid">';
    for (var i = 0; i < window.CONTRIBUTING.length; i++) out += slotHtml(window.CONTRIBUTING[i]);
    out += "</div>";
    root.innerHTML = out;
  }

  render();
  /* The language switch rewrites every [data-i18n] on the page; these slots
     are built here, so they are rebuilt on the event i18n.js fires. */
  document.addEventListener("i18n:changed", render);
})();
