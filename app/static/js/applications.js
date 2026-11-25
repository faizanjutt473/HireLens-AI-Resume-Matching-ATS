const al=$('#appList');
if(al){
 const lab=s=>s.charAt(0).toUpperCase()+s.slice(1);
 (async()=>{
  try{
   const a=(await api('/applications/mine')).applications;
   $('#stApplied').textContent=a.length;
   $('#stShort').textContent=a.filter(x=>x.stage==='shortlisted').length;
   $('#stInt').textContent=a.filter(x=>x.stage==='interview').length;
   al.innerHTML=a.length?a.map(x=>`<div class="job" style="padding:12px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(x.job_title)}</b><div class="muted">${esc(x.company)} · applied ${ago(x.applied_at)}</div></div>${x.match_score!=null?`<div class="ring" style="--p:${x.match_score}" title="Match score"><b>${Math.round(x.match_score)}%</b></div>`:''}<span class="chip">${lab(x.stage)}</span></div>`).join(''):'<p class="muted">No applications yet. <a href="jobs.html" style="color:#fff">Browse open jobs</a></p>';
  }catch(e){al.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
 })();
}
const il=$('#intList');
if(il){
 (async()=>{
  try{
   const list=(await api('/interviews/mine')).interviews;
   il.innerHTML=list.length?list.map(i=>`<div class="job" style="padding:12px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(i.job_title)}</b> · ${esc(i.company)}<div class="muted">${new Date(i.scheduled_at).toLocaleString([],{dateStyle:'medium',timeStyle:'short'})} · ${i.duration_minutes} min</div><div class="muted" style="overflow-wrap:anywhere">${esc(i.location_or_link)}</div>${i.notes?`<div class="muted">${esc(i.notes)}</div>`:''}</div></div>`).join(''):'<p class="muted">No interviews scheduled yet.</p>';
  }catch(e){il.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
 })();
}