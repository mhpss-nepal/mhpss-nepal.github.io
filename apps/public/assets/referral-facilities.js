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
     - on the map a hospital is a pin at its own location: an OpenStreetMap
       feature (pin.osm, read on pin.read), checked to lie inside the COD-AB
       palika in pin.pcode, which has to be the palika or district its
       printed address names. A hospital is a public place; the partner rows
       are never a point -- they are counted on a palika
     - hospitals whose own pages do not mention psychiatry are not listed,
       and neither are hospitals whose website could not be opened (they are
       recorded in "not_listed" below, so the gap is visible)

   Read on 17 September 2026. A service listed here is not a promise that it
   is open today.

   Codes follow assets/codes.js 0.3.0 (the lists agreed with EDCD on 17 Sep
   2026): a service at the hospital is FAC, the facility setting, where it was
   INP; Tribhuvan University Teaching Hospital's "Clinical Psychology" is
   CPSY, the clinical psychologist the new list adds. The quotations are the
   same; only the codes they are filed under changed.
   ===================================================================== */
window.REFERRAL_FACILITIES = {
 "read": "2026-09-17",
 "entries": [
  {
   "id": "trishuli",
   "kind": "hospital",
   "name": {
    "en": "Trishuli Hospital",
    "ne": "त्रिशुली अस्पताल"
   },
   "address": "विदुर-९, कोलोनी, नुवाकोट, बागमती प्रदेश",
   "district": "NP0328",
   "pcode": "NP0328301",
   "phones": [
    {
     "text": "०१०५६०१८८",
     "tel": "010560188",
     "src": 1
    },
    {
     "text": "10560188",
     "tel": "10560188",
     "label": "toll",
     "src": 1
    }
   ],
   "quotes": [
    {
     "text": "General Psychiatric Consultations",
     "src": 0
    },
    {
     "text": "Medication Management",
     "src": 0
    },
    {
     "text": "Individual, couples, and family therapy.",
     "src": 0
    },
    {
     "text": "Counselling Service (Collaboration with Psychiatric nurses and psychosocial counsellor)",
     "src": 0
    },
    {
     "text": "Short-term admission (2 beds) for acute psychiatric crises",
     "src": 0
    },
    {
     "text": "मनोचिकित्सा",
     "src": 2
    }
   ],
   "services": {
    "SPEC": 0,
    "MEDS": 1,
    "CNS-I": [
     2,
     3
    ]
   },
   "cadres": {
    "PSYT": 0,
    "PSC": 3
   },
   "modes": {
    "FAC": 0
   },
   "sources": [
    {
     "title": "मनोचिकित्सा — Trishuli Hospital",
     "url": "https://trishulihospital.bagamati.gov.np/pages/psychiatry-15"
    },
    {
     "title": "Trishuli Hospital — home page",
     "url": "https://trishulihospital.bagamati.gov.np/"
    },
    {
     "title": "Trishuli Hospital — services",
     "url": "https://trishulihospital.bagamati.gov.np/services-list/"
    }
   ],
   "pin": {
    "lat": 27.924727,
    "lon": 85.140964,
    "pcode": "NP0328301",
    "osm": "relation/10953586",
    "osm_name": "Trishuli Hospital",
    "site_map": {
     "lat": 27.924663,
     "lon": 85.140763,
     "url": "https://trishulihospital.bagamati.gov.np/"
    },
    "read": "2026-09-17"
   }
  },
  {
   "id": "bharatpur",
   "kind": "hospital",
   "name": {
    "en": "Provincial Hospital Bharatpur",
    "ne": "भरतपुर अस्पताल"
   },
   "address": "भरतपुर, चितवन",
   "district": "NP0335",
   "pcode": "NP0335101",
   "phones": [],
   "quotes": [
    {
     "text": "Psychiatric",
     "src": 0,
     "context": "consultants"
    }
   ],
   "services": {
    "SPEC": 0
   },
   "cadres": {
    "PSYT": 0
   },
   "modes": {
    "FAC": 0
   },
   "sources": [
    {
     "title": "Consultants — Bharatpur Hospital",
     "url": "https://www.bharatpurhospital.gov.np/Consultant"
    }
   ],
   "pin": {
    "lat": 27.682068,
    "lon": 84.435801,
    "pcode": "NP0335101",
    "osm": "way/930045826",
    "osm_name": "BHARATPUR HOSPITAL",
    "read": "2026-09-17"
   }
  },
  {
   "id": "bir",
   "kind": "hospital",
   "name": {
    "en": "Bir Hospital",
    "ne": "वीर अस्पताल"
   },
   "address": "Mahaboudha, Kathmandu, Bagmati, Nepal",
   "district": "NP0327",
   "pcode": null,
   "phones": [
    {
     "text": "+977-1-5321119",
     "tel": "+97715321119",
     "src": 1
    }
   ],
   "quotes": [
    {
     "text": "Psychiatric",
     "src": 0,
     "context": "department"
    },
    {
     "text": "The department offers mental health care for high school students and older.",
     "src": 0
    }
   ],
   "services": {
    "SPEC": 1
   },
   "cadres": {
    "PSYT": 0
   },
   "modes": {
    "FAC": 1
   },
   "sources": [
    {
     "title": "Psychiatric — Bir Hospital",
     "url": "https://www.birhospital.gov.np/en/department/21"
    },
    {
     "title": "Bir Hospital — home page",
     "url": "https://www.birhospital.gov.np/en"
    }
   ],
   "pin": {
    "lat": 27.70524,
    "lon": 85.313278,
    "pcode": "NP0327101",
    "osm": "relation/10953874",
    "osm_name": "Bir Hospital",
    "read": "2026-09-17"
   }
  },
  {
   "id": "tuth",
   "kind": "hospital",
   "name": {
    "en": "Tribhuvan University Teaching Hospital",
    "ne": "त्रिभुवन विश्वविद्यालय शिक्षण अस्पताल"
   },
   "address": "Maharajgunj, Kathmandu, Bagmati Pradesh, Nepal",
   "district": "NP0327",
   "pcode": null,
   "phones": [
    {
     "text": "+977-1-4512505",
     "tel": "+97714512505",
     "src": 0
    }
   ],
   "quotes": [
    {
     "text": "DEPARTMENT OF PSYCHIATRY& MENTAL HEALTH",
     "src": 0
    },
    {
     "text": "Child Guidance Clinic",
     "src": 0
    },
    {
     "text": "De-addiction OPD",
     "src": 0
    },
    {
     "text": "Clinical Psychology",
     "src": 0
    }
   ],
   "services": {
    "SPEC": 0
   },
   "cadres": {
    "PSYT": 0,
    "CPSY": 3
   },
   "modes": {
    "FAC": 0
   },
   "sources": [
    {
     "title": "Psychiatry & Mental Health — Teaching Hospital",
     "url": "https://tuth.org.np/psychiatry-mental-health/"
    }
   ],
   "pin": {
    "lat": 27.736108,
    "lon": 85.33008,
    "pcode": "NP0327101",
    "osm": "relation/2421673",
    "osm_name": "TU Teaching Hospital",
    "site_map": {
     "lat": 27.735992,
     "lon": 85.33026,
     "url": "https://tuth.org.np/"
    },
    "read": "2026-09-17"
   }
  },
  {
   "id": "csh",
   "kind": "hospital",
   "name": {
    "en": "Civil Service Hospital",
    "ne": "निजामती कर्मचारी अस्पताल"
   },
   "address": "Minbhawan, Kathmandu, Nepal",
   "district": "NP0327",
   "pcode": null,
   "phones": [],
   "quotes": [
    {
     "text": "Psychiatry Unit",
     "src": 0
    },
    {
     "text": "General OPD Services (2:30 PM ONWARDS)",
     "src": 0
    }
   ],
   "services": {
    "SPEC": 0
   },
   "cadres": {
    "PSYT": 0
   },
   "modes": {
    "FAC": 1
   },
   "sources": [
    {
     "title": "Psychiatry Unit — Civil Service Hospital",
     "url": "https://csh.gov.np/en/department/psychiatry2985unit-4556"
    }
   ],
   "pin": {
    "lat": 27.686906,
    "lon": 85.338742,
    "pcode": "NP0327101",
    "osm": "relation/10953876",
    "osm_name": "Civil Service Hospital",
    "read": "2026-09-17"
   }
  },
  {
   "id": "mhl",
   "kind": "hospital",
   "name": {
    "en": "Mental Hospital, Lagankhel",
    "ne": "मानसिक अस्पताल, लगनखेल"
   },
   "address": "लगनखेल, ललितपुर",
   "district": "outside",
   "outside": "Lalitpur",
   "pcode": null,
   "phones": [
    {
     "text": "०१५४२१६१२",
     "tel": "015421612",
     "src": 1
    }
   ],
   "quotes": [
    {
     "text": "नेपालमा पहिलो पटक ५० शैयाको मानसिक अस्पताल ललितपुरको लगनखेलमा स्थापना।",
     "src": 0
    }
   ],
   "services": {
    "SPEC": 0
   },
   "cadres": {
    "PSYT": 0
   },
   "modes": {
    "FAC": 0
   },
   "sources": [
    {
     "title": "परिचय — Mental Hospital Lagankhel",
     "url": "https://mhl.gov.np/pages/introduction-2/"
    },
    {
     "title": "Mental Hospital Lagankhel — home page",
     "url": "https://mhl.gov.np/"
    }
   ],
   "pin": {
    "lat": 27.66794,
    "lon": 85.322447,
    "pcode": "NP0325101",
    "osm": "way/181575432",
    "osm_name": "Mental Hospital",
    "read": "2026-09-17"
   }
  },
  {
   "id": "patan",
   "kind": "hospital",
   "name": {
    "en": "Patan Hospital"
   },
   "address": "Lagankhel, Lalitpur",
   "district": "outside",
   "outside": "Lalitpur",
   "pcode": null,
   "phones": [],
   "quotes": [
    {
     "text": "Department of Psychiatry",
     "src": 0
    },
    {
     "text": "24-hour emergency and consultation liaison services",
     "src": 0
    },
    {
     "text": "Psychology services",
     "src": 0
    },
    {
     "text": "Child and Adolescent Guidance Clinic",
     "src": 0
    },
    {
     "text": "Tele-consultation services",
     "src": 0
    }
   ],
   "services": {
    "SPEC": 0
   },
   "cadres": {
    "PSYT": 0,
    "PSY": 2
   },
   "modes": {
    "FAC": 1,
    "TEL": 4
   },
   "sources": [
    {
     "title": "Department of Psychiatry — Patan Academy of Health Sciences",
     "url": "https://web.pahs.edu.np/hospital-services/in-patient-department/department-of-psychiatry/"
    }
   ],
   "pin": {
    "lat": 27.668353,
    "lon": 85.320522,
    "pcode": "NP0325101",
    "osm": "way/695917198",
    "osm_name": "Patan Hospital",
    "read": "2026-09-17"
   }
  },
  {
   "id": "hl1166",
   "kind": "helpline",
   "name": {
    "en": "National Suicide Prevention Helpline",
    "ne": "राष्ट्रिय आत्महत्या रोकथाम हेल्पलाईन"
   },
   "address": "मानसिक अस्पताल, लगनखेल",
   "district": null,
   "pcode": null,
   "phones": [
    {
     "text": "1166",
     "tel": "1166",
     "label": "toll",
     "src": 1
    }
   ],
   "quotes": [
    {
     "text": "राष्ट्रिय आत्महत्या रोकथाम हेल्पलाईन ११६६",
     "src": 0
    }
   ],
   "services": {
    "HELP": 0
   },
   "cadres": {},
   "modes": {
    "TEL": 0
   },
   "sources": [
    {
     "title": "आत्महत्या रोकथाम हटलाइन — Mental Hospital Lagankhel",
     "url": "https://mhl.gov.np/pages/hotline-3/"
    },
    {
     "title": "Mental Hospital Lagankhel — home page",
     "url": "https://mhl.gov.np/"
    }
   ]
  },
  {
   "id": "hltpo",
   "kind": "helpline",
   "name": {
    "en": "Psychosocial Support Helpline — TPO Nepal"
   },
   "address": "",
   "district": null,
   "pcode": null,
   "phones": [
    {
     "text": "1660 010 2005",
     "tel": "16600102005",
     "src": 0
    }
   ],
   "quotes": [
    {
     "text": "Psychosocial Support Helpline",
     "src": 0
    },
    {
     "text": "Every Day From 9 AM to 5 PM",
     "src": 0
    },
    {
     "text": "You can call this number free of cost from Nepal Telecom network.",
     "src": 0
    }
   ],
   "services": {
    "HELP": 0
   },
   "cadres": {},
   "modes": {
    "TEL": 0
   },
   "sources": [
    {
     "title": "TPO Nepal — home page",
     "url": "https://www.tponepal.org/"
    }
   ]
  }
 ],
 "not_listed": [
  {
   "name": "Rasuwa Hospital",
   "why": "no-psychiatry",
   "url": "https://rasuwahospital.bagamati.gov.np/services-list/"
  },
  {
   "name": "Gorkha Hospital",
   "why": "no-psychiatry",
   "url": "https://gorkhahospital.gov.np/services-list/"
  },
  {
   "name": "Dhading Hospital",
   "why": "unreachable",
   "url": "https://dhadinghospital.bagamati.gov.np/"
  },
  {
   "name": "Damauli Hospital",
   "why": "unreachable",
   "url": "https://damaulihospital.gandaki.gov.np/"
  },
  {
   "name": "Madhyabindu Hospital",
   "why": "unreachable",
   "url": "https://madhyabinduhospital.gandaki.gov.np/"
  }
 ],
 "pins_note": "Each hospital's location is an OpenStreetMap feature (© OpenStreetMap contributors, ODbL), read on the date given, and checked to lie inside the COD-AB palika in pin.pcode (tools/map-build.py check). Where the hospital's own website embeds a map centred on the hospital, its centre is kept in pin.site_map; the two agree within 30 m."
};
