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
    revision: "2026-09-16",

    /* ---- strings that NO machine may translate --------------------------
       Matched as prefixes, so a PHQ-9 item added next month is protected
       without anyone remembering to add it here.

       These are not excluded because a machine translates them clumsily.
       They are excluded because translating them changes what they ARE:

       phq9.item*    The Nepali PHQ-9 is validated as a specific culturally
                     adapted wording (Kohrt et al., BMC Psychiatry 2016:
                     cut-off >=10, sensitivity 0.94, specificity 0.80,
                     PPV 0.42). That cut-off belongs to those words. Re-word
                     the items and the threshold measures nothing -- you are
                     scoring people against a line validated for a different
                     questionnaire.
       phq9.item9*   The suicide item and the instruction that follows it.
                     Someone acts on this in a real crisis.
       consent.*     Consent given in Nepali to something the English did
                     not say is not consent. Modal verbs are exactly where
                     machine translation drifts.
       safeguard.*   The referral form's GBV / child-protection /
                     immediate-risk gate. A worker ticks it believing what
                     it says.
       clinical.*    Terms with an established equivalent in Ministry usage.
                     A machine will invent a different one, and then our
                     forms stop matching the national vocabulary -- which is
                     the whole reason the code lists exist.

       A string matching these renders in ENGLISH on the Nepali page, with
       its own note saying why. That is more honest than a machine-rendered
       clinical instrument, and safer than hiding the gap. */
    /* KEPT IN ENGLISH ON PURPOSE, by key prefix.
       -----------------------------------------------------------------
       These prefixes were written against key names that did not exist
       yet, so for a while the list protected NOTHING -- 0 of 204 keys --
       while every Nepali page carried a notice saying clinical wording is
       kept in English. The claim was true only by accident, because there
       was no Nepali for those strings anyway. The first worksheet import
       would have quietly ended that.
       tools/i18n-check.py now reports any prefix here that matches no key,
       and the notice only claims this when the page really has one. */
    professionalOnly: [
      /* the safety statements on the self-report form. These are the
         sentences that tell a reader the form is not ready and that free
         text carries a risk -- a machine draft of a safety warning is not
         a safety warning. */
      "sr.p007",          /* the not-in-Nepali-yet warning */
      "sr.p001",          /* the free-text risk warning */
      "sr.clinicalNote",  /* why there is no screening questionnaire here */
      /* forward-looking: these pages are not keyed yet, and when they are
         these prefixes catch the instrument and consent wording before any
         translator sees it. A machine-rendered PHQ-9 is not the PHQ-9, and
         consent given to different words is not consent. */
      "phq9.item", "phq9.scale", "phq9.cutoff",
      "consent.", "safeguard.", "clinical."
    ],

    /* Keys that need no Nepali entry: they are already language-specific
       (the bilingual notice holds its own Nepali and its own English) or
       invariant in every language. Declared, not assumed. */
    noTranslationNeeded: ["mt."],

    /* PLACEHOLDERS — a bridge, and it is meant to be temporary.
       -----------------------------------------------------------------
       "Select…", "— choose —", "All districts": the first line of every
       dropdown, and the first Nepali word a field worker looks for. They
       live in the pages' own code, so on a page not yet keyed up they
       stayed English while every option below them turned Nepali -- an
       English instruction above a Nepali list, which is the worst of both.

       Keying each page up replaces these with proper keys. Until then
       they are matched by their English text, which is exactly the loose
       English the gate exists to catch -- so this map is the ONE place it
       is allowed, it is listed here where it can be seen, and l18n warns
       in the console about any placeholder it could not match. Delete an
       entry when its page is keyed. */
    placeholders: {
      "— choose —":            "— छनोट गर्नुहोस् —",
      "Select…":               "छान्नुहोस्…",
      "— choose your site —":  "— तपाईंको स्थान छान्नुहोस् —",
      "Not specified":         "उल्लेख नगरिएको",
      "All districts":         "सबै जिल्ला",
      "Ongoing":               "चालु",
      "Other — not listed":    "अन्य — सूचीमा नभएको",
      "Somewhere else":        "अन्य कतै"
    },

    /* Where each Nepali string came from, so the page can say so and the
       gate can tell a machine draft from reviewed text.
         machine = drafted automatically, English remains authoritative
         human   = written or checked by a person
       A key absent from both is simply not translated yet. */
    source: { machine: [
      "banner.demo",
      "foot.cards",
      "foot.contact",
      "foot.flood",
      "foot.referral",
      "foot.resources",
      "foot.site",
      "foot.tools",
      "hl.all",
      "home.hl",
      "hub.d1.go",
      "hub.d1.layer",
      "hub.d1.title",
      "hub.d2.go",
      "hub.d2.layer",
      "hub.d2.title",
      "hub.d3.layer",
      "hub.d3.soon",
      "hub.d3.title",
      "hub.d4.go",
      "hub.d4.title",
      "hub.d5.go",
      "hub.d5.title",
      "hub.d6.go",
      "hub.d6.title",
      "hub.flow.title",
      "hub.org",
      "hub.ref",
      "hub.title",
      "i18n.keptTitle",
      "i18n.todoTitle",
      "jump.flood.1",
      "jump.flood.2",
      "jump.flood.3",
      "jump.flood.4",
      "jump.flood.5",
      "jump.flood.6",
      "jump.label",
      "jump.referral.1",
      "jump.referral.2",
      "jump.referral.3",
      "lang.select",
      "live.col.district",
      "live.col.org",
      "live.col.orgs",
      "live.col.palika",
      "live.col.reports",
      "map.type.mun",
      "map.type.rm",
      "mast.cluster",
      "mast.hub",
      "mast.place",
      "mt.dismiss",
      "mt.readEnglish",
      "nav.access",
      "nav.band.bps",
      "nav.band.contact",
      "nav.band.flood",
      "nav.band.home",
      "nav.band.iec",
      "nav.band.referral",
      "nav.band.resources",
      "nav.band.videos",
      "nav.coordination",
      "nav.forms",
      "nav.hub",
      "nav.inbox",
      "nav.method",
      "nav.whoSees",
      "ref.access",
      "ref.architecture",
      "ref.method",
      "ref.strip"
    ], human: [] }
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
    "hub.foot.line2": "Prepared for the WHO Nepal mental health team, the Ministry of Health and Food Safety and EDCD. Not agreed with EDCD or the MHPSS Technical Working Group.",
    "hub.foot.source": "Source and method on GitHub",
    "hub.foot.emblem": "No WHO or Government of Nepal emblem is used: WHO emblem use requires express written permission and the Nepal national emblem belongs to the Ministry. Prepared with AI assistance.",
    "hub.meta.title": "MHPSS Nepal — Integrated Hub",
    "hub.meta.desc": "One door to the mental health and psychosocial support information system for the Rasuwa–Bhote Koshi flood response. Demonstration build; all figures synthetic.",

    "banner.trialSub": "· drafts for the MHPSS Technical Working Group to approve · nothing you enter is sent anywhere",










    /* ---- swept prose: ml ---- */
    "ml.act.open": "📝 Open here",
    "ml.act.qr": "📱 QR",
    "ml.p001": "<b>Layer 2, as described on 15 September, cannot live here.</b> The meeting described a password-protected backend holding name, sex, gender and location. GitHub Pages serves static files from a public repository; it has no password and no database. The named layer has to sit on the WHO or government infrastructure noted on 14 September, and the forms on this page are the specification for it — not a substitute.",
    "ml.p002": "<b>The contact code is a stand-in, not the answer.</b> It is worked out from a few low-variation details, so it is a pseudonym rather than a truly anonymous token: someone holding a list of candidate names could in principle test them against a code. That is acceptable for agreeing the questions. It is not acceptable for a live register of flood-affected people. A real deployment needs the code salted with a secret the handset never sees — which means a server, and therefore the WHO or EDCD backend, not this site.",
    "ml.p003": "Training records",
    "ml.p004": "Service provider directory",
    "ml.p005": "Frontliner support",
    "ml.p006": "For the person themselves",
    "ml.p007": "Referral pathway",
    "ml.p008": "Clinical follow-up · PHQ-9",
    "ml.p009": "Daily contact · new vs returning",
    "ml.p010": "Service delivery · 4Ws / 5W",
    "ml.p011": "<b>None of these forms submits anywhere.</b> This site is a static site with no server behind it, so there is nothing for a form to send data to. Each form validates what you type, calculates what it should calculate, saves it in your own browser, and lets you export a file. They are here so the Technical Working Group can see and agree the questions <i>before</i> anything is collected for real. Do not use them to record a real service and assume it was captured — it was not.",
    "ml.p012": "Layer 1 · Field · Form master list",
    "ml.p013": "So that anyone can check a question against the meeting that asked for it, rather than taking it on trust.",
    "ml.p014": "Problem described 14 Sep 2026. Belongs in the backend, not here.",
    "ml.p015": "Partners request PFA training repeatedly for the same people because training is not linked to names in a database. Fixing that needs a named database — which is exactly the thing this public site must not hold.",
    "ml.p016": "Requested 14 Sep 2026. Blocked on the same site-code list as the coverage analysis.",
    "ml.p017": "Adding a psychiatrist, counsellor or service point to the directory that Layer 3 would map. Deliberately not drafted yet: the site code list is not agreed, and a half-agreed directory is worse than the Excel sheet it would replace.",
    "ml.p018": "Target population named 14 Sep 2026. Waiting on the open action item: “define what ground-level information needs to be collected on a daily basis”.",
    "ml.p019": "Search and rescue teams, army, police, volunteers, forensics staff, helicopter crews moving bodies. Named as a distinct target population, but no agreed content: a group-session count is easy, a wellbeing measure for uniformed responders is a governance decision, not a form decision.",
    "ml.p020": "From the NCD meeting, 15 Sep 2026: “two separate form types … one for clients directly, to protect privacy”, and self-reporting, 14 Sep 2026.",
    "ml.p021": "The second form type: filled in by the affected person, not by a worker. Completely anonymous — no code, no contact details, no way back to who answered. It reports how a shelter is doing as a whole, and shows someone where to get help.",
    "ml.p022": "From both meetings, 14–15 Sep 2026: referral directory beyond the current single Excel sheet, and linkage with the protection cluster.",
    "ml.p023": "Where a person was sent, for what, and whether they arrived. This is the one link between the psychosocial side and the clinical side — without it, a referral to a health facility disappears into HMIS and the continuum of care cannot be shown.",
    "ml.p024": "Nepali version validated by Kohrt et al., BMC Psychiatry 2016 — cut-off ≥10, sensitivity 0.94, specificity 0.80, but positive predictive value only 0.42. Answers to “track progression from acute distress to clinical disorders”, 14 Sep 2026.",
    "ml.p025": "Nine items, scored and interpreted on the handset. Used to follow <b>one person over time</b> after they have been referred for care — not to screen a shelter. The form states plainly what the score does and does not mean.",
    "ml.p026": "From the NCD data-system meeting, 15 Sep 2026: new vs returning client, province/subdistrict, focal person, type of service provider, GPS pin, unique-ID anchor.",
    "ml.p027": "The daily form. New or returning, municipality and ward, who delivered it, what kind of provider, and a location pin. A <b>contact code</b> is worked out on your own phone so a returning person is recognised without their name or number ever leaving the handset.",
    "ml.p028": "Feeds the 4Ws table and the national 5W. Fields follow IASC MHPSS 4Ws (2012) Table 1, plus four marked additions.",
    "ml.p029": "One row per activity, per site, per day. Coded sites and activities, sex and age disaggregation, both calendars. Records <b>services, not people</b> — there is no field for a name, and none is to be added.",
    "ml.p030": "<b>Open here</b> loads the form in this page. <b>Copy link</b> gives you a link to send a field worker over WhatsApp, so they fill it in on their own phone. <b>QR</b> shows a printable code for a noticeboard at a holding centre. Every form works on a phone, and keeps working with no signal.",
    "ml.p031": "<b>Where the exports go</b> — the worker exports a file and sends it to you over WhatsApp or email; you drop it into the <a href=\"../hub/inbox.html\">field inbox</a>, which turns the files into one table. Nothing travels on its own, because there is no server behind this site.",
    "ml.p032": "<b>No signal</b> — once a form has been opened on a phone, it keeps working offline. Entries stay in that phone's browser until exported.",
    "ml.p033": "<b>QR</b> — print it and put it on the wall at a holding centre. A phone camera opens the form. Useful for the self-report form, where you want people to reach it without being handed a link.",
    "ml.p034": "<b>Copy link</b> — paste it into WhatsApp and send it to a field worker. They open it on their own phone, fill it in there, and export. No app, no account, no sign-in.",
    "ml.p035": "<b>Open here</b> — you fill it in yourself, on this device. Use this when someone reports to you by phone or on paper and you are entering it.",
    "ml.p036": "One link, every form a field worker needs",
    "ml.p037": "What still has to be decided above this page",
    "ml.p038": "Where each form comes from",
    "ml.p039": "How to use these",
    "ml.p040": "Forms",
    "ml.p041": "Training attendance <span class=\"est\">not drafted</span>",
    "ml.p042": "Directory entry <span class=\"est\">not drafted</span>",
    "ml.p043": "Frontliner group session <span class=\"est\">not drafted</span>",
    "ml.p044": "Self-report — how are you coping",
    "ml.p045": "Referral out / in",
    "ml.p046": "Depression measure (Nepali)",
    "ml.p047": "Service contact record",
    "ml.p048": "Activity report",
    "ml.p049": "What the record says",
    "ml.p050": "Source",
    "ml.p051": "Form",
    "ml.p052": "The meeting left this open: “Team to define what ground-level information needs to be collected on a daily basis for the first layer forms.” Until that is answered, three cards above stay undrafted on purpose.",
    "ml.p053": "<span class=\"est\">Not established</span>",
    "ml.p054": "Daily form list",
    "ml.p055": "“Two separate form types … one for clients directly, to protect privacy.”",
    "ml.p056": "MHPSS Data System Design Meeting, 15 Sep 2026",
    "ml.p057": "Self-report",
    "ml.p058": "Referral directory beyond a single Excel sheet; protection-cluster linkage; clinical cases currently vanish into HMIS.",
    "ml.p059": "Both meetings, 14–15 Sep 2026",
    "ml.p060": "Referral",
    "ml.p061": "Meeting asked for tracking “progression from acute distress to clinical disorders”. The instrument and its cut-off come from the published Nepali validation, not from the meeting.",
    "ml.p062": "Nepal Flood MHPSS Briefing, 14 Sep 2026 + Kohrt et al. 2016",
    "ml.p063": "PHQ-9",
    "ml.p064": "Mobile-friendly link-based form, GPS pinning, new vs returning client, province/subdistrict, focal person, type of service provider; unique-ID anchor with fallback matching at Layer 2.",
    "ml.p065": "MHPSS Data System Design Meeting, 15 Sep 2026",
    "ml.p066": "Service contact",
    "ml.p067": "Published tool. Four additions are marked as additions on the Method page, with the reason for each.",
    "ml.p068": "IASC MHPSS 4Ws (2012), Table 1",
    "ml.p069": "Activity report",
    "ml.p070": "🔗 Copy link",
    "ml.p071": "🔗 Copy link",
    "ml.p072": "🔗 Copy link",
    "ml.p073": "🔗 Copy link",
    "ml.p074": "🔗 Copy link",
    "ml.p075": "📱 QR for this page",
    "ml.p076": "🔗 Copy the link to this page",
    "ml.p077": "Send this one link and a field worker has all the forms — no app to install, nothing to sign in to.",
    "ml.p078": "Printable card sheet",
    "ml.p079": "One A4 sheet, six cut-out cards, every form's QR on it — asked for by the data system review on 16 September.",

    /* ---- 4Ws form: what the total counts ----
       The single field that decides whether any figure here can enter the
       5W. The cleaned backlog is 11,973 service contacts; the form used to
       instruct "people, count them once", so the two could not be joined.
       R-U1 (NDRRMA / EDCD) still rules on what the 5W takes. */
    "f4.h4":            "How many",
    "f4.h4hint":        "counts only, never a list",
    "f4.reachLab":      "Total reached",
    "f4.reachHelp":     "Enter the figure your organisation already records. The next question asks what it counts, so nothing has to be converted first.",
    "f4.basisLab":      "What does that number count?",
    "f4.basisPick":     "\u2014 choose \u2014",
    "f4.basisContacts": "Service contacts \u2014 each time someone was seen",
    "f4.basisPeople":   "Distinct people \u2014 this organisation, this period",
    "f4.basisUnsure":   "Not sure",
    "f4.basisHelp":     "Both are legitimate and they are not the same figure, so the system keeps them apart instead of adding them together. Neither answer deduplicates across organisations.",
    "f4.distLab":       "Distinct people, if you know it <span class=\"opt\">\u2014 optional</span>",
    "f4.distHelp":      "If your organisation has already removed its own repeat visits, put that figure here. It is kept beside the contact count, never in place of it.",

    /* ---- 4Ws form: age and sex disaggregation ----
       Four bands, chosen so 0-4 + 5-17 is the official "under 18" and
       18-59 + 60+ is the official "18 and over". The team asked for an
       under-5 figure and the official 5Ws has only the two bands; this
       grid answers both, so nothing has to be collected twice. */
    "f4.disLabel": "Disaggregation <span class=\"opt\">— optional, but leave a row blank rather than partly filled</span>",
    "f4.hAge":     "Age",
    "f4.hFemale":  "Female",
    "f4.hMale":    "Male",
    "f4.hOther":   "Not recorded",
    "f4.hRow":     "Total",
    "f4.colTotal": "All ages",
    "f4.tally":    "Disaggregated sum",
    "f4.rollLabel": "Rolls up to the official 5Ws bands",
    "f4.rollU18":  "under 18",
    "f4.roll18":   "18 and over",
    "f4.ofwHead":  "Of whom <span>— already counted above, <b>never added to it</b></span>",
    "f4.ofPwd":    "Persons with disabilities",
    "f4.ofPreg":   "Pregnant or postpartum",
    "f4.ofwNote":  "One person can be in both, and is in a band above as well. These two are checked against the total but are never summed with it or with each other.",
    "f4.disHelp":  "Reports in the current workbook carry breakdowns typed into the provider column \u2014 a \u201cwomen 18+ = 12, men 18+ = 9\u201d where an organisation name should be \u2014 because the form has nowhere else to put them. Here they have somewhere, the parts are checked against the total, and the four bands fold to the two the official 5Ws asks for.",
    /* 0.3.0 fields, 16 Sep 2026: funding as a list, joint-activity partners,
       palika-level reports. English only until the translator returns. */
    "f4.donorsLab":    "Funding source <span class=\"opt\">\u2014 optional, tick all that apply</span>",
    "f4.donorsHelp":   "Recorded so that one organisation reporting under two donors is not mistaken for two organisations. An activity funded by two donors carries both.",
    "f4.partnersLab":  "Joint activity with <span class=\"opt\">\u2014 optional</span>",
    "f4.partnersHelp": "Organisations that did this activity with you \u2014 not the funder, which goes above. Item C of the IASC 4Ws.",
    "f4.palikaLab":    "Palika (local level)",
    "f4.palikaHelp":   "Named after the official list of local levels. A palika-level report is counted at palika level and never as a site, so it cannot close a gap on the roster.",

    "sr.age.choose": "— choose —",
    "sr.age.u18": "Under 18",
    "sr.age.18to24": "18 to 24",
    "sr.age.25to59": "25 to 59",
    "sr.age.60plus": "60 or over",
    "sr.age.noSay": "I would rather not say",
    "sr.yes": "Yes",
    "sr.no": "No",
    "page.selfreport.brand": "How are you coping",
    "page.selfreport.sub": "Anonymous · nothing here identifies you",
    "nav.backToForms": "← Forms",
    "page.index.brand": "Field forms",
    "page.index.sub": "Layer 1 · Rasuwa / Bhote Koshi",

    /* ---- swept prose: sr ---- */
    "sr.p001": "<b>Free text is the risk on this form.</b> Question 5 is open, anonymous, and may be filled in by someone in distress or may name another person. Whoever exports these answers has to read them before they go anywhere, and remove anything that identifies someone. That is a named human responsibility — no form design removes it.",
    "sr.p002": "“Send” saves the answer in this browser. There is no server behind this site, so nothing actually leaves the device — a worker exports the answers and passes them on.",
    "sr.p003": "Please do not write your name or anyone else's name here.",
    "sr.p004": "Question 3 and question 4 together are the useful pair: a site where everyone knows about the service but nobody can reach it has a different problem from a site where nobody has been told it exists.",
    "sr.p005": "There is no score and no threshold here. This is not a test and it does not say anything about your health.",
    "sr.p006": "The site is the only location recorded. Not your tent, not your ward.",
    "sr.p007": "<b>This form is not in Nepali yet, and it should not be used until it is.</b> The questions have not been translated. A form in a language people do not read gives you the answers of whoever happens to read English, which is worse than no answers at all.",
    "sr.p008": "Anything you want the people running this site to know? <span class=\"opt\">— optional</span>",
    "sr.p009": "I do not need it",
    "sr.p010": "I have not tried",
    "sr.p011": "I tried but could not",
    "sr.p012": "4. Have you been able to reach it?",
    "sr.p013": "I am not sure",
    "sr.p014": "3. Do you know where to get support for how you are feeling, at this site?",
    "sr.p015": "Something else",
    "sr.p016": "Medical care",
    "sr.p017": "Work or money",
    "sr.p018": "Replacing lost documents",
    "sr.p019": "Support for my children",
    "sr.p020": "Help with sleep",
    "sr.p021": "News about a missing family member",
    "sr.p022": "Someone to talk to",
    "sr.p023": "2. What would help most right now?",
    "sr.p024": "I am not coping",
    "sr.p025": "Difficult most days",
    "sr.p026": "Some difficult days",
    "sr.p027": "Mostly all right",
    "sr.p028": "Well",
    "sr.p029": "1. Over the past week, how have you been coping?",
    "sr.p030": "Roughly how old are you?",
    "sr.p031": "Which site are you at?",
    "sr.p032": "This form is for the people living at a site, not for staff. It does not ask your name, your phone number, or anything that could point back to you — and because of that, <b>nobody can follow up with you afterwards</b>. If you want someone to contact you, tell a worker instead of using this form. What you write here is used to see how a whole site is doing, and what is missing there.",
    "sr.p033": "TO BE FILLED IN BY THE MHPSS TECHNICAL WORKING GROUP: the helpline number for this response. No number has been confirmed, so none is printed here. This page must not be printed or put on a wall until a real, answered number is in this box.",
    "sr.p034": "You do not have to fill anything in first. Speak to any counsellor or health worker at this site — you can ask for them by name at the help desk, and it is free.",
    "sr.p035": "Four questions, and nobody will know it was you",
    "sr.p036": "Notes for whoever fields this",
    "sr.p037": "If you need help today",
    "sr.p038": "Clear this device",
    "sr.p039": "Export CSV",
    "sr.p040": "Send",
    "sr.p041": "Why there is no screening questionnaire on this page.",
    "sr.clinicalNote": "<b>Why there is no screening questionnaire on this page.</b> An anonymous form filled in by whoever walks past is the worst possible place for a clinical instrument: you cannot consent someone properly, you cannot give them the result, you cannot follow up a positive answer, and the people who answer are not a sample of anything. So this form asks about needs and about access to services \u2014 questions an anonymous respondent can actually answer usefully \u2014 and the clinical measure sits on the <a href=\"phq9.html\">PHQ-9 form</a>, with a named worker, consent, and a referral pathway behind it.",

    /* ==== BEGIN layer3-shared: the public website's shared blocks (tools/nav.py), live panels (assets/public-read.js) and map (tools/map-build.py). 16 Sep 2026 ==== */
    "mast.cluster": "Health Cluster · Nepal",
    "mast.place": "Rasuwa · Nuwakot · flood response",
    "mast.hub": "Coordination hub",
    "banner.demo": "DEMONSTRATION BUILD · draft",
    "banner.demoSub": "· not agreed with EDCD or the MHPSS Technical Working Group",
    "ref.strip": "How this system works",
    "ref.architecture": "Architecture",
    "ref.method": "Method",
    "ref.access": "Who sees what",
    "ref.layer3": "Layer 3 position",
    "jump.label": "On this page",
    "jump.flood.1": "Overview",
    "jump.flood.2": "Response summary",
    "jump.flood.3": "Helplines",
    "jump.flood.4": "Tools and resources",
    "jump.flood.5": "Programme guidance",
    "jump.flood.6": "Coordination",
    "jump.referral.1": "Helplines",
    "jump.referral.2": "The affected area",
    "jump.referral.3": "Who provides what, where",
    "foot.site": "This website",
    "foot.flood": "Flood Response",
    "foot.referral": "Referral Directory",
    "foot.resources": "Resources",
    "foot.contact": "Contact",
    "foot.tools": "Working tools",
    "foot.cards": "Printable form cards",
    "nav.band.home": "Home",
    "nav.band.flood": "Flood Response",
    "nav.band.bps": "BPS+",
    "nav.band.iec": "IEC",
    "nav.band.referral": "Referral Directory",
    "nav.band.resources": "Resources",
    "nav.band.videos": "Videos",
    "nav.band.contact": "Contact",
    "foot.draft": "MHPSS Technical Working Group, Nepal · Rasuwa–Bhotekoshi flood response · draft, September 2026. <b>Not yet agreed with EDCD or the MHPSS Technical Working Group.</b>",
    "foot.privacy": "This website presents programme-level information only. It holds no names, no client identifiers and no case information of any kind. No WHO or Government of Nepal emblem is used: WHO emblem use requires express written permission, and the national emblem belongs to the Government of Nepal. The mark in the masthead is an original one.",
    "hl.1166.kind": "National helpline · toll free",
    "hl.1166.name": "Suicide Prevention Helpline Service",
    "hl.1166.meta": "Mental Hospital, Lagankhel (मानसिक अस्पताल, लगनखेल), under the स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय / Ministry of Health and Food Safety. Toll free.",
    "hl.1166.from": "As printed on <a href=\"https://mhl.gov.np/\">mhl.gov.np</a>, read 16 September 2026. The hours are not stated there.",
    "hl.tpo.kind": "Psychosocial support · toll free",
    "hl.tpo.name": "Psychosocial Support Helpline",
    "hl.tpo.meta": "TPO Nepal. Every day from 9 AM to 5 PM. Free of cost from the Nepal Telecom network.",
    "hl.tpo.from": "As printed on <a href=\"https://www.tponepal.org/\">tponepal.org</a>, read 16 September 2026.",
    "hl.1115.kind": "Urgent health help · not a mental health line",
    "hl.1115.name": "Health Hotline",
    "hl.1115.meta": "स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय / Ministry of Health and Food Safety: “Free emergency helpline for urgent health assistance, medical rescue coordination, and hospital bed queries.”",
    "hl.1115.from": "<a href=\"https://giwmscdnone.gov.np/media/pdf_upload/EN_SitRep_13_Health_Sector_Response_to_Flash_Flood_in_Rasuwa_07-09-2026_l28spiw.pdf\">Situation Report #13</a> on the health sector response, 7 September 2026.",
    "hl.note": "A number is listed only where the service itself, or the Ministry, prints it. A number seen only in a news story is not listed until an official page carrying it has been found.",
    "hl.all": "All helplines, with their sources →",
    "live.checking": "Checking whether a summary has been published…",
    "live.noconfig": "The register is not connected to this build of the site.",
    "live.error": "The register could not be reached just now. The page tries again by itself when the connection returns.",
    "live.nonePublished": "Nothing has been published yet",
    "live.schema": "A summary was published in a form this page cannot read yet.",
    "live.preview": "Preview — not published",
    "live.published": "Published {when} — it changes only when a coordinator publishes again",
    "live.fewer": "fewer than {n}",
    "live.basis": "What is counted",
    "live.period": "Reports dated {from} to {to}.",
    "live.floor": "Counts below {n} are not shown.",
    "live.flood.none": "<b>No summary has been published yet.</b> A coordinator publishes it from the coordination hub once the Technical Working Group has agreed what may be shown. It will count the activity reports partners submit through the field forms: service contacts by district and by type of support, the organisations reporting, and the palikas they report from.",
    "live.flood.contacts": "service contacts — sessions, not people",
    "live.flood.reports": "activity reports",
    "live.flood.orgs": "organisations reporting",
    "live.flood.palikas": "palikas with a report",
    "live.flood.byFamily": "Service contacts by type of support",
    "live.col.district": "District",
    "live.col.contacts": "Contacts",
    "live.col.reports": "Reports",
    "live.col.orgs": "Organisations",
    "live.col.palika": "Palika",
    "live.col.org": "Organisation",
    "live.col.services": "Services reported",
    "live.col.last": "Last report",
    "live.ref.none": "<b>The directory has not been published yet.</b> It will list which organisation provides which mental health and psychosocial service in which palika, drawn from the activity reports partners submit, once the Technical Working Group has agreed it can be published.",
    "live.ref.empty": "The published directory lists no services yet.",
    "map.aria": "Map of the districts affected by the Rasuwa–Bhotekoshi flood, with the fifteen palikas declared disaster crisis areas filled in.",
    "map.type.mun": "Municipality",
    "map.type.rm": "Rural municipality",
    "map.key.decl": "Declared disaster crisis area",
    "map.key.other": "Other palika in an affected district",
    "map.key.dist": "Affected district",
    "map.key.ctx": "District with reported MHPSS activity, not declared affected",
    "map.key.served": "Palika listed in the published directory",
    "flood.stamp": "Prepared for WHO Nepal and the <span lang=\"ne\">स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय</span> / Ministry of Health and Food Safety (EDCD)",
    "home.cite": "IASC, <a href=\"https://interagencystandingcommittee.org/iasc-task-force-mental-health-and-psychosocial-support-emergency-settings/iasc-guidelines-mental-health-and-psychosocial-support-emergency-settings-2007\">Guidelines on Mental Health and Psychosocial Support in Emergency Settings</a>, 2007, page 1",
    "flood.tl.1": "elapsed",
    "flood.tl.2": "date not set",
    "flood.tl.3": "the reporting calendar has still to be agreed",
    "flood.tl.4": "Bhotekoshi flood",
    "flood.tl.5": "26 August 2026",
    "flood.tl.6": "Bhadra 10, 2083",
    "flood.tl.7": "Today",
    "flood.tl.8": "nothing reported into this system yet",
    "flood.tl.9": "First reporting cycle",
    "flood.tl.10": "not yet scheduled",
    "flood.tl.11": "needs the roster and the code list",
    "flood.tl.aria": "Three stations. The Bhotekoshi flood on 26 August 2026, Bhadra 10 2083. Today. And the first reporting cycle, which is not yet scheduled.",
    "flood.flow.1": "LAYER 1 · FIELD",
    "flood.flow.2": "One entry, on a phone, with no signal",
    "flood.flow.3": "LAYER 2 · COORDINATION",
    "flood.flow.4": "Duplication read, coverage measured",
    "flood.flow.5": "LAYER 3 · PUBLIC",
    "flood.flow.6": "Aggregates only — this website",
    "flood.flow.7": "aggregated",
    "flood.flow.8": "aggregated",
    "flood.flow.9": "a record, with a code —",
    "flood.flow.10": "never a name",
    "flood.flow.11": "a count, by site and week",
    "flood.flow.12": "a gap, against the roster",
    "flood.flow.aria": "Three layers. Layer 1, field entry: a record with a code, never a name. Layer 2, coordination: counts by site and week. Layer 3, public: gaps against the roster. Data flows upward only.",
    "flood.cap.2": "What this response records at each layer, and the state of it.",
    "flood.tl.day": "{n} day",
    "flood.tl.days": "{n} days",
    "home.hl": "Helplines",
    "fig.roster": "On the proposed holding-centre roster",
    "fig.roster.note": "the denominator every coverage figure is measured against",
    "fig.govlist": "On the district administration's list, not on that roster",
    "fig.govlist.note": "DAO Nuwakot, 29 Bhadra 2083 · whether they join the denominator is an open question",
    "fig.offlist": "Reported by partners, on neither list",
    "fig.offlist.note": "shown apart, and never counted as a gap",
    "fig.outside": "Reported outside Rasuwa and Nuwakot",
    "cov.cap.1": "The four figures the dashboard is built to produce, and the state of each.",
    /* ==== END layer3-shared ==== */

    /* ---- swept prose: home ---- */
    "home.p002": "<span>Health Cluster · Nepal</span> <span class=\"tagpill\">draft</span>",
    "home.p003": "<a href=\"resources.html\">Resources →</a> <a href=\"flood-response.html#coordination\">How the response is coordinated →</a>",
    "home.p004": "Common activity codes, one site list, forms a field worker can fill on a phone with no signal, and a dashboard that shows the coverage gap rather than only the total reached.",
    "home.p005": "The IASC Guidelines on MHPSS in Emergency Settings, the MHPSS Minimum Service Package, shared assessment instruments, and referral pathways, with supervision and training routed to whoever can provide them.",
    "home.p006": "A standing meeting and one shared table for who is doing what and where, so the health and protection tracks see the same picture without either giving up its own reporting line.",
    "home.p007": "<span class=\"state\">To be confirmed</span> Membership is listed by category, not by name, until the group confirms its own participant list. Naming an organisation before it has agreed to be named would be a claim, not a record.",
    "home.p008": "Organisations whose main work is not MHPSS, but whose work carries mental health or psychosocial components, belong in the same picture:",
    "home.p009": "MHPSS in Nepal has long been coordinated through two tracks: a mental health sub-cluster under the Health Cluster, and a psychosocial working group under Protection. One shared table does not ask anyone to leave their own.",
    "home.p010": "<span class=\"state\">To be agreed</span> The group’s own mission statement will be published here, in its members’ words, once they have agreed it.",
    "home.p011": "“The composite term mental health and psychosocial support is used in this document to describe any type of local or outside support that aims to protect or promote psychosocial well-being and/or prevent or treat mental disorder.”",
    "home.p012": "The group coordinates mental health and psychosocial support, the support the IASC Guidelines define in these words:",
    "home.p013": "<a href=\"flood-response.html\">Flood Response →</a> <a href=\"referral-directory.html\">Referral Directory →</a> <a href=\"resources.html\">Resources →</a>",
    "home.p014": "Mental health and psychosocial support in the Rasuwa–Bhotekoshi flood response: who to call, where to refer someone, the materials and resources that exist, and the people coordinating it.",
    "home.p015": "Education, nutrition and camp management",
    "home.p016": "Gender-based violence services",
    "home.p017": "Protection and child protection",
    "home.p018": "Professional associations and academic departments",
    "home.p019": "Organisations providing mental health and psychosocial support in the response",
    "home.p020": "WHO Nepal",
    "home.p021": "District health offices, Rasuwa and Nuwakot",
    "home.p022": "<span lang=\"ne\">स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय</span> / Ministry of Health and Food Safety — Epidemiology and Disease Control Division, NCD and Mental Health Section",
    "home.p023": "MHPSS Technical Working Group Nepal",
    "home.p024": "<span class=\"no\">3</span> What the group does",
    "home.p025": "<span class=\"no\">2</span> About the group, and who takes part",
    "home.p026": "<span class=\"no\">1</span> Mission",
    "home.p027": "Information management",
    "home.p028": "Technical resources",
    "home.p029": "Coordination",
    "home.p030": "Across sectors",
    "home.p031": "Partners",
    "home.p032": "Convened under the Health Cluster",
    "home.p033": "Forms and dashboard built, not yet agreed",
    "home.p034": "Referral pathways to be agreed",
    "home.p035": "Meeting rhythm to be set",

    /* ---- swept prose: flood ---- */
    "flood.p004": "<b>0 of 4</b><span>in place</span>",
    "flood.p005": "<span class=\"bpill plain\">Roster not yet agreed with EDCD</span> <span class=\"bpill plain\">Activity codes not yet agreed</span> <span class=\"bpill crimson\">No organisation has reported yet</span>",
    "flood.p006": "Awaiting the first reporting cycle",
    "flood.p007": "Holding-centre roster sites with no MHPSS service reported",
    "flood.p008": "Flood Response",
    "flood.p009": "<span class=\"live\">DRAFT</span> <span>Event: <b>Rasuwa–Bhotekoshi flood, 26 August 2026 · 10 Bhadra 2083</b></span> <span class=\"sep\">·</span> <span>Declared disaster crisis areas: <b>15 local levels in 5 districts</b></span> <span class=\"sep\">·</span> <span>Reporting into this system: <b>not yet started</b></span>",
    "flood.p010": "<a href=\"contact-us.html\">Contact →</a> <a href=\"hub/\">Coordination hub →</a> <a href=\"architecture.html\">How this system works →</a>",
    "flood.p011": "A way for organisations to register with the group has not been set up yet. Until it is, the roles on the Contact page are the way in.",
    "flood.p012": "The Technical Working Group’s meeting rhythm is still to be set. It will be published here once it is agreed.",
    "flood.p013": "Data moves one way. It is entered once in the field, interpreted at coordination level, and published only as aggregates. Nothing on the public layer can reach back down into a record about a person.",
    "flood.p014": "<b>Five codes sit across the layers rather than in one.</b> Referral is a pathway between layers, not a layer; a helpline contact is a channel, and the support given over it belongs to whichever layer it came from; rapid assessment, coordination meetings and training are system functions. The published mapping of the MHPSS Minimum Service Package onto the pyramid marks coordination and assessment as not applicable to a single layer for the same reason. <b>The grouping into layers is this response's own; the activity numbers are the IASC's.</b> Eight codes carry the IASC 4Ws activity subcode of the 2012 manual, Table 2, as a direct match. For five more — specialised service, medication, referral, IEC material and assessment — the subcode depends on the cadre of whoever delivered the service or on what it covered, so the form leaves it blank for coordination to assign rather than guessing. Whether a helpline contact and a coordination meeting belong in a 4Ws activity list at all is still to be decided, and so is whether the 2012 codes stay the basis: an updated set in a May 2024 draft toolkit has not been obtained.",
    "flood.p015": "<b>Source</b> — IASC, <i>Guidelines on Mental Health and Psychosocial Support in Emergency Settings</i>, 2007: the intervention pyramid figure and the description of each layer. The four layer names are as printed there. Later renderings of the figure label the layers differently; this page keeps the 2007 wording.",
    "flood.p016": "Ten of the fifteen activity codes on the field form sit in layers 2, 3 and 4. Nothing on the form records layer 1, because basic services and security are delivered by the other clusters. So this system can show whether MHPSS reached a holding centre — it cannot show whether that centre has water. The two have to be read side by side, and a coverage figure from here should never be presented as a picture of the whole response.",
    "flood.p017": "Security, adequate governance and services that address basic physical needs — food, shelter, water, basic health care, control of communicable diseases — through which the well-being of all people is protected.",
    "flood.p018": "Family tracing and reunification, assisted mourning and communal healing ceremonies, mass communication on constructive coping, supportive parenting, formal and non-formal education, livelihoods, and the activation of social networks.",
    "flood.p019": "More focused individual, family or group interventions by trained and supervised workers: psychological first aid, and basic mental health care by primary health care workers.",
    "flood.p020": "The small percentage whose suffering is intolerable and who may have significant difficulty in basic daily functioning. A small share of the population — but in a large emergency, still thousands of people.",
    "flood.p021": "All layers are important and should ideally be implemented concurrently. The pyramid is wide at the bottom because that is where most people are reached, not because the bottom layer matters more.",
    "flood.p022": "MHPSS is not one service. The IASC Guidelines describe a layered system of complementary supports, and a response is read on whether all four layers are present — not on the total number of people seen. The activity codes on the field form are grouped to these layers, so coverage can be read layer by layer rather than as a single number.",
    "flood.p031": "<b>Nothing in this section is reported data.</b> The forms and the dashboard work today and can be used, but every figure inside them is synthetic and marked as such on the page itself. No number here should be quoted as a response figure, in a report or to a donor, until the Technical Working Group has agreed the roster and a reporting calendar.",
    "flood.p032": "Five forms, on a phone, working with no signal.",
    "flood.p033": "The figure this coordination exists to produce.",
    "flood.p034": "Unique individuals. A contact is a session; the two are never added.",
    "flood.p035": "The denominator. Every coverage figure is measured against it.",
    "flood.p036": "<b>Calendars</b> — dates in Bikram Sambat appear only where the response has supplied them. No conversion between the two calendars is computed on this page or in the forms, because no verified conversion table is held. <b>Elapsed time</b> is counted from the flood date and updates itself.",
    "flood.p037": "The forms and the dashboard were built in the three weeks after the flood, and they work today. What does not exist is an agreement to use them on a schedule. That is a decision to be taken at the Technical Working Group, not a piece of software still to be written — and it is why the figures above are empty rather than late.",
    "flood.p038": "Three stations, not an axis: the third has no date yet, so drawing a length for it would be inventing one.",
    "flood.p039": "Which holding centres have received a mental health or psychosocial service, which have received none, and who is providing what — counted once, against one roster, by every organisation reporting.",
    "flood.p040": "This section is about coordination rather than services: what a shared picture of who is doing what, and where, needs before it can be drawn, and where the response stands today. It is written for partners and for the Ministry.",
    "flood.p041": "No guidance on MHPSS programme priorities by phase — immediate, medium and longer term — has been published for this response. When the Technical Working Group adopts one, it will be posted here.",
    "flood.p042": "<b>Sources</b> — the code of conduct is hosted by <a href=\"https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods\">WHO Nepal</a>; the Ministry of Health and Food Safety’s <a href=\"https://giwmscdnone.gov.np/media/pdf_upload/EN_SitRep_21_Health_Sector_Response_to_Flash_Flood_in_Rasuwa_15-09-2026_lenybiz.pdf\">Situation Report #21</a> (15 September 2026) records that it was developed for psychosocial counsellors working in flood-affected areas. Materials approved for use in this response are added here as they are published.",
    "flood.p043": "A sheet of cards with a QR code for each form, to print and put where field workers will see it.",
    "flood.p044": "Activity report, service contact, PHQ-9, referral and self-report. They open on a phone and keep working with no signal. Draft: not yet agreed as the response’s reporting system.",
    "flood.p045": "WHO, 2011. How to support people in the immediate aftermath of a crisis.",
    "flood.p046": "For counsellors providing mental health and psychosocial support in flood-affected areas. Issued by the Epidemiology and Disease Control Division. In Nepali.",
    "flood.p047": "For the organisations and workers supporting people affected by the flood.",
    "flood.p048": "Three numbers, each as the service or the Ministry prints it. Two are for mental health and psychosocial support; the third is the Ministry’s hotline for urgent health help.",
    "flood.p049": "<b>How it is counted</b> — service contacts are sessions, not people: one person seen three times is three contacts, so contacts are never added to people reached. No count small enough to point to a person is shown, and no place smaller than a palika. The summary changes only when a coordinator publishes it, and it carries the time it was published.",
    "flood.p050": "What partners have reported through this group’s field forms, once the Technical Working Group publishes it. It is not the whole response: the Ministry’s own figures for mental health and psychosocial support are in its situation reports, linked above.",
    "flood.p051": "<b>Source</b> — decision of the Ministry of Home Affairs published in the Nepal Gazette on 13 Bhadra 2083, as reported by <a href=\"https://prasashan.com/2026/08/29/796869/\">Prasashan</a> and <a href=\"https://www.onlinekhabar.com/2026/08/2006217/decision-to-declare-15-flood-affected-local-levels-as-disaster-prone-areas-published-in-the-gazette\">Onlinekhabar</a>; the Gazette notice itself has not been read for this page. Seventeen municipalities in six districts: <a href=\"https://www.undp.org/asia-pacific/nepal-floods-2026\">UNDP, Nepal Floods 2026</a>. <a href=\"referral-directory.html#map\">See the declared palikas on the map →</a>",
    "flood.p052": "These are the palikas the Government has declared, not every place the flood touched. UNDP, citing the Flash Appeal, counts 17 municipalities in six districts, adding Chitwan; the two municipalities beyond the Gazette’s fifteen are not named in any source read for this page, so they are not listed or drawn.",
    "flood.p053": "Fifteen local levels in five districts, declared for three months under section 32(1) of the Disaster Risk Reduction and Management Act, 2074.",
    "flood.p054": "National Disaster Risk Reduction and Management Authority, Situation Report #01",
    "flood.p055": "“5 districts are affected, including 2 severely affected districts (Rasuwa and Nuwakot) … and 3 moderately affected districts (Dhading, Gorkha, and Chitwan).”",
    "flood.p056": "National Disaster Risk Reduction and Management Authority, <a href=\"https://ndrrma.gov.np/mediafiles/rasuwa/Rasuwa_Flood_SitRep_Temp_ENG_01_01092026.pdf\">Situation Report #01</a>, 1 September 2026",
    "flood.p057": "“…a major ice–rock avalanche occurred in the upper Bhote Koshi watershed near the China–Nepal border, approximately 20 km upstream of Rasuwagadhi.”",
    "flood.p058": "Ministry of Home Affairs, <a href=\"https://moha.gov.np/en/post/ha-ra-tha-ka-apa-l-11\">Official Disaster Relief Appeal</a>",
    "flood.p059": "“On Wednesday, 10 Bhadra 2083 (26 August 2026) at 8:40 AM, a massive flood in the Bhote Koshi River of Rasuwa District caused heavy loss of life and property.”",
    "flood.p060": "Each fact below is quoted from the body that published it, with the source beside it. The sources do not agree on how far the flood reached, because they were written on different days and for different purposes, so no number on this page is given without its own.",
    "flood.p061": "What happened, which helplines to call, the tools field partners use, and how mental health and psychosocial support in the response is coordinated.",
    "flood.p062": "<a href=\"access-explained.html\">Who can see what</a> — the access model in plain language",
    "flood.p063": "<a href=\"architecture.html\">Architecture concept</a> — how the three layers are built",
    "flood.p064": "<a href=\"method.html\">Data model and method</a> — what the model holds, and what it refuses to guess",
    "flood.p065": "The register refuses names, phone numbers, dates of birth, national IDs and precise locations",
    "flood.p066": "A reported site that is not on the roster is shown apart, never counted as a gap",
    "flood.p067": "No automatic Bikram Sambat conversion, because no verified conversion table is held",
    "flood.p068": "An IASC activity subcode is left blank where it depends on who delivered the service or what it covered",
    "flood.p069": "<span class=\"box\"></span> <span class=\"txt\"><b>One cycle of partner submissions</b> <i>Needs all three above. Until it happens, every figure on this page is empty rather than estimated.</i></span> <span class=\"st grey\">none yet</span>",
    "flood.p070": "<span class=\"box\"></span> <span class=\"txt\"><b>Reporting calendar</b> <i>Who submits, against which roster, and how often.</i></span> <span class=\"st\">not set</span>",
    "flood.p071": "<span class=\"box\"></span> <span class=\"txt\"><b>Activity code list</b> <i>Consolidated from what partners submitted, and carrying the IASC 4Ws subcodes of the 2012 manual where the match is direct. Not yet agreed with EDCD or the Technical Working Group.</i></span> <span class=\"st\">not agreed</span>",
    "flood.p072": "<span class=\"box\"></span> <span class=\"txt\"><b>Holding-centre roster</b> <i>The list of sites, and the population at each. Agreed with EDCD and the district health offices in Rasuwa and Nuwakot.</i></span> <span class=\"st\">not agreed</span>",
    "flood.p073": "Rasuwa–Bhotekoshi flood",
    "flood.p074": "<span class=\"no\">6</span> How MHPSS in the response is coordinated",
    "flood.p075": "Not published yet",
    "flood.p076": "<span class=\"no\">5</span> Phased programme guidance",
    "flood.p077": "<span class=\"no\">4</span> Tools and resources for the field",
    "flood.p078": "<span class=\"no\">3</span> Helplines",
    "flood.p079": "<span class=\"no\">2</span> Response summary",
    "flood.p080": "<span class=\"no\">1</span> Overview",
    "flood.p081": "Joining the group",
    "flood.p082": "Meetings",
    "flood.p083": "Meetings, and joining the group",
    "flood.p084": "Read further",
    "flood.p085": "What the model refuses to guess",
    "flood.p086": "How a report becomes a figure on this site",
    "flood.p087": "Where this sits in the MHPSS response",
    "flood.p089": "Forms in the field",
    "flood.p090": "Sites with no service",
    "flood.p091": "People reached",
    "flood.p092": "Holding-centre roster",
    "flood.p093": "One shared table for MHPSS in the Rasuwa–Bhotekoshi response",
    "flood.p094": "Printable form cards",
    "flood.p095": "Field forms",
    "flood.p096": "Psychological first aid: guide for field workers",
    "flood.p097": "Code of conduct for psychosocial counsellors",
    "flood.p098": "For the wider picture",
    "flood.p099": "The IASC intervention pyramid",
    "flood.p101": "Where the response is now",
    "flood.p102": "What a coverage figure requires",
    "flood.p103": "Declared disaster crisis areas",
    "flood.p104": "State",
    "flood.p105": "Codes",
    "flood.p106": "Activity codes on the field form",
    "flood.p107": "Layer",
    "flood.p112": "outside this system",
    "flood.p113": "No activity code. This layer is delivered by the other clusters; what the Technical Working Group reports is whether MHPSS is present within it",
    "flood.p114": "1 · Basic services and security",
    "flood.p115": "code list not agreed",
    "flood.p116": "Psychoeducation and awareness sessions; recreational and structured activity; child-friendly space activity; IEC material distribution",
    "flood.p117": "2 · Community and family supports",
    "flood.p118": "code list not agreed",
    "flood.p119": "Psychological first aid; individual and group psychosocial counselling; support to responders and staff care",
    "flood.p120": "3 · Focused, non-specialised supports",
    "flood.p121": "code list not agreed",
    "flood.p122": "Specialised mental health service; psychotropic medication provision",
    "flood.p123": "4 · Specialised services",
    "flood.p139": "What this figure says",
    "flood.p140": "Basic services and security",
    "flood.p141": "Community and family supports",
    "flood.p142": "Focused, non-specialised supports",
    "flood.p143": "Specialised services",
    "flood.p145": "What this figure says",
    "flood.p146": "What this list says",
    "flood.p147": "ready to use · synthetic data only",
    "flood.p148": "needs the roster and one reporting cycle",
    "flood.p149": "Not yet reporting",
    "flood.p150": "see the counting rules below",
    "flood.p151": "Not yet reporting",
    "flood.p152": "with EDCD and the district health offices",
    "flood.p153": "To be confirmed",
    "flood.p154": "not yet agreed",
    "flood.p155": "Open the card sheet →",
    "flood.p156": "Open the forms →",
    "flood.p157": "Open the guide →",
    "flood.p158": "Open the code (PDF) →",
    "flood.p159": "ENGLISH",
    "flood.p160": "WHO Nepal",
    "flood.p161": "ENGLISH",
    "flood.p162": "OCHA, on ReliefWeb",
    "flood.p163": "ENGLISH",
    "flood.p164": "National Disaster Risk Reduction and Management Authority — Situation Report #01, 1 September 2026",
    "flood.p165": "ENGLISH",
    "flood.p166": "Health Emergency Operation Centre — dashboard",
    "flood.p167": "NEPALI",
    "flood.p168": "Epidemiology and Disease Control Division — published 15 September 2026",
    "flood.p169": "ENGLISH",
    "flood.p170": "Ministry of Health and Food Safety, Health Emergency and Disaster Management Unit — 16 September 2026, with a section on mental health and psychosocial support",
    "flood.p171": "NEPALI",
    "flood.p172": "Ministry of Health and Food Safety — the health sector response, posted daily",
    "flood.p173": "Rasuwa and Nuwakot most severely",
    "flood.p174": "Where",
    "flood.p175": "An ice–rock avalanche upstream",
    "flood.p176": "What caused it",
    "flood.p177": "26 August 2026, 8:40 AM",
    "flood.p178": "When",

    /* ---- swept prose: bps ---- */
    "bps.p001": "BPS+",
    "bps.p002": "This page is for a basic psychosocial skills course adapted to Nepal and to this response, module by module and in the languages the course is taught in. Nothing is posted until real, approved material exists; a course is not described here before it has been written.",
    "bps.p003": "A short course in basic psychosocial skills for frontline workers in the flood response.",
    "bps.p004": "Basic psychosocial skills",
    "bps.p005": "No course material has been published here yet",
    "bps.p006": "The guide such a course starts from",
    "bps.p007": "ENGLISH",
    "bps.p008": "WHO, 2011",
    "bps.p009": "ENGLISH",
    "bps.p010": "Inter-Agency Standing Committee Reference Group on Mental Health and Psychosocial Support, 2020",

    /* ---- swept prose: iec ---- */
    "iec.p001": "<b>Source</b> — Ministry of Health and Food Safety, Health Emergency and Disaster Management Unit, <a href=\"https://giwmscdnone.gov.np/media/pdf_upload/EN_SitRep_21_Health_Sector_Response_to_Flash_Flood_in_Rasuwa_15-09-2026_lenybiz.pdf\">Situation Report #21</a> on the health sector response to the flash flood in Rasuwa, 15 September 2026.",
    "iec.p002": "The Ministry of Health and Food Safety reports that “Mental Health IEC materials are being distributed” in the response. Those materials are not on this site. They will be listed here, by topic, once they are approved for publication.",
    "iec.p003": "Leaflets, posters and messages on mental health and psychosocial support, to hand out and put up where people affected by the flood will see them.",
    "iec.p004": "Information, education and communication materials",
    "iec.p005": "No materials have been published here yet",

    /* ---- swept prose: refdir ---- */
    "refdir.p001": "Referral Directory",
    "refdir.p002": "<b>Before it is published</b> — the Technical Working Group and the Epidemiology and Disease Control Division have to agree that listing organisations by palika is safe for the people they serve, and each organisation listed has to agree to be named. Referral pathways between services, with their criteria, have not been agreed yet: this page lists services, it does not prescribe a route.",
    "refdir.p003": "Which organisation provides which mental health and psychosocial service, palika by palika, as partners report it through this group’s field forms.",
    "refdir.p004": "<b>Declared palikas</b> — decision of the Ministry of Home Affairs published in the Nepal Gazette on 13 Bhadra 2083, as reported by <a href=\"https://prasashan.com/2026/08/29/796869/\">Prasashan</a> and <a href=\"https://www.onlinekhabar.com/2026/08/2006217/decision-to-declare-15-flood-affected-local-levels-as-disaster-prone-areas-published-in-the-gazette\">Onlinekhabar</a>; Nepali names as those reports print them. <b>Affected districts</b> — National Disaster Risk Reduction and Management Authority, <a href=\"https://ndrrma.gov.np/mediafiles/rasuwa/Rasuwa_Flood_SitRep_Temp_ENG_01_01092026.pdf\">Situation Report #01</a>, and <a href=\"https://www.undp.org/asia-pacific/nepal-floods-2026\">UNDP</a>. <b>River corridors</b> — <a href=\"https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods\">WHO Nepal, 2026 Rasuwa flash floods</a>. <b>Kathmandu and Nawalparasi (Bardaghat Susta East)</b> are drawn because this response’s site list records MHPSS activity there, not because they are affected. <b>Boundaries</b> — OCHA Common Operational Dataset, Nepal administrative boundaries v02 (Survey Department of Nepal; UN Resident Coordinator’s Office), <a href=\"https://data.humdata.org/dataset/cod-ab-npl\">HDX</a>, CC BY-IGO; simplified for the screen, not for measurement.",
    "refdir.p005": "The declared palikas follow the Bhote Koshi and Trishuli river corridors, along which WHO describes communities as affected: from the northern border through Nuwakot and Dhading, down to Gorkha and Tanahun. Chitwan is counted as affected by the national disaster authority, but none of its palikas is on the Government’s declaration, so it is drawn with no palika filled.",
    "refdir.p006": "The fifteen palikas the Government has declared disaster crisis areas, drawn on the official boundaries, with the districts around them. When the directory below is published, every palika it lists is outlined here as well.",
    "refdir.p007": "For someone who needs to talk to a person now, or for a worker who needs a referral route that is open today.",
    "refdir.p008": "Helplines that can be called today, the area the Government has declared affected, and, once it is published, which organisation provides which mental health and psychosocial service in which palika.",
    "refdir.p009": "The name or phone number of any person, worker or client",
    "refdir.p010": "Any place smaller than a palika, or a point on the map",
    "refdir.p011": "The name of a holding centre, a shelter or a school",
    "refdir.p012": "The date of the most recent report",
    "refdir.p013": "The services reported there, named as on the field forms",
    "refdir.p014": "The organisation, the palika and the district",
    "refdir.p015": "Where to refer someone",
    "refdir.p016": "<span class=\"no\">3</span> Who provides what, where",
    "refdir.p017": "<span class=\"no\">2</span> The affected area",
    "refdir.p018": "<span class=\"no\">1</span> Helplines",
    "refdir.p019": "What it never shows",
    "refdir.p020": "What the directory shows",
    "refdir.p021": "Declared disaster crisis areas, palika by palika",
    "refdir.p022": "What this map says",

    /* ---- swept prose: res ---- */
    "res.p001": "Resources",
    "res.p002": "<b>Adding a resource</b> — send the published link through the roles on the <a href=\"contact-us.html\">Contact</a> page. A resource is listed when it can be opened at its source, and it is listed under the name its publisher gives it.",
    "res.p003": "Published guidance, tools and research for the organisations working in the response. Each item links to the body that published it; nothing is listed that has not been found at its source.",
    "res.p004": "Resources",
    "res.p005": "Publications on Nepal",
    "res.p006": "Training, tools and guidelines",
    "res.p007": "Core MHPSS guidance",
    "res.p008": "For this response, in Nepal",
    "res.p009": "ENGLISH",
    "res.p010": "Sherchan, Samuel, Marahatta and others — WHO South-East Asia Journal of Public Health, 2017",
    "res.p011": "ENGLISH",
    "res.p012": "Chase, Marahatta, Sidgel and others — International Journal of Mental Health Systems, 2018",
    "res.p013": "ENGLISH",
    "res.p014": "Inter-Agency Standing Committee Reference Group, 2012 — on the MHPSS Network",
    "res.p015": "ENGLISH",
    "res.p016": "Inter-Agency Standing Committee, 2020",
    "res.p017": "ENGLISH",
    "res.p018": "WHO, 2011",
    "res.p019": "ENGLISH",
    "res.p020": "Inter-Agency Standing Committee",
    "res.p021": "ENGLISH",
    "res.p022": "Inter-Agency Standing Committee, 2007",
    "res.p023": "NEPALI",
    "res.p024": "Ministry of Health and Food Safety — the health sector response, including mental health and psychosocial support, posted daily",
    "res.p025": "NEPALI",
    "res.p026": "Epidemiology and Disease Control Division, 2026 — hosted by WHO Nepal",

    /* ---- swept prose: vid ---- */
    "vid.p001": "Videos",
    "vid.p002": "Videos will be listed here, with the organisation that made each one and the language it is in, once there are videos approved for use in this response.",
    "vid.p003": "Short videos on mental health and psychosocial support, for people affected by the flood and for the workers supporting them.",
    "vid.p004": "Videos",
    "vid.p005": "No videos have been published here yet",

    /* ---- swept prose: contact ---- */
    "contact.p001": "Contact",
    "contact.p002": "This page has no contact form and lists no personal phone number, by design. A form would collect information about the people who use it, and the group holds no information about individuals.",
    "contact.p003": "The group coordinates services; it does not provide them. For someone who needs support now, the helplines are on the <a href=\"flood-response.html#helplines\">Flood Response</a> and <a href=\"referral-directory.html#helplines\">Referral Directory</a> pages.",
    "contact.p004": "Three roles coordinate the group. The names and addresses of the people holding them are published here once each has agreed to be listed.",
    "contact.p005": "Contact the group",
    "contact.p006": "Information management",
    "contact.p007": "WHO co-lead",
    "contact.p008": "Technical Working Group lead",
    "contact.p009": "Looking for help, not the group?",
    "contact.p010": "For the field forms, the coordination hub and the reporting calendar",
    "contact.p011": "To be confirmed",
    "contact.p012": "WHO Nepal",
    "contact.p013": "To be confirmed",
    "contact.p014": "Ministry of Health and Food Safety — Epidemiology and Disease Control Division",
    "contact.p015": "To be confirmed",

    /* ---- swept prose: cov ---- */
    "cov.p001": "<span><i class=\"roster\"></i>On the proposed roster · no service reported</span> <span><i class=\"served\"></i>On the roster · at least one service reported</span> <span><i class=\"govlist\"></i>On the district list, not on the roster</span> <span><i class=\"offroster\"></i>Reported off both lists</span> <span><i class=\"outside\"></i>Outside the two districts</span>",
    "cov.p002": "<b>Counting rules</b> — reach is unique individuals; a service contact is a session. The two are never added together. A site that appears in a report but is not on the roster is shown separately and is never counted as a gap. Activity codes carry the IASC 4Ws subcode of the 2012 manual where the match is direct, and leave it blank where it depends on who delivered the service or what it covered, rather than guess.",
    "cov.p003": "<b>Source</b> — the site list in <code>assets/codes.js</code>, following the code list of 15 September 2026: the holding-centre roster held by the district health offices, the District Administration Office Nuwakot list of 29 Bhadra 2083, and the site names appearing in partner reports. The roster has not been agreed with EDCD, so the denominator may still change. Fifteen further sites sit in Dhading, Kathmandu, Nawalparasi (Bardaghat Susta East) and Sindhupalchok: the response reached beyond the two flood districts, which is why a district column exists on every form.",
    "cov.p004": "The roster holds 23 sites. The district administration in Nuwakot lists 12 more, and partners have reported from 31 places that are on neither list, 15 of them outside the two districts. The difference is not an error in the data to be cleaned up — it is the roster question: either those places belong on the roster, or the response has extended past it. Only EDCD and the district health offices in Rasuwa and Nuwakot can settle that, and until they do, the denominator of every coverage figure is provisional. That is the first thing to put on an agenda, ahead of any reporting format.",
    "cov.p005": "A square is one site code in the response's site list. A square is filled when at least one organisation has reported an MHPSS activity there. None is filled, because no organisation has reported yet — so this figure is, for now, the gap itself.",
    "cov.p006": "A total can look healthy while a whole holding centre has nobody. So the measure is not the total reached — it is coverage against the official roster, and the gap is the point.",
    "cov.p007": "What is being measured, and against what",
    "cov.p008": "Every site in the response, one square each",
    "cov.p009": "State",
    "cov.p010": "Denominator",
    "cov.p011": "Definition",
    "cov.p012": "Figure",
    "cov.p013": "calendar not agreed",
    "cov.p014": "Partners active in the response",
    "cov.p015": "Partners submitting against the shared roster in a given cycle",
    "cov.p016": "Organisations reporting",
    "cov.p017": "no submissions",
    "cov.p018": "Sessions. One person may have several; never added to the figure above",
    "cov.p019": "Service contacts",
    "cov.p020": "no submissions",
    "cov.p021": "Affected population at the site",
    "cov.p022": "Unique individuals, deduplicated across organisations",
    "cov.p023": "People reached",
    "cov.p024": "roster not agreed",
    "cov.p025": "Holding-centre roster",
    "cov.p026": "Roster sites for which no organisation has reported any MHPSS activity",
    "cov.p027": "Sites with no service",
    "cov.p028": "What this figure says",

    /* ---- the machine-translation notice ----
       Shown in BOTH languages at once, on purpose. A notice that says "this
       was machine translated" must not itself depend on machine translation
       to be readable -- that fails at the one point where it matters. So the
       Nepali and the English sit side by side and the reader gets whichever
       they can read.

       The Nepali below was drafted by Claude, not a translator. It is the
       FIRST string that should go to a human, ahead of any page content:
       it is the sentence that tells a Ministry reader how much to trust
       everything else on the page. */
    "mt.notice.ne":       "यो पृष्ठ स्वचालित रूपमा अनुवाद गरिएको हो।",
    "mt.authoritative.ne": "अंग्रेजी संस्करण आधिकारिक हो।",
    "mt.clinicalKept.ne": "चिकित्सकीय शब्दावली अंग्रेजीमै राखिएको छ।",
    /* The wording for a page that is NOT yet keyed up: its prose is still
       English, but the choices in its dropdowns come from the code lists,
       which now have Nepali. Saying "this page was translated
       automatically" there would be false, and a false notice is worse
       than no notice. */
    /* A page with no keys AND no dropdowns: nothing on it is in Nepali,
       so neither of the other two sentences is true of it. Saying nothing
       would be worse -- a reader who pressed NEP and saw English needs to
       know that is the state of the page, not a fault in their browser. */
    "mt.notyet.ne":       "यो पृष्ठ अझै नेपालीमा उपलब्ध छैन।",
    "mt.notyet.auth.ne":  "अंग्रेजी संस्करण आधिकारिक हो।",
    "mt.notyet.en":       "This page is not available in Nepali yet.",
    "mt.notyet.auth.en":  "The English version is the authoritative one.",
    "mt.partial.ne":      "यो फारमका सूचीका विकल्पहरू नेपालीमा स्वचालित रूपमा अनुवाद गरिएका छन्। बाँकी पृष्ठ अझै अंग्रेजीमा छ।",
    "mt.partial.auth.ne": "अंग्रेजी संस्करण आधिकारिक हो।",
    "mt.partial.en":      "The choices in this form's lists have been translated automatically into Nepali. The rest of this page is still in English.",
    "mt.partial.auth.en": "The English version is the authoritative one.",
    "mt.notice.en":       "This page was translated automatically.",
    "mt.authoritative.en": "The English version is the authoritative one.",
    "mt.clinicalKept.en": "Clinical wording is kept in English.",
    "mt.readEnglish":     "Read in English",
    "mt.dismiss":         "Dismiss",
    "i18n.keptTitle":     "Kept in English on purpose — clinical wording awaiting professional translation",

    /* ---- the untranslated marker ---- */
    "i18n.todoTitle":     "Not yet translated — shown in English",
    "i18n.progress":      "{done} of {total} translated"
  },

  /* Filled by the translator, imported from the worksheet. Empty is not a
     bug: an empty value renders the English with a visible marker so that
     a half-translated page cannot be mistaken for a finished one. */
  /* AI-DRAFTED, NOT REVIEWED BY A TRANSLATOR.
     Short strings only -- navigation, titles, layer labels, buttons. The
     long descriptive paragraphs are deliberately absent: at 60 words a
     draft reads awkwardly in a way a reader notices, and an awkward
     Ministry-facing page costs more than a visibly untranslated one. Those
     show as "to do" until a person writes them.

     Terms are taken from the response's own documents where it has one --
     होल्डिङ सेन्टर from the roster sheet's own title, समन्वय from
     जिल्ला समन्वय समिति, प्रतिवेदन from the daily reporting sheet. A
     general translation engine cannot do that, and would invent its own
     vocabulary that then fails to match the national one. */
  ne: {
    "hub.d1.go": "फारम सूची खोल्नुहोस् →",
    "hub.d1.layer": "तह १ · क्षेत्र",
    "hub.d1.title": "क्षेत्रीय फारमहरू",
    "hub.d2.go": "समन्वय दृश्य खोल्नुहोस् →",
    "hub.d2.layer": "तह २ · समन्वय",
    "hub.d2.title": "समन्वय दृश्य",
    "hub.d3.layer": "तह ३ · सार्वजनिक",
    "hub.d3.soon": "योजनामा · हस्तान्तरणको अवस्था पढ्नुहोस्",
    "hub.d3.title": "सार्वजनिक तह",
    "hub.d4.go": "अवधारणा पढ्नुहोस् →",
    "hub.d4.title": "संरचनाको अवधारणा",
    "hub.d5.go": "विधि पढ्नुहोस् →",
    "hub.d5.title": "डेटा ढाँचा र विधि",
    "hub.d6.go": "पहुँच ढाँचा पढ्नुहोस् →",
    "hub.d6.title": "कसले के देख्न सक्छ",
    "hub.flow.title": "दिशा किन महत्त्वपूर्ण छ",
    "hub.org": "विश्व स्वास्थ्य संगठन · नेपाल &nbsp;·&nbsp; स्वास्थ्य तथा खाद्य स्वच्छता मन्त्रालय",
    "hub.ref": "सन्दर्भ",
    "hub.title": "एकीकृत केन्द्र",
    "i18n.keptTitle": "जानाजानी अंग्रेजीमा राखिएको — चिकित्सकीय शब्दावली व्यावसायिक अनुवाद कुर्दै",
    "i18n.todoTitle": "अझै अनुवाद भएको छैन — अंग्रेजीमा देखाइएको",
    "lang.select": "भाषा छान्नुहोस्",
    "mt.dismiss": "बन्द गर्नुहोस्",
    "mt.readEnglish": "अंग्रेजीमा पढ्नुहोस्",
    "nav.access": "पहुँच",
    "nav.coordination": "समन्वय दृश्य",
    "nav.forms": "क्षेत्रीय फारमहरू",
    "nav.hub": "केन्द्र",
    "nav.inbox": "क्षेत्रीय इनबक्स",
    "nav.method": "विधि",
    "nav.whoSees": "कसले के देख्न सक्छ",
    /* ==== BEGIN layer3-shared (machine drafts, short strings only) ==== */
    "mast.cluster": "स्वास्थ्य क्लस्टर · नेपाल",
    "mast.place": "रसुवा · नुवाकोट · बाढी प्रतिकार्य",
    "mast.hub": "समन्वय केन्द्र",
    "banner.demo": "प्रदर्शन संस्करण · मस्यौदा",
    "ref.strip": "यो प्रणाली कसरी काम गर्छ",
    "ref.architecture": "संरचना",
    "ref.method": "विधि",
    "ref.access": "कसले के देख्न सक्छ",
    "jump.label": "यस पृष्ठमा",
    "jump.flood.1": "समग्र विवरण",
    "jump.flood.2": "प्रतिकार्य सारांश",
    "jump.flood.3": "हेल्पलाइन",
    "jump.flood.4": "औजार तथा स्रोत सामग्री",
    "jump.flood.5": "कार्यक्रम मार्गदर्शन",
    "jump.flood.6": "समन्वय",
    "jump.referral.1": "हेल्पलाइन",
    "jump.referral.2": "प्रभावित क्षेत्र",
    "jump.referral.3": "कसले कहाँ के सेवा दिन्छ",
    "foot.site": "यो वेबसाइट",
    "foot.flood": "बाढी प्रतिकार्य",
    "foot.referral": "रेफरल निर्देशिका",
    "foot.resources": "स्रोत सामग्री",
    "foot.contact": "सम्पर्क",
    "foot.tools": "कामका औजार",
    "foot.cards": "छाप्न मिल्ने फारम कार्ड",
    "nav.band.home": "गृहपृष्ठ",
    "nav.band.flood": "बाढी प्रतिकार्य",
    "nav.band.bps": "BPS+ तालिम",
    "nav.band.iec": "IEC सामग्री",
    "nav.band.referral": "रेफरल निर्देशिका",
    "nav.band.resources": "स्रोत सामग्री",
    "nav.band.videos": "भिडियो",
    "nav.band.contact": "सम्पर्क",
    "hl.all": "सबै हेल्पलाइन, स्रोतसहित →",
    "live.col.district": "जिल्ला",
    "live.col.palika": "पालिका",
    "live.col.org": "संस्था",
    "live.col.orgs": "संस्था",
    "live.col.reports": "प्रतिवेदन",
    "map.type.mun": "नगरपालिका",
    "map.type.rm": "गाउँपालिका",
    "home.hl": "हेल्पलाइन",
    /* ==== END layer3-shared ==== */
  }
};
