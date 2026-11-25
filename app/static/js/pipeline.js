const board=$('#board'),up=$('#upcoming');
const fmt=iso=>new Date(iso).toLocaleString([],{dateStyle:'medium',timeStyle:'short'});

// ---- upcoming interviews (employer) ----
const loadUpcoming=async()=>{
 if(!up)return;
 try{
  const list=(await api('/interviews/upcoming')).interviews;
  up.innerHTML=list.length?list.map(i=>`<div class="job" style="padding:12px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(i.candidate_name)}</b> · ${esc(i.job_title)}<div class="muted">${fmt(i.scheduled_at)} · ${i.duration_minutes} min · ${esc(i.location_or_link)}</div></div><button class="btn sm" data-cancel="${i.id}">Cancel</button></div>`).join(''):'<p class="muted">No interviews scheduled.</p>';
 }catch(e){up.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
};
if(up){
 up.addEventListener('click',async e=>{
  const b=e.target.closest('[data-cancel]');
  if(!b||!confirm('Cancel this interview? The candidate will be emailed.'))return;
  try{await api(`/interviews/${b.dataset.cancel}/cancel`,{method:'POST'});toast('Interview cancelled');loadUpcoming()}
  catch(err){toast(err.message)}
 });
 loadUpcoming();
}

// ---- hiring pipeline ----
if(board){
 const sel=$('#pipeJob'),LABEL={applied:'Applied',shortlisted:'Shortlisted',interview:'Interview',hired:'Hired',rejected:'Rejected'};
 let apps=[],pending=null;
 const cardHtml=a=>`<div class="cand" data-id="${a.id}" draggable="true"><b style="color:#fff">${esc(a.candidate_name)}</b><div class="muted" style="font-size:.85rem;overflow-wrap:anywhere">${esc(a.email)}</div><div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px"><span class="chip">${a.match_score!=null?Math.round(a.match_score)+'% match':'No score'}</span>${a.has_resume?`<button class="btn sm" data-resume="${a.id}">Resume</button>`:''}</div>${a.matched.length?`<div class="tags" style="margin-top:10px">${a.matched.map(s=>`<span class="chip">${esc(s)}</span>`).join('')}</div>`:''}</div>`;
 const render=()=>$$('.col',board).forEach(col=>{
  const list=apps.filter(a=>a.stage===col.dataset.stage);
  $('.n',col).textContent=list.length;
  $('.cards',col).innerHTML=list.length?list.map(cardHtml).join(''):'<p class="muted" style="font-size:.85rem">Drop candidates here</p>';
 });
 const loadBoard=async()=>{
  try{
   const d=await api('/pipeline/jobs/'+sel.value);
   apps=d.applicants;render();
   $('#stTotal').textContent=d.stats.total;$('#stShort').textContent=d.stats.shortlisted;$('#stHired').textContent=d.stats.hired;
   $('#stAvg').textContent=d.stats.avg_days_to_hire!=null?d.stats.avg_days_to_hire+' days':'-';
  }catch(e){toast(e.message)}
 };
 const loadJobs=async()=>{
  try{
   const jobs=(await api('/jobs/mine')).jobs,prev=sel.value;
   sel.innerHTML=jobs.map(j=>`<option value="${j.id}">${esc(j.title)} (${j.status})</option>`).join('');
   $('#pipeWrap').hidden=!jobs.length;$('#pipeEmpty').hidden=!!jobs.length;
   if(!jobs.length)return;
   if(jobs.some(j=>String(j.id)===prev))sel.value=prev;
   loadBoard();
  }catch{}
 };
 sel.onchange=loadBoard;
 new MutationObserver(loadJobs).observe($('#myJobs'),{childList:true});

 board.addEventListener('dragstart',e=>{const c=e.target.closest('.cand');if(!c)return;c.classList.add('drag');e.dataTransfer.setData('text/plain',c.dataset.id);e.dataTransfer.effectAllowed='move'});
 board.addEventListener('dragend',e=>{const c=e.target.closest('.cand');if(c)c.classList.remove('drag')});
 $$('.col',board).forEach(col=>{
  col.ondragover=e=>{e.preventDefault();col.classList.add('over')};
  col.ondragleave=e=>{if(!col.contains(e.relatedTarget))col.classList.remove('over')};
  col.ondrop=async e=>{
   e.preventDefault();col.classList.remove('over');
   const a=apps.find(x=>x.id===+e.dataTransfer.getData('text/plain'));
   if(!a||a.stage===col.dataset.stage)return;
   if(col.dataset.stage==='interview'){ // interview needs date, time and place first
    pending=a;$('#schedWho').textContent='Interview with '+a.candidate_name;
    const now=new Date(Date.now()-new Date().getTimezoneOffset()*6e4).toISOString().slice(0,16);
    $('#idt').min=now;$('#sched').classList.add('open');return;
   }
   const old=a.stage;a.stage=col.dataset.stage;render();
   try{await api(`/pipeline/applications/${a.id}/stage`,{method:'PATCH',body:{stage:a.stage}});toast(a.candidate_name+' moved to '+LABEL[a.stage]);loadBoard()}
   catch(err){a.stage=old;render();toast(err.message)}
  };
 });
 $('#schedForm').addEventListener('submit',async e=>{
  e.preventDefault();
  if(!pending)return;
  if(!$('#idt').value||!$('#iloc').value.trim())return toast('Add a date, time and meeting link or location');
  const btn=$('button:not([type=button])',e.target);btn.disabled=true;
  try{
   await api('/interviews',{method:'POST',body:{application_id:pending.id,scheduled_at:new Date($('#idt').value).toISOString(),duration_minutes:+$('#idur').value||45,location_or_link:$('#iloc').value.trim(),notes:$('#inote').value.trim()||null}});
   toast('Interview scheduled. Invitation sent.');
   $('#sched').classList.remove('open');e.target.reset();$('#idur').value=45;pending=null;
   loadBoard();loadUpcoming();
  }catch(err){toast(err.message)}
  btn.disabled=false;
 });
 board.addEventListener('click',async e=>{
  const b=e.target.closest('[data-resume]');if(!b)return;
  const w=window.open('','_blank');
  try{
   const r=await fetch(`/api/pipeline/applications/${b.dataset.resume}/resume`,{headers:{Authorization:'Bearer '+localStorage.getItem('access')}});
   if(!r.ok)throw new Error(r.status===401?'Session expired. Reload the page.':'Could not open resume');
   w.location=URL.createObjectURL(await r.blob());
  }catch(err){if(w)w.close();toast(err.message)}
 });
}