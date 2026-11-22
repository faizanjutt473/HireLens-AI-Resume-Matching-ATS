const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const logo=s=>`https://cdn.simpleicons.org/${s}/ffffff`;
const LOGO=`<a class="brand" href="index.html" aria-label="HireLens home"><svg class="mark" viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" aria-hidden="true"><path d="M14 38A40 40 0 0 1 86 38"/><path d="M14 62A40 40 0 0 0 86 62"/><path d="M29 36Q40 20 62 21" stroke="#6B6B6B"/><path d="M71 64Q62 79 40 79" stroke="#6B6B6B"/><circle cx="31" cy="80" r="1.5" stroke="#6B6B6B"/></svg><span class="wm"><b>HIRE</b><span>LENS</span></span></a>`;
const page=document.body.dataset.page;
const NAV=[['index.html','Home','home'],['jobs.html','Find jobs','jobs'],['candidate.html','Candidate portal','candidate'],['employer.html','Employer portal','employer']];
$('#nav').outerHTML=`<header class="nav"><div class="wrap">${LOGO}
<button class="burger" aria-label="Menu" aria-expanded="false">Menu</button>
<nav class="links" aria-label="Main">${NAV.map(n=>`<a href="${n[0]}" class="${page===n[2]?'on':''}">${n[1]}</a>`).join('')}<a href="login.html">Log in</a><a class="btn pri sm" href="register.html">Create account</a></nav></div></header>`;
$('.burger').onclick=e=>{const o=$('.links').classList.toggle('open');e.target.setAttribute('aria-expanded',o)};
const ft=$('#foot');if(ft)ft.outerHTML=`<footer class="foot"><div class="wrap"><div>${LOGO}<p class="muted" style="margin-top:8px">Hiring that reads resumes so you don't have to.</p></div><div><a href="jobs.html">Jobs</a><a href="candidate.html">Candidates</a><a href="employer.html">Employers</a><a href="login.html">Log in</a></div></div></footer>`;
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.15});
$$('.rv').forEach(el=>io.observe(el));
function toast(m){let t=$('.toast')||document.body.appendChild(Object.assign(document.createElement('div'),{className:'toast',role:'status'}));t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2600)}
$$('.count').forEach(el=>{const to=+el.dataset.to;let n=0;const st=()=>{n+=Math.ceil(to/40);el.textContent=Math.min(n,to).toLocaleString();if(n<to)requestAnimationFrame(st)};st()});
$$('form[data-validate]').forEach(f=>f.addEventListener('submit',e=>{e.preventDefault();let ok=true;
 $$('input[required]',f).forEach(i=>{const bad=!i.value.trim()||(i.type==='email'&&!/^\S+@\S+\.\S+$/.test(i.value))||(i.type==='password'&&i.value.length<8);i.closest('.field').classList.toggle('bad',bad);if(bad)ok=false});
 if(ok){toast('Done. Redirecting...');setTimeout(()=>location.href=f.dataset.next,900)}}));
$$('.seg').forEach(s=>s.onclick=e=>{const b=e.target.closest('button');if(!b)return;$$('button',s).forEach(x=>x.classList.toggle('on',x===b));$('#role').value=b.dataset.role;$('form[data-validate]').dataset.next=b.dataset.role==='employer'?'employer.html':'candidate.html'});
const JOBS=[['Senior ML Engineer','Google','google','Remote','Full-time',92,['Python','PyTorch','NLP']],['Backend Developer','Spotify','spotify','Lahore','Full-time',86,['Flask','PostgreSQL','Docker']],['Data Scientist','Airbnb','airbnb','Islamabad','Contract',81,['SQL','scikit-learn','Pandas']],['AI Engineer','Stripe','stripe','Remote','Full-time',88,['FastAPI','LLMs','Redis']],['Computer Vision Engineer','Netflix','netflix','Karachi','Full-time',74,['OpenCV','PyTorch','CUDA']],['MLOps Engineer','Shopify','shopify','Remote','Part-time',69,['Docker','CI/CD','AWS']]];
const jl=$('#jobList');
if(jl){const draw=()=>{const q=$('#q').value.toLowerCase(),l=$('#loc').value,t=$('#type').value;
 const r=JOBS.filter(j=>(j[0]+j[1]+j[6]).toLowerCase().includes(q)&&(!l||j[3]===l)&&(!t||j[4]===t)).sort((a,b)=>b[5]-a[5]);
 $('#count').textContent=r.length+' jobs found';
 jl.innerHTML=r.length?r.map(j=>`<article class="card lift job"><div class="logo"><img src="${logo(j[2])}" alt="${j[1]} logo"></div><div class="info"><h3>${j[0]}</h3><div class="muted">${j[1]} · ${j[3]} · ${j[4]}</div><div class="tags">${j[6].map(s=>`<span class="chip">${s}</span>`).join('')}</div></div><div class="ring" style="--p:${j[5]}" title="Resume match"><b>${j[5]}%</b></div><button class="btn pri sm" onclick="toast('Application sent to ${j[1]}')">Apply</button></article>`).join(''):`<div class="empty"><h3>No jobs match those filters</h3><p class="muted">Clear a filter or try a broader keyword.</p></div>`};
 jl.innerHTML='<div class="skel"></div>'.repeat(3);setTimeout(draw,700);$$('#q,#loc,#type').forEach(i=>i.oninput=draw)}
const dz=$('#drop');
if(dz){const fi=$('#file');dz.onclick=()=>fi.click();
 ['dragover','dragenter'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add('over')}));
 ['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove('over')}));
 dz.addEventListener('drop',e=>go(e.dataTransfer.files[0]));fi.onchange=()=>go(fi.files[0]);
 function go(f){if(!f)return;if(!/\.(pdf|docx?)$/i.test(f.name))return toast('Upload a PDF or Word file');
  dz.innerHTML=`<p>Reading <b>${f.name}</b>...</p><div class="bar"><i id="pb"></i></div>`;setTimeout(()=>$('#pb').style.width='100%',50);
  setTimeout(()=>{dz.innerHTML=`<p><b>${f.name}</b> uploaded</p>`;$('#skills').innerHTML=['Python','PyTorch','FastAPI','scikit-learn','OpenCV','SQL','Docker'].map((s,i)=>`<span class="chip" style="animation-delay:${i*80}ms">${s}</span>`).join('');toast('Skills extracted')},1400)}}
$$('.cand').forEach(c=>{c.draggable=true;c.ondragstart=e=>{c.classList.add('drag');e.dataTransfer.setData('t',c.id)};c.ondragend=()=>c.classList.remove('drag')});
$$('.col').forEach(col=>{col.ondragover=e=>{e.preventDefault();col.classList.add('over')};col.ondragleave=()=>col.classList.remove('over');
 col.ondrop=e=>{e.preventDefault();col.classList.remove('over');const c=document.getElementById(e.dataTransfer.getData('t'));col.appendChild(c);cnt();toast(c.dataset.n+' moved to '+col.dataset.s);if(col.dataset.s==='Interview')$('#sched').classList.add('open')}});
function cnt(){$$('.col').forEach(c=>$('.n',c).textContent=$$('.cand',c).length)}if($('.col'))cnt();
$$('[data-close]').forEach(b=>b.onclick=()=>b.closest('.modal').classList.remove('open'));
$$('[data-bar]').forEach(b=>setTimeout(()=>b.style.width=b.dataset.bar+'%',300));
// hover: text inside cards drifts with the cursor
if(!matchMedia('(prefers-reduced-motion:reduce)').matches){
 const drift=c=>{c.addEventListener('mousemove',e=>{const r=c.getBoundingClientRect();c.style.setProperty('--mx',((e.clientX-r.left)/r.width-.5).toFixed(2));c.style.setProperty('--my',((e.clientY-r.top)/r.height-.5).toFixed(2))});c.addEventListener('mouseleave',()=>{c.style.setProperty('--mx',0);c.style.setProperty('--my',0)})};
 $$('.card,.cand').forEach(drift);
 // home: blocks sway up/down and sideways while scrolling
 if(page==='home'){const els=$$('.hero h1,.hero p,.hero .row,.logos,section h2,.card');
  els.forEach((el,i)=>el.dataset.sp=(i%2?1:-1)*(16+(i%3)*8));
  let busy=false;const tick=()=>{busy=false;const vh=innerHeight;els.forEach(el=>{const r=el.getBoundingClientRect();if(r.bottom<-200||r.top>vh+200)return;const k=(r.top+r.height/2-vh/2)/vh,s=+el.dataset.sp;el.style.setProperty('--py',(k*s*1.6).toFixed(1)+'px');el.style.setProperty('--px',(Math.sin(k*3)*s*.6).toFixed(1)+'px')})};
  addEventListener('scroll',()=>{if(!busy){busy=true;requestAnimationFrame(tick)}},{passive:true});tick()}}
if(page==='home'){$$('main .card').forEach(c=>c.classList.add('shade'));$$('.hero h1,section h2').forEach(h=>h.classList.add('flow'))}

if(page==='home'){
 const h=$('.hero h1');h.classList.remove('flow');
 h.insertAdjacentHTML('beforebegin',`<div class="biglogo">${LOGO.replace('class="brand"','class="brand big"')}</div>`);
 if(!matchMedia('(prefers-reduced-motion:reduce)').matches){
  const full=h.textContent.trim();h.setAttribute('aria-label',full);h.style.minHeight=h.offsetHeight+'px';
  h.innerHTML='<span aria-hidden="true" id="tw"></span><span class="tw-c" aria-hidden="true"></span>';
  const t=$('#tw');let i=0,dir=1;
  const step=()=>{i+=dir;t.textContent=full.slice(0,i);
   if(dir===1&&i===full.length){dir=-1;return setTimeout(step,2800)}
   if(dir===-1&&i===0){dir=1;return setTimeout(step,600)}
   setTimeout(step,dir===1?(full[i-1]===' '?140:65):22)};
  setTimeout(step,500)}}
