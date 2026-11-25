async function api(path,opt={}){
 const h={...(opt.headers||{})};
 if(opt.body&&!(opt.body instanceof FormData)){h['Content-Type']='application/json';opt={...opt,body:JSON.stringify(opt.body)}}
 const send=()=>{const t=localStorage.getItem('access');if(t)h.Authorization='Bearer '+t;return fetch('/api'+path,{...opt,headers:h})};
 let r=await send();
 if(r.status===401&&localStorage.getItem('refresh')){
  const rr=await fetch('/api/auth/refresh',{method:'POST',headers:{Authorization:'Bearer '+localStorage.getItem('refresh')}});
  if(rr.ok){localStorage.setItem('access',(await rr.json()).access_token);r=await send()}
  else{localStorage.clear();location.href='login.html';return}
 }
 let d=null;try{d=await r.json()}catch{}
 if(!r.ok)throw Object.assign(new Error((d&&d.message)||'Request failed'),{status:r.status});
 return d;
}