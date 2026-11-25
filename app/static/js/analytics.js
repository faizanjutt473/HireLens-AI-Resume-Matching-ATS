const an=$('#analytics');
if(an){
 const dur=d=>d==null?'-':d<1?Math.max(1,Math.round(d*24))+' hrs':d.toFixed(1)+' days';
 const LAB={applied:'Applied',shortlisted:'Shortlisted',interview:'Interview',hired:'Hired'};
 const bars=(rows,key,label,max)=>rows.length?rows.map(r=>`<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between;gap:10px"><span style="color:#fff">${esc(label(r))}</span><span class="muted">${r.count}</span></div><div class="bar"><i data-w="${max?Math.round(r.count/max*100):0}"></i></div></div>`).join(''):'<p class="muted">Nothing to show yet.</p>';
 const render=d=>{
  const s=d.summary;
  $('#anStats').innerHTML=[[s.applicants,'Total applicants'],[s.hired,'Hired'],[dur(s.avg_days_to_hire),'Average time-to-hire'],[s.avg_match!=null?Math.round(s.avg_match)+'%':'-','Average match score'],[s.open_jobs+' / '+s.jobs,'Open jobs']].map(x=>`<div class="card"><b>${x[0]}</b>${x[1]}</div>`).join('');
  const top=d.funnel[0].count;
  $('#anFunnel').innerHTML=top?d.funnel.map(f=>`<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between"><span style="color:#fff">${LAB[f.stage]}</span><span class="muted">${f.count}${top?' · '+Math.round(f.count/top*100)+'%':''}</span></div><div class="bar"><i data-w="${Math.round(f.count/top*100)}"></i></div></div>`).join('')+(s.rejected?`<p class="muted">${s.rejected} rejected</p>`:''):'<p class="muted">No applicants yet.</p>';
  const mx=Math.max(1,...d.timeline.map(t=>t.count));
  $('#anTime').innerHTML=`<div style="display:flex;align-items:flex-end;gap:5px;height:130px">${d.timeline.map(t=>`<div title="${t.date}: ${t.count}" style="flex:1;background:#FFFFFF;border-radius:4px 4px 0 0;height:${Math.max(t.count?6:2,t.count/mx*100)}%;opacity:${t.count?1:.25}"></div>`).join('')}</div><div style="display:flex;justify-content:space-between" class="muted"><small>${d.timeline[0].date.slice(5)}</small><small>${d.timeline[13].date.slice(5)}</small></div>`;
  const nm=r=>r.skill;
  $('#anYours').innerHTML=bars(d.demand_yours,'skill',nm,Math.max(1,...d.demand_yours.map(r=>r.count)));
  $('#anMarket').innerHTML=bars(d.demand_market,'skill',nm,Math.max(1,...d.demand_market.map(r=>r.count)));
  $('#anApp').innerHTML=bars(d.applicant_skills,'skill',nm,Math.max(1,...d.applicant_skills.map(r=>r.count)));
  $('#anJobs').innerHTML=d.per_job.length?d.per_job.map(j=>`<div class="job" style="padding:10px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(j.title)}</b><div class="muted">${j.applicants} applicants · ${j.hired} hired</div></div><span class="chip">${dur(j.avg_days_to_hire)}</span></div>`).join(''):'<p class="muted">Post a job to see this.</p>';
  requestAnimationFrame(()=>requestAnimationFrame(()=>$$('[data-w]',an).forEach(b=>b.style.width=b.dataset.w+'%')));
 };
 let t;
 const load=async()=>{try{render(await api('/analytics/employer'))}catch(e){toast(e.message)}};
 load();
 // pipeline badalne par analytics khud refresh ho (stats wale numbers update hote hain)
 const hook=$('#stHired');
 if(hook)new MutationObserver(()=>{clearTimeout(t);t=setTimeout(load,500)}).observe(hook,{childList:true});
}