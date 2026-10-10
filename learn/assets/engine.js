(()=>{'use strict';
const $=id=>document.getElementById(id), SLUG=/^[a-z][a-z0-9-]*$/, VERSION=/^\d+\.\d+\.\d+$/, TYPES=['text','steps','example','safety','reflection','job_aid','external_resource'];
let D,locale='en',courses=[],C=null,contentHash='',state=null,openGeneration=0,loadGeneration=0,requestedModule=null,pendingIdentity=null;
const tr=(key,args={})=>String(D?.[locale]?.[key]??D?.en?.[key]??key).replace(/\{(\w+)\}/g,(_,k)=>args[k]??'');
function el(tag,text,attrs={}){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));return e;}
function ui(tag,key,args={},attrs={}){return el(tag,tr(key,args),{lang:locale,...attrs});}
function button(key,fn,attrs={}){const b=ui('button',key,{}, {type:'button',...attrs});b.onclick=fn;return b;}
function must(ok){if(!ok)throw Error('Invalid learning package');}
function keys(o,expected){must(o!==null&&typeof o==='object'&&!Array.isArray(o));must(Object.keys(o).sort().join(' ')==expected.split(' ').sort().join(' '));}
function text(t){must(typeof t==='string'&&t.trim().length>0&&t.length<=50000&&!/<[^>]*>|(?:javascript|data|vbscript)\s*:/i.test(t));}
function slug(t){must(typeof t==='string'&&SLUG.test(t));}
function list(a,fn,required=true){must(Array.isArray(a)&&a.length<=500&&(!required||a.length>0));a.forEach(fn);}
function distinct(a){must(new Set(a).size===a.length);}
function minutes(n){must(Number.isInteger(n)&&n>0&&n<=10000);}
function validate(c){
 keys(c,'schema_version module_id content_version language translation_source_version title audience objectives scope_limits prerequisites estimated_minutes approval sources lessons questions completion_policy job_aids open_questions');
 must(c.schema_version===1);slug(c.module_id);must(typeof c.content_version==='string'&&VERSION.test(c.content_version));must(['en','ne'].includes(c.language));
 must(c.language==='en'?c.translation_source_version===null:typeof c.translation_source_version==='string'&&VERSION.test(c.translation_source_version));text(c.title);
 ['audience','objectives','scope_limits'].forEach(k=>list(c[k],text));['prerequisites','open_questions'].forEach(k=>list(c[k],text,false));minutes(c.estimated_minutes);
 keys(c.approval,'status technical_reviewer language_reviewer approver review_due');must(['draft','in-review','approved'].includes(c.approval.status));
 ['technical_reviewer','language_reviewer','approver','review_due'].forEach(k=>{if(c.approval[k]!==null)text(c.approval[k]);});
 if(c.approval.review_due!==null)must(/^\d{4}-\d{2}-\d{2}$/.test(c.approval.review_due));
 list(c.sources,s=>{keys(s,'source_id title edition reference location rights');slug(s.source_id);['title','edition','reference','location','rights'].forEach(k=>text(s[k]));});distinct(c.sources.map(s=>s.source_id));
 const refs=a=>{list(a,id=>{slug(id);must(c.sources.some(s=>s.source_id===id));});distinct(a);};
 list(c.lessons,l=>{keys(l,'lesson_id title objective estimated_minutes blocks');slug(l.lesson_id);text(l.title);text(l.objective);must(c.objectives.includes(l.objective));minutes(l.estimated_minutes);list(l.blocks,b=>{keys(b,'type body source_ids');must(TYPES.includes(b.type));text(b.body);refs(b.source_ids);});});distinct(c.lessons.map(l=>l.lesson_id));
 list(c.questions,q=>{keys(q,'question_id objective prompt options correct_option_id source_ids');slug(q.question_id);text(q.objective);must(c.objectives.includes(q.objective));text(q.prompt);list(q.options,o=>{keys(o,'option_id text rationale');slug(o.option_id);text(o.text);text(o.rationale);});must(q.options.length>=2);distinct(q.options.map(o=>o.option_id));must(q.options.some(o=>o.option_id===q.correct_option_id));refs(q.source_ids);});distinct(c.questions.map(q=>q.question_id));
 keys(c.completion_policy,'mode required_lesson_ids pass_percent');must(c.completion_policy.mode==='formative_trial'&&c.completion_policy.pass_percent===null);list(c.completion_policy.required_lesson_ids,id=>{slug(id);must(c.lessons.some(l=>l.lesson_id===id));});distinct(c.completion_policy.required_lesson_ids);
 list(c.job_aids,a=>{keys(a,'aid_id title body source_ids');slug(a.aid_id);text(a.title);text(a.body);refs(a.source_ids);});distinct(c.job_aids.map(a=>a.aid_id));return c;
}
function safeUrl(raw){try{const u=new URL(raw);return u.protocol==='https:'&&!u.username&&!u.password&&!u.port&&(raw==='https://mhpss-nepal.github.io/referral-directory.html'||['www.who.int','interagencystandingcommittee.org','www.mhpssmsp.org','spherestandards.org','campus.paho.org','whoacademy.org'].includes(u.hostname))?u.href:null;}catch{return null;}}
async function get(path){const response=await fetch(path,{cache:'no-store',credentials:'omit',redirect:'error'});if(!response.ok)throw Error('Unavailable');const raw=await response.text();must(raw.length<3000000);return raw;}
async function sha(raw){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw));return Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,'0')).join('');}
async function load(){
 const loading=++loadGeneration;cancelOpen(null);$('retry').hidden=true;$('load-status').textContent=tr('loading');$('released-courses').replaceChildren();$('reader-root').replaceChildren();courses=[];C=null;state=null;contentHash='';progressKey='';opted=false;storageMessage='';document.body.removeAttribute('data-ready');
 try{
  const dictionary=JSON.parse(await get('assets/ui.json'));if(loading!==loadGeneration)return;must(dictionary.en&&dictionary.ne&&Object.keys(dictionary.en).every(k=>typeof dictionary.ne[k]==='string'));D=dictionary;updateLocale();
  const catalogue=JSON.parse(await get('content/catalogue.json'));keys(catalogue,'schema_version modules');must(catalogue.schema_version===1);list(catalogue.modules,entry=>{
   keys(entry,'module_id content_version language path sha256');slug(entry.module_id);must(typeof entry.content_version==='string'&&VERSION.test(entry.content_version));must(['en','ne'].includes(entry.language));
   must(typeof entry.path==='string'&&entry.path===`modules/${entry.module_id}/${entry.content_version}/${entry.language}.json`);must(typeof entry.sha256==='string'&&/^[a-f0-9]{64}$/.test(entry.sha256));
  },false);distinct(catalogue.modules.map(e=>e.module_id+'/'+e.language));
  // Validate every package before exposing any reader: one malformed entry closes the entire catalogue.
  const loaded=await Promise.all(catalogue.modules.map(async entry=>{const raw=await get('content/'+entry.path);must(await sha(raw)===entry.sha256);const c=validate(JSON.parse(raw));must(c.module_id===entry.module_id&&c.content_version===entry.content_version&&c.language===entry.language);return {c,hash:entry.sha256};}));
  for(const row of loaded)if(row.c.language==='ne'){const en=loaded.find(r=>r.c.module_id===row.c.module_id&&r.c.language==='en');must(en&&row.c.translation_source_version===en.c.content_version);}
  if(loading!==loadGeneration)return;courses=loaded;renderCourses();$('load-status').textContent=tr(courses.length?'loaded':'empty');document.body.dataset.ready='';
 }catch{if(loading!==loadGeneration)return;$('load-status').textContent=tr('loadError');$('load-status').setAttribute('role','alert');$('retry').hidden=false;$('retry').textContent=tr('retry');}
}
function renderCourses(){const root=$('released-courses');root.replaceChildren();if(!courses.length)return;root.append(ui('h2','published'));
 const ids=[...new Set(courses.map(r=>r.c.module_id))];for(const id of ids){const r=courses.find(r=>r.c.module_id===id&&r.c.language===locale)||courses.find(r=>r.c.module_id===id&&r.c.language==='en')||courses.find(r=>r.c.module_id===id);const card=el('article',undefined,{class:'published-card',lang:r.c.language});card.append(el('h3',r.c.title),button('start',()=>openCourse(r),{'data-start':id}));root.append(card);}}
function updateLocale(){document.documentElement.lang=locale;document.querySelectorAll('[data-ui]').forEach(e=>{e.textContent=tr(e.dataset.ui);e.lang=locale==='ne'&&e.dataset.ui.startsWith('catalogue_')&&D.ne[e.dataset.ui]===D.en[e.dataset.ui]?'en':locale;});$('locale').value=locale;$('locale-review').textContent=tr('uiDraft');$('locale-review').lang=locale;$('missing-course').hidden=locale!=='ne'||Boolean(C&&C.language==='ne');$('missing-course').textContent=tr('missingCourse');$('missing-course').lang=locale;renderCourses();if(C)renderReader();}
$('locale').onchange=e=>{locale=e.target.value;const generation=++openGeneration,next=rendition(requestedModule);if(next&&next.c!==C){persist();openCourse(next,generation);}else pendingIdentity=null;updateLocale();};$('retry').onclick=load;
$('theme').onclick=()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';};
function initial(){return {lesson:C.lessons[0].lesson_id,read:[],answers:Object.create(null),checked:Object.create(null)};}
let progressKey='',opted=false,storageMessage='';
function validState(s){
 keys(s,'lesson read answers checked');must(C.lessons.some(l=>l.lesson_id===s.lesson));list(s.read,id=>must(C.lessons.some(l=>l.lesson_id===id)),false);distinct(s.read);
 must(s.answers&&typeof s.answers==='object'&&!Array.isArray(s.answers)&&s.checked&&typeof s.checked==='object'&&!Array.isArray(s.checked));
 for(const [id,value] of Object.entries(s.answers)){const q=C.questions.find(q=>q.question_id===id);must(q&&q.options.some(o=>o.option_id===value));}
 for(const [id,value] of Object.entries(s.checked))must(value===true&&Object.hasOwn(s.answers,id));
}
function restore(){opted=false;storageMessage='';try{const raw=localStorage.getItem(progressKey);if(raw===null)return;const saved=JSON.parse(raw);keys(saved,'schema_version rendition_hash state');must(saved.schema_version===2&&typeof saved.rendition_hash==='string'&&/^[a-f0-9]{64}$/.test(saved.rendition_hash));validState(saved.state);
 const sameRendition=saved.rendition_hash===contentHash;state={...saved.state,answers:Object.assign(Object.create(null),sameRendition?saved.state.answers:{}),checked:Object.assign(Object.create(null),sameRendition?saved.state.checked:{})};opted=true;}catch{storageMessage='storageError';}}
function persist(){if(!opted)return;try{localStorage.setItem(progressKey,JSON.stringify({schema_version:2,rendition_hash:contentHash,state}));}catch{opted=false;storageMessage='storageError';if($('save-progress'))$('save-progress').checked=false;if($('storage-status'))$('storage-status').textContent=tr('storageError');}}
function clearProgress(){try{localStorage.removeItem(progressKey);}catch{storageMessage='storageError';}}
function settings(root){const section=el('section',undefined,{class:'settings'}),label=el('label'),input=el('input',undefined,{id:'save-progress',type:'checkbox'});input.checked=opted;input.onchange=()=>{opted=input.checked;if(opted)persist();else clearProgress();};label.append(input,ui('span','save'));section.append(label,ui('p','saveNote'),button('reset',()=>{cancelOpen(C.module_id);opted=false;clearProgress();state=initial();if(storageMessage!=='storageError')storageMessage='resetDone';renderReader();},{id:'reset-progress'}),ui('p',storageMessage||'memoryOnly',{}, {id:'storage-status',role:'status'}));root.append(section);}
// Intent owns authority; an identity promise is only reusable work, never authority.
function cancelOpen(module){openGeneration++;requestedModule=module;pendingIdentity=null;}
function rendition(module){return courses.find(r=>r.c.module_id===module&&r.c.language===locale)||courses.find(r=>r.c.module_id===module&&r.c.language==='en')||courses.find(r=>r.c.module_id===module);}
async function openCourse(row,generation){if(generation===undefined){generation=++openGeneration;requestedModule=row.c.module_id;pendingIdentity=null;row=rendition(requestedModule);}const c=row.c,source=courses.find(r=>r.c.module_id===c.module_id&&r.c.language==='en')||row;
 const shape=JSON.stringify({module:c.module_id,version:c.content_version,source:source.hash,lessons:c.lessons.map(l=>l.lesson_id),questions:c.questions.map(q=>[q.question_id,q.options.map(o=>o.option_id),q.correct_option_id])});
 if(!pendingIdentity||pendingIdentity.shape!==shape)pendingIdentity={shape,promise:sha(shape)};
 const identity=pendingIdentity;try{const key='mhpss.learn.v1.'+c.module_id+'.'+await identity.promise;if(generation!==openGeneration||requestedModule!==c.module_id||rendition(requestedModule)!==row)return;
 pendingIdentity=null;C=c;contentHash=row.hash;progressKey=key;state=initial();restore();updateLocale();$('reader-root').scrollIntoView({block:'start'});$('reader-title').focus();
 }catch{if(generation!==openGeneration)return;pendingIdentity=null;$('load-status').textContent=tr('loadError');}}
function citations(ids){const box=el('div',undefined,{'data-citation':'',class:'citations',lang:C.language});box.append(ui('strong','sources'));ids.forEach(id=>{const s=C.sources.find(s=>s.source_id===id);box.append(el('p',`${s.source_id} · ${s.title} · ${s.edition} · ${s.reference} · ${s.location}`));const url=safeUrl(s.reference);if(url)box.append(el('a',s.title,{href:url,target:'_blank',rel:'noopener noreferrer'}));});return box;}
function bullets(content,key,values){content.append(ui('h3',key));const ul=el('ul');values.forEach(v=>ul.append(el('li',v,{lang:C.language})));content.append(ul);}
function download(body,id){const url=URL.createObjectURL(new Blob([body],{type:'text/plain;charset=utf-8'}));const link=el('a',undefined,{href:url,download:id+'-'+C.content_version+'.txt'});document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function renderReader(){const root=$('reader-root');root.replaceChildren();root.append(el('h2',C.title,{id:'reader-title',tabindex:'-1',lang:C.language}),ui('p','lineage',{version:C.content_version,language:C.language,hash:contentHash},{id:'lineage'}));
 settings(root);const layout=el('div',undefined,{class:'reader-layout'}),nav=el('nav',undefined,{class:'lesson-nav','aria-label':tr('lessons')});
 C.lessons.forEach((l,i)=>nav.append(button('lesson',()=>{state.lesson=l.lesson_id;persist();renderReader();$('lesson-title').focus();},{'data-lesson':l.lesson_id,'aria-current':state.lesson===l.lesson_id?'step':'false','aria-label':tr('lesson',{number:i+1})+' — '+l.title})));
 Array.from(nav.children).forEach((b,i)=>b.textContent=tr('lesson',{number:i+1}));
 const main=el('article'),content=el('div',undefined,{id:'course-content',lang:C.language});
 bullets(content,'audience',C.audience);bullets(content,'objectives',C.objectives);bullets(content,'scope',C.scope_limits);if(C.prerequisites.length)bullets(content,'prerequisites',C.prerequisites);
 const lesson=C.lessons.find(l=>l.lesson_id===state.lesson);content.append(el('h2',lesson.title,{id:'lesson-title',tabindex:'-1'}),el('p',lesson.objective));
 lesson.blocks.forEach((block,i)=>{const section=el('section',undefined,{class:'block '+block.type,'data-block':block.type});section.append(ui('h3',block.type));
  if(block.type==='steps'){const ol=el('ol');block.body.split(/\n+/).filter(x=>x.trim()).forEach(s=>ol.append(el('li',s)));section.append(ol);}else section.append(el('p',block.body));
  if(block.type==='reflection'){section.append(ui('label','reflectionHint',{}, {for:'reflection-'+i}),el('textarea',undefined,{id:'reflection-'+i,autocomplete:'off',spellcheck:'false','aria-label':tr('reflectionHint')}));}
  if(block.type==='job_aid')section.append(button('download',()=>download(block.body,'lesson-aid-'+i)));
  section.append(citations(block.source_ids));content.append(section);
 });main.append(content,button('markRead',()=>{if(!state.read.includes(lesson.lesson_id))state.read.push(lesson.lesson_id);persist();renderReader();},{id:'mark-read'}),ui('p','read',{count:state.read.length,total:C.lessons.length},{id:'read-progress',role:'status'}));layout.append(nav,main);root.append(layout);renderQuiz(root);renderResources(root);
}
function renderQuiz(root){root.append(ui('h2','quiz'));const quiz=el('div',undefined,{id:'quiz-content',lang:C.language});
 C.questions.forEach(q=>{const field=el('fieldset',undefined,{'data-question':q.question_id});field.append(el('legend',q.prompt));const feedback=el('div'),err=el('p','',{role:'alert'});
 q.options.forEach(o=>{const label=el('label',undefined,{class:'option'}),input=el('input',undefined,{type:'radio',name:q.question_id,value:o.option_id});input.checked=state.answers[q.question_id]===o.option_id;input.onchange=()=>{state.answers[q.question_id]=o.option_id;delete state.checked[q.question_id];persist();feedback.replaceChildren();err.textContent='';updateScore();};label.append(input,el('span',o.text));field.append(label);});
 const show=()=>{feedback.replaceChildren();if(!state.checked[q.question_id])return;feedback.append(ui('strong',state.answers[q.question_id]===q.correct_option_id?'correct':'incorrect'));q.options.forEach(o=>{const section=el('section',undefined,{'data-rationale':o.option_id});section.append(el('h4',o.text),el('p',o.rationale),citations(q.source_ids));feedback.append(section);});};
 field.append(button('check',()=>{if(!state.answers[q.question_id]){err.textContent=tr('choose');err.lang=locale;return;}state.checked[q.question_id]=true;persist();show();updateScore();},{'data-check':''}),err,feedback);show();quiz.append(field);
 });root.append(quiz,ui('p','incomplete',{}, {id:'score',role:'status'}),ui('p','completionPending',{}, {id:'completion-summary',role:'status'}));updateScore();}
function updateScore(){const checked=C.questions.every(q=>state.checked[q.question_id]);$('score').textContent=checked?tr('score',{count:C.questions.filter(q=>state.answers[q.question_id]===q.correct_option_id).length,total:C.questions.length}):tr('incomplete');$('completion-summary').textContent=tr(checked&&C.completion_policy.required_lesson_ids.every(id=>state.read.includes(id))?'completionDone':'completionPending');}
function renderResources(root){root.append(ui('h2','job_aid'));C.job_aids.forEach((a,i)=>{const section=el('section',undefined,{lang:C.language});section.append(el('h3',a.title),el('p',a.body),citations(a.source_ids),button('download',()=>download(a.body,a.aid_id),i===0?{id:'download-aid'}:{}));root.append(section);});const details=el('details');details.append(ui('summary','sources'));C.sources.forEach(s=>details.append(citations([s.source_id])));root.append(details);}
load();
})();
