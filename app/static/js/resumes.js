const rz=$('#rzone');
if(rz){
 const fi=$('#rfile'),msg=$('#rmsg'),list=$('#resumeList'),box=$('#skillBox'),idle='<b>Drop your resume here</b> or click to browse';
 let resumes=[];
 const x='style="background:none;border:0;color:var(--muted);cursor:pointer;font-size:1rem;line-height:1;padding:0 0 0 4px"';
 const render=()=>{
  list.innerHTML=resumes.length?resumes.map(r=>`<div class="job" style="padding:12px 0;border-bottom:1px solid var(--line)"><div class="info"><b style="color:#fff">${esc(r.filename)}</b><div class="muted">${ago(r.uploaded_at)} · ${r.skills.length} skills${r.is_active?' · active':''}</div></div>${r.is_active?'':`<button class="btn sm" data-use="${r.id}">Use this</button>`}<button class="btn sm" data-del="${r.id}">Delete</button></div>`).join(''):'<p class="muted">No resume uploaded yet.</p>';
  const a=resumes.find(r=>r.is_active);
  box.innerHTML=a?`<div class="tags">${a.skills.map((s,i)=>`<span class="chip">${esc(s)}<button ${x} data-rm="${i}" aria-label="Remove ${esc(s)}">×</button></span>`).join('')||'<span class="muted">No skills detected. Add them below.</span>'}</div><form id="addSkill" style="display:flex;gap:8px;margin-top:14px"><input id="newSkill" placeholder="Add a skill" aria-label="Add a skill" maxlength="40"><button class="btn sm">Add</button></form>`:'<span class="muted">Upload a resume to see your skills.</span>';
 };
 const load=async()=>{try{resumes=(await api('/resumes')).resumes;render()}catch(e){toast(e.message)}};
 const save=async(r,body)=>{try{const d=await api('/resumes/'+r.id,{method:'PATCH',body});Object.assign(r,d.resume);render()}catch(e){toast(e.message)}};
 const send=async f=>{
  if(!f)return;
  if(!/\.(pdf|docx)$/i.test(f.name))return toast('Upload a PDF or Word (.docx) file');
  if(f.size>5*1024*1024)return toast('File is larger than 5 MB');
  msg.textContent='Reading '+f.name+'...';rz.classList.add('over');
  const fd=new FormData();fd.append('file',f);
  try{const d=await api('/resumes',{method:'POST',body:fd});toast(d.resume.skills.length+' skills found');await load()}
  catch(e){toast(e.message)}
  msg.innerHTML=idle;rz.classList.remove('over');fi.value='';
 };
 rz.onclick=()=>fi.click();
 rz.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fi.click()}};
 ['dragover','dragenter'].forEach(ev=>rz.addEventListener(ev,e=>{e.preventDefault();rz.classList.add('over')}));
 ['dragleave','drop'].forEach(ev=>rz.addEventListener(ev,e=>{e.preventDefault();rz.classList.remove('over')}));
 rz.addEventListener('drop',e=>send(e.dataTransfer.files[0]));
 fi.onchange=()=>send(fi.files[0]);
 list.addEventListener('click',async e=>{
  const u=e.target.closest('[data-use]'),d=e.target.closest('[data-del]');
  if(u){await save(resumes.find(r=>r.id==u.dataset.use),{is_active:true});load()}
  if(d&&confirm('Delete this resume?')){try{await api('/resumes/'+d.dataset.del,{method:'DELETE'});toast('Resume deleted');load()}catch(err){toast(err.message)}}
 });
 box.addEventListener('click',e=>{const b=e.target.closest('[data-rm]');if(!b)return;const a=resumes.find(r=>r.is_active);save(a,{skills:a.skills.filter((_,i)=>i!==+b.dataset.rm)})});
 box.addEventListener('submit',e=>{e.preventDefault();const v=$('#newSkill').value.trim();if(!v)return;const a=resumes.find(r=>r.is_active);save(a,{skills:[...a.skills,v]})});
 load();
}