#!/usr/bin/env python3
"""
MHPSS Nepal -- the live contrast sweep (needs Playwright, so it is run before a
deploy rather than inside the guard)
---------------------------------------------------------------------
Walks every text-bearing element on every page, in light and in dark, resolves
the background it actually sits on through its ancestors, and reports anything
below its WCAG AA threshold for its own size and weight. The token gate beside
this file catches a bad token; only this catches a cascade landing a passing
colour on an unexpected background.

  python3 tools/contrast-sweep.py http://127.0.0.1:8000

On 16 September 2026 it found 109 failing elements and was run down to 0.
"""
from playwright.sync_api import sync_playwright
import json, sys
B = sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:9063"
PAGES=["/","/flood-response.html","/bps.html","/iec.html","/referral-directory.html",
       "/resources.html","/videos.html","/contact-us.html","/method.html","/architecture.html","/access-explained.html","/layer3.html"]
# the hub and the forms: swept in their own repositories since 17 Sep 2026
JS = """() => {
  const lum = c => { const m=c.match(/[\\d.]+/g); if(!m) return null;
    if (m.length>3 && +m[3]===0) return null;
    const f=x=>{x/=255; return x<=0.03928?x/12.92:Math.pow((x+0.055)/1.055,2.4)};
    return 0.2126*f(+m[0])+0.7152*f(+m[1])+0.0722*f(+m[2]); };
  const bgOf = el => { let n=el;
    while(n && n!==document.documentElement){ const c=getComputedStyle(n).backgroundColor;
      const l=lum(c); if(l!==null) return l; n=n.parentElement; }
    return lum(getComputedStyle(document.body).backgroundColor) ?? 1; };
  const out=[];
  for (const el of document.querySelectorAll('body *')) {
    if (el.children.length && [...el.childNodes].every(n=>n.nodeType!==3||!n.textContent.trim())) continue;
    const t=(el.textContent||'').trim(); if(!t) continue;
    const cs=getComputedStyle(el);
    if (cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0) continue;
    const r=el.getBoundingClientRect(); if(r.width<2||r.height<2) continue;
    const fg=lum(cs.color); if(fg===null) continue;
    const bg=bgOf(el);
    const ratio=(Math.max(fg,bg)+0.05)/(Math.min(fg,bg)+0.05);
    const px=parseFloat(cs.fontSize), bold=+cs.fontWeight>=700;
    const need=(px>=24||(px>=18.66&&bold))?3:4.5;
    if (ratio<need) out.push({tag:el.tagName, cls:String(el.className).slice(0,28),
      txt:t.slice(0,26), px:+px.toFixed(1), ratio:+ratio.toFixed(2), need,
      fg:cs.color, bg:(()=>{let n=el; while(n&&n!==document.documentElement){
        const c=getComputedStyle(n).backgroundColor; if(lum(c)!==null) return c; n=n.parentElement;}
        return getComputedStyle(document.body).backgroundColor;})()});
  }
  const seen=new Set(), u=[];
  for(const o of out){const k=o.tag+o.cls+o.px+o.fg; if(!seen.has(k)){seen.add(k);u.push(o);}}
  return u.slice(0,12);
}"""
bad={}
with sync_playwright() as p:
    br=p.chromium.launch()
    for scheme in ("light","dark"):
        for path in PAGES:
            ctx=br.new_context(viewport={"width":1280,"height":900}, color_scheme=scheme)
            pg=ctx.new_page(); pg.goto(B+path, wait_until="load", timeout=25000); pg.wait_for_timeout(1700)
            r=pg.evaluate(JS)
            if r: bad["%s %s"%(scheme,path)]=r
            ctx.close()
    br.close()
n=sum(len(v) for v in bad.values())
print("pages checked: %d   failing elements: %d"%(len(PAGES)*2, n))
print(json.dumps(bad, indent=1) if bad else "every text element clears its WCAG threshold, light and dark")
