/* =====================================================================
   MHPSS Nepal — controlled vocabularies
   ---------------------------------------------------------------------
   PROVENANCE. Every list below is derived from records already held by
   the response, not invented. Since 16 Sep 2026 the lists follow the data
   workstream's code lists of 15 Sep 2026 (workbook "MHPSS Nepal code
   lists": sheets Sites, Palikas, Districts, Organisations, Activities and
   the 47-item delta list), source references [S1]..[S22] as in that
   workbook:
     - SITES      : the holding-centre roster sheet of the daily reporting
                    workbook (23, source:"roster"), sites named in submitted
                    reports but not on that roster (31, "reported"), the DAO
                    Nuwakot list of 29 Bhadra 2083 (12, "gov-list"), and 8
                    codes retired or merged, kept only so old records resolve.
     - PALIKAS    : the 16 local levels that appear in reports or on the
                    roster, keyed by the OCHA COD-AB Nepal v02 adm3 P-code
                    (HDX cod-ab-npl, Survey Department and UN RCO; valid from
                    14 Mar 2024, last updated 14 Aug 2026).
     - ORGS       : provider names actually appearing in submitted reports;
                    official names where the workstream verified them.
     - ACTIVITIES : activity descriptions actually submitted, consolidated,
                    now carrying the IASC 4Ws activity subcodes of the 2012
                    manual (Table 2) where the match is direct, and a rule
                    where it is conditional.
     - DISTRICTS / TARGET GROUPS / CADRES : standard operational categories.

   Anything unverified is marked. Open questions are listed in META and in
   the block they concern. Nothing here should be treated as an agreed list
   until the MHPSS Technical Working Group and EDCD have signed it off.
   ===================================================================== */

const META = {
  version: "0.3.0-draft",
  compiled: "2026-09-17",
  basis: "Data workstream code lists of 15 Sep 2026 and delta list D-S01..D-M07; palika P-codes from OCHA COD-AB NPL v02; EDCD review of 17 Sep 2026 (cadre list, service settings, districts); districts from the RDNA Rasuwa-Bhotekoshi Flood 2026 (NDRRMA/NPC) and NDRRMA SitRep #1 of 1 Sep 2026",
  status: "DRAFT — not agreed with EDCD or the MHPSS Technical Working Group",
  /* held open, not decided here: see the block each one concerns */
  questions: ["D-S14", "D-S23", "D-O02", "D-C01", "D-C02", "D-A03", "D-A05"],
};

/* ---------------------------------------------------------------------
   DISTRICTS
   `province` from the workstream's Districts sheet [S7]: Bagmati except NAW. NAW carries the official name and keeps
   "Nawalpur" as an alias because partners write it [D-S24]. SIN added for
   one KOSHISH record at Chautara Hospital [D-S25] -- whether that record is
   part of the flood response is an open question (D-S23), so the district
   exists but is not treated as a response district.
   ------------------------------------------------------------------- */
const DISTRICTS = [
  { code: "RAS", name: "Rasuwa", province: "Bagmati", np: "रसुवा", np_src: "draft" },
  { code: "NUW", name: "Nuwakot", province: "Bagmati", np: "नुवाकोट", np_src: "draft" },
  { code: "DHA", name: "Dhading", province: "Bagmati", np: "धादिङ", np_src: "draft" },
  { code: "KTM", name: "Kathmandu", province: "Bagmati", np: "काठमाडौं", np_src: "draft" },
  { code: "CHT", name: "Chitwan", province: "Bagmati", np: "चितवन", np_src: "draft" },
  { code: "NAW", name: "Nawalparasi (Bardaghat Susta East)", alias: "Nawalpur", province: "Gandaki", np: "नवलपरासी (बर्दघाट सुस्ता पूर्व)", np_src: "draft" },
  { code: "SIN", name: "Sindhupalchok", province: "Bagmati", np: "सिन्धुपाल्चोक", np_src: "draft", question: "D-S23" },
  /* Added 17 Sep 2026: Gorkha named by EDCD in the review and listed as a
     core assessment district in the RDNA (local levels Shahid Lakhan and
     Gandaki RMs); Tanahun listed in the RDNA "where information available"
     and in NDRRMA SitRep #1 (missing persons). Their palikas follow once the
     COD-AB P-codes are handed over. */
  { code: "GOR", name: "Gorkha", province: "Gandaki", np: "गोरखा", np_src: "draft", src: "EDCD review 17 Sep 2026; RDNA 2026; NDRRMA SitRep #1" },
  { code: "TAN", name: "Tanahun", province: "Gandaki", np: "तनहुँ", np_src: "draft", src: "RDNA 2026; NDRRMA SitRep #1" },
  { code: "OTH", name: "Other — specify", np: "अन्य — उल्लेख गर्नुहोस्", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   PALIKAS  [D-S26]
   The 16 local levels that appear in submitted reports or on the roster.
   Official English and Devanagari names from the data workstream's code
   list (sources S3 MoFAGA booklet, S4 MoFAGA contact lists, S5 NSO census
   ward table, S6 NHFR, S8 local-government sites). `pcode` is the OCHA
   COD-AB Nepal v02 adm3 P-code -- the humanitarian join key, the one the
   NDRRMA 5W and any map will match on. It is the KEY of this list: no
   second identifier to keep in step.
   A record that names only a palika and no site is coded at palika level
   (a substantial share of the backlog records do); a palika is not a site and never
   enters the roster denominator.
   ------------------------------------------------------------------- */
const PALIKAS = [
  { pcode: "NP0329403", name: "Uttargaya Rural Municipality", np: "उत्तरगया गाउँपालिका", type: "RM", wards: 5, district: "RAS", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0329402", name: "Gosaikunda Rural Municipality", np: "गोसाईकुण्ड गाउँपालिका", type: "RM", wards: 6, district: "RAS", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0329404", name: "Kalika Rural Municipality", np: "कालिका गाउँपालिका", type: "RM", wards: 5, district: "RAS", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  /* Added 17 Sep 2026 from the official list of affected local levels in the
     RDNA Rasuwa-Bhotekoshi Flood 2026 (NDRRMA / NPC). P-codes as the COD-AB
     NPL v02 file names them (read the same day); ward counts and Devanagari
     spellings are drafts until the data workstream's code-list ruling
     confirms them. Shivapuri RM (Nuwakot, NDRRMA SitRep #1) is NOT added:
     COD-AB carries two units of that name in Nuwakot (NP0328410, NP0328596)
     and does not say which is the rural municipality -- a ruling first. */
  { pcode: "NP0329401", name: "Aamachhodingmo Rural Municipality", np: "आमाछोदिङमो गाउँपालिका", type: "RM", district: "RAS", province: "Bagmati", np_src: "draft", src: "RDNA 2026; NDRRMA SitRep #1; pcode COD-AB NPL v02 (17 Sep)" },
  { pcode: "NP0436408", name: "Shahid Lakhan Rural Municipality", np: "शहीद लखन गाउँपालिका", type: "RM", district: "GOR", province: "Gandaki", np_src: "draft", src: "RDNA 2026; pcode COD-AB NPL v02 (17 Sep)" },
  { pcode: "NP0436409", name: "Gandaki Rural Municipality", np: "गण्डकी गाउँपालिका", type: "RM", district: "GOR", province: "Gandaki", np_src: "draft", src: "RDNA 2026; pcode COD-AB NPL v02 (17 Sep)" },
  { pcode: "NP0335401", name: "Ichchhakamana Rural Municipality", alias: "Ichchha Kamana", np: "इच्छाकामना गाउँपालिका", type: "RM", district: "CHT", province: "Bagmati", np_src: "draft", src: "RDNA 2026; pcode COD-AB NPL v02 (17 Sep), spelt Ichchha Kamana there" },
  { pcode: "NP0328301", name: "Bidur Municipality", np: "विदुर नगरपालिका", type: "M", wards: 13, district: "NUW", province: "Bagmati", src: "[S3][S4][S5][S6]; pcode COD-AB NPL v02" },
  { pcode: "NP0328302", name: "Belkotgadhi Municipality", np: "बेलकोटगढी नगरपालिका", type: "M", wards: 13, district: "NUW", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0328402", name: "Kispang Rural Municipality", np: "किस्पाङ गाउँपालिका", type: "RM", wards: 5, district: "NUW", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0328406", name: "Likhu Rural Municipality", np: "लिखु गाउँपालिका", type: "RM", wards: 6, district: "NUW", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0328403", name: "Tarakeshwor Rural Municipality", np: "तारकेश्वर गाउँपालिका", type: "RM", wards: 6, district: "NUW", province: "Bagmati", src: "[S3][S4][S5][S6]; pcode COD-AB NPL v02" },
  { pcode: "NP0330410", name: "Galchhi Rural Municipality", np: "गल्छी गाउँपालिका", type: "RM", wards: 8, district: "DHA", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0330409", name: "Gajuri Rural Municipality", np: "गजुरी गाउँपालिका", type: "RM", wards: 8, district: "DHA", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0330408", name: "Benighat Rorang Rural Municipality", np: "बेनीघाट रोराङ्ग गाउँपालिका", type: "RM", wards: 10, district: "DHA", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0330407", name: "Siddhalek Rural Municipality", np: "सिद्धलेक गाउँपालिका", type: "RM", wards: 7, district: "DHA", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0327101", name: "Kathmandu Metropolitan City", np: "काठमाडौं महानगरपालिका", type: "MC", wards: 32, district: "KTM", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0335101", name: "Bharatpur Metropolitan City", np: "भरतपुर महानगरपालिका", type: "MC", wards: 29, district: "CHT", province: "Bagmati", src: "[S3][S4][S5][S6]; pcode COD-AB NPL v02" },
  { pcode: "NP0447301", name: "Madhya Bindu Municipality", np: "मध्यविन्दु नगरपालिका", type: "M", wards: 15, district: "NAW", province: "Gandaki", src: "[S3][S4][S5][S8]; pcode COD-AB NPL v02" },
  { pcode: "NP0323302", name: "Choutara Sangachowkgadhi Municipality", np: "चौतारा साँगाचोकगढी नगरपालिका", type: "M", wards: 14, district: "SIN", province: "Bagmati", src: "[S3][S5][S6][S8]; pcode COD-AB NPL v02" },
];

/* ---------------------------------------------------------------------
   SITES  -- the data workstream's list of 15 Sep 2026, applied 16 Sep 2026
   source   roster    on the workbook's holding-centre roster sheet (23)
            reported  named in submitted reports, not on that roster (31)
            gov-list  on the DAO Nuwakot list of 29 Bhadra, not on the roster
                      (12). QUESTION D-S14: do these enter the coverage
                      roster? Until ruled they are selectable on the form but
                      NOT in the denominator.
            retired   merged into another code or retired because a palika
                      or a ward is not a site (8). Kept so old records still
                      resolve; never offered on the form.
   palika   the COD-AB pcode, a key into PALIKAS; null = not established
   ward     as sourced; `ward_src` says by whom. A range means the former
            VDC spans several wards and the exact one is not established.
   np       Devanagari as printed in the source named in `np_src`; absent
            where no source carries one -- NOT drafted.
   pop      LEFT NULL IN THIS PUBLIC COPY (unpublished operational figures).
   open     the data workstream's open question on this site, verbatim.
   ------------------------------------------------------------------- */
const SITES = [
  // ---- Rasuwa ----
  { code: "RAS-01", district: "RAS", palika: "NP0329402", ward: "6", ward_src: "[S3 p.211]", name: "District Coordination Committee, Rasuwa (Dhunche)", np: "जिल्ला समन्वय समिति, रसुवा", np_src: "Roster [S1]", pop: null, source: "roster", open: "No report string maps to this site. Still open?" },
  { code: "RAS-02", district: "RAS", palika: "NP0329403", name: "Shantibazar", np: "शान्तिबजार", np_src: "Roster [S1]", pop: null, source: "roster", open: "No report string maps to this site. Not locatable in the administrative sources checked [S3, S6]. Open, and covered by anyone?" },
  { code: "RAS-03", district: "RAS", palika: "NP0329403", ward: "5", ward_src: "[S1] (partner-reported)", name: "Shivalaya (holding centre at Shivalaya Basic School)", np: "शिवालय", np_src: "Roster [S1]", pop: null, source: "roster", open: "Confirm the roster's शिवालय is the holding centre at Shivalaya Basic School, Uttargaya-5." },
  { code: "RAS-04", district: "RAS", palika: "NP0329403", name: "Shree Komin Syambangphel Secondary School", np: "श्री कोमिन श्यामबाङफेल माध्यमिक विद्यालय", np_src: "Roster [S1]", pop: null, source: "roster", open: "Is this the \"Komin, Syafrubesi\" site partners report in Gosaikunda-5 (RAS-R4)? Roster says Uttargaya; Syafrubesi is Gosaikunda-5 [S9]. Until confirmed, reports stay on RAS-R4 and RAS-04 shows no report." },
  // ---- Rasuwa · reported / DAO list ----
  { code: "RAS-R1", district: "RAS", palika: "NP0329403", ward: "5", ward_src: "[S1] (one partner)", name: "Nilkantha Secondary School (holding centre)", pop: null, source: "reported", open: "Devanagari name not in any source obtained." },
  { code: "RAS-R2", district: "RAS", palika: "NP0329403", ward: "5", ward_src: "[S1] (partner-reported)", name: "Bhimsenthan Basic School (holding centre)", pop: null, source: "reported" },
  { code: "RAS-R3", district: "RAS", palika: "NP0329403", ward: "5", ward_src: "[S1]", name: "Shivalaya Basic School, Uttargaya-5", pop: null, source: "retired", merged_into: "RAS-03", open: "See RAS-03." },
  { code: "RAS-R4", district: "RAS", palika: "NP0329402", ward: "5", ward_src: "[S1][S9]", name: "Komin, Syafrubesi", pop: null, source: "reported", open: "Possible identity with roster RAS-04 - confirm." },
  { code: "RAS-R5", district: "RAS", palika: "NP0329404", ward: "3", ward_src: "[S1] (partner-reported)", name: "Sundhara Secondary School", pop: null, source: "reported", open: "Is this the \"Kalika school\" / \"Kalika Holding Centre\" reported by CWIN?" },
  { code: "RAS-R6", district: "RAS", palika: "NP0329404", ward: "3", ward_src: "[S1][S8]", name: "Dharapani (locality), Kalika-3", pop: null, source: "reported", open: "Is there a named holding centre at Dharapani?" },
  { code: "RAS-R7", district: "RAS", palika: "NP0329403", ward: "4", ward_src: "[S1] (partner-reported)", name: "Nava Bijaya Mahendra Secondary School", pop: null, source: "reported" },
  { code: "RAS-R8", district: "RAS", palika: "NP0329403", ward: "4", ward_src: "[S1] (partner-reported)", name: "Dhunge School (reported as \"Dhunge Aa.Bi Secondary School\")", pop: null, source: "reported", open: "Basic or secondary school? The reported name is contradictory." },
  { code: "RAS-R9", district: "RAS", palika: "NP0329403", name: "Barahi Basic School", pop: null, source: "reported" },
  { code: "RAS-R10", district: "RAS", palika: "NP0329403", ward: "4", ward_src: "[S6]", name: "Laharepauwa Health Post (health camp)", pop: null, source: "reported", open: "One partner wrote \"Rasuwa 1 Bogatitar\" (Bogatitar = Uttargaya-5 [S6]). Where was the health camp held?" },
  // ---- Nuwakot ----
  { code: "NUW-01", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S2][S1] (DAO camp location) ; roster lists 8 and 9", name: "Bhairam (Bhairum) Secondary School", np: "भैरम मा.वि., बिदुर-०८, बिदुर-०९", np_src: "Roster [S1]", pop: null, source: "roster", open: "DAO lists this school together with the Colony covered hall (NUW-08) as one camp. Has NUW-08 merged into NUW-01?" },
  { code: "NUW-02", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S1] (roster)", name: "Church, Bidur Colony-9", np: "चर्च , बिदुर कोलोनी -०९", np_src: "Roster [S1]", pop: null, source: "roster", open: "Not on the DAO list of 29 Bhadra [S2] and no report maps to it. Closed or uncovered?" },
  { code: "NUW-03", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S1] (roster)", name: "Sparkle Academy", np: "स्पार्कल एकेडेमी, बिदुर-०९", np_src: "Roster [S1]", pop: null, source: "roster", open: "Not on the DAO list. Same school as DAO's \"Star Boarding, Colony\" (NUW-27), which CMC-Nepal calls Star Academy?" },
  { code: "NUW-04", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S1][S2]", name: "Trishuli Basic School", np: "त्रिशुली आ.वि., बिदुर ०९", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-05", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S2]", name: "Sulakshana Secondary School", np: "सुलक्षणा मा.वि. (roster); शुलक्षणा मा.वि. (DAO)", np_src: "Roster [S1]; DAO [S2]", pop: null, source: "roster" },
  { code: "NUW-06", district: "NUW", palika: "NP0328301", ward: "2", ward_src: "[S1][S2]", name: "Pitrimoksha - Kriyaputri Bhawan / Safe House (near District Administration Office)", np: "पितृमोक्ष (जिल्ला प्रशासन कार्यालय नजिक), बिदुर-२", np_src: "Roster [S1]", pop: null, source: "roster", open: "TPO Nepal writes \"Pitri Mokshya Kriyaputri Bhawan\" (one place). DAO lists \"सेफहाउस/क्रियापुत्रि भवन\" as one camp at Bidur-2. But KOSHISH (Bhadra 13 meeting note) lists \"Kriyaputribhawan\" and \"Safe house\" in Bidur-2 as two of seven centres. Confirm: is the Safe House a separate centre?" },
  { code: "NUW-07", district: "NUW", palika: "NP0328301", ward: "5", ward_src: "[S2]", name: "Chandrajyoti Secondary School", np: "चन्द्रज्योति मा.वि., बिदुर नगरपालिका", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-08", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S1][S2] (inferred)", name: "Covered Hall, Colony-9", np: "कभर्ड हल, कोलोनी ९", np_src: "Roster [S1]", pop: null, source: "roster", open: "DAO lists \"Colony covered hall / Bhairum school\" as one camp (see NUW-01)." },
  { code: "NUW-09", district: "NUW", palika: "NP0328301", ward: "2", ward_src: "[S2][S1] (DAO camp location) ; roster names the Bidur-4 Battar area", name: "Covered Hall (hosting Battar, Bidur-4)", np: "कभर्ड हल बिदुर ४ बट्टार क्षेत्र, बिदुर नगरपालिका", np_src: "Roster [S1]", pop: null, source: "roster", open: "Partners call it \"Battar kabaddi hall\", \"Taekwondo hall, Bidur-2\" and \"Taekwondo covered hall, Battar\". Confirm these are one building." },
  { code: "NUW-10", district: "NUW", palika: "NP0328301", ward: "5", ward_src: "[S1][S2][S6]", name: "Ayurveda and Alternative Hospital, Devighat", np: "आयुर्वेद तथा वैकल्पिक चिकित्सालय, देविघाट, बिदुर-५", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-11", district: "NUW", palika: "NP0328301", ward: "10", ward_src: "[S2]", name: "Sundari Kyaureni Secondary School (Gerkhutar)", np: "सुन्दरी ब्योरिनी मा.वि. (roster); सुन्दरि क्यौरीनि मा.वि. (DAO)", np_src: "Roster [S1]; DAO [S2]", pop: null, source: "roster", open: "Confirm the roster spelling ब्योरिनी is a typing error." },
  { code: "NUW-12", district: "NUW", palika: "NP0328301", name: "Ranabhuneshwari Secondary School / Ward Office", np: "रणभुनेश्र्वरी मा.वि./वडा कार्यालय, बिदुर नगरपालिका", np_src: "Roster [S1]", pop: null, source: "roster", open: "Not on the DAO list and no report maps to it. Closed or uncovered?" },
  { code: "NUW-13", district: "NUW", palika: "NP0328402", ward: "5", ward_src: "[S1][S2]", name: "Tribhuvan Secondary School (Archale)", np: "त्रिभुवन मा.वि., किस्पाङ ०५", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-14", district: "NUW", palika: "NP0328402", ward: "5", ward_src: "[S1] (roster)", name: "Karki Manakamana Basic School", np: "कार्की मनकामना आ.वि. ०५, किस्पाङ गाउँपालिका", np_src: "Roster [S1]", pop: null, source: "roster", open: "Not on the DAO list; no report names it (two Kispang-5 records name no site)." },
  { code: "NUW-15", district: "NUW", palika: "NP0328302", ward: "7", ward_src: "[S3]", name: "Mahadev Secondary School, Ratmate", np: "महादेव मा.वि. रातमाटे, बेलकोटगढी न.पा.", np_src: "Roster [S1]", pop: null, source: "roster", open: "DAO lists \"Mahadev Campus, Mahadev Phant\" (NUW-29) and \"Shiladevi Secondary School, Ratmate\" (NUW-30) in ward 7 but no Mahadev Secondary School. CWIN names \"Mahadev School\" and \"Mahadev Campus\" as two holding centres (row 54) - so NUW-15 and NUW-29 are kept apart. Is the school still open?" },
  { code: "NUW-16", district: "NUW", palika: "NP0328301", ward_src: "[S3] 7, 8 or 9 (not established)", name: "Janakalyan Samuha, Tupche", np: "जनकल्याण समुह तुप्चे", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-17", district: "NUW", palika: "NP0328301", ward: "4", ward_src: "[S2]", name: "Tamang Plaza, Battar", np: "तामाङ प्लाजा ४ (roster); तामाङ प्लाजा विदुर ४ बट्टार (DAO)", np_src: "Roster [S1]; DAO [S2]", pop: null, source: "roster" },
  { code: "NUW-18", district: "NUW", palika: "NP0328301", ward: "7", ward_src: "[S3] (inferred)", name: "Community Building, Akhare, Tupche", np: "सामुदायिक भवन अखरे तुप्चे ७", np_src: "Roster [S1]", pop: null, source: "roster", open: "Is this the camp DAO lists as \"Library/Health Post, Tupchetar\" (NUW-26)?" },
  { code: "NUW-19", district: "NUW", palika: "NP0328301", ward: "7", ward_src: "[S3] (inferred)", name: "Church, Dandathoktar, Tupche", np: "चर्च डाँडाथोकटार, तुप्चे ७", np_src: "Roster [S1]", pop: null, source: "roster" },
  { code: "NUW-20", district: "NUW", palika: "NP0328301", ward: "1", ward_src: "[S2]", name: "Indrayani Basic School", np: "इन्दायणी आ.वि. विदुर १", np_src: "DAO [S2]", pop: null, source: "gov-list" },
  { code: "NUW-21", district: "NUW", palika: "NP0328301", ward: "2", ward_src: "[S2]", name: "Health Post, Bidur-2 (Nuwakot Darbar)", np: "स्वास्थ्य चौकी विदुर २ नुवाकोट दरबार", np_src: "DAO [S2]", pop: null, source: "gov-list" },
  { code: "NUW-22", district: "NUW", palika: "NP0328301", ward: "3", ward_src: "[S2]", name: "Chandi Basic School, Mairitar", np: "चण्डी आ.वी मैरिटार", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "No report names it." },
  { code: "NUW-23", district: "NUW", palika: "NP0328301", ward: "2", ward_src: "[S2]", name: "Annapurna Panchakanya Basic School", np: "अन्नपुर्ण पञ्चकन्या आ.वि", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "No report names it." },
  { code: "NUW-24", district: "NUW", palika: "NP0328301", ward: "4", ward_src: "[S2]", name: "United Basic School", np: "युनाइटेड आधारभुत विद्यालय", np_src: "DAO [S2]", pop: null, source: "gov-list" },
  { code: "NUW-25", district: "NUW", palika: "NP0328301", ward: "6", ward_src: "[S2]", name: "Battar Chautara / Chisyan Kendra (cold store)", np: "बट्टार चौतारा/ चिस्यान केन्द्र", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "No report names it." },
  { code: "NUW-26", district: "NUW", palika: "NP0328301", ward: "7", ward_src: "[S2]", name: "Library / Health Post, Tupchetar", np: "लाईबेरी/स्वास्थ्य चौकी तुप्चेटार", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "Relation to roster Tupche sites NUW-16, NUW-18, NUW-19?" },
  { code: "NUW-27", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S2]", name: "Star Boarding School, Colony", np: "स्टार बोर्डिङ कोलोनि", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "Same school as roster NUW-03 Sparkle Academy? CMC-Nepal writes \"Star Academy\"." },
  { code: "NUW-28", district: "NUW", palika: "NP0328301", ward: "10", ward_src: "[S2]", name: "Khamare Syale, Keraghari", np: "खमारे स्याले, केराघारी", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "No report names it." },
  { code: "NUW-29", district: "NUW", palika: "NP0328302", ward: "7", ward_src: "[S2]", name: "Mahadev Campus, Mahadev Phant", np: "महादेव क्याम्पस महादेव फाँट", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "See NUW-15." },
  { code: "NUW-30", district: "NUW", palika: "NP0328302", ward: "7", ward_src: "[S2]", name: "Shiladevi Secondary School, Ratmate", np: "शिलादेवी मा वि रातमाटे", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "No report names it. See NUW-15." },
  { code: "NUW-31", district: "NUW", palika: "NP0328302", ward: "8", ward_src: "[S2]", name: "Janasewa Basic School", np: "जनसेवा आ. वि", np_src: "DAO [S2]", pop: null, source: "gov-list", open: "TPO Nepal calls it \"Paachkhaal Holding Center\"; CWIN calls it \"Janasewa campus\"." },
  // ---- Nuwakot · reported / DAO list ----
  { code: "NUW-R1", district: "NUW", palika: "NP0328301", ward: "2", name: "Kriyaputri Bhawan / Safe Home", pop: null, source: "retired", merged_into: "NUW-06", open: "See NUW-06. KOSHISH also names a \"Bidur 2-UHC\" among Bidur-2 centres - not established what it is." },
  { code: "NUW-R2", district: "NUW", palika: "NP0328301", name: "Samudayik Bahuudeshya Bhawan (community multipurpose building) holding centre", pop: null, source: "reported", open: "Not on the DAO list by this name. Which DAO camp is it?" },
  { code: "NUW-R3", district: "NUW", palika: "NP0328301", ward: "9", ward_src: "[S1] (partner-reported)", name: "Trishuli Hospital (including its OCMC)", pop: null, source: "reported", open: "A health facility service point, not a holding centre." },
  { code: "NUW-R4", district: "NUW", palika: "NP0328301", ward: "4", name: "Battar Kabaddi Hall", pop: null, source: "retired", merged_into: "NUW-09", open: "See NUW-09." },
  { code: "NUW-R5", district: "NUW", palika: "NP0328302", ward: "7", name: "Belkotgadhi Municipality-7", pop: null, source: "retired", retired_reason: "palika-level coding" },
  { code: "NUW-R6", district: "NUW", palika: "NP0328301", ward: "2", ward_src: "[S1] (partner-reported)", name: "Rani Mauri Hotel", pop: null, source: "reported" },
  { code: "NUW-R7", district: "NUW", palika: "NP0328302", ward: "7", ward_src: "[S3]", name: "Ratmate Church", pop: null, source: "reported" },
  { code: "NUW-R8", district: "NUW", palika: null, name: "Himalayan School", pop: null, source: "reported", open: "Palika not stated." },
  { code: "NUW-R9", district: "NUW", palika: null, name: "Siyale holding centre", pop: null, source: "reported", open: "Palika not stated." },
  { code: "NUW-R10", district: "NUW", palika: "NP0328301", name: "Patanjali Yog Bhawan", pop: null, source: "reported" },
  // ---- Dhading · reported / DAO list ----
  { code: "DHA-R1", district: "DHA", palika: "NP0330410", ward: "4", ward_src: "[S1] (partner-reported)", name: "Dhading Multiple Campus holding centre, Mastar", pop: null, source: "reported" },
  { code: "DHA-R2", district: "DHA", palika: "NP0330410", name: "Galchhi RM (community-based)", pop: null, source: "retired", retired_reason: "palika-level coding" },
  { code: "DHA-R3", district: "DHA", palika: "NP0330409", name: "Gajuri RM", pop: null, source: "retired", retired_reason: "palika-level coding" },
  { code: "DHA-R4", district: "DHA", palika: "NP0330408", name: "Benighat Rorang RM", pop: null, source: "retired", retired_reason: "palika-level coding" },
  { code: "DHA-R5", district: "DHA", palika: "NP0330409", ward: "5", ward_src: "[S1] (partner-reported)", name: "Galaudi holding centre (Sub-division Forest Office premises)", pop: null, source: "reported", open: "Is \"Galdhu holding centre, Gajuri RM\" (CMC-Nepal) the same place?" },
  { code: "DHA-R6", district: "DHA", palika: "NP0330409", ward: "5", ward_src: "[S1] (partner-reported)", name: "Ratomate (Ratamata) holding centre, Phokrakhola", pop: null, source: "reported" },
  { code: "DHA-R7", district: "DHA", palika: "NP0330410", ward: "4-7", ward_src: "[S3] (not established)", name: "Success Academy, Baireni", pop: null, source: "reported" },
  { code: "DHA-R8", district: "DHA", palika: "NP0330410", ward: "6", ward_src: "[S1] (partner-reported)", name: "Bageshwori Secondary School, Baireni", pop: null, source: "reported" },
  { code: "DHA-R9", district: "DHA", palika: "NP0330408", ward: "5", ward_src: "[S1] (partner-reported)", name: "Chandrodaya Secondary School", pop: null, source: "reported" },
  { code: "DHA-R10", district: "DHA", palika: "NP0330410", ward: "6", ward_src: "[S6]", name: "Baireni Hospital", pop: null, source: "reported" },
  { code: "DHA-R11", district: "DHA", palika: "NP0330407", ward: "6", ward_src: "[S1] (partner-reported)", name: "Satyawati Secondary School", pop: null, source: "reported", open: "Named only in a two-site record." },
  { code: "DHA-R12", district: "DHA", palika: "NP0330407", ward: "6", ward_src: "[S1] (partner-reported)", name: "Mahakali Secondary School", pop: null, source: "reported", open: "Named only in a two-site record." },
  // ---- Kathmandu · reported / DAO list ----
  { code: "KTM-R1", district: "KTM", palika: "NP0327101", ward: "15", ward_src: "[S1] (partner-reported)", name: "Mustang Gumba holding centre, Swayambhu", pop: null, source: "reported" },
  { code: "KTM-R2", district: "KTM", palika: null, name: "Yellow Gumba", pop: null, source: "reported" },
  { code: "KTM-R3", district: "KTM", palika: null, name: "Geeta Mata School (children from Yellow Gumba and Mustang Gumba)", pop: null, source: "reported" },
  { code: "KTM-R4", district: "KTM", palika: null, name: "Nepal Buddhist Dharma Service Association premises", pop: null, source: "reported", open: "Confirm it is a service point." },
  // ---- Chitwan · reported / DAO list ----
  { code: "CHT-R1", district: "CHT", palika: "NP0335101", name: "Bharatpur", pop: null, source: "retired", retired_reason: "palika-level coding" },
  // ---- Nawalparasi (Bardaghat Susta East) · reported / DAO list ----
  { code: "NAW-R1", district: "NAW", palika: null, name: "Madhyabindu Provincial Hospital", pop: null, source: "reported" },
  // ---- Sindhupalchok · reported / DAO list ----
  { code: "SIN-R1", district: "SIN", palika: "NP0323302", ward: "4-7", ward_src: "[S3] (not established)", name: "Chautara Hospital", pop: null, source: "reported", open: "Outside the flood-affected districts in the workbook. Does this KOSHISH record belong to the flood response?" },

  { code: "OTHER", district: "OTH", name: "Other — not on this list (specify below)", pop: null, source: "escape", np: "अन्य", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   ACTIVITIES
   Consolidated from what partners actually submitted. `iasc` is the IASC
   4Ws activity subcode from the 2012 manual, Table 2 (back cover) [S10],
   transcribed by the data workstream from the PDF text layer and checked
   against the page image. Three shapes:
     iasc: "7.1"            a direct match          (D-A01)
     iasc: null, iasc_of:[] the subcode depends on content or on the cadre
                            of the person delivering; the rule says how
                                                    (D-A02)
     question: "D-A03"      whether the code belongs in a 4Ws activity list
                            at all is open -- kept until ruled
   `iasc_conf` is the workstream's confidence in the match.
   OPEN: D-A05 -- the MHPSS MSP platform calls these the "old" 2014 codes and
   points to an updated set in a May 2024 draft toolkit that could not be
   obtained; which version to use is ruling R-A2. A record that combines
   several activities carries several subcodes only under ruling R-A1.
   ------------------------------------------------------------------- */
const ACTIVITIES = [
  { code: "PFA",   iasc: "7.1",  iasc_conf: "High",   iasc_rule: "Direct match.", name: "Psychological first aid",                group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "मनोवैज्ञानिक प्राथमिक उपचार", np_src: "draft", np_note: "PFA has an official WHO Nepali translation -- adopt ITS term, do not keep ours" },
  { code: "CNS-I", iasc: "8.1",  iasc_conf: "High",   iasc_rule: "Basic counselling for individuals. Use 8.4 only if the partner reports psychotherapy.", name: "Individual psychosocial counselling",    group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "व्यक्तिगत मनोसामाजिक परामर्श", np_src: "draft" },
  { code: "CNS-G", iasc: "8.2",  iasc_conf: "High",   iasc_rule: "Basic counselling for groups or families.", name: "Group psychosocial counselling",         group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "सामूहिक मनोसामाजिक परामर्श", np_src: "draft" },
  { code: "PSED",  iasc: "1.2",  iasc_conf: "Medium", iasc_rule: "1.2 raising awareness on MHPSS fits community sessions. Psychoeducation for identified individuals has no specific subcode (8.6 Other, describe).", name: "Psychoeducation / awareness session",    group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "मनोशिक्षा / जनचेतना सत्र", np_src: "draft" },
  { code: "RECR",  iasc: "3.5",  iasc_conf: "High",   iasc_rule: "3.5 excludes activities at child-friendly spaces; those are 4.1.", name: "Recreational / structured activity",     group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "मनोरञ्जनात्मक / संरचित क्रियाकलाप", np_src: "draft" },
  { code: "CFS",   iasc: "4.1",  iasc_conf: "High",   iasc_rule: "Direct match.", name: "Child-friendly space activity",          group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "बालमैत्री क्षेत्रको क्रियाकलाप", np_src: "draft" },
  { code: "SPEC",  iasc: null, iasc_of: ["10.1", "10.2", "9.1", "9.2"], iasc_conf: "Medium", iasc_rule: "10.1 non-pharmacological, 10.2 pharmacological, by specialised providers. If delivered by non-specialised providers use 9.1 / 9.2. Needs the cadre field.", name: "Specialised mental health service",      group: "Specialised", groupNp: "विशेषज्ञ सेवा", np: "विशेषज्ञ मानसिक स्वास्थ्य सेवा", np_src: "draft" },
  { code: "MEDS",  iasc: null, iasc_of: ["10.2", "9.2"], iasc_conf: "Medium", iasc_rule: "10.2 if the prescriber is a specialised provider, 9.2 if non-specialised. Cannot be assigned without cadre.", name: "Psychotropic medication provision",      group: "Specialised", groupNp: "विशेषज्ञ सेवा", np: "मनोरोग औषधि उपलब्ध गराइएको", np_src: "draft" },
  { code: "REF",   iasc: null, iasc_of: ["7.2", "9.3"], iasc_conf: "Medium", iasc_rule: "7.2 linking vulnerable people to resources with follow-up; 9.3 when community workers identify and refer people with mental disorders.", name: "Referral made to another service",       group: "Referral", groupNp: "प्रेषण", np: "अन्य सेवामा प्रेषण (रेफर)", np_src: "draft" },
  { code: "HELP",  iasc: null, question: "D-A03", iasc_rule: "No IASC subcode describes a channel. Record what was delivered (7.1, 8.1, 7.2 ...) with modality TEL. Whether HELP stays an activity is open.", name: "Helpline contact",                       group: "Remote support", groupNp: "दूरस्थ सहयोग", np: "हेल्पलाइन सम्पर्क", np_src: "draft" },
  { code: "IEC",   iasc: null, iasc_of: ["1.1", "1.2"], iasc_conf: "Medium", iasc_rule: "1.1 information on the situation or available services; 1.2 MHPSS messages.", name: "IEC material distribution",              group: "Community support", groupNp: "समुदायस्तरीय सहयोग", np: "सूचना-शिक्षा-सञ्चार सामग्री वितरण", np_src: "draft" },
  { code: "ASMT",  iasc: null, iasc_of: ["11.1", "9.3"], iasc_conf: "Medium", iasc_rule: "11.1 situation analysis or assessment (no people count). Screening that identifies individuals with mental disorders is 9.3.", name: "Rapid assessment / identification",      group: "Assessment", groupNp: "आकलन", np: "द्रुत आकलन / पहिचान", np_src: "draft" },
  { code: "COORD", iasc: null, question: "D-A03", iasc_conf: "Low", iasc_rule: "Not an MHPSS service activity; attach no people count. 6.1 only if it is orientation of, or advocacy with, aid agencies. Whether COORD stays in a 4Ws activity list is open.", name: "Coordination meeting",                   group: "Coordination", groupNp: "समन्वय", np: "समन्वय बैठक", np_src: "draft" },
  { code: "TRAIN", iasc: "11.3", iasc_conf: "High",   iasc_rule: "Training / orienting (specify topic).", name: "Training / orientation delivered",       group: "Capacity", groupNp: "क्षमता विकास", np: "तालिम / अभिमुखीकरण सञ्चालन", np_src: "draft" },
  { code: "STAFF", iasc: "11.5", iasc_conf: "High",   iasc_rule: "The manual records support to aid workers as 11.5 and never under codes 7-10. Whether police, army and search-and-rescue staff count as aid workers is not stated in the manual (open).", name: "Support to responders / staff care",     group: "Focused support", groupNp: "केन्द्रित सहयोग", np: "कार्यकर्तालाई सहयोग / स्टाफ केयर", np_src: "draft" },
  /* "Other (free text)" on every list -- EDCD, 17 Sep 2026. The text travels
     in activityOther; after one or two months the entries say whether the
     list or the guidance needs work. Not part of the activity taxonomy,
     which is being reworked on the IASC layers separately. */
  { code: "OTH",   iasc: null, iasc_conf: null, iasc_rule: "Not coded until the text is reviewed.", name: "Other — specify", group: "Not stated", groupNp: "उल्लेख नगरिएको", np: "अन्य — उल्लेख गर्नुहोस्", np_src: "draft" },
];

/* ---------------------------------------------------------------------
   ORGANISATIONS — providers appearing in submitted reports
   `name`     as partners write it: what the dropdown shows and what a
              report is matched on.
   `official` the registered name where the data workstream verified it on
              the organisation's own site [S14]; absent = not established.
   `donors`   the funding tags seen alongside the provider name. The same
              organisation reporting under two donor tags is a funding
              attribution, NOT two organisations — the de-duplication check
              relies on this distinction. One record carries two tags at
              once (D-O05).
   `partners` organisations written as joint-activity partners, not donors
              (IASC Table 1 item C) -- recorded here until the record schema
              carries a partners field (D-O04).
   OPEN: D-O02 (GOVPSC). KMC, one record, is entered under OTHER with the
   name "KMC" until it is identified (D-O06). Ruling R-O1 on SaMi is open.
   ------------------------------------------------------------------- */
const ORGS = [
  { code: "TPO",    name: "TPO Nepal",                              official: "Transcultural Psychosocial Organization Nepal (TPO Nepal)", type: "National NGO", donors: ["UNICEF", "Save the Children"], partners: ["Madhyabindu Provincial Hospital (facility partner)"] },
  { code: "CMC",    name: "CMC-Nepal",                              official: "Centre for Mental Health and Counseling-Nepal (CMC-Nepal)", type: "National NGO", donors: ["SDC", "UNICEF", "UNFPA", "AWO"], note: "AWO = AWO International e.V.; its funding link to CMC-Nepal is as reported by CMC-Nepal and not visible on either public website." },
  { code: "CWIN",   name: "CWIN Nepal",                             official: "Child Workers in Nepal Concerned Centre (CWIN-Nepal)", type: "National NGO", donors: ["UNICEF"], partners: ["National Federation of Psychosocial Counsellors Nepal (as written; not found in public sources)"] },
  { code: "NRCS",   name: "Nepal Red Cross Society",                type: "National society", donors: [], note: "Expansion not re-verified in this pass. Reports mostly at district or palika level." },
  { code: "KOS",    name: "KOSHISH",                                type: "National NGO", donors: [], note: "Official full name not established (secondary sources only)." },
  { code: "SAMI",   name: "SaMi – Safer Migration Programme",       official: "Safer Migration (SaMi) Programme, bilateral Government of Nepal–Switzerland programme; local governments implementing it appoint and mobilise psychosocial counsellors [S13]", type: "Government programme (palika-appointed counsellors)", donors: [], ruling: "R-O1 open: record the implementing agency as SaMi, or as the rural municipality that appoints the counsellor? The two strings naming Galchhi RM counsellors are probably this programme; confirm with Galchhi RM." },
  { code: "VID",    name: "Vidushi Psychological Support Center",   type: "Not established", donors: [], note: "Spelt as the partner writes it; no official page found." },
  { code: "GOVPSC", name: "Government-deployed counsellor (EDCD)",  type: "Not established", donors: [], question: "D-O02", note: "No record in the report sheet supports this label; the strings behind the inventory's Palika PSC name Galchhi RM counsellors. Retire unless a report shows EDCD-deployed counsellors." },
  { code: "OTHER",  name: "Other — not on this list (specify)",     donors: [], np: "अन्य", np_src: "draft" },
];

/* Funding tags seen in reports. "Save the Children" sat in the remarks
   column of five TPO Nepal records and was missing here (D-O01). */
/* Funding tags. Removed from the FIELD form on 17 Sep 2026 (EDCD): funding
   is collected from the organisations, not from workers on the ground. The
   list stays for the records already held and for the reconciliation
   lists; no form offers it. */
const DONORS = ["UNICEF", "SDC", "UNFPA", "AWO", "Save the Children", "Own funds", "Other", "Not specified"];

/* Cadre of the person delivering — absent from the current form, which is
   why counsellor, psychologist and psychiatrist cannot be counted apart. */
const CADRES = [
  /* The cadre list approved by the Coordinator on 17 Sep 2026 (afternoon):
     EDCD's list of the morning review, plus the cadres Nepal's own system
     names and EDCD's list left out (psychiatric nurse, CPSW, FCHV, the
     mhGAP-trained prescriber). The IASC 4Ws form has no cadre item -- this
     field is our addition -- so each code carries the two frames the world
     counts in: `layer` = the IASC pyramid layer that delivers it
     (specialised / focused / community; the 4Ws activity codes 9 and 10
     draw the same specialist / non-specialist line) and `atlas` = the WHO
     Mental Health Atlas workforce category, so the dashboard can roll up
     either way without touching the codes. Two points are still with EDCD
     and are NOT decided here: whether PSY stays a code of its own, and
     whether VOL splits into PFA volunteers and other trained volunteers. */
  { code: "PSYT", name: "Psychiatrist", np: "मनोचिकित्सक", np_src: "draft", layer: "specialised", iasc_code: "10", atlas: "psychiatrist" },
  { code: "CPSY", name: "Clinical psychologist", np: "क्लिनिकल मनोविद्", np_src: "draft", np_note: "क्लिनिकल साइकोलोजिस्ट is also in use -- one has to be chosen", layer: "specialised", iasc_code: "10", atlas: "psychologist", src: "EDCD review 17 Sep 2026" },
  { code: "PSY",  name: "Psychologist (non-clinical)", np: "मनोविद्", np_src: "draft", np_note: "मनोवैज्ञानिक is also current -- one has to be chosen and used consistently", layer: "specialised", iasc_code: "10", atlas: "psychologist", question: "EDCD 17 Sep: confirm it stays a separate code" },
  { code: "PNUR", name: "Psychiatric / mental health nurse", np: "मानसिक स्वास्थ्य नर्स", np_src: "draft", layer: "specialised", iasc_code: "10", atlas: "mental health nurse", src: "Nepal cadre (district hospital deployments); data workstream ruling R-W1; approved 17 Sep 2026" },
  { code: "MO",   name: "Medical officer / doctor, mhGAP-trained (prescriber)", np: "मेडिकल अफिसर / चिकित्सक (mhGAP तालिमप्राप्त)", np_src: "draft", layer: "focused", iasc_code: "9", atlas: "other medical doctor", src: "Nepal mhGAP prescriber cadre; approved 17 Sep 2026 as an optional split of HW" },
  { code: "HW",   name: "Health worker, non-specialist (nurse, ANM, AHW, HA)", np: "स्वास्थ्यकर्मी, विशेषज्ञ नभएको (नर्स, अनमी, अहेब, हे.अ.)", np_src: "draft", layer: "focused", iasc_code: "9", atlas: "nurse / other health worker" },
  { code: "PSC",  name: "Psychosocial counsellor (NHTC-certified)", np: "मनोसामाजिक परामर्शकर्ता", np_src: "draft", np_note: "cadre title -- check against the NHTC psychosocial counsellor training curriculum", layer: "focused", iasc_code: null, atlas: "other paid mental health worker" },
  { code: "CPSW", name: "Community psychosocial worker", np: "सामुदायिक मनोसामाजिक कार्यकर्ता", np_src: "draft", layer: "focused", iasc_code: null, atlas: "other paid mental health worker", src: "Nepal cadre; data workstream ruling R-W1; approved 17 Sep 2026" },
  { code: "SW",   name: "Social worker", np: "सामाजिक कार्यकर्ता", np_src: "draft", layer: "focused", iasc_code: null, atlas: "social worker" },
  { code: "FCHV", name: "Female community health volunteer", np: "महिला सामुदायिक स्वास्थ्य स्वयंसेविका", np_src: "draft", layer: "community", iasc_code: null, atlas: null, src: "Nepal government cadre; approved 17 Sep 2026" },
  { code: "VOL",  name: "Trained volunteer (including PFA volunteers)", np: "तालिम प्राप्त स्वयंसेवक (PFA स्वयंसेवकसहित)", np_src: "draft", layer: "community", iasc_code: null, atlas: null, question: "EDCD 17 Sep: confirm whether PFA volunteers and other trained volunteers are two codes" },
  { code: "OTH",  name: "Other — specify", np: "अन्य — उल्लेख गर्नुहोस्", np_src: "draft", layer: null, iasc_code: null, atlas: null },
  /* retired 17 Sep 2026 (merged into PSC): kept so records that carry it still resolve; never offered on a form */
  { code: "SPSC", name: "Senior psychosocial counsellor", np: "वरिष्ठ मनोसामाजिक परामर्शकर्ता", np_src: "draft", retired: true, mergeInto: "PSC", layer: "focused", iasc_code: null, atlas: "other paid mental health worker" },
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
  { code: "TG-OTH", name: "Other group — specify", np: "अन्य समूह — उल्लेख गर्नुहोस्", np_src: "draft", src: "EDCD review 17 Sep 2026: Other on every list" },
];

/* Service setting — where the activity took place. The four settings agreed
   with EDCD on 17 Sep 2026, chosen so a field worker can tell them apart
   and so the form outlives the emergency: holding centres are temporary,
   facilities are not. Telephone / helpline stays, because the helpline
   reports on the same form. The earlier codes are retired, not deleted, so
   a record that carries one still reads. */
const MODALITIES = [
  { code: "HC",  name: "In person — holding centre", np: "प्रत्यक्ष — होल्डिङ सेन्टर", np_src: "draft", src: "EDCD review 17 Sep 2026" },
  { code: "COM", name: "In person — outreach in the community", np: "प्रत्यक्ष — समुदायमा पहुँच सेवा", np_src: "draft", src: "EDCD review 17 Sep 2026" },
  { code: "FAC", name: "Facility — health facility, school, hospital, OCMC, other government facility", np: "संस्था — स्वास्थ्य संस्था, विद्यालय, अस्पताल, OCMC, अन्य सरकारी निकाय", np_src: "draft", src: "EDCD review 17 Sep 2026" },
  { code: "TEL", name: "Telephone / helpline", np: "टेलिफोन / हेल्पलाइन", np_src: "draft" },
  { code: "OTH", name: "Other — specify", np: "अन्य — उल्लेख गर्नुहोस्", np_src: "draft" },
  { code: "INP", name: "In person, at a site (code retired 17 Sep 2026)", np: "प्रत्यक्ष, सेवा स्थलमा", np_src: "draft", retired: true },
  { code: "OUT", name: "In person, outreach / mobile (code retired 17 Sep 2026)", np: "प्रत्यक्ष, घुम्ती / पहुँच सेवा", np_src: "draft", retired: true },
];

const STATUS = [
  { code: "ONG", name: "Ongoing", np: "चालु", np_src: "draft" },
  { code: "CMP", name: "Completed", np: "सम्पन्न", np_src: "draft" },
  { code: "PLN", name: "Planned", np: "योजनामा", np_src: "draft" },
];

/* One cadre per person. Some people on the four workforce lists carry
   different labels in different lists, and the lists are undated, so
   "most recent wins" cannot be applied; the workstream's ruling R-W1 is
   that the most specialised label wins, in this order (D-C03).
   OPEN: D-C01 psychiatric nurse and D-C02 community psychosocial worker
   have no code and are entered as OTH until ruled. */
const CADRE_RANK = ["PSYT", "CPSY", "PSY", "PNUR", "MO", "HW", "PSC", "CPSW", "SW", "FCHV", "VOL", "OTH"];

/* Convenience lookups */
const siteByCode = Object.fromEntries(SITES.map((s) => [s.code, s]));
const orgByCode = Object.fromEntries(ORGS.map((o) => [o.code, o]));
const districtByCode = Object.fromEntries(DISTRICTS.map((d) => [d.code, d]));
const activityByCode = Object.fromEntries(ACTIVITIES.map((a) => [a.code, a]));
const palikaByCode = Object.fromEntries(PALIKAS.map((p) => [p.pcode, p]));

/* Roster sites only — the denominator for coverage-gap analysis.
   A site that is merely "reported" cannot be counted as uncovered,
   because nobody ever said it should be covered. Whether the DAO-listed
   centres ("gov-list") join this denominator is open (D-S14); until it is
   ruled they are offered on the forms and kept out of the denominator. */
const ROSTER_SITES = SITES.filter((s) => s.source === "roster");

/* What a form may offer: everything except a retired code. A retired code
   stays in SITES so that an old record still resolves to a name; it is
   never a choice for a new one. */
const FORM_SITES = SITES.filter((s) => s.source !== "retired");

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
  [["SITES", SITES], ["PALIKAS", PALIKAS], ["DISTRICTS", DISTRICTS], ["ACTIVITIES", ACTIVITIES],
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

/* A site's palika as words. `site.palika` is a P-code so that maps and the
   NDRRMA 5W join on it; nobody should have to read one. */
function palikaName(pcode) {
  var p = palikaByCode[pcode];
  return p ? label(p) : "";
}

window.CODES = {
  META, DISTRICTS, PALIKAS, SITES, ACTIVITIES, ORGS, DONORS, CADRES, CADRE_RANK,
  TARGET_GROUPS, MODALITIES, STATUS,
  siteByCode, orgByCode, districtByCode, activityByCode, palikaByCode,
  ROSTER_SITES, FORM_SITES,
  label, labelOf, palikaName, ph, npCoverage
};
