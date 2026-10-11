"""Additive strict schema v2. Structure is never clinical/release authority."""
import copy, re, math, hashlib
from pathlib import Path
RESERVED={'__proto__','prototype','constructor','toString','valueOf','hasOwnProperty','__defineGetter__','__defineSetter__'}
NEW={'contrast_pair','scene_tap','buddy_practice'}
ID=re.compile(r'^[a-z][a-z0-9-]{0,95}$')
SCENE_ID=re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,95}$')
ASSET_VERSION=re.compile(r'^[a-z][a-z0-9.-]{0,95}$')
FILE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\.(?:webp|png|jpg)$')
BAD=re.compile(r'<[^>]*>|(?:javascript|data|vbscript)\s*:',re.I)

def json_safety(data):
    errors=[]
    def walk(x,p='$',depth=0):
        if depth>80: errors.append(p+': nesting too deep'); return
        if type(x) is dict:
            for k,v in x.items():
                if type(k) is not str or k in RESERVED: errors.append(p+': reserved/nonstring key')
                walk(v,p+'.'+str(k),depth+1)
        elif type(x) is list:
            for i,v in enumerate(x): walk(v,p+f'[{i}]',depth+1)
        elif type(x) is float and not math.isfinite(x): errors.append(p+': finite numbers required')
        elif type(x) not in (str,int,float,bool,type(None)): errors.append(p+': JSON value required')
    try: walk(data)
    except (RecursionError,RuntimeError): errors.append('$: invalid recursive data')
    return errors

def padded_areas(areas,width,height,size):
    """Centred full-size padded boxes, shifted inside the uncropped image."""
    if width<size or height<size: raise ValueError('target cannot fit')
    result=[]
    for l,t,r,b in areas:
        w=max((r-l)*width,size); h=max((b-t)*height,size)
        x=min(max((l+r)*width/2-w/2,0),width-w)
        y=min(max((t+b)*height/2-h/2,0),height-h)
        result.append((x,y,x+w,y+h))
    return result

def validate_v2(d,legacy,*,mode='draft',asset_root=None,check_assets=False):
    e=[]
    def reserved_ids(x):
        if type(x) is dict:
            for k,v in x.items():
                if k.endswith('_id') and type(v) is str and v in RESERVED:
                    e.append(k+': reserved object ID')
                reserved_ids(v)
        elif type(x) is list:
            for v in x:reserved_ids(v)
    reserved_ids(d)
    def ck(ok,p,m):
        if not ok:e.append(p+': '+m)
        return ok
    def shape(x,required,optional,p):
        return ck(type(x) is dict and set(required)<=set(x) and set(x)<=set(required)|set(optional),p,'invalid required/unknown fields')
    def txt(x,p):return ck(type(x) is str and 0<len(x.strip())<=20000 and not BAD.search(x),p,'bounded nonempty plain text required')
    def ident(x,p,rx=ID):return ck(type(x) is str and x not in RESERVED and bool(rx.fullmatch(x)),p,'invalid/reserved ID')
    def arr(x,p):return ck(type(x) is list and len(x)>0,p,'nonempty list required')
    def pos(x,p):return ck(type(x) is int and x>0,p,'positive integer required, not bool')
    top='schema_version module_id content_version language translation_source_version title audience objectives scope_limits prerequisites estimated_minutes approval sources lessons questions completion_policy job_aids open_questions'.split()
    if not shape(d,top,['scenes'],'$'):return e
    scenes={}; blocks={}; questions={}
    sources={s['source_id'] for s in d['sources'] if type(s) is dict and type(s.get('source_id')) is str} if type(d['sources']) is list else set()
    def refs(x,p):
        if arr(x,p):
            ck(all(type(s) is str and s in sources for s in x),p,'unknown source ref')
            if all(type(s) is str for s in x):ck(len(x)==len(set(x)),p,'duplicate source ref')
    def scene_ref(x,p):ck(type(x) is str and x in scenes,p,'unknown scene ID')
    registry=d.get('scenes',[])
    if ck(type(registry) is list,'scenes','list required'):
        for i,s in enumerate(registry):
            p=f'scenes[{i}]'
            if not shape(s,'scene_id file asset_version width height alt status sha256'.split(),[],p):continue
            valid_id=ident(s['scene_id'],p+'.scene_id',SCENE_ID)
            if valid_id:
                ck(s['scene_id'] not in scenes,p,'duplicate scene'); scenes[s['scene_id']]=s
            valid_file=ck(type(s['file']) is str and bool(FILE.fullmatch(s['file'])) and '..' not in s['file'],p+'.file','local derivative basename only')
            valid_version=ck(type(s['asset_version']) is str and bool(ASSET_VERSION.fullmatch(s['asset_version'])) and '..' not in s['asset_version'],p+'.asset_version','safe version slug required')
            pos(s['width'],p+'.width');pos(s['height'],p+'.height');txt(s['alt'],p+'.alt')
            ck(s['status'] in ('candidate','approved'),p+'.status','candidate/approved only')
            if mode=='release':ck(s['status']!='candidate',p,'candidate ineligible for structural release, including unused scenes')
            valid_hash=ck(type(s['sha256']) is str and bool(re.fullmatch('[0-9a-f]{64}',s['sha256'])),p+'.sha256','lowercase sha256 required')
            if check_assets and valid_file and valid_version and valid_hash:
                try:
                    from PIL import Image
                    root=Path(asset_root).absolute(); path=root/s['asset_version']/'web'/s['file']
                    current=root
                    if root.is_symlink():raise ValueError('symlink asset root')
                    for part in path.relative_to(root).parts:
                        current=current/part
                        if current.is_symlink():raise ValueError('symlink media path')
                    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('media escaped root')
                    blob=path.read_bytes()
                    if hashlib.sha256(blob).hexdigest()!=s['sha256']:raise ValueError('asset hash mismatch')
                    with Image.open(path) as im:
                        im.load()
                        if im.size!=(s['width'],s['height']):raise ValueError('asset dimensions mismatch')
                        if im.format not in {'WEBP','PNG','JPEG'}:raise ValueError('unsupported image encoding')
                except (OSError,ValueError,TypeError,ImportError) as exc:e.append(p+': media verification failed: '+str(exc))
    projected=copy.deepcopy(d); projected['schema_version']=1;projected.pop('scenes',None)
    if not ck(type(d['lessons']) is list,'lessons','list required'):return e
    for i,l in enumerate(d['lessons']):
        p=f'lessons[{i}]'
        if not shape(l,'lesson_id title objective estimated_minutes blocks'.split(),['transfer_goals','refresher'],p):continue
        pl=projected['lessons'][i];pl.pop('transfer_goals',None);pl.pop('refresher',None)
        if not ck(type(l['blocks']) is list,p+'.blocks','list required'):continue
        for j,b in enumerate(l['blocks']):
            q=p+f'.blocks[{j}]'
            if not ck(type(b) is dict,q,'object required'):continue
            typ=b.get('type');bid=b.get('block_id')
            if 'block_id' in b or typ in NEW:
                if ident(bid,q+'.block_id'):
                    ck(bid not in blocks,q,'duplicate module block ID');blocks[bid]=(l,b)
            if 'scene_id' in b:scene_ref(b['scene_id'],q+'.scene_id')
            pb=pl['blocks'][j]
            if type(typ) is not str:ck(False,q,'string block type required');continue
            if typ not in NEW:
                shape(b,'type body source_ids'.split(),['block_id','scene_id'],q)
                pb.pop('block_id',None);pb.pop('scene_id',None)
                continue
            pl['blocks'][j]={'type':'text','body':'V2 structural projection only','source_ids':b.get('source_ids')}
            refs(b.get('source_ids'),q+'.source_ids')
            if typ=='contrast_pair':
                if not shape(b,'type block_id prompt unhelpful helpful source_ids'.split(),['scene_id'],q):continue
                txt(b['prompt'],q+'.prompt')
                if shape(b['unhelpful'],'body source_ids'.split(),['scene_id'],q+'.unhelpful'):
                    txt(b['unhelpful']['body'],q+'.unhelpful.body');refs(b['unhelpful']['source_ids'],q+'.unhelpful.source_ids')
                    if 'scene_id' in b['unhelpful']:scene_ref(b['unhelpful']['scene_id'],q+'.unhelpful.scene_id')
                if shape(b['helpful'],['ref_block_id'],['scene_id'],q+'.helpful'):
                    ident(b['helpful']['ref_block_id'],q+'.helpful.ref_block_id')
                    if 'scene_id' in b['helpful']:scene_ref(b['helpful']['scene_id'],q+'.helpful.scene_id')
            elif typ=='buddy_practice':
                if not shape(b,'type block_id minutes roles source_ids'.split(),['scene_id'],q):continue
                pos(b['minutes'],q+'.minutes'); role_ids=[];flags=[]
                if arr(b['roles'],q+'.roles'):
                    for r in b['roles']:
                        if not shape(r,'role_id role instruction'.split(),['fictional_only'],q+'.roles'):continue
                        ck(r['role_id'] in ('helper','person','observer'),q,'invalid role_id');role_ids.append(r['role_id'])
                        txt(r['role'],q+'.role');txt(r['instruction'],q+'.instruction')
                        if 'fictional_only' in r:ck(type(r['fictional_only']) is bool,q,'fictional_only boolean required')
                        flags.append(r.get('fictional_only') is True)
                        ck((r['role_id']=='person' and r.get('fictional_only') is True) or (r['role_id']!='person' and r.get('fictional_only',False) is False),q,'only person requires fictional_only:true')
                ck(sorted(str(x) for x in role_ids)==['helper','observer','person'] and sum(flags)==1,q,'exactly three stable roles and one safeguard required')
            else:
                if not shape(b,'type block_id scene_id instruction layout targets list_alternative source_ids'.split(),[],q):continue
                txt(b['instruction'],q+'.instruction')
                good_layout=shape(b['layout'],'min_image_width_px target_size_px'.split(),[],q+'.layout')
                if good_layout:
                    good_layout=ck(type(b['layout']['min_image_width_px']) is int and b['layout']['min_image_width_px']>=280,q,'min_image_width_px >=280 required') and ck(type(b['layout']['target_size_px']) is int and b['layout']['target_size_px']>=24,q,'target_size_px >=24 required')
                tids=[];boxes=[]
                if arr(b['targets'],q+'.targets'):
                    for t in b['targets']:
                        if not shape(t,'target_id label areas explanation source_ids'.split(),[],q+'.target'):continue
                        if ident(t['target_id'],q+'.target_id'):tids.append(t['target_id'])
                        txt(t['label'],q+'.label');txt(t['explanation'],q+'.explanation');refs(t['source_ids'],q+'.source_ids')
                        if arr(t['areas'],q+'.areas'):
                            valid=[]
                            for a in t['areas']:
                                ok=type(a) is list and len(a)==4 and all(type(n) in (int,float) and math.isfinite(n) for n in a)
                                ok=ok and 0<=a[0]<a[2]<=1 and 0<=a[1]<a[3]<=1
                                if ck(ok,q+'.areas','finite ordered normalized rectangle required'):valid.append(a)
                            s=scenes.get(b['scene_id']) if type(b['scene_id']) is str else None
                            if good_layout and s and type(s['width']) is int and type(s['height']) is int and s['width']>0 and s['height']>0:
                                w=b['layout']['min_image_width_px']; h=w*s['height']/s['width']
                                try:boxes.extend((t['target_id'],a) for a in padded_areas(valid,w,h,b['layout']['target_size_px']))
                                except ValueError as exc:ck(False,q,str(exc))
                ck(len(tids)==len(set(tids)),q,'duplicate target IDs')
                for n,(ta,a) in enumerate(boxes):
                    for tb,z in boxes[n+1:]:
                        if ta!=tb:ck(not(a[0]<z[2] and z[0]<a[2] and a[1]<z[3] and z[1]<a[3]),q,'padded different-target overlap')
                true_ids=[];false=0
                if arr(b['list_alternative'],q+'.list_alternative'):
                    for item in b['list_alternative']:
                        if not shape(item,'text did why source_ids'.split(),['target_id'],q+'.list'):continue
                        txt(item['text'],q+'.text');txt(item['why'],q+'.why');refs(item['source_ids'],q+'.source_ids')
                        ck(type(item['did']) is bool,q,'did boolean required')
                        if item['did'] is True:
                            if ident(item.get('target_id'),q+'.target_id'):true_ids.append(item['target_id'])
                            target=next((t for t in b['targets'] if type(t) is dict and t.get('target_id')==item.get('target_id')),None) if type(b['targets']) is list else None
                            ck(target is not None and item['text']==target.get('label') and item['why']==target.get('explanation') and item['source_ids']==target.get('source_ids'),q,'image/list labels explanations and sources must match')
                        elif item['did'] is False:false+=1;ck('target_id' not in item,q,'false list item cannot carry target_id')
                ck(sorted(true_ids)==sorted(tids) and false>=1,q,'exactly one true item per target and >=1 false required')
    if type(d['questions']) is list:
        for i,q in enumerate(d['questions']):
            p=f'questions[{i}]'
            if not shape(q,'question_id objective prompt options correct_option_id source_ids'.split(),['scene_id'],p):continue
            if ident(q['question_id'],p+'.question_id'):questions[q['question_id']]=q
            pq=projected['questions'][i];pq.pop('scene_id',None)
            if 'scene_id' in q:scene_ref(q['scene_id'],p+'.scene_id')
            flags=[]
            if type(q['options']) is list:
                for j,o in enumerate(q['options']):
                    if not shape(o,'option_id text rationale'.split(),['band'],p+'.options'):continue
                    ident(o['option_id'],p+'.option_id');flags.append('band' in o)
                    if 'band' in o:ck(o['band'] in ('could_harm','basic','further'),p,'invalid band')
                    pq['options'][j].pop('band',None)
                ck(not any(flags) or all(flags),p,'band must be all-or-none')
    for l in d['lessons']:
        if type(l) is not dict:continue
        for b in l.get('blocks',[]) if type(l.get('blocks')) is list else []:
            if type(b) is dict and b.get('type')=='contrast_pair' and type(b.get('helpful')) is dict:
                ref=b['helpful'].get('ref_block_id');match=blocks.get(ref) if type(ref) is str else None
                ck(match is not None and match[0] is l and match[1]['type']=='example','contrast_pair','helpful ref must resolve to same-lesson explicit example')
        if 'transfer_goals' in l and shape(l['transfer_goals'],'prompt options_from_block_id'.split(),[],'transfer_goals'):
            g=l['transfer_goals'];txt(g['prompt'],'transfer_goals.prompt');ref=g['options_from_block_id'];match=blocks.get(ref) if type(ref) is str else None
            ck(match is not None and match[0] is l and match[1]['type'] in ('text','steps','job_aid'),'transfer_goals','same-lesson legacy text/steps/job_aid ref required')
        if 'refresher' in l and shape(l['refresher'],'question_ids offsets_days'.split(),[],'refresher'):
            r=l['refresher'];qs=r['question_ids'];ds=r['offsets_days']
            if arr(qs,'refresher.question_ids'):
                ck(all(type(q) is str and q in questions and questions[q]['objective']==l.get('objective') for q in qs),'refresher','question ref must match lesson objective')
                if all(type(q) is str for q in qs):ck(len(qs)==len(set(qs)),'refresher','duplicate question ref')
            if arr(ds,'refresher.offsets_days'):
                good=all(type(n) is int and 0<n<=365 for n in ds)
                ck(good and all(a<b for a,b in zip(ds,ds[1:])),'refresher','strict increasing unique positive integer offsets <=365 required')
    e.extend(legacy(projected))
    return e
