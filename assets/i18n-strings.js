/* =====================================================================
   MHPSS Nepal — all page text, both languages, in one file
   ---------------------------------------------------------------------
   THIS IS THE ONLY PLACE PAGE TEXT LIVES. The HTML carries structure and
   keys; it carries no prose. That is what makes a change land in both
   languages at once: there is one copy of every sentence, not two.

   HOW TO ADD OR CHANGE TEXT
     1. edit the English here
     2. run  tools/i18n-check.py  --worksheet   to regenerate the
        translation worksheet for whoever is translating
     3. the deploy script refuses to publish a page whose keys are not
        all present, so a half-translated string cannot ship silently

   NEPALI IS NOT WRITTEN HERE BY CLAUDE. Every `ne` value comes from a
   human translator. This is a government health system read by the
   Ministry: a mistranslated clinical term is a real harm, not an
   inconvenience. Strings marked `pro: true` in the audit list below must
   go to a professional translator and never to anyone's best guess --
   PHQ-9 items above all, because a reworded PHQ-9 is not the validated
   instrument. See claude/layer1-forms.md.
   ===================================================================== */

window.I18N_STRINGS = {

  /* Language names, shown on the toggle. Labels match the ones the
     Ministry of Health's own site uses, so the control is familiar:
     NEP / ENG. */
  _meta: {
    langs: [
      { code: "en", label: "ENG", name: "English",  html: "en" },
      { code: "ne", label: "NEP", name: "नेपाली",   html: "ne" }
    ],
    // Bumped whenever the English changes, so a stale translation is visible.
    revision: "2026-09-16"
  },

  en: {
    /* ---- shared chrome ---- */
    "nav.hub":            "Hub",
    "nav.forms":          "Field forms",
    "nav.coordination":   "Coordination view",
    "nav.inbox":          "Field inbox",
    "nav.access":         "Access",
    "nav.method":         "Method",
    "nav.whoSees":        "Who can see what",
    "banner.trial":       "TRIAL INSTRUMENT — NOT THE LIVE REPORTING SYSTEM",
    "lang.select":        "Select language",

    /* ---- attribution band ---- */
    "attrib.body":        "Developed for the MHPSS Technical Working Group, Rasuwa / Bhote Koshi flood response, with support from WHO Nepal and in coordination with the Ministry of Health and Food Safety — Epidemiology and Disease Control Division.",
    "attrib.who":         "WHO Nepal",
    "attrib.whoRole":     "with the support of",
    "attrib.mohp":        "MoHP · EDCD",
    "attrib.mohpRole":    "in coordination with",

    /* ---- hub landing page ---- */
    "hub.synth": "DEMONSTRATION — EVERY FIGURE BEHIND THESE DOORS IS SYNTHETIC",
    "hub.synthSub": "· not response data · must not be quoted",
    "hub.org": "World Health Organization · Nepal &nbsp;·&nbsp; Ministry of Health and Food Safety",
    "hub.title": "Integrated Hub",
    "hub.sub": "One door to the mental health and psychosocial support information system for the Rasuwa–Bhote Koshi flood response. Choose the layer you work in.",
    "hub.oneway": "Information moves <b>one direction only</b> — field → coordination → public",
    "hub.d1.layer": "LAYER 1 · FIELD",
    "hub.d1.title": "Field forms",
    "hub.d1.desc": "One link a field worker can open on a phone, with every form behind it: activity report, service contact, referral, follow-up measure, and a self-report for the people at a site. Copy a link to send over WhatsApp, or print a QR code. Works with no signal.",
    "hub.d1.go": "Open the form list →",
    "hub.d2.layer": "LAYER 2 · COORDINATION",
    "hub.d2.title": "Coordination view",
    "hub.d2.desc": "Which holding centres are at zero, who is working where, activity mix, the deployed workforce and helpline demand — plus the field inbox, where forms exported from phones are imported. Service-level information only, and no individual is named anywhere in it.",
    "hub.d2.go": "Open the coordination view →",
    "hub.d3.layer": "LAYER 3 · PUBLIC",
    "hub.d3.title": "Public layer",
    "hub.d3.desc": "Aggregated figures submitted into the government-owned national 5W, and a public page owned and hosted by EDCD. Not built yet — this page sets out what goes there and who owns it.",
    "hub.d3.soon": "Planned · read the handover position",
    "hub.ref": "REFERENCE",
    "hub.d4.title": "Architecture concept",
    "hub.d4.desc": "The three layers, the one-direction boundary, and the question that decides everything: who <em>hosts</em> the database, who <em>controls</em> it, and who <em>owns</em> it.",
    "hub.d4.go": "Read the concept →",
    "hub.d6.title": "Who can see what",
    "hub.d6.desc": "The page to put in front of partners. Reporting needs no account at all; reading the records has to be granted by name. Sets out what the system refuses to store whatever a form asks for — and what it does <em>not</em> protect against.",
    "hub.d6.go": "Read the access model →",
    "hub.d5.title": "Data model & method",
    "hub.d5.desc": "Field-by-field mapping to the IASC 4Ws model, and an honest register of what is <em>not</em> established — the codes we refuse to guess and the conversions we refuse to fake.",
    "hub.d5.go": "Read the method →",
    "hub.flow.title": "Why the direction matters",
    "hub.flow.body": "Layer 1 writes. Layer 2 reads Layer 1 and writes nothing back. Layer 3 receives aggregates and <strong>cannot read the layer below it</strong>. No layer can reach down. That is what makes it safe to hand the public layer to the Ministry without handing over anything that identifies a person — and it is why the boundary is a design rule, not a setting someone can change later.",
    "hub.foot.line1": "Rasuwa–Bhote Koshi flood response · mental health and psychosocial support · draft, September 2026",
    "hub.foot.line2": "Prepared for the WHO Nepal mental health team, the Ministry of Health and Food Safety and EDCD. Not agreed with EDCD or the MHPSS sub-cluster.",
    "hub.foot.source": "Source and method on GitHub",
    "hub.foot.emblem": "No WHO or Government of Nepal emblem is used: WHO emblem use requires express written permission and the Nepal national emblem belongs to the Ministry. Prepared with AI assistance.",
    "hub.meta.title": "MHPSS Nepal — Integrated Hub",
    "hub.meta.desc": "One door to the mental health and psychosocial support information system for the Rasuwa–Bhote Koshi flood response. Demonstration build; all figures synthetic.",

    /* ---- the untranslated marker ---- */
    "i18n.todoTitle":     "Not yet translated — shown in English",
    "i18n.progress":      "{done} of {total} translated"
  },

  /* Filled by the translator, imported from the worksheet. Empty is not a
     bug: an empty value renders the English with a visible marker so that
     a half-translated page cannot be mistaken for a finished one. */
  ne: {
  }
};
