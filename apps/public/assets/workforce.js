/* MHPSS Nepal -- staff deployed, by district and palika. Built by
   tools/workforce-build.py from the de-identified workforce roster; counts only,
   no person, no place of work, nothing below a palika. A number of one or two
   is "lt3"; a number hidden so that a neighbour cannot be worked out is "ge3".
   Do not edit by hand: rebuild, then run tools/workforce-build.py check. */
window.WORKFORCE = {
 "schema": 1,
 "exported": "2026-09-14",
 "built": "2026-09-17",
 "floor": 3,
 "people": 221,
 "cadre_order": [
  "PSYT",
  "CPSY",
  "PSY",
  "PNUR",
  "PSC",
  "CPSW",
  "VOL",
  "OTH",
  "NS"
 ],
 "cadres": {
  "PSYT": 11,
  "CPSY": 8,
  "PSY": 20,
  "PNUR": "lt3",
  "PSC": 125,
  "CPSW": "lt3",
  "VOL": 41,
  "OTH": 9,
  "NS": 3
 },
 "districts": [
  {
   "d": "NP0328",
   "n": 73,
   "c": {
    "PSYT": 6,
    "CPSY": "ge3",
    "PSY": 8,
    "PNUR": "lt3",
    "PSC": 36,
    "CPSW": 0,
    "VOL": 15,
    "OTH": "lt3",
    "NS": "lt3"
   }
  },
  {
   "d": "NP0329",
   "n": 43,
   "c": {
    "PSYT": 0,
    "CPSY": "lt3",
    "PSY": "ge3",
    "PNUR": 0,
    "PSC": 21,
    "CPSW": 0,
    "VOL": 11,
    "OTH": "lt3",
    "NS": 0
   }
  },
  {
   "d": "NP0330",
   "n": 23,
   "c": {
    "PSYT": 0,
    "CPSY": "lt3",
    "PSY": 0,
    "PNUR": 0,
    "PSC": "ge3",
    "CPSW": 0,
    "VOL": 0,
    "OTH": 0,
    "NS": 0
   }
  },
  {
   "d": "NP0327",
   "n": 40,
   "c": {
    "PSYT": "lt3",
    "CPSY": "lt3",
    "PSY": 3,
    "PNUR": 0,
    "PSC": 24,
    "CPSW": 0,
    "VOL": 6,
    "OTH": "lt3",
    "NS": "lt3"
   }
  },
  {
   "d": "NP0447",
   "n": "lt3"
  },
  {
   "d": "outside",
   "n": "lt3"
  },
  {
   "d": "none",
   "n": 48,
   "c": {
    "PSYT": 3,
    "CPSY": "lt3",
    "PSY": "lt3",
    "PNUR": 0,
    "PSC": 28,
    "CPSW": 0,
    "VOL": 9,
    "OTH": 4,
    "NS": "lt3"
   }
  }
 ],
 "palikas": {
  "NP0328": [
   {
    "p": "NP0328301",
    "n": 30,
    "c": {
     "PSYT": "ge3",
     "CPSY": 4,
     "PSY": 4,
     "PNUR": 0,
     "PSC": 17,
     "CPSW": 0,
     "VOL": 0,
     "OTH": "lt3",
     "NS": 0
    }
   },
   {
    "p": "NP0328302",
    "n": 16,
    "c": {
     "PSYT": "lt3",
     "CPSY": 0,
     "PSY": "lt3",
     "PNUR": "lt3",
     "PSC": 11,
     "CPSW": 0,
     "VOL": 0,
     "OTH": 0,
     "NS": "lt3"
    }
   },
   {
    "p": "NP0328402",
    "n": 3,
    "c": {
     "PSYT": 0,
     "CPSY": 0,
     "PSY": "lt3",
     "PNUR": 0,
     "PSC": "lt3",
     "CPSW": 0,
     "VOL": 0,
     "OTH": 0,
     "NS": 0
    }
   },
   {
    "p": "unnamed",
    "n": 26,
    "c": {
     "PSYT": "lt3",
     "CPSY": "lt3",
     "PSY": "lt3",
     "PNUR": 0,
     "PSC": "ge3",
     "CPSW": 0,
     "VOL": 15,
     "OTH": 0,
     "NS": 0
    }
   }
  ],
  "NP0329": [
   {
    "p": "NP0329402",
    "n": 5,
    "c": {
     "PSYT": "lt3",
     "CPSY": 0,
     "PSY": "lt3",
     "PNUR": "lt3",
     "PSC": "ge3",
     "CPSW": "lt3",
     "VOL": 0,
     "OTH": 0,
     "NS": "lt3"
    }
   },
   {
    "p": "NP0329403",
    "n": 10,
    "c": {
     "PSYT": 0,
     "CPSY": "lt3",
     "PSY": 0,
     "PNUR": 0,
     "PSC": 7,
     "CPSW": 0,
     "VOL": "lt3",
     "OTH": 0,
     "NS": 0
    }
   },
   {
    "p": "NP0329404",
    "n": "lt3"
   },
   {
    "p": "unnamed",
    "n": 28,
    "c": {
     "PSYT": 0,
     "CPSY": "lt3",
     "PSY": 6,
     "PNUR": 0,
     "PSC": 10,
     "CPSW": 0,
     "VOL": 9,
     "OTH": "lt3",
     "NS": 0
    }
   }
  ],
  "NP0330": [
   {
    "p": "NP0330301",
    "n": "lt3"
   },
   {
    "p": "NP0330302",
    "n": "lt3"
   },
   {
    "p": "NP0330408",
    "n": "lt3"
   },
   {
    "p": "NP0330409",
    "n": 3,
    "c": {
     "PSYT": 0,
     "CPSY": 0,
     "PSY": 0,
     "PNUR": 0,
     "PSC": 3,
     "CPSW": 0,
     "VOL": 0,
     "OTH": 0,
     "NS": 0
    }
   },
   {
    "p": "NP0330410",
    "n": 5,
    "c": {
     "PSYT": 0,
     "CPSY": 0,
     "PSY": 0,
     "PNUR": 0,
     "PSC": 5,
     "CPSW": 0,
     "VOL": 0,
     "OTH": 0,
     "NS": 0
    }
   },
   {
    "p": "unnamed",
    "n": 13,
    "c": {
     "PSYT": 0,
     "CPSY": "lt3",
     "PSY": 0,
     "PNUR": 0,
     "PSC": "ge3",
     "CPSW": 0,
     "VOL": 0,
     "OTH": 0,
     "NS": 0
    }
   }
  ],
  "NP0327": [
   {
    "p": "NP0327101",
    "n": "lt3"
   },
   {
    "p": "NP0327305",
    "n": "lt3"
   },
   {
    "p": "unnamed",
    "n": 38,
    "c": {
     "PSYT": "lt3",
     "CPSY": "lt3",
     "PSY": 3,
     "PNUR": 0,
     "PSC": 22,
     "CPSW": 0,
     "VOL": 6,
     "OTH": "lt3",
     "NS": "lt3"
    }
   }
  ]
 },
 "organisations": {
  "NP0328": [
   [
    "TPO Nepal",
    18,
    false
   ],
   [
    "NRCS",
    17,
    false
   ],
   [
    "CWIN Nepal",
    15,
    false
   ],
   [
    "CMC-Nepal",
    9,
    false
   ],
   [
    "KOSHISH",
    3,
    false
   ],
   [
    "Kathmandu Medical College",
    "lt3",
    false
   ],
   [
    "KCH",
    "lt3",
    true
   ],
   [
    "Vidushi Psychological Support Center / Antardhoni Nepal",
    "lt3",
    false
   ],
   [
    "",
    9,
    false
   ]
  ],
  "NP0329": [
   [
    "CMC-Nepal",
    13,
    false
   ],
   [
    "CWIN Nepal",
    9,
    false
   ],
   [
    "NRCS",
    9,
    false
   ],
   [
    "TPO Nepal",
    3,
    false
   ],
   [
    "Happy Club / Manobislesan Kendra",
    "lt3",
    true
   ],
   [
    "SOMHPIN",
    "lt3",
    true
   ],
   [
    "",
    7,
    false
   ]
  ],
  "NP0330": [
   [
    "CWIN Nepal",
    12,
    false
   ],
   [
    "TPO Nepal",
    3,
    false
   ],
   [
    "CMC-Nepal",
    "lt3",
    false
   ],
   [
    "",
    "ge3",
    false
   ]
  ],
  "NP0327": [
   [
    "CWIN Nepal",
    10,
    false
   ],
   [
    "CMC-Nepal",
    7,
    false
   ],
   [
    "Vidushi Psychological Support Center / Antardhoni Nepal",
    7,
    false
   ],
   [
    "KMC",
    6,
    true
   ],
   [
    "NRCS",
    3,
    false
   ],
   [
    "Kathmandu Medical College",
    "lt3",
    false
   ],
   [
    "Kanti",
    "lt3",
    true
   ],
   [
    "Kanti Children's Hospital",
    "lt3",
    false
   ],
   [
    "TPO Nepal",
    "lt3",
    false
   ],
   [
    "",
    7,
    false
   ]
  ]
 },
 "placed": {
  "palika": 73,
  "district_only": 98,
  "none": 48
 }
};
