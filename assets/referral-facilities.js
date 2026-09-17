/* =====================================================================
   MHPSS Nepal -- hospitals and helplines for the Referral Directory
   ---------------------------------------------------------------------
   Layer 3. Read by assets/referral-find.js on referral-directory.html.

   This list is the OFFICIAL-SOURCE tier of the directory. It is kept apart
   from the partner tier (public_stats/referral_directory, published by the
   Technical Working Group) and the two are never merged into one count.

   The rules an entry has to meet, checked by tools/map-build.py check:
     - every service, provider type and way of access carries the words the
       facility's own website prints, in "quotes", with the page it is on
       and the date it was read; nothing is listed from memory, from news
       reports or from a directory run by someone else
     - "provider type" for a hospital means a psychiatry department, unit or
       service, or consultant psychiatrists, named on the hospital's own
       pages -- never the name of a person; no person is named anywhere here
     - place: the palika P-code only when the printed address names the
       palika; otherwise the district, and the page says "palika not stated"
     - never a point on the map: a hospital is shown on its palika, or on its
       district, as the partner rows are
     - hospitals whose own pages do not mention psychiatry are not listed,
       and neither are hospitals whose website could not be opened (they are
       recorded in "not_listed" below, so the gap is visible)

   Read on 17 September 2026. A service listed here is not a promise that it
   is open today.
   ===================================================================== */
window.REFERRAL_FACILITIES = {
  "read": "2026-09-17",
  "entries": [
    {
      "id": "trishuli",
      "kind": "hospital",
      "name": { "en": "Trishuli Hospital", "ne": "त्रिशुली अस्पताल" },
      "address": "विदुर-९, कोलोनी, नुवाकोट, बागमती प्रदेश",
      "district": "NP0328",
      "pcode": "NP0328301",
      "phones": [
        { "text": "०१०५६०१८८", "tel": "010560188", "src": 1 },
        { "text": "10560188", "tel": "10560188", "label": "toll", "src": 1 }
      ],
      "quotes": [
        { "text": "General Psychiatric Consultations", "src": 0 },
        { "text": "Medication Management", "src": 0 },
        { "text": "Individual, couples, and family therapy.", "src": 0 },
        { "text": "Counselling Service (Collaboration with Psychiatric nurses and psychosocial counsellor)", "src": 0 },
        { "text": "Short-term admission (2 beds) for acute psychiatric crises", "src": 0 },
        { "text": "मनोचिकित्सा", "src": 2 }
      ],
      "services": { "SPEC": 0, "MEDS": 1, "CNS-I": [2, 3] },
      "cadres": { "PSYT": 0, "PSC": 3 },
      "modes": { "INP": 0 },
      "sources": [
        { "title": "मनोचिकित्सा — Trishuli Hospital", "url": "https://trishulihospital.bagamati.gov.np/pages/psychiatry-15" },
        { "title": "Trishuli Hospital — home page", "url": "https://trishulihospital.bagamati.gov.np/" },
        { "title": "Trishuli Hospital — services", "url": "https://trishulihospital.bagamati.gov.np/services-list/" }
      ]
    },
    {
      "id": "bharatpur",
      "kind": "hospital",
      "name": { "en": "Provincial Hospital Bharatpur", "ne": "भरतपुर अस्पताल" },
      "address": "भरतपुर, चितवन",
      "district": "NP0335",
      "pcode": "NP0335101",
      "phones": [],
      "quotes": [
        { "text": "Psychiatric", "src": 0, "context": "consultants" }
      ],
      "services": { "SPEC": 0 },
      "cadres": { "PSYT": 0 },
      "modes": { "INP": 0 },
      "sources": [
        { "title": "Consultants — Bharatpur Hospital", "url": "https://www.bharatpurhospital.gov.np/Consultant" }
      ]
    },
    {
      "id": "bir",
      "kind": "hospital",
      "name": { "en": "Bir Hospital", "ne": "वीर अस्पताल" },
      "address": "Mahaboudha, Kathmandu, Bagmati, Nepal",
      "district": "NP0327",
      "pcode": null,
      "phones": [
        { "text": "+977-1-5321119", "tel": "+97715321119", "src": 1 }
      ],
      "quotes": [
        { "text": "Psychiatric", "src": 0, "context": "department" },
        { "text": "The department offers mental health care for high school students and older.", "src": 0 }
      ],
      "services": { "SPEC": 1 },
      "cadres": { "PSYT": 0 },
      "modes": { "INP": 1 },
      "sources": [
        { "title": "Psychiatric — Bir Hospital", "url": "https://www.birhospital.gov.np/en/department/21" },
        { "title": "Bir Hospital — home page", "url": "https://www.birhospital.gov.np/en" }
      ]
    },
    {
      "id": "tuth",
      "kind": "hospital",
      "name": { "en": "Tribhuvan University Teaching Hospital", "ne": "त्रिभुवन विश्वविद्यालय शिक्षण अस्पताल" },
      "address": "Maharajgunj, Kathmandu, Bagmati Pradesh, Nepal",
      "district": "NP0327",
      "pcode": null,
      "phones": [
        { "text": "+977-1-4512505", "tel": "+97714512505", "src": 0 }
      ],
      "quotes": [
        { "text": "DEPARTMENT OF PSYCHIATRY& MENTAL HEALTH", "src": 0 },
        { "text": "Child Guidance Clinic", "src": 0 },
        { "text": "De-addiction OPD", "src": 0 },
        { "text": "Clinical Psychology", "src": 0 }
      ],
      "services": { "SPEC": 0 },
      "cadres": { "PSYT": 0, "PSY": 3 },
      "modes": { "INP": 0 },
      "sources": [
        { "title": "Psychiatry & Mental Health — Teaching Hospital", "url": "https://tuth.org.np/psychiatry-mental-health/" }
      ]
    },
    {
      "id": "csh",
      "kind": "hospital",
      "name": { "en": "Civil Service Hospital", "ne": "निजामती कर्मचारी अस्पताल" },
      "address": "Minbhawan, Kathmandu, Nepal",
      "district": "NP0327",
      "pcode": null,
      "phones": [],
      "quotes": [
        { "text": "Psychiatry Unit", "src": 0 },
        { "text": "General OPD Services (2:30 PM ONWARDS)", "src": 0 }
      ],
      "services": { "SPEC": 0 },
      "cadres": { "PSYT": 0 },
      "modes": { "INP": 1 },
      "sources": [
        { "title": "Psychiatry Unit — Civil Service Hospital", "url": "https://csh.gov.np/en/department/psychiatry2985unit-4556" }
      ]
    },
    {
      "id": "mhl",
      "kind": "hospital",
      "name": { "en": "Mental Hospital, Lagankhel", "ne": "मानसिक अस्पताल, लगनखेल" },
      "address": "लगनखेल, ललितपुर",
      "district": "outside",
      "outside": "Lalitpur",
      "pcode": null,
      "phones": [
        { "text": "०१५४२१६१२", "tel": "015421612", "src": 1 }
      ],
      "quotes": [
        { "text": "नेपालमा पहिलो पटक ५० शैयाको मानसिक अस्पताल ललितपुरको लगनखेलमा स्थापना।", "src": 0 }
      ],
      "services": { "SPEC": 0 },
      "cadres": { "PSYT": 0 },
      "modes": { "INP": 0 },
      "sources": [
        { "title": "परिचय — Mental Hospital Lagankhel", "url": "https://mhl.gov.np/pages/introduction-2/" },
        { "title": "Mental Hospital Lagankhel — home page", "url": "https://mhl.gov.np/" }
      ]
    },
    {
      "id": "patan",
      "kind": "hospital",
      "name": { "en": "Patan Hospital" },
      "address": "Lagankhel, Lalitpur",
      "district": "outside",
      "outside": "Lalitpur",
      "pcode": null,
      "phones": [],
      "quotes": [
        { "text": "Department of Psychiatry", "src": 0 },
        { "text": "24-hour emergency and consultation liaison services", "src": 0 },
        { "text": "Psychology services", "src": 0 },
        { "text": "Child and Adolescent Guidance Clinic", "src": 0 },
        { "text": "Tele-consultation services", "src": 0 }
      ],
      "services": { "SPEC": 0 },
      "cadres": { "PSYT": 0, "PSY": 2 },
      "modes": { "INP": 1, "TEL": 4 },
      "sources": [
        { "title": "Department of Psychiatry — Patan Academy of Health Sciences", "url": "https://web.pahs.edu.np/hospital-services/in-patient-department/department-of-psychiatry/" }
      ]
    },
    {
      "id": "hl1166",
      "kind": "helpline",
      "name": { "en": "National Suicide Prevention Helpline", "ne": "राष्ट्रिय आत्महत्या रोकथाम हेल्पलाईन" },
      "address": "मानसिक अस्पताल, लगनखेल",
      "district": null,
      "pcode": null,
      "phones": [
        { "text": "1166", "tel": "1166", "label": "toll", "src": 1 }
      ],
      "quotes": [
        { "text": "राष्ट्रिय आत्महत्या रोकथाम हेल्पलाईन ११६६", "src": 0 }
      ],
      "services": { "HELP": 0 },
      "cadres": {},
      "modes": { "TEL": 0 },
      "sources": [
        { "title": "आत्महत्या रोकथाम हटलाइन — Mental Hospital Lagankhel", "url": "https://mhl.gov.np/pages/hotline-3/" },
        { "title": "Mental Hospital Lagankhel — home page", "url": "https://mhl.gov.np/" }
      ]
    },
    {
      "id": "hltpo",
      "kind": "helpline",
      "name": { "en": "Psychosocial Support Helpline — TPO Nepal" },
      "address": "",
      "district": null,
      "pcode": null,
      "phones": [
        { "text": "1660 010 2005", "tel": "16600102005", "src": 0 }
      ],
      "quotes": [
        { "text": "Psychosocial Support Helpline", "src": 0 },
        { "text": "Every Day From 9 AM to 5 PM", "src": 0 },
        { "text": "You can call this number free of cost from Nepal Telecom network.", "src": 0 }
      ],
      "services": { "HELP": 0 },
      "cadres": {},
      "modes": { "TEL": 0 },
      "sources": [
        { "title": "TPO Nepal — home page", "url": "https://www.tponepal.org/" }
      ]
    }
  ],
  "not_listed": [
    { "name": "Rasuwa Hospital", "why": "no-psychiatry", "url": "https://rasuwahospital.bagamati.gov.np/services-list/" },
    { "name": "Gorkha Hospital", "why": "no-psychiatry", "url": "https://gorkhahospital.gov.np/services-list/" },
    { "name": "Dhading Hospital", "why": "unreachable", "url": "https://dhadinghospital.bagamati.gov.np/" },
    { "name": "Damauli Hospital", "why": "unreachable", "url": "https://damaulihospital.gandaki.gov.np/" },
    { "name": "Madhyabindu Hospital", "why": "unreachable", "url": "https://madhyabinduhospital.gandaki.gov.np/" }
  ]
};
