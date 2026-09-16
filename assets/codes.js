/* =====================================================================
   MHPSS Nepal — controlled vocabularies
   ---------------------------------------------------------------------
   PROVENANCE. Every list below is derived from records already held by
   the response, not invented:
     - SITES      : holding-centre roster sheet "होल्डिङ सेन्टरहरुको विवरण"
                    of the daily reporting workbook (Rasuwa 4 · Nuwakot 19),
                    plus sites that appear in submitted reports but are not
                    on that roster (marked source:"reported").
     - ORGS       : provider names actually appearing in submitted reports.
     - ACTIVITIES : activity descriptions actually submitted, consolidated.
                    The IASC 4Ws activity CODES are NOT filled in — the
                    official code list must be obtained from the manual
                    before `iasc` is populated. Do not guess them.
     - DISTRICTS / TARGET GROUPS / CADRES : standard operational categories.

   Anything unverified is marked. Nothing here should be treated as an
   agreed list until the MHPSS sub-cluster and EDCD have signed it off.
   ===================================================================== */

const META = {
  version: "0.1.0-draft",
  compiled: "2026-09-15",
  status: "DRAFT — not agreed with EDCD or the MHPSS sub-cluster",
};

/* ---------------------------------------------------------------------
   DISTRICTS
   Districts appearing in submitted reports. Bagmati Province unless noted.
   ------------------------------------------------------------------- */
const DISTRICTS = [
  { code: "RAS", name: "Rasuwa", np: "रसुवा", np_src: "draft" },
  { code: "NUW", name: "Nuwakot", np: "नुवाकोट", np_src: "draft" },
  { code: "DHA", name: "Dhading", np: "धादिङ", np_src: "draft" },
  { code: "KTM", name: "Kathmandu", np: "काठमाडौं", np_src: "draft" },
  { code: "CHT", name: "Chitwan", np: "चितवन", np_src: "draft" },
  { code: "NAW", name: "Nawalpur", note: "Gandaki Province", np: "नवलपुर", np_src: "draft" },
  { code: "OTH", name: "Other — specify", np: "अन्य — उल्लेख गर्नुहोस्", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   SITES
   `roster`   = on the official holding-centre roster sheet
   `reported` = appears in submitted reports but not on that roster;
                needs confirmation before it is treated as a service point
   `pop`      = LEFT NULL IN THIS PUBLIC COPY. The roster records a population
                for most sites, but those are unpublished operational figures for
                named locations; they are held in the data inventory shared with
                WHO, the Ministry and EDCD, not here. The demonstration data
                supplies synthetic populations so the coverage view still works.
   ------------------------------------------------------------------- */
const SITES = [
  // ---- Rasuwa · roster ----
  { code: "RAS-01", district: "RAS", name: "District Coordination Committee, Dhunche", np: "जिल्ला समन्वय समिति, रसुवा", palika: "Dhunche", pop: null, source: "roster" },
  { code: "RAS-02", district: "RAS", name: "Shantibazar", np: "शान्तिबजार", palika: "Uttargaya RM", pop: null, source: "roster" },
  { code: "RAS-03", district: "RAS", name: "Shivalaya", np: "शिवालय", palika: null, pop: null, source: "roster" },
  { code: "RAS-04", district: "RAS", name: "Shree Komin Syambangphel Secondary School", np: "श्री कोमिन श्यामबाङफेल माध्यमिक विद्यालय", palika: "Uttargaya RM", pop: null, source: "roster" },
  // ---- Rasuwa · reported but not on the roster ----
  { code: "RAS-R1", district: "RAS", name: "Nilkantha Secondary School, Uttargaya RM", palika: "Uttargaya RM", pop: null, source: "reported" },
  { code: "RAS-R2", district: "RAS", name: "Bhimsenthan Basic School, Uttargaya-5", palika: "Uttargaya RM", pop: null, source: "reported" },
  { code: "RAS-R3", district: "RAS", name: "Shivalaya Basic School, Uttargaya-5", palika: "Uttargaya RM", pop: null, source: "reported" },
  { code: "RAS-R4", district: "RAS", name: "Komin, Syaphrubesi, Gosaikunda-5", palika: "Gosaikunda RM", pop: null, source: "reported" },
  { code: "RAS-R5", district: "RAS", name: "Sundhara Secondary School, Kalika-3", palika: "Kalika RM", pop: null, source: "reported" },
  { code: "RAS-R6", district: "RAS", name: "Dharapani, Kalika-3", palika: "Kalika RM", pop: null, source: "reported" },

  // ---- Nuwakot · roster ----
  { code: "NUW-01", district: "NUW", name: "Bhairam Secondary School, Bidur-8 / Bidur-9", np: "भैरम मा.वि., बिदुर-०८, बिदुर-०९", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-02", district: "NUW", name: "Church, Bidur Colony-9", np: "चर्च, बिदुर कोलोनी-०९", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-03", district: "NUW", name: "Sparkle Academy, Bidur-9", np: "स्पार्कल एकेडेमी, बिदुर-०९", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-04", district: "NUW", name: "Trishuli Basic School, Bidur-9", np: "त्रिशुली आ.वि., बिदुर-०९", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-05", district: "NUW", name: "Sulakshana Secondary School", np: "सुलक्षणा मा.वि.", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-06", district: "NUW", name: "Pitrimoksha (near District Administration Office), Bidur-2", np: "पितृमोक्ष, बिदुर-२", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-07", district: "NUW", name: "Chandrajyoti Secondary School, Bidur", np: "चन्द्रज्योति मा.वि.", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-08", district: "NUW", name: "Covered Hall, Colony-9", np: "कभर्ड हल, कोलोनी ९", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-09", district: "NUW", name: "Covered Hall, Bidur-4 Battar", np: "कभर्ड हल बिदुर ४ बट्टार", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-10", district: "NUW", name: "Ayurveda & Alternative Hospital, Devighat, Bidur-5", np: "आयुर्वेद तथा वैकल्पिक चिकित्सालय, देविघाट, बिदुर-५", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-11", district: "NUW", name: "Sundari Byorini Secondary School, Bidur", np: "सुन्दरी ब्योरिनी मा.वि.", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-12", district: "NUW", name: "Ranabhuneshwari Secondary School / Ward Office, Bidur", np: "रणभुनेश्वरी मा.वि./वडा कार्यालय", palika: "Bidur Mun.", pop: null, source: "roster" },
  { code: "NUW-13", district: "NUW", name: "Tribhuwan Secondary School, Kispang-5", np: "त्रिभुवन मा.वि., किस्पाङ ०५", palika: "Kispang RM", pop: null, source: "roster" },
  { code: "NUW-14", district: "NUW", name: "Karki Manakamana Basic School, Kispang-5", np: "कार्की मनकामना आ.वि. ०५", palika: "Kispang RM", pop: null, source: "roster" },
  { code: "NUW-15", district: "NUW", name: "Mahadev Secondary School, Ratmate, Belkotgadhi", np: "महादेव मा.वि. रातमाटे", palika: "Belkotgadhi Mun.", pop: null, source: "roster" },
  { code: "NUW-16", district: "NUW", name: "Janakalyan Samuha, Tupche", np: "जनकल्याण समुह तुप्चे", palika: "Tupche", pop: null, source: "roster" },
  { code: "NUW-17", district: "NUW", name: "Tamang Plaza-4", np: "तामाङ प्लाजा ४", palika: null, pop: null, source: "roster" },
  { code: "NUW-18", district: "NUW", name: "Community Building, Akhare, Tupche-7", np: "सामुदायिक भवन अखरे तुप्चे ७", palika: "Tupche", pop: null, source: "roster" },
  { code: "NUW-19", district: "NUW", name: "Church, Dandathoktar, Tupche-7", np: "चर्च डाँडाथोकटार, तुप्चे ७", palika: "Tupche", pop: null, source: "roster" },
  // ---- Nuwakot · reported but not on the roster ----
  { code: "NUW-R1", district: "NUW", name: "Kriyaputri Bhawan / Safe Home, Bidur", palika: "Bidur Mun.", pop: null, source: "reported" },
  { code: "NUW-R2", district: "NUW", name: "Samudayik Bahuudeshya Bhawan Holding Centre, Bidur", palika: "Bidur Mun.", pop: null, source: "reported" },
  { code: "NUW-R3", district: "NUW", name: "Trishuli Hospital, Bidur-9", palika: "Bidur Mun.", pop: null, source: "reported" },
  { code: "NUW-R4", district: "NUW", name: "Battar Kabaddi Hall, Bidur-4", palika: "Bidur Mun.", pop: null, source: "reported" },
  { code: "NUW-R5", district: "NUW", name: "Belkotgadhi Municipality-7", palika: "Belkotgadhi Mun.", pop: null, source: "reported" },

  // ---- Dhading · reported ----
  { code: "DHA-R1", district: "DHA", name: "Dhading Multiple Campus Holding Centre, Galchhi RM", palika: "Galchhi RM", pop: null, source: "reported" },
  { code: "DHA-R2", district: "DHA", name: "Galchhi RM (community-based)", palika: "Galchhi RM", pop: null, source: "reported" },
  { code: "DHA-R3", district: "DHA", name: "Gajuri RM", palika: "Gajuri RM", pop: null, source: "reported" },
  { code: "DHA-R4", district: "DHA", name: "Benighat Rorang RM", palika: "Benighat Rorang RM", pop: null, source: "reported" },

  // ---- Kathmandu / onward-referral locations · reported ----
  { code: "KTM-R1", district: "KTM", name: "Mustang Gumba", palika: "Kathmandu", pop: null, source: "reported" },
  { code: "KTM-R2", district: "KTM", name: "Yellow Gumba", palika: "Kathmandu", pop: null, source: "reported" },
  { code: "CHT-R1", district: "CHT", name: "Bharatpur", palika: "Bharatpur Mun.", pop: null, source: "reported" },
  { code: "NAW-R1", district: "NAW", name: "Madhyabindu Provincial Hospital", palika: "Madhyabindu Mun.", pop: null, source: "reported" },

  { code: "OTHER", district: "OTH", name: "Other — not on this list (specify below)", pop: null, source: "escape", np: "अन्य", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   ACTIVITIES
   Consolidated from what partners actually submitted. `iasc` is left
   null on purpose: the official IASC 4Ws activity code list has not
   been obtained. Populate it from the manual — do not guess.
   ------------------------------------------------------------------- */
const ACTIVITIES = [
  { code: "PFA",   iasc: null, name: "Psychological first aid",                group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "मनोवैज्ञानिक प्राथमिक उपचार", np_src: "draft", np_note: "PFA has an official WHO Nepali translation -- adopt ITS term, do not keep ours" },
  { code: "CNS-I", iasc: null, name: "Individual psychosocial counselling",    group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "व्यक्तिगत मनोसामाजिक परामर्श", np_src: "draft" },
  { code: "CNS-G", iasc: null, name: "Group psychosocial counselling",         group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "सामूहिक मनोसामाजिक परामर्श", np_src: "draft" },
  { code: "PSED",  iasc: null, name: "Psychoeducation / awareness session",    group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "मनोशिक्षा / जनचेतना सत्र", np_src: "draft" },
  { code: "RECR",  iasc: null, name: "Recreational / structured activity",     group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "मनोरञ्जनात्मक / संरचित क्रियाकलाप", np_src: "draft" },
  { code: "CFS",   iasc: null, name: "Child-friendly space activity",          group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "बालमैत्री क्षेत्रको क्रियाकलाप", np_src: "draft" },
  { code: "SPEC",  iasc: null, name: "Specialised mental health service",      group: "Specialised", groupNp: "विशेषज्ञ सेवा", np: "विशेषज्ञ मानसिक स्वास्थ्य सेवा", np_src: "draft" },
  { code: "MEDS",  iasc: null, name: "Psychotropic medication provision",      group: "Specialised", groupNp: "विशेषज्ञ सेवा", np: "मनोरोग औषधि उपलब्ध गराइएको", np_src: "draft" },
  { code: "REF",   iasc: null, name: "Referral made to another service",       group: "Referral", groupNp: "प्रेषण", np: "अन्य सेवामा प्रेषण (रेफर)", np_src: "draft" },
  { code: "HELP",  iasc: null, name: "Helpline contact",                       group: "Remote support", groupNp: "दूरस्थ सहयोग", np: "हेल्पलाइन सम्पर्क", np_src: "draft" },
  { code: "IEC",   iasc: null, name: "IEC material distribution",              group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "सूचना-शिक्षा-सञ्चार सामग्री वितरण", np_src: "draft" },
  { code: "ASMT",  iasc: null, name: "Rapid assessment / identification",      group: "Assessment", groupNp: "आकलन", np: "द्रुत आकलन / पहिचान", np_src: "draft" },
  { code: "COORD", iasc: null, name: "Coordination meeting",                   group: "Coordination", groupNp: "समन्वय", np: "समन्वय बैठक", np_src: "draft" },
  { code: "TRAIN", iasc: null, name: "Training / orientation delivered",       group: "Capacity", groupNp: "क्षमता विकास", np: "तालिम / अभिमुखीकरण सञ्चालन", np_src: "draft" },
  { code: "STAFF", iasc: null, name: "Support to responders / staff care",     group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "कार्यकर्तालाई सहयोग / स्टाफ केयर", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   ORGANISATIONS — providers appearing in submitted reports
   `donors` records the funding tags seen alongside the provider name.
   The same organisation reporting under two donor tags is a funding
   attribution, NOT two organisations — the de-duplication check relies
   on this distinction.
   ------------------------------------------------------------------- */
const ORGS = [
  { code: "TPO",    name: "TPO Nepal",                              donors: ["UNICEF"] },
  { code: "CMC",    name: "CMC-Nepal",                              donors: ["SDC", "UNICEF", "UNFPA", "AWO"] },
  { code: "CWIN",   name: "CWIN Nepal",                             donors: ["UNICEF"] },
  { code: "NRCS",   name: "Nepal Red Cross Society",                donors: [] },
  { code: "KOS",    name: "KOSHISH",                                donors: [] },
  { code: "SAMI",   name: "SaMi (via RM psychosocial counsellors)", donors: [] },
  { code: "VID",    name: "Vidushi Psychological Support Centre",   donors: [] },
  { code: "GOVPSC", name: "Government-deployed counsellor (EDCD)",  donors: [] },
  { code: "OTHER",  name: "Other — not on this list (specify)",     donors: [], np: "अन्य", np_src: "draft" },
];

const DONORS = ["UNICEF", "SDC", "UNFPA", "AWO", "Own funds", "Other", "Not specified"];

/* Cadre of the person delivering — absent from the current form, which is
   why counsellor, psychologist and psychiatrist cannot be counted apart. */
const CADRES = [
  { code: "PSC",  name: "Psychosocial counsellor", np: "मनोसामाजिक परामर्शकर्ता", np_src: "draft", np_note: "cadre title -- check against the EDCD/IOM psychosocial counsellor training curriculum" },
  { code: "SPSC", name: "Senior psychosocial counsellor", np: "वरिष्ठ मनोसामाजिक परामर्शकर्ता", np_src: "draft" },
  { code: "PSY",  name: "Psychologist", np: "मनोविद्", np_src: "draft", np_note: "मनोवैज्ञानिक is also current -- one has to be chosen and used consistently" },
  { code: "PSYT", name: "Psychiatrist", np: "मनोचिकित्सक", np_src: "draft" },
  { code: "SW",   name: "Social worker", np: "सामाजिक कार्यकर्ता", np_src: "draft" },
  { code: "HW",   name: "Health worker (non-specialist)", np: "स्वास्थ्यकर्मी (विशेषज्ञ नभएको)", np_src: "draft" },
  { code: "VOL",  name: "Trained volunteer", np: "तालिम प्राप्त स्वयंसेवक", np_src: "draft" },
  { code: "OTH",  name: "Other", np: "अन्य", np_src: "draft" },
];

/* Target groups — category codes only. Never a description of a person. */
const TARGET_GROUPS = [
  { code: "TG-BER", name: "Families of missing or deceased persons", np: "बेपत्ता वा मृतकका परिवार", np_src: "draft" },
  { code: "TG-DIS", name: "Displaced households at a holding centre or shelter", np: "आश्रयस्थल वा अस्थायी शिविरमा रहेका विस्थापित परिवार", np_src: "draft" },
  { code: "TG-COM", name: "Affected community, general", np: "प्रभावित समुदाय, सामान्य", np_src: "draft" },
  { code: "TG-CHI", name: "Children and adolescents", np: "बालबालिका र किशोरकिशोरी", np_src: "draft" },
  { code: "TG-OLD", name: "Older people", np: "ज्येष्ठ नागरिक", np_src: "draft", np_note: "the statutory term in Nepal -- confirm it is what MoH wants on a form" },
  { code: "TG-PWD", name: "People with disabilities", np: "अपाङ्गता भएका व्यक्ति", np_src: "draft", np_note: "check against the Act Relating to Rights of Persons with Disabilities 2017 wording" },
  { code: "TG-PEX", name: "People with a pre-existing mental health condition", np: "पहिलेदेखि मानसिक स्वास्थ्य समस्या भएका व्यक्ति", np_src: "draft" },
  { code: "TG-RES", name: "Frontline responders (SAR, army, police, volunteers, forensic, health)", np: "अग्रपङ्क्तिका कार्यकर्ता (खोज-उद्धार, सेना, प्रहरी, स्वयंसेवक, फोरेन्सिक, स्वास्थ्य)", np_src: "draft" },
  { code: "TG-PRG", name: "Pregnant and postpartum women", np: "गर्भवती र सुत्केरी महिला", np_src: "draft" },
];

const MODALITIES = [
  { code: "INP", name: "In person, at a site", np: "प्रत्यक्ष, सेवा स्थलमा", np_src: "draft" },
  { code: "OUT", name: "In person, outreach / mobile", np: "प्रत्यक्ष, घुम्ती / पहुँच सेवा", np_src: "draft" },
  { code: "TEL", name: "Telephone / helpline", np: "टेलिफोन / हेल्पलाइन", np_src: "draft" },
  { code: "OTH", name: "Other", np: "अन्य", np_src: "draft" },
];

const STATUS = [
  { code: "ONG", name: "Ongoing", np: "चालु", np_src: "draft" },
  { code: "CMP", name: "Completed", np: "सम्पन्न", np_src: "draft" },
  { code: "PLN", name: "Planned", np: "योजनामा", np_src: "draft" },
];

/* Convenience lookups */
const siteByCode = Object.fromEntries(SITES.map((s) => [s.code, s]));
const orgByCode = Object.fromEntries(ORGS.map((o) => [o.code, o]));
const districtByCode = Object.fromEntries(DISTRICTS.map((d) => [d.code, d]));
const activityByCode = Object.fromEntries(ACTIVITIES.map((a) => [a.code, a]));

/* Roster sites only — the denominator for coverage-gap analysis.
   A site that is merely "reported" cannot be counted as uncovered,
   because nobody ever said it should be covered. */
const ROSTER_SITES = SITES.filter((s) => s.source === "roster");

/* ---------------------------------------------------------------------
   Exposed as a global rather than an ES module on purpose: the form has
   to open straight from a file on a laptop, with no server, and browsers
   refuse ES module imports over file://. Offline-from-a-USB-stick is a
   requirement here, not a convenience.
   ------------------------------------------------------------------- */
/* ---------------------------------------------------------------------
   THE LABEL RESOLVER — one place that decides which language a code list
   shows in.
   ---------------------------------------------------------------------
   Every dropdown in every form was built from `it.name`, which is always
   English. So the Nepali site names already in this file -- 23 of them,
   written by someone who knows the places -- never appeared anywhere: the
   Nepali page still showed the English name. Adding `np` to the other
   lists would have been dead weight for the same reason.

   Now a list item carries `np` and this function picks it when the page
   is in Nepali, so adding a Nepali label to any list makes it appear in
   every form at once. Same principle as the string dictionary: one copy,
   one place, and no page has to remember.

   `np_src` records where the Nepali came from:
     "confirmed"  checked against a Nepali-language source, named in the
                  comment above the list
     "draft"      our rendering, NOT yet confirmed against an official
                  Nepali term -- the page says so, and these are what the
                  worksheet asks a Nepali speaker to check first
   Absent `np` falls back to English rather than showing a blank, because
   a field worker facing an empty dropdown cannot report at all.
   ------------------------------------------------------------------- */
function isNepali() {
  try { return document.documentElement.getAttribute("data-lang") === "ne"; }
  catch (e) { return false; }
}
function label(it) {
  if (it == null) return "";
  if (typeof it === "string") return it;
  if (isNepali() && it.np) return it.np;
  return it.name || "";
}
/* A dropdown's first line -- "Select…", "All districts". See the
   placeholders note in assets/i18n-strings.js for why these are matched by
   their English text and why that is temporary. Anything unmatched is
   returned unchanged and warned about once, so it stays visible. */
var phMissed = {};
function ph(txt) {
  if (!txt || !isNepali()) return txt;
  var map = (window.I18N_STRINGS && window.I18N_STRINGS._meta &&
             window.I18N_STRINGS._meta.placeholders) || {};
  if (map[txt]) return map[txt];
  if (!phMissed[txt]) {
    phMissed[txt] = 1;
    try { console.warn("[codes] placeholder with no Nepali:", txt); } catch (e) {}
  }
  return txt;
}

/* the lookup form: a code, and the list it belongs to */
function labelOf(list, code) {
  if (!list || !code) return code || "";
  for (var i = 0; i < list.length; i++) {
    if (list[i] && list[i].code === code) return label(list[i]);
  }
  return code;
}
/* How much of each list exists in Nepali, and how much of that is still a
   draft. Reported by tools/i18n-check.py so the code lists are counted
   next to the prose rather than being invisible to it. */
function npCoverage() {
  var out = {};
  [["SITES", SITES], ["DISTRICTS", DISTRICTS], ["ACTIVITIES", ACTIVITIES],
   ["CADRES", CADRES], ["TARGET_GROUPS", TARGET_GROUPS],
   ["MODALITIES", MODALITIES], ["STATUS", STATUS], ["ORGS", ORGS]
  ].forEach(function (pair) {
    var list = pair[1], np = 0, draft = 0;
    list.forEach(function (it) {
      if (it && it.np) { np++; if (it.np_src !== "confirmed") draft++; }
    });
    out[pair[0]] = { total: list.length, np: np, draft: draft };
  });
  return out;
}

window.CODES = {
  META, DISTRICTS, SITES, ACTIVITIES, ORGS, DONORS, CADRES,
  TARGET_GROUPS, MODALITIES, STATUS,
  siteByCode, orgByCode, districtByCode, activityByCode, ROSTER_SITES,
  label, labelOf, ph, npCoverage
};
