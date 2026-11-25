const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sess=()=>JSON.parse(localStorage.getItem('user')||'null');
const ago=iso=>{const d=Math.floor((Date.now()-new Date(iso))/864e5);return d<1?'Today':d===1?'1 day ago':d+' days ago'};

// ---- jobs.html: live search, match rings and apply ----
const jf=$('#jobFeed');
if(jf){
 const me=sess(),isCand=!!me&&me.role==='candidate';
 let timer,applied=new Set();
 const card=j=>`<article class="card lift job" data-job="${j.id}"><div class="logo" aria-hidden="true"><b style="color:#fff;font-size:1.2rem">${esc(j.company.charAt(0).toUpperCase())}</b></div><div class="info"><h3>${esc(j.title)}</h3><div class="muted">${esc(j.company)} · ${esc(j.location||'Location not set')} · ${esc(j.job_type)} · ${ago(j.created_at)}</div><div class="tags">${j.skills.map(s=>`<span class="chip">${esc(s)}</span>`).join('')}</div></div><div class="ring-slot"></div><button class="btn pri sm" data-apply="${j.id}" ${applied.has(j.id)?'disabled':''}>${applied.has(j.id)?'Applied':'Apply'}</button></article>`;
 const rings=async ids=>{
  if(!isCand||!ids.length)return;
  try{
   const d=await api('/applications/scores?job_ids='+ids.join(','));
   const hint=$('#resumeHint');
   if(!d.has_resume){if(!hint)$('#count').insertAdjacentHTML('afterend','<p id="resumeHint" class="muted" style="margin-bottom:14px">Upload a resume in your <a href="candidate.html" style="color:#fff">candidate portal</a> to see how well you match each job.</p>');return}
   if(hint)hint.remove();
   Object.entries(d.scores).forEach(([id,s])=>{
    const slot=$(`[data-job="${id}"] .ring-slot`);if(!slot)return;
    const tip=(s.matched.length?'Matched: '+s.matched.join(', '):'')+(s.missing.length?(s.matched.length?' | ':'')+'Missing: '+s.missing.join(', '):'');
    slot.innerHTML=`<div class="ring" style="--p:${s.score}" title="${esc(tip)}"><b>${Math.round(s.score)}%</b></div>`;
   });
  }catch{}
 };
 const load=async()=>{
  jf.innerHTML='<div class="skel"></div>'.repeat(3);
  const p=new URLSearchParams({q:$('#q').value.trim(),location:$('#loc').value.trim(),type:$('#type').value});
  try{
   const d=await api('/jobs?'+p);
   $('#count').textContent=d.total+(d.total===1?' job found':' jobs found');
   jf.innerHTML=d.jobs.length?d.jobs.map(card).join(''):`<div class="empty"><h3>No jobs match those filters</h3><p class="muted">Clear a filter or try a broader keyword.</p></div>`;
   rings(d.jobs.map(j=>j.id));
  }catch(e){jf.innerHTML=`<div class="empty"><h3>Could not load jobs</h3><p class="muted">${esc(e.message)}</p></div>`}
 };
 $$('#q,#loc').forEach(i=>i.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(load,300)}));
 $('#type').onchange=load;
 jf.addEventListener('click',async e=>{
  const b=e.target.closest('[data-apply]');if(!b)return;
  if(!me)return location.href='login.html';
  if(!isCand)return toast('Log in with a candidate account to apply');
  b.disabled=true;
  try{
   const d=await api('/applications',{method:'POST',body:{job_id:+b.dataset.apply}});
   applied.add(+b.dataset.apply);b.textContent='Applied';
   toast('Applied. Your match score is '+Math.round(d.application.match_score)+'%');
  }catch(err){
   toast(err.message);
   if(err.status===409){applied.add(+b.dataset.apply);b.textContent='Applied'}else b.disabled=false;
  }
 });
 (async()=>{
  if(isCand){try{applied=new Set((await api('/applications/mine')).applications.map(a=>a.job_id))}catch{}}
  load();
 })();
}

// ---- employer.html: post, close and reopen jobs ----
const mj=$('#myJobs');
if(mj){
 const row=j=>`<div class="job" style="padding:12px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(j.title)}</b><div class="muted">${esc(j.location||'Location not set')} · ${esc(j.job_type)} · ${j.applicants} applicants</div></div><span class="chip">${j.status}</span><button class="btn sm" data-toggle="${j.id}" data-status="${j.status}">${j.status==='open'?'Close':'Reopen'}</button></div>`;
 const load=async()=>{
  try{const d=await api('/jobs/mine');mj.innerHTML=d.jobs.length?d.jobs.map(row).join(''):'<div class="empty"><p class="muted">No jobs yet. Post your first one.</p></div>'}
  catch(e){mj.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
 };
 load();
 $('#openPost').onclick=()=>$('#postJob').classList.add('open');
 mj.addEventListener('click',async e=>{const b=e.target.closest('[data-toggle]');if(!b)return;
  try{await api('/jobs/'+b.dataset.toggle,{method:'PATCH',body:{status:b.dataset.status==='open'?'closed':'open'}});load()}
  catch(err){toast(err.message)}});
 $('#jobForm').addEventListener('submit',async e=>{
  e.preventDefault();const f=e.target,btn=$('button:not([type=button])',f);
  const body={title:$('#jt').value.trim(),description:$('#jd').value.trim(),location:$('#jl').value.trim()||null,job_type:$('#jy').value,experience_level:$('#jx').value||null,skills:$('#js').value.split(',').map(s=>s.trim()).filter(Boolean)};
  btn.disabled=true;
  try{await api('/jobs',{method:'POST',body});toast('Job published');f.reset();$('#postJob').classList.remove('open');load()}
  catch(err){toast(err.message)}
  btn.disabled=false;
 });
}