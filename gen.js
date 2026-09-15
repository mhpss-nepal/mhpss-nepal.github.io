/* Synthetic demonstration dataset for the MHPSS Nepal Hub.
   Deterministic (seeded) so the demo is identical on every machine.
   NO real reported figures. NO personal data. */
const fs = require('fs');
const src = fs.readFileSync('assets/codes.js','utf8');
// eval the vocab file in a sandbox to reuse the exact lists
const sandbox = { window:{} };
new Function('window', src + '\n; window.__x = {SITES,ACTIVITIES,ORGS,CADRES,TARGET_GROUPS,MODALITIES,STATUS,DISTRICTS};')(sandbox.window);
const V = sandbox.window.__x;

let seed = 20830511;
function rnd(){ seed = (seed*1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
const pick = a => a[Math.floor(rnd()*a.length)];
const int  = (lo,hi) => lo + Math.floor(rnd()*(hi-lo+1));

const roster   = V.SITES.filter(s=>s.source==='roster');
const reported = V.SITES.filter(s=>s.source==='reported');

/* Deliberate coverage gaps — the whole point of the hub.
   Six roster sites receive nothing at all. Chosen to be plausible:
   the small, remote and zero-population ones. */
const NEVER_SERVED = new Set(['RAS-01','NUW-03','NUW-08','NUW-14','NUW-16','NUW-19']);
/* Two more served only once, early, then dropped. */
const DROPPED = new Set(['NUW-15','RAS-03']);

const ORGS = V.ORGS.filter(o=>o.code!=='OTHER');
const ACTS = V.ACTIVITIES.filter(a=>!['COORD','TRAIN'].includes(a.code));

/* Which organisations work where — a realistic, fixed assignment. */
const FOOTPRINT = {
  TPO:   ['NUW-01','NUW-04','NUW-05','NUW-11','NUW-R3','NUW-R5','NUW-13','DHA-R1'],
  CMC:   ['RAS-02','RAS-04','RAS-R1','RAS-R2','NUW-01','NUW-02','NUW-07','NUW-10','DHA-R3'],
  CWIN:  ['NUW-07','NUW-09','NUW-10','NUW-17','NUW-18','NUW-R1','RAS-R3'],
  NRCS:  ['NUW-01','NUW-06','NUW-09','NUW-R4','RAS-02'],
  KOS:   ['NUW-10','NUW-07','NUW-12'],
  SAMI:  ['DHA-R1','DHA-R2','DHA-R4','NUW-R5'],
  VID:   ['NUW-R2','KTM-R2'],
  GOVPSC:['RAS-04','RAS-R4','NUW-12','NUW-15','RAS-03'],
};
const CADRE_OF = { TPO:['PSY','PSC','SPSC'], CMC:['PSC','SPSC','PSY'], CWIN:['PSC','SW','VOL'],
  NRCS:['VOL','PSC'], KOS:['PSC','SW'], SAMI:['PSC'], VID:['PSY','PSYT'], GOVPSC:['PSC','HW'] };
const ACT_WEIGHT = { PFA:26, 'CNS-I':14, 'CNS-G':8, PSED:11, RECR:13, CFS:8, SPEC:4, MEDS:3, REF:4, HELP:5, IEC:3, ASMT:6, STAFF:5 };
const weighted = () => {
  const tot = Object.values(ACT_WEIGHT).reduce((a,b)=>a+b,0);
  let r = rnd()*tot;
  for (const [k,v] of Object.entries(ACT_WEIGHT)) { r -= v; if (r<=0) return k; }
  return 'PFA';
};
const TG_FOR = { CFS:['TG-CHI'], RECR:['TG-CHI','TG-DIS'], PFA:['TG-DIS','TG-COM','TG-BER'],
  'CNS-I':['TG-BER','TG-PEX','TG-DIS'], 'CNS-G':['TG-DIS','TG-COM'], PSED:['TG-COM','TG-DIS'],
  SPEC:['TG-PEX'], MEDS:['TG-PEX'], REF:['TG-PEX','TG-PWD'], HELP:['TG-COM'],
  IEC:['TG-COM'], ASMT:['TG-DIS'], STAFF:['TG-RES'] };

/* BS Bhadra 2083 day n -> a stable label. No AD conversion is performed
   anywhere in this project; the AD field here is a synthetic sequence only. */
const DAYS = 30;                       // Bhadra 11 .. Ashwin 10, notionally
const bsLabel = d => d<=32 ? `2083-05-${String(d).padStart(2,'0')}`
                           : `2083-06-${String(d-32).padStart(2,'0')}`;
const adSeq   = d => { const t = new Date(Date.UTC(2026,7,27)); t.setUTCDate(t.getUTCDate()+(d-11)); return t.toISOString().slice(0,10); };

function fnv(str){ let h=0x811c9dc5; for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;} return h.toString(36); }

const records = [];
for (let d = 11; d <= 11+DAYS-1; d++) {
  const ramp = d<14 ? 0.35 : d<18 ? 1.0 : d<26 ? 0.85 : 0.55;   // response ramps up then tapers
  for (const org of ORGS) {
    const sites = FOOTPRINT[org.code];
    const n = Math.max(0, Math.round((sites.length*0.45) * ramp * (0.6+rnd()*0.9)));
    const used = new Set();
    for (let k=0;k<n;k++){
      const site = pick(sites);
      if (used.has(site)) continue; used.add(site);
      if (NEVER_SERVED.has(site)) continue;
      if (DROPPED.has(site) && d>16) continue;
      const act = weighted();
      const modality = act==='HELP' ? 'TEL' : (rnd()<0.17 ? 'OUT' : 'INP');
      const s = V.SITES.find(x=>x.code===site);
      const base = act==='CNS-I' ? int(1,6) : act==='SPEC'||act==='MEDS' ? int(1,9)
                 : act==='HELP' ? int(1,7) : act==='REF' ? int(1,4) : int(6,42);
      const total = Math.max(1, Math.round(base * (0.7+ramp*0.5)));
      let dis = null;
      if (rnd() < 0.72) {                       // 72% carry disaggregation
        let rem = total;
        const fU = Math.round(rem*(0.10+rnd()*0.22)); rem -= fU;
        const mU = Math.round(rem*(0.12+rnd()*0.26)); rem -= mU;
        const f  = Math.round(rem*(0.45+rnd()*0.25)); rem -= f;
        dis = { fU18:fU, mU18:mU, oU18:0, f18:f, m18:Math.max(0,rem), o18:0 };
      }
      const rec = {
        id: fnv([org.code,site,bsLabel(d),act,modality].join('|')),
        org: org.code, donor: (org.donors[0]||'Not specified'),
        district: s.district, site,
        activity: act, modality,
        cadre: pick(CADRE_OF[org.code]),
        dateBS: bsLabel(d), dateAD: adSeq(d),
        reachedTotal: total,
        ...(dis||{}),
        targetGroups: [pick(TG_FOR[act]||['TG-COM'])],
        status: d > 11+DAYS-4 ? 'ONG' : 'CMP',
        pwd: rnd()<0.12 ? int(1,3) : 0,
      };
      records.push(rec);
    }
  }
}

/* Synthetic workforce roster — invented names, no contact details at all. */
const FIRST = ['Anisha','Bibek','Chandra','Deepa','Ehsan','Gita','Hari','Ishwor','Jyoti','Kabita','Laxman','Mina','Nabin','Ojaswi','Prakash','Rita','Sabin','Tara','Umesh','Yamuna','Bimala','Suraj','Nirmala','Kiran','Sabina','Dipesh','Manisha','Rajesh','Sunita','Anil'];
const LAST  = ['Adhikari','Bhandari','Chaudhary','Dhakal','Gurung','Karki','Lama','Magar','Neupane','Oli','Pandey','Rai','Shrestha','Tamang','Thapa','Bista','Sherpa','Poudel'];
const workforce = [];
const seenName = new Set();
for (const org of ORGS) {
  const nStaff = { TPO:34, CMC:41, CWIN:33, NRCS:29, KOS:12, SAMI:18, VID:8, GOVPSC:14 }[org.code];
  for (let i=0;i<nStaff;i++){
    let nm; let guard=0;
    do { nm = `${pick(FIRST)} ${pick(LAST)}`; guard++; } while (seenName.has(nm) && guard<40);
    seenName.add(nm);
    workforce.push({ name:nm, org:org.code, cadre:pick(CADRE_OF[org.code]),
                     district: pick([...new Set(FOOTPRINT[org.code].map(c=>V.SITES.find(s=>s.code===c).district))]) });
  }
}

/* Synthetic helpline volumes — 5 lines, one silent. */
const LINES = [
  {code:'L1115', name:'1115 Hello Health', base:5},
  {code:'LTPO',  name:'TPO Nepal 16600102005', base:4},
  {code:'LCMC',  name:'CMC-Nepal helpline', base:2},
  {code:'L1098', name:'CWIN child helpline 1098', base:3},
  {code:'LSUI',  name:'National suicide-prevention helpline', base:0},
];
const helpline = [];
for (let d=11; d<11+DAYS; d++){
  const row = { dateBS: bsLabel(d) };
  for (const L of LINES) row[L.code] = L.base===0 ? null : Math.max(0, Math.round(L.base*(0.4+rnd()*1.6)));
  helpline.push(row);
}

/* Synthetic roster populations. The real per-site figures are unpublished
   operational data for named locations and are deliberately not in this repo;
   codes.js carries pop:null. These stand in so the coverage view still works. */
const sitePop = {};
roster.forEach(function(s){ sitePop[s.code] = [0,0,8,30,42,50,60,73,75,91,95,115,150,180,200,200,200,200,250,250,300,400,420][Math.floor(rnd()*23)]; });

const out = {
  meta: {
    generated: '2026-09-15',
    synthetic: true,
    notice: 'EVERY FIGURE IN THIS FILE IS SYNTHETIC. Generated deterministically for demonstration only. It is not response data and must never be quoted as such.',
    seed: 20830511,
    windowBS: [bsLabel(11), bsLabel(11+DAYS-1)],
  },
  records, workforce, helpline, sitePop,
  lines: LINES.map(({code,name})=>({code,name})),
};
fs.writeFileSync('data/demo.json', JSON.stringify(out));
const reach = records.reduce((a,r)=>a+r.reachedTotal,0);
const servedRoster = new Set(records.map(r=>r.site).filter(c=>c.length===6 && !c.includes('-R')));
console.log('records', records.length, '| reach', reach, '| workforce', workforce.length,
            '| roster sites served', [...servedRoster].filter(c=>roster.some(s=>s.code===c)).length, 'of', roster.length,
            '| bytes', fs.statSync('data/demo.json').size);
