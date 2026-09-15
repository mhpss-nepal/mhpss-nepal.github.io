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
  { code: "RAS", name: "Rasuwa" },
  { code: "NUW", name: "Nuwakot" },
  { code: "DHA", name: "Dhading" },
  { code: "KTM", name: "Kathmandu" },
  { code: "CHT", name: "Chitwan" },
  { code: "NAW", name: "Nawalpur", note: "Gandaki Province" },
  { code: "OTH", name: "Other — specify" },
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

  { code: "OTHER", district: "OTH", name: "Other — not on this list (specify below)", pop: null, source: "escape" },
];

/* ---------------------------------------------------------------------
   ACTIVITIES
   Consolidated from what partners actually submitted. `iasc` is left
   null on purpose: the official IASC 4Ws activity code list has not
   been obtained. Populate it from the manual — do not guess.
   ------------------------------------------------------------------- */
const ACTIVITIES = [
  { code: "PFA",   iasc: null, name: "Psychological first aid",                group: "Focused support" },
  { code: "CNS-I", iasc: null, name: "Individual psychosocial counselling",    group: "Focused support" },
  { code: "CNS-G", iasc: null, name: "Group psychosocial counselling",         group: "Focused support" },
  { code: "PSED",  iasc: null, name: "Psychoeducation / awareness session",    group: "Community support" },
  { code: "RECR",  iasc: null, name: "Recreational / structured activity",     group: "Community support" },
  { code: "CFS",   iasc: null, name: "Child-friendly space activity",          group: "Community support" },
  { code: "SPEC",  iasc: null, name: "Specialised mental health service",      group: "Specialised" },
  { code: "MEDS",  iasc: null, name: "Psychotropic medication provision",      group: "Specialised" },
  { code: "REF",   iasc: null, name: "Referral made to another service",       group: "Referral" },
  { code: "HELP",  iasc: null, name: "Helpline contact",                       group: "Remote support" },
  { code: "IEC",   iasc: null, name: "IEC material distribution",              group: "Community support" },
  { code: "ASMT",  iasc: null, name: "Rapid assessment / identification",      group: "Assessment" },
  { code: "COORD", iasc: null, name: "Coordination meeting",                   group: "Coordination" },
  { code: "TRAIN", iasc: null, name: "Training / orientation delivered",       group: "Capacity" },
  { code: "STAFF", iasc: null, name: "Support to responders / staff care",     group: "Focused support" },
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
  { code: "OTHER",  name: "Other — not on this list (specify)",     donors: [] },
];

const DONORS = ["UNICEF", "SDC", "UNFPA", "AWO", "Own funds", "Other", "Not specified"];

/* Cadre of the person delivering — absent from the current form, which is
   why counsellor, psychologist and psychiatrist cannot be counted apart. */
const CADRES = [
  { code: "PSC",  name: "Psychosocial counsellor" },
  { code: "SPSC", name: "Senior psychosocial counsellor" },
  { code: "PSY",  name: "Psychologist" },
  { code: "PSYT", name: "Psychiatrist" },
  { code: "SW",   name: "Social worker" },
  { code: "HW",   name: "Health worker (non-specialist)" },
  { code: "VOL",  name: "Trained volunteer" },
  { code: "OTH",  name: "Other" },
];

/* Target groups — category codes only. Never a description of a person. */
const TARGET_GROUPS = [
  { code: "TG-BER", name: "Families of missing or deceased persons" },
  { code: "TG-DIS", name: "Displaced households at a holding centre or shelter" },
  { code: "TG-COM", name: "Affected community, general" },
  { code: "TG-CHI", name: "Children and adolescents" },
  { code: "TG-OLD", name: "Older people" },
  { code: "TG-PWD", name: "People with disabilities" },
  { code: "TG-PEX", name: "People with a pre-existing mental health condition" },
  { code: "TG-RES", name: "Frontline responders (SAR, army, police, volunteers, forensic, health)" },
  { code: "TG-PRG", name: "Pregnant and postpartum women" },
];

const MODALITIES = [
  { code: "INP", name: "In person, at a site" },
  { code: "OUT", name: "In person, outreach / mobile" },
  { code: "TEL", name: "Telephone / helpline" },
  { code: "OTH", name: "Other" },
];

const STATUS = [
  { code: "ONG", name: "Ongoing" },
  { code: "CMP", name: "Completed" },
  { code: "PLN", name: "Planned" },
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
window.CODES = {
  META, DISTRICTS, SITES, ACTIVITIES, ORGS, DONORS, CADRES,
  TARGET_GROUPS, MODALITIES, STATUS,
  siteByCode, orgByCode, districtByCode, activityByCode, ROSTER_SITES
};
