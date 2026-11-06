import {initializeApp} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import * as A from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import * as F from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import fbcfg from "./firebase-config.js";
export const app=initializeApp(fbcfg),auth=A.getAuth(app),db=F.getFirestore(app);export{A,F,fbcfg};
export const J=s=>{try{return JSON.parse(s||"{}")}catch{return{}}};
export const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
export const online=s=>!!(s.seen&&Date.now()/1000-s.seen<90);
// A child can belong to several parents (parentIds). Legacy single parentId is still understood.
export const parentsOf=d=>Array.isArray(d.parentIds)?d.parentIds:(d.parentId?[d.parentId]:[]);
const pad=n=>String(n).padStart(2,"0");
export const clock=sec=>{sec=Math.max(0,Math.floor(sec));const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;return h?`${h}:${pad(m)}:${pad(s)}`:`${m}:${pad(s)}`};
const ago=t=>{const x=Math.floor(Date.now()/1000-t);return x<90?"just now":x<3600?Math.floor(x/60)+" min ago":x<86400?Math.floor(x/3600)+" h ago":Math.floor(x/86400)+" d ago"};
export const when=t=>{const d=new Date(t*1000),n=new Date(),day=Math.round((new Date(n.getFullYear(),n.getMonth(),n.getDate())-new Date(d.getFullYear(),d.getMonth(),d.getDate()))/864e5);
 return (day===0?"Today":day===1?"Yesterday":d.toLocaleDateString([],{month:"short",day:"numeric"}))+" "+d.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"}).toLowerCase()};
// Blocked-site log. Preferred source: status.siteHits = {"domain":{n:count,last:unixSeconds}} (agent, later).
// Fallback: count "Blocked website: domain" events so the page works with the current agent.
const hits=s=>{const m={};for(const[k,v]of Object.entries(s.siteHits||{}))m[k.toLowerCase()]={n:+v.n||0,last:+v.last||0};
 if(!s.siteHits)for(const e of s.events||[]){const x=/^Blocked website:?\s*([^\s,;]+)/i.exec(e.message||"");if(x){const k=x[1].toLowerCase().replace(/^https?:\/\/|^www\.|\/.*$/g,"");m[k]=m[k]||{n:0,last:0};m[k].n++;m[k].last=Math.max(m[k].last,e.at||0)}}
 return Object.entries(m).sort((a,b)=>b[1].last-a[1].last)};
const BR=["chrome.exe","msedge.exe","firefox.exe","brave.exe","opera.exe","vivaldi.exe"];
const FILTERS=[["adult","Adult content","Pornography and explicit sites"],["gambling","Gambling & betting","Casinos, sportsbooks, lotteries"],["social","Social media","Facebook, TikTok, Instagram and similar"],["proxy","VPNs & proxies","Stops filter bypass tools"],["safe","Safe search","Google, Bing and YouTube restricted mode"]];
const PRESETS={child:{adult:true,gambling:true,social:true,proxy:true,safeSearch:true},teen:{adult:true,gambling:true,social:false,proxy:true,safeSearch:true}};

// One child's dashboard. role 'admin' may lock sections from the parent. save(cfg, adminCfg|undefined).
// Returned element has .refresh(newDoc) which updates live data without losing unsaved edits.
export function panel(id,d,role,save){
 const adm=role==="admin",a=J(d.adminCfg);let c=J(d.cfg);
 if(adm)for(const k of ["apps","allowedApps","blockedGames","allowedGames","blockGames","sites","allowedSites","safeSearch","locationEnabled"])if(k in a)c[k]=a[k];
 const L=a.locked||[],susp=()=>!adm&&!!d.suspended,dis=k=>(!adm&&L.includes(k))||susp()?"disabled":"";
 const lkt=k=>adm?`<label class=lkt><input type=checkbox data-l=${k} ${L.includes(k)?"checked":""}> Lock from parent</label>`:L.includes(k)?`<span class=lkt>🔒 Locked by administrator</span>`:"";
 const w={};for(const k of ["apps","allowedApps","blockedGames","allowedGames","sites","allowedSites"])w[k]=[...(c[k]||[])];
 let pending=null,tab="over",tlf="all",vsf="all",vq="",showBg=false;const open=new Set();
 const el=document.createElement("div");el.className="c dev";
 const chipEd=k=>{const off=dis(k==="sites"||k==="allowedSites"?"sites":k.includes("ame")?"games":"apps");return `<div class=chips data-k=${k}>${w[k].map(x=>`<span class=chip>${esc(x)}${off?"":`<button type=button data-rm="${esc(x)}" aria-label="Remove ${esc(x)}">×</button>`}</span>`).join("")}${off?"":`<input data-add placeholder="Type and press Enter">`}</div>`};
 const tg=(f,t,s,on,k)=>`<label class=tg><input type=checkbox data-f=${f} ${on?"checked":""} ${dis(k)}><span class=sl></span><span class=tt><b>${t}</b><small>${s}</small></span></label>`;
 const flt=f=>f==="safe"?c.safeSearch!==false:!!c[f];
 const lockedNow=()=>!!c.paused||!!d.suspended;
 const calc=()=>{const s=J(d.status),on=online(s),wk=[0,6].includes(new Date().getDay()),base=wk?(c.limitWk??c.limit):c.limit,bonus=c.bonus&&c.bonus.day===s.day?+c.bonus.min:0,
  lim=base==null||isNaN(+base)?null:+base+bonus,us=s.usedSec!=null?+s.usedSec:(+s.used||0)*60,run=on&&!!s.active&&!lockedNow();
  return {s,on,lim,used:Math.floor(us/60),run,rem:lim==null?null:Math.max(0,lim*60-us-(run?Math.min(Math.max(Date.now()/1000-s.seen,0),30):0))}};
 const stateLine=(s,on,run,lk,rem)=>{
  if(s.agentMode==="monitor-only-unassigned")return "⚠ Not counting: choose the child's Windows account in the Schedule tab.";
  if(!on)return "⏸ Paused: the device is offline.";
  const lc=s.lock;if(lk||rem===0||(lc&&s.msg)){
   if(!lc)return "Waiting for the device to apply the lock…";
   return (lc.ok?"✓ ":"⚠ ")+esc(lc.note||"")+" · "+when(lc.at)+(lc.checked?" · re-checked "+ago(lc.checked):"")}
  if(run)return "▶ Counting down: the child is using the PC.";
  return s.childState==="locked"?"⏸ Paused: the child's screen is locked.":"⏸ Paused: the child is not signed in.";};
 const head=()=>{const {s,on,lim,used,rem,run}=calc(),pct=lim?Math.min(100,(lim*60-(rem??0))/(lim*60)*100):0,lk=lockedNow(),
  until=Number(c.unlockedUntil||0),unl=until>Date.now()/1000,
  ack=pending&&(Number(s.policyAppliedAt||0)>=pending-2)?(pending=null,"✓ Device confirmed the change"):pending?"Sent. Waiting for the device to confirm…":"";
  const al=[];if(!s.seen)al.push("The agent has never reported. Finish installing it on the child's PC.");else if(!on)al.push("Device offline for "+ago(s.seen).replace(" ago","")+". Locks and changes apply when it reconnects.");
  if(on&&s.msg)al.push("Restriction active: "+s.msg);if(on&&s.agentMode==="monitor-only-unassigned")al.push("No child account is set, so screen time and locking are not active yet.");if(lim&&rem!=null&&rem>0&&rem<lim*6)al.push("Screen time almost used up.");
  return `${d.suspended?`<div class=banner style="margin:0 0 14px">⛔ This child is suspended by the administrator. The device stays locked.</div>`:""}
  <div class=timer><div class="tbox ${lk?"lk":""}"><small>${lk?"Device is locked":unl?"Temporarily unlocked":"Screen time left today"}</small>
   <div class=big data-timer>${lk?"Locked":rem==null?"No limit":clock(rem)}</div>
   <div class="pbar ${pct>90?"d":pct>70?"w":""}"><i data-bar style="width:${pct}%"></i></div>
   <small>${used} min used${lim!=null?` of ${lim} min`:""}${unl?` · unlock ends ${when(until)}`:""}</small>
   <div class=tstat>${stateLine(s,on,run,lk,rem)}</div></div>
  <div class=lockbox><button class="lockbtn ${lk?"ok":"dg"}" data-q=${lk?"unlock":"lock"} ${dis("control")}>${lk?"🔓 Unlock device now":"🔒 Lock device now"}</button>
   ${lk?`<select data-q=unlock-min ${dis("control")} aria-label="Unlock length"><option value=30>Unlock for 30 minutes</option><option value=60>Unlock for 1 hour</option><option value=120>Unlock for 2 hours</option><option value=0>Unlock until I lock again</option></select>`:`<div class=row><select data-q=extend-min ${dis("control")} aria-label="Extra time"><option value=15>+15 min</option><option value=30 selected>+30 min</option><option value=60>+1 hour</option><option value=120>+2 hours</option></select><button class=gr data-q=extend ${dis("control")}>Add screen time</button></div>`}
   <span class=q role=status>${ack}</span>${lkt("control")}</div></div>
  ${al.length?`<div class=alerts><b>Needs attention</b><ul>${al.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`:""}`};
 const over=()=>{const {s,on,lim}=calc(),h=s.hist||{},ks=Object.keys(h).sort().slice(-7),mx=Math.max(lim||0,...ks.map(k=>h[k]),1),ap=Object.entries(s.apps||{}).sort((x,y)=>y[1]-x[1]).slice(0,6),am=ap.length?ap[0][1]||1:1,dv=s.device||{},loc=s.location;
  return `<div class=tiles><div class=t><small>Connection</small><b class="${on?"on":"off"}">${on?"● Online":"○ Offline"}</b></div><div class=t><small>Last seen</small><b>${s.seen?ago(s.seen):"never"}</b></div><div class=t><small>Now</small><b>${on?(s.active?"Using the PC":"Idle"):"—"}</b></div><div class=t><small>Computer</small><b>${esc(dv.computerName||"—")}</b></div></div>
  <div class=sec><b>Screen time, last days</b></div><div class=chart>${ks.map(k=>`<div class=col title="${k}: ${h[k]} min"><i style="height:${Math.round(h[k]/mx*100)}%"></i><small>${k.slice(5)}</small></div>`).join("")||"<small>No data yet</small>"}</div>
  <div class=sec><b>Top apps today</b></div>${ap.map(([n,m])=>`<div class=ar><span>${esc(n)}</span><span class=bar><i style="width:${Math.max(4,m/am*100)}%"></i></span><small>${Math.round(m)}m</small></div>`).join("")||"<small>None yet</small>"}
  <div class=sec><b>Location</b></div><div class=t>${s.locationEnabled?(loc?`<a target=_blank rel=noopener href="https://maps.google.com/?q=${Number(loc.latitude)},${Number(loc.longitude)}">Open latest location in Maps</a><small>Accuracy ${Math.round(Number(loc.accuracy)||0)} m · ${esc(loc.capturedAt||"")}</small>`:"<span class=off>Precise location not available</span>"):"Location sharing is off"}${s.locationEnabled&&s.ipLocation?`<small>Approximate: ${esc([s.ipLocation.city,s.ipLocation.region,s.ipLocation.country].filter(Boolean).join(", ")||"unknown")}</small>`:""}</div>`};
 const ICON={web:"🌐",block:"⛔",app:"🧩",screen:"⏱️",sys:"⚙️"};
 const dayName=t=>{const d=new Date(t*1000),n=new Date(),k=Math.round((new Date(n.getFullYear(),n.getMonth(),n.getDate())-new Date(d.getFullYear(),d.getMonth(),d.getDate()))/864e5);return k===0?"Today":k===1?"Yesterday":d.toLocaleDateString([],{weekday:"long",month:"short",day:"numeric"})};
 const timeline=()=>{const s=J(d.status),all=(s.timeline||s.events||[]).map(e=>({...e,kind:e.kind||(/^Blocked/.test(e.message||"")?"block":/^Application/.test(e.message||"")?"app":"sys")}));
  const list=all.filter(e=>tlf==="all"?e.kind!=="sys":e.kind===tlf).sort((a,b)=>b.at-a.at);
  if(!list.length)return `<div class=empty>${all.length?"Nothing in this filter yet.":"No activity reported yet. Updates appear here within seconds of the child using the PC."}</div>`;
  let day="",h="";for(const e of list){const dn=dayName(e.at);if(dn!==day){day=dn;h+=`<div class=tlday>${esc(dn)}</div>`}
   const txt=e.d?`${esc((e.message||"").replace(e.d,""))}<a href="http://${esc(e.d)}" target=_blank rel="noopener noreferrer">${esc(e.d)}</a>`:esc(e.message);
   h+=`<div class="tli k-${esc(e.kind)}"><span class=ti>${new Date(e.at*1000).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}</span><span class=ic>${ICON[e.kind]||"•"}</span><span>${txt}</span></div>`}
  return h};
 const visits=()=>{const s=J(d.status),blk=new Set((c.sites||[]).concat(w.sites)),q=vq.trim().toLowerCase();
  let list=(s.sites||[]).filter(x=>(showBg||!x.g||x.b)&&(vsf==="all"||(vsf==="blocked"&&x.b>0))&&(!q||x.d.includes(q))).sort((a,b)=>Math.max(b.l,b.bl)-Math.max(a.l,a.bl));
  if(!s.sites)return `<div class=empty>Visited sites appear here once the updated agent (v5.2+) is running on the child's PC.</div>`;
  if(!list.length)return `<div class=empty>No websites match.</div>`;
  return list.map(x=>{const isB=blk.has(x.d),last=Math.max(x.l,x.bl);
   return `<details class=site data-d="${esc(x.d)}" ${open.has(x.d)?"open":""}><summary><a href="http://${esc(x.d)}" target=_blank rel="noopener noreferrer">http://${esc(x.d)}</a>
    ${x.b?`<span class="tag bad">blocked ${x.b} ${x.b===1?"time":"times"}</span>`:""}${isB?`<span class="tag gy">on block list</span>`:""}${x.g?`<span class="tag gy">background</span>`:""}
    <small>${x.n?x.n+(x.n===1?" visit":" visits")+" · ":""}Last: ${when(last)}</small></summary>
    <div class=sbody><small>First seen ${when(x.f)}</small>${(x.v||[]).length?`<div class=vt>${[...x.v].reverse().map(t=>`<span class=chip style="padding:3px 10px">${when(t)}</span>`).join("")}</div>`:""}
    <div class=row style="margin-top:8px">${isB?`<button class=gr data-unblk="${esc(x.d)}" ${dis("sites")}>Remove from block list</button>`:`<button class=dg data-blk="${esc(x.d)}" ${dis("sites")}>Block this site</button>`}<a class="b gr" href="http://${esc(x.d)}" target=_blank rel="noopener noreferrer">Open site</a></div></div></details>`}).join("")};
 const sitesLog=()=>{const h=hits(J(d.status));return h.length?h.map(([dom,v])=>`<div class=hit><div><a href="http://${esc(dom)}" target=_blank rel="noopener noreferrer">http://${esc(dom)}</a><br><small>Last: ${v.last?when(v.last):"unknown"}</small></div><span class=cnt>blocked ${v.n} ${v.n===1?"time":"times"}</span></div>`).join(""):`<div class=empty>No blocked attempts yet. Blocked websites will appear here with the time of each attempt.</div>`};
 const body=()=>`<div class=tabs role=tablist>${[["over","Overview"],["live","Live timeline"],["visits","Sites visited"],["web","Website rules"],["apps","Apps & games"],["time","Schedule"]].map(([k,t])=>`<button class="${k===tab?"act":""}" data-tab=${k} role=tab>${t}</button>`).join("")}</div>
 <div class=pane data-p=over ${tab!=="over"?"hidden":""}><div class=ov>${over()}</div></div>
 <div class=pane data-p=web ${tab!=="web"?"hidden":""}>
  <div class=sec><b>Blocked attempts</b><small>Newest first</small></div><div class=hits>${sitesLog()}</div>
  <div class=sec><b>Age profile</b>${lkt("adult")}</div><div class=seg>${[["child","Child · under 13"],["teen","Teen · 13 to 17"],["custom","Custom"]].map(([k,t])=>`<button type=button data-age=${k} class="${(c.ageGroup||"custom")===k?"act":""}" ${dis("adult")}>${t}</button>`).join("")}</div>
  <div class=sec><b>Content filters</b></div><div class=grid>${FILTERS.map(([f,t,s])=>tg(f,t,s,flt(f),f==="safe"?"browsers":"adult")).join("")}</div>
  <div class=sec><b>Always block these sites</b>${lkt("sites")}</div>${chipEd("sites")}
  <div class=sec><b>Always allow these sites</b></div>${chipEd("allowedSites")}
  <div class=sec><b>Blocked browsers</b>${lkt("browsers")}</div><div class=grid>${BR.map(b=>tg("br-"+b,b.replace(".exe",""),"Block this browser",(c.browsers||[]).includes(b),"browsers")).join("")}</div></div>
 <div class=pane data-p=apps ${tab!=="apps"?"hidden":""}>
  <div class=sec><b>Blocked apps</b>${lkt("apps")}</div>${chipEd("apps")}<div class=sec><b>Allowed app exceptions</b></div>${chipEd("allowedApps")}
  <div class=sec><b>Games</b>${lkt("games")}</div><div class=grid>${tg("bg","Block common games","Steam, Epic, Roblox, Minecraft and others",c.blockGames,"games")}</div>
  <div class=sec><b>Extra blocked games</b></div>${chipEd("blockedGames")}<div class=sec><b>Allowed games</b></div>${chipEd("allowedGames")}</div>
 <div class=pane data-p=time ${tab!=="time"?"hidden":""}><div class=sec><b>Daily limits and hours</b>${lkt("time")}</div><div class=fields>
  <label>Child's Windows username<input data-f=ch value="${esc(c.child||"")}" ${dis("time")}>${(J(d.status).accounts||[]).length&&!dis("time")?`<span class=row style="margin-top:6px"><small>Signed in on the PC:</small>${J(d.status).accounts.map(u=>`<button type=button class=gr data-acct="${esc(u)}" style="padding:4px 10px">${esc(u)}</button>`).join("")}</span>`:""}</label>
  <label>School days limit (min)<input data-f=li type=number min=0 value="${c.limit??120}" ${dis("time")}></label>
  <label>Weekend limit (min)<input data-f=lw type=number min=0 value="${c.limitWk??c.limit??120}" ${dis("time")}></label>
  <label>Allowed from<input data-f=st type=time value="${c.start||"07:00"}" ${dis("time")}></label><label>Allowed until<input data-f=en type=time value="${c.end||"21:00"}" ${dis("time")}></label></div>
  <div class=sec><b>Location</b>${lkt("location")}</div><div class=grid>${tg("loc","Share device location","Needs Windows Location Services",c.locationEnabled,"location")}</div></div>
 <div class=pane data-p=live ${tab!=="live"?"hidden":""}><div class=seg style="margin-bottom:10px">${[["all","Everything"],["web","Websites"],["block","Blocked"],["app","Apps"],["screen","Screen time"]].map(([k,t])=>`<button type=button data-tlf=${k} class="${k===tlf?"act":""}">${t}</button>`).join("")}</div><div class=tl>${timeline()}</div></div>
 <div class=pane data-p=visits ${tab!=="visits"?"hidden":""}><div class=row><input data-vq placeholder="Search websites" value="${esc(vq)}" aria-label="Search websites"><div class=seg style="flex:none">${[["all","All"],["blocked","Blocked only"]].map(([k,t])=>`<button type=button data-vsf=${k} class="${k===vsf?"act":""}">${t}</button>`).join("")}</div></div>
  <label class=tg style="margin:10px 0"><input type=checkbox data-bg ${showBg?"checked":""}><span class=sl></span><span class=tt><b>Show background services</b><small>Windows, Google and CDN lookups that are not sites the child chose</small></span></label><div class=vl>${visits()}</div></div>
 <div class=savebar><button data-q=save ${susp()?"disabled":""}>Save settings</button><span class=m role=status></span></div>`;
 el.innerHTML=`<div class=dhead><h3>${esc(d.name||"Child")}</h3></div><div class=pane data-h></div><div data-b></div>`;
 const $=s=>el.querySelector(s),H=$("[data-h]");
 const drawHead=()=>{H.innerHTML=head()};drawHead();$("[data-b]").innerHTML=body();
 const refreshLive=()=>{drawHead();$(".ov").innerHTML=over();$(".hits").innerHTML=sitesLog();$(".tl").innerHTML=timeline();$(".vl").innerHTML=visits()};
 const tick=()=>{if(!el.isConnected)return clearInterval(t);const {rem,lim}=calc(),tm=$("[data-timer]");if(tm&&!lockedNow()&&rem!=null){tm.textContent=clock(rem);const b=$("[data-bar]");if(b)b.style.width=Math.min(100,(lim*60-rem)/(lim*60)*100)+"%"}};
 const t=setInterval(tick,1000),t2=setInterval(()=>el.isConnected?refreshLive():clearInterval(t2),30000);
 el.refresh=nd=>{if(nd){d=nd;const n=J(d.cfg);for(const k of ["paused","unlockedUntil","bonus"])c[k]=n[k]}refreshLive()};
 const commit=async nc=>{try{c=nc;pending=Math.floor(Date.now()/1000);await save(nc,adm?{...a,paused:nc.paused,bonus:nc.bonus,unlockedUntil:nc.unlockedUntil,locked:L}:undefined);drawHead()}catch(e){pending=null;drawHead();$(".q").textContent="Failed: "+(e.code||e.message)}};
 const collect=()=>{const v=s=>$(`[data-f=${s}]`),ck=s=>v(s).checked,n={...c,...w};
  Object.assign(n,{blockGames:ck("bg"),browsers:BR.filter(b=>ck("br-"+b)),safeSearch:ck("safe"),adult:ck("adult"),gambling:ck("gambling"),social:ck("social"),proxy:ck("proxy"),locationEnabled:ck("loc"),child:v("ch").value.trim(),limit:+v("li").value,limitWk:+v("lw").value,start:v("st").value,end:v("en").value});return n};
 const addChip=(k,val)=>{val=val.trim().toLowerCase().replace(/^https?:\/\/|^www\.|\/.*$/g,"");if(k.includes("pps")||k.includes("ame"))val=val.replace(/^.*[\\/]/,"");if(val&&!w[k].includes(val))w[k].push(val)};
 const redrawChips=k=>{const box=el.querySelector(`.chips[data-k=${k}]`);box.outerHTML=chipEd(k);el.querySelector(`.chips[data-k=${k}] input`)?.focus()};
 const doSave=async()=>{const n=collect();let ac;if(adm)ac={...a,...n,locked:[...el.querySelectorAll("[data-l]:checked")].map(x=>x.dataset.l)};try{await save(n,ac);c=n;$(".m").textContent="Saved ✓ The device will pick this up shortly."}catch(err){$(".m").textContent="Failed: "+(err.code||err.message)}};
 el.addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
  if(b.dataset.tab){tab=b.dataset.tab;el.querySelectorAll("[data-tab]").forEach(x=>x.classList.toggle("act",x===b));el.querySelectorAll("[data-p]").forEach(p=>p.hidden=p.dataset.p!==tab);return}
  if(b.dataset.rm!==undefined){const k=b.closest(".chips").dataset.k;w[k]=w[k].filter(x=>x!==b.dataset.rm);redrawChips(k);return}
  if(b.dataset.age){const g=b.dataset.age;el.querySelectorAll("[data-age]").forEach(x=>x.classList.toggle("act",x===b));c.ageGroup=g;const p=PRESETS[g];if(p)for(const[f,v]of Object.entries(p)){const i=$(`[data-f=${f==="safeSearch"?"safe":f}]`);if(i)i.checked=v}return}
  if(b.dataset.acct){$("[data-f=ch]").value=b.dataset.acct;$(".m").textContent="Account selected. Press Save settings to start counting.";return}
  if(b.dataset.tlf){tlf=b.dataset.tlf;el.querySelectorAll("[data-tlf]").forEach(x=>x.classList.toggle("act",x===b));$(".tl").innerHTML=timeline();return}
  if(b.dataset.vsf){vsf=b.dataset.vsf;el.querySelectorAll("[data-vsf]").forEach(x=>x.classList.toggle("act",x===b));$(".vl").innerHTML=visits();return}
  if(b.dataset.blk||b.dataset.unblk){const dom=b.dataset.blk||b.dataset.unblk;if(b.dataset.blk){addChip("sites",dom);w.allowedSites=w.allowedSites.filter(x=>x!==dom)}else{w.sites=w.sites.filter(x=>x!==dom)}redrawChips("sites");doSave().then(()=>{$(".vl").innerHTML=visits()});return}
  const q=b.dataset.q;if(q==="lock")commit({...c,paused:true,unlockedUntil:0});
  else if(q==="unlock"){const m=Number($("[data-q=unlock-min]").value);commit({...c,paused:false,unlockedUntil:m?Math.floor(Date.now()/1000)+m*60:Math.floor(Date.now()/1000)+86400*30})}
  else if(q==="extend"){const m=Number($("[data-q=extend-min]").value)||30,day=J(d.status).day||new Date().toLocaleDateString("sv"),p=c.bonus&&c.bonus.day===day?+c.bonus.min:0;commit({...c,bonus:{day,min:p+m}})}
  else if(q==="save")doSave()});
 el.addEventListener("input",e=>{if(e.target.dataset.vq!==undefined){vq=e.target.value;$(".vl").innerHTML=visits()}});
 el.addEventListener("change",e=>{if(e.target.dataset.bg!==undefined){showBg=e.target.checked;$(".vl").innerHTML=visits()}});
 el.addEventListener("toggle",e=>{const dm=e.target.dataset&&e.target.dataset.d;if(dm){e.target.open?open.add(dm):open.delete(dm)}},true);
 el.addEventListener("keydown",e=>{if(e.key==="Enter"&&e.target.dataset.add!==undefined){e.preventDefault();const k=e.target.closest(".chips").dataset.k;addChip(k,e.target.value);redrawChips(k)}});
 return el}
