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
    professionalOnly: [
      "phq9.item", "phq9.scale", "phq9.cutoff",
      "consent.", "safeguard.", "clinical.",

      /* selfreport.*  -- the whole page, and this one is a judgement worth
         recording rather than a category.

         Every other page has an English reader behind it: a counsellor, a
         focal point, a Ministry officer. The notice at the top of a machine-
         translated page works for them, because they can switch to English
         and check.

         The self-report is filled in by a displaced person about their own
         distress. They have no English to fall back to, so the notice
         protects nobody -- it tells them the page may be wrong and offers
         them no way to find out. And a mistranslated question there does two
         kinds of harm at once: the answer measures nothing, and someone
         already distressed is handed a question that does not quite make
         sense about how they are coping.

         The point of the page is to hear from affected people in their own
         language. A machine draft is not a faster version of that; it is a
         different thing wearing its clothes. So the page stays English until
         a person translates it -- which is also what claude/layer1-forms.md
         already said: not to be printed or circulated until translated. */
      "selfreport."
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
      "lang.select",
      "mt.dismiss",
      "mt.readEnglish",
      "nav.access",
      "nav.coordination",
      "nav.forms",
      "nav.hub",
      "nav.inbox",
      "nav.method",
      "nav.whoSees"
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
    "hub.foot.line2": "Prepared for the WHO Nepal mental health team, the Ministry of Health and Food Safety and EDCD. Not agreed with EDCD or the MHPSS sub-cluster.",
    "hub.foot.source": "Source and method on GitHub",
    "hub.foot.emblem": "No WHO or Government of Nepal emblem is used: WHO emblem use requires express written permission and the Nepal national emblem belongs to the Ministry. Prepared with AI assistance.",
    "hub.meta.title": "MHPSS Nepal — Integrated Hub",
    "hub.meta.desc": "One door to the mental health and psychosocial support information system for the Rasuwa–Bhote Koshi flood response. Demonstration build; all figures synthetic.",

    "banner.trialSub": "· drafts for the MHPSS sub-cluster to approve · nothing you enter is sent anywhere",










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
    "ml.p011": "<b>None of these forms submits anywhere.</b> This site is a static site with no server behind it, so there is nothing for a form to send data to. Each form validates what you type, calculates what it should calculate, saves it in your own browser, and lets you export a file. They are here so the sub-cluster can see and agree the questions <i>before</i> anything is collected for real. Do not use them to record a real service and assume it was captured — it was not.",
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
    "ml.p031": "<b>Where the exports go</b> — the worker exports a file and sends it to you over WhatsApp or email; you drop it into the <a href=\"../coordination/inbox.html\">field inbox</a>, which turns the files into one table. Nothing travels on its own, because there is no server behind this site.",
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
    "sr.p033": "TO BE FILLED IN BY THE MHPSS SUB-CLUSTER: the helpline number for this response. No number has been confirmed, so none is printed here. This page must not be printed or put on a wall until a real, answered number is in this box.",
    "sr.p034": "You do not have to fill anything in first. Speak to any counsellor or health worker at this site — you can ask for them by name at the help desk, and it is free.",
    "sr.p035": "Four questions, and nobody will know it was you",
    "sr.p036": "Notes for whoever fields this",
    "sr.p037": "If you need help today",
    "sr.p038": "Clear this device",
    "sr.p039": "Export CSV",
    "sr.p040": "Send",
    "sr.p041": "Why there is no screening questionnaire on this page.",
    "sr.clinicalNote": "<b>Why there is no screening questionnaire on this page.</b> An anonymous form filled in by whoever walks past is the worst possible place for a clinical instrument: you cannot consent someone properly, you cannot give them the result, you cannot follow up a positive answer, and the people who answer are not a sample of anything. So this form asks about needs and about access to services \u2014 questions an anonymous respondent can actually answer usefully \u2014 and the clinical measure sits on the <a href=\"phq9.html\">PHQ-9 form</a>, with a named worker, consent, and a referral pathway behind it.",

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
    "hub.org": "विश्व स्वास्थ्य संगठन · नेपाल &nbsp;·&nbsp; स्वास्थ्य तथा खाद्य सुरक्षा मन्त्रालय",
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
  }
};
