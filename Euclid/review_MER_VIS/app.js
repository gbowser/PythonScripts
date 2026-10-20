'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (x,a,b) => Math.max(a, Math.min(b,x));
const finite = x => typeof x === 'number' && Number.isFinite(x);
const fmt = (x,n=2) => finite(x) ? x.toFixed(n) : '—';
const deg = x => finite(x) ? `${fmt(x)}°` : '—';
const median = values => {const a=values.filter(finite).sort((x,y)=>x-y),n=a.length;return n ? (a[Math.floor((n-1)/2)]+a[Math.floor(n/2)])/2 : null;};
const axialDifference = (a,b) => ((a-b+90)%180+180)%180-90;
function axialMean(values,weights){let x=0,y=0;values.forEach((a,i)=>{let w=weights?.[i]??1;x+=w*Math.cos(a*Math.PI/90);y+=w*Math.sin(a*Math.PI/90);});return values.length ? ((Math.atan2(y,x)*90/Math.PI)%180+180)%180 : null;}
function scatter(values){const mean=axialMean(values);return values.length ? Math.sqrt(values.reduce((s,v)=>s+axialDifference(v,mean)**2,0)/values.length) : null;}
const flagsLabel = {
 disc_PA_sparse_sampling:'Sparse disc sampling',disc_PA_unstable:'Disc PA varies across radius',
 disc_axis_ratio_unstable:'Changing disc ellipticity',small_bar_sensitive_to_resolution:'Small candidate bar interval',
 no_bar_detected:'No accepted bar; disc retained',weak_ellipse_bar_signature:'Class B bar-profile evidence',
 centre_offset_large:'Large centre offset',centre_unstable:'Centre changes across radius',
 relaxed_fit:'Relaxed fit recovery',disc_range_fallback:'Disc interval fallback',small_disc:'Small disc',
 bar_disc_ranges_close:'Disc and bar intervals close',iteration_limited_samples:'Iteration-limited samples',
 short_accepted_profile:'Short accepted profile',high_inclination:'High inclination',
 star_mask_removed:'Star mask removed in retry',neighbour_mask_removed:'Neighbour mask removed in retry'};
const S={boot:null,g:null,id:null,settings:null,pixels:null,imageMeta:null,calc:null,filtered:[],token:null,
 imageRequest:0,galaxyRequest:0,dirty:false,drag:null,imageAbort:null,view:null};
const fieldIds=['discMin','discMax','barMin','barMax','noBar','pool','minDisc','maxGap','paThreshold','epsThreshold','barThreshold','sparseEnabled','paEnabled','epsEnabled','smallBarEnabled'];
const displayIds=['stretch','minimum','maximum','gamma','invert','ellipses','centres','overlayMode','showRejected'];
const reviewIds=['discDecision','barDecision','centreDecision','ruleAction','notes'];
const clone = obj => JSON.parse(JSON.stringify(obj));

function showError(error){$('error').hidden=false;$('error').textContent=String(error.message??error);}
function clearError(){$('error').hidden=true;}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4200);}
async function api(url,options={}){const response=await fetch(url,options);const body=await response.json();if(!response.ok)throw new Error(body.error??response.statusText);return body;}
function storageKey(name){return `MER_VIS_${S.boot?.storage_key??'boot'}_${name}`;}
function drafts(){try{return JSON.parse(localStorage.getItem(storageKey('drafts'))??'{}');}catch{return {};}}
function saveDraft(){if(!S.g)return;const all=drafts();all[S.id]={settings:clone(S.settings),view:S.view,form:getForm()};localStorage.setItem(storageKey('drafts'),JSON.stringify(all));}
function markDirty(){S.dirty=true;$('saveStatus').textContent='Unsaved assessment / trial settings';saveDraft();}
function getForm(){return {disc_decision:$('discDecision').value,bar_decision:$('barDecision').value,centre_decision:$('centreDecision').value,rule_action:$('ruleAction').value,notes:$('notes').value};}
function setForm(form={}){form=form??{};$('discDecision').value=form.disc_decision??'not_assessed';$('barDecision').value=form.bar_decision??'not_assessed';$('centreDecision').value=form.centre_decision??'not_assessed';$('ruleAction').value=form.rule_action??'unsure';$('notes').value=form.notes??'';}

function defaultSettings(g){const b=g.intervals.bar;return {
 disc:[...(g.intervals.disc.every(finite)?g.intervals.disc:[.5,Math.max(1,...g.profile.map(p=>p.sma_arcsec??0))])],
 bar:[...(b.every(finite)?b:[.5,1.5])],editedDisc:false,editedBar:false,noBar:!b.every(finite),pool:'pipeline',
 rules:{...S.boot.rules,sparse_enabled:true,pa_enabled:true,eps_enabled:true,small_bar_enabled:true},
 display:{stretch:'asinh',minimum:null,maximum:null,gamma:1,invert:false,ellipses:true,centres:true,overlayMode:'selected',showRejected:true}};}

function queue(){let list=S.boot.sample;const category=$('category').value;if(category!=='all')list=list.filter(r=>r.category===category);if($('unreviewed').checked)list=list.filter(r=>!S.boot.reviews[r.object_id]);S.filtered=list;
 let html='',last='';for(const row of list){if(last!==row.category){html+=`<div class="queue-category">${esc(row.category_label)}</div>`;last=row.category;}const name=S.boot.catalogue.find(r=>r.object_id===row.object_id)?.name;html+=`<button class="queue-item ${S.id===row.object_id?'active':''}" data-id="${esc(row.object_id)}">${S.boot.reviews[row.object_id]?'<span class="tick">✓</span>':''}${esc(row.object_id)}${name?`<span class="name">${esc(name)}</span>`:''}</button>`;}
 $('queue').innerHTML=html||'<p class="small">No examples remain in this view.</p>';
 $('queue').querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>loadGalaxy(b.dataset.id));
 const n=S.boot.sample.filter(r=>S.boot.reviews[r.object_id]).length;$('progress').textContent=`${n} of ${S.boot.sample.length} sample galaxies reviewed`;
 const i=list.findIndex(r=>r.object_id===S.id);$('position').textContent=i>=0?`${i+1} / ${list.length} in this view`:'Additional galaxy';$('prev').disabled=i<=0;$('next').disabled=i<0||i>=list.length-1;
 reviewSummary();
}
function reviewSummary(){const rows=Object.entries(S.boot.categories).map(([key,name])=>{const sample=S.boot.sample.filter(r=>r.category===key),reviewed=sample.map(r=>S.boot.reviews[r.object_id]).filter(Boolean);let actions={};reviewed.forEach(r=>actions[r.rule_action]=(actions[r.rule_action]??0)+1);return `<tr><td>${esc(name)}</td><td>${reviewed.length} / ${sample.length}</td><td>${Object.entries(actions).map(([k,n])=>`${esc(k)}: ${n}`).join('; ')||'—'}</td></tr>`;});$('reviewSummary').innerHTML=`<table><thead><tr><th>Group</th><th>Reviewed</th><th>Rule suggestions</th></tr></thead><tbody>${rows.join('')}</tbody></table><p class="small">These purposively selected examples do not estimate percentages across all 2,777 galaxies.</p>`;}

async function loadGalaxy(id){saveDraft();clearError();const request=++S.galaxyRequest;try{
 $('galaxyTitle').textContent='Loading galaxy…';S.imageAbort?.abort();const g=await api('/api/galaxy?id='+encodeURIComponent(id));if(request!==S.galaxyRequest)return;
 S.id=id;S.g=g;S.pixels=null;S.imageMeta=null;S.dirty=false;S.settings=defaultSettings(g);
 const draft=drafts()[id],saved=g.review;if(saved?.settings)S.settings={...S.settings,...clone(saved.settings)};
 if(draft?.settings)S.settings={...S.settings,...clone(draft.settings)};
 S.view=draft?.view??saved?.settings?.view??[...g.default_window];
 setForm(draft?.form??saved);writeControls();
 $('galaxyTitle').textContent=`Galaxy ${id}`;$('galaxyName').textContent=g.name||'';
 const item=S.boot.sample.find(r=>r.object_id===id);$('reason').textContent=item?`${item.category_label} · ${item.selection_reason}`:'Additional galaxy outside the 48-example sample';
 $('originalFlags').textContent='Pipeline issues: '+(g.original.flags.map(f=>flagsLabel[f]??f).join(' · ')||'No counted geometry flags')+(g.original.information?' · Nearly face-on (informational)':'');
 $('saveStatus').textContent=saved?`Saved assessment: ${saved.reviewed_utc.replace('T',' ').replace('Z',' UTC')}`:'Exploration is not marked as reviewed until you save.';
 localStorage.setItem(storageKey('last_galaxy'),id);queue();recalculate();await loadImage(true);
 }catch(e){if(e.name!=='AbortError')showError(e);}}

function writeControls(){const s=S.settings,d=s.display,r=s.rules;
 for(const [id,value] of Object.entries({discMin:s.disc[0],discMax:s.disc[1],barMin:s.bar[0],barMax:s.bar[1]}))$(id).value=fmt(value,3);
 $('noBar').checked=s.noBar;$('pool').value=s.pool;
 for(const [id,key] of [['minDisc','min_disc'],['maxGap','max_gap'],['paThreshold','pa_rms'],['epsThreshold','eps_span'],['barThreshold','small_bar']])$(id).value=r[key];
 for(const [id,key] of [['sparseEnabled','sparse_enabled'],['paEnabled','pa_enabled'],['epsEnabled','eps_enabled'],['smallBarEnabled','small_bar_enabled']])$(id).checked=r[key]!==false;
 for(const id of displayIds){const el=$(id);if(el.type==='checkbox')el.checked=d[id]??true;else if(d[id]!=null)el.value=d[id];}
 $('gammaValue').value=Number(d.gamma).toFixed(2);$('barMin').disabled=$('barMax').disabled=s.noBar;
}
function readGeometryControls(changed){const s=S.settings;clearError();
 for(const kind of ['disc','bar'])if(changed===kind+'Min'||changed===kind+'Max'){const bounds=[...s[kind]];bounds[changed===kind+'Min'?0:1]=$(changed).valueAsNumber;if(!bounds.every(finite)||bounds[0]<0||bounds[1]<=bounds[0]){showError('Use finite, non-negative interval bounds with outer radius greater than inner radius.');return;}s[kind]=bounds;s['edited'+(kind==='disc'?'Disc':'Bar')]=true;}
 s.noBar=$('noBar').checked;s.pool=$('pool').value;
 for(const [id,key] of [['minDisc','min_disc'],['maxGap','max_gap'],['paThreshold','pa_rms'],['epsThreshold','eps_span'],['barThreshold','small_bar']]){const el=$(id);if(finite(el.valueAsNumber)){const value=clamp(el.valueAsNumber,Number(el.min),Number(el.max));s.rules[key]=value;el.value=value;}}
 for(const [id,key] of [['sparseEnabled','sparse_enabled'],['paEnabled','pa_enabled'],['epsEnabled','eps_enabled'],['smallBarEnabled','small_bar_enabled']])s.rules[key]=$(id).checked;
 $('barMin').disabled=$('barMax').disabled=s.noBar;markDirty();recalculate();}
function pool(){return S.g.profile.filter(p=>p.used_for_geometry||(S.settings.pool==='marginal'&&p.marginal));}
function selected(points,which){const s=S.settings;if(which==='bar'&&s.noBar)return [];const bounds=s[which];if(!bounds.every(finite)||bounds[1]<=bounds[0])return [];
 if(!s['edited'+(which==='disc'?'Disc':'Bar')]&&s.pool==='pipeline')return points.filter(p=>p['selected_'+which]);
 // Numeric controls display 0.001 arcsec; retain edge points that round to the entered boundary.
 return points.filter(p=>p.sma_arcsec>=bounds[0]-.00051&&p.sma_arcsec<=bounds[1]+.00051);}
function weightedPA(points){return points.length?axialMean(points.map(p=>p.pa_sky_deg),points.map(p=>1/Math.max(p.pa_error_deg??20,.3)**2)):null;}

function calculate(){const points=pool(),disc=selected(points,'disc'),bar=selected(points,'bar');let radii=disc.map(p=>p.sma_arcsec).sort((a,b)=>a-b);const span=radii.length?Math.max(...radii)-Math.min(...radii):0;
 const gap=radii.length>1?Math.max(...radii.slice(1).map((r,i)=>r-radii[i])):0,maxGap=span>0?gap/span:1;
 const q=disc.length?1-median(disc.map(p=>p.ellipticity)):null;
 const epsSpan=disc.length?Math.max(...disc.map(p=>p.ellipticity))-Math.min(...disc.map(p=>p.ellipticity)):null;
 const pa=weightedPA(disc),paScatter=scatter(disc.map(p=>p.pa_sky_deg));
 const faceOn=q!==null&&q>.9,r=S.settings.rules,sparse=disc.length<r.min_disc||span<=0||maxGap>r.max_gap;
 let issues=[];if(disc.length<3)issues.push('Fewer than three disc ellipses: no trial disc geometry');
 else if(faceOn)issues.push('Nearly face-on: PA ambiguity is informational');
 else if(r.sparse_enabled!==false&&sparse)issues.push('Sparse disc sampling');
 else if(r.pa_enabled!==false&&paScatter>r.pa_rms)issues.push('Disc PA varies across radius');
 if(r.eps_enabled!==false&&epsSpan>r.eps_span)issues.push('Changing disc ellipticity');
 const bpa=weightedPA(bar),bscatter=scatter(bar.map(p=>p.pa_sky_deg));let grade=null,drop=null,peak=null;
 if(bar.length){const sorted=[...bar].sort((a,b)=>a.sma_arcsec-b.sma_arcsec);const smooth=sorted.map((p,i)=>median(sorted.slice(Math.max(0,i-1),Math.min(sorted.length,i+2)).map(x=>x.ellipticity)));const idx=smooth.indexOf(Math.max(...smooth)),peakPoint=sorted[idx];peak=smooth[idx];
  const beyond=points.filter(p=>p.sma_arcsec>peakPoint.sma_arcsec&&p.sma_arcsec<=Math.max(2.5*peakPoint.sma_arcsec,peakPoint.sma_arcsec+1));
  if(beyond.length){drop=peak-Math.min(...beyond.map(p=>p.ellipticity));const twist=Math.max(...beyond.map(p=>Math.abs(axialDifference(p.pa_sky_deg,peakPoint.pa_sky_deg)))),offset=finite(pa)?Math.abs(axialDifference(bpa,pa)):0;
   if(bar.length>=3&&peak>=.2&&bscatter<=10&&(drop>=.08||(drop>=.04&&Math.max(twist,offset)>=10)))grade=drop>=.1&&bscatter<=5&&peak>=.3?'A-style':'B-style';}}
 const storedBar=!S.settings.editedBar&&S.settings.pool==='pipeline'&&S.g.original.bar_status.startsWith('detected_');
 if(storedBar&&!S.settings.noBar)grade=S.g.original.bar_status.endsWith('_A')?'A (stored)':'B (stored)';
 if(!S.settings.noBar){if(r.small_bar_enabled!==false&&S.settings.bar[1]<r.small_bar)issues.push('Small candidate feature: bar identification uncertain');if(!grade)issues.push('Selected bar interval does not pass the signature screen');else if(grade.startsWith('B'))issues.push('Weaker B-style bar-profile evidence');}
 // Leave-one-out spread describes sensitivity; it is not a confidence interval.
 const leaveOut=disc.length>=4?disc.map((p,i)=>weightedPA(disc.filter((_,j)=>j!==i))).map(x=>Math.abs(axialDifference(x,pa))):[];
 return {disc_pa:disc.length>=3?pa:null,bar_pa:!S.settings.noBar&&bar.length>=3?bpa:null,
  inclination:disc.length>=3?Math.acos(clamp(q,0,1))*180/Math.PI:null,n_disc:disc.length,n_bar:bar.length,
  pa_scatter:paScatter,eps_span:epsSpan,max_gap_fraction:maxGap,span_arcsec:span,axis_ratio:q,face_on:faceOn,
  sparse,issues,bar_grade:grade,bar_drop:drop,bar_peak:peak,bar_scatter:bscatter,
  leave_one_out_pa_change:leaveOut.length?Math.max(...leaveOut):null,disc,bar};}

function recalculate(){if(!S.g)return;S.calc=calculate();const c=S.calc,g=S.g;
 const rows=[['Disc PA',g.original.disc_pa,c.disc_pa,g.euclid.disc_pa,true],['Inclination',g.original.inclination,c.inclination,g.euclid.inclination,false],['Bar PA',g.original.bar_pa,c.bar_pa,null,true]];
 $('geometryTable').innerHTML=rows.map(([name,a,b,e,axial])=>`<tr><td>${name}</td><td>${deg(a)}</td><td>${deg(b)}</td><td>${name==='Bar PA'?'Not provided':deg(e)}</td><td>${finite(b)&&finite(e)?deg(axial?axialDifference(b,e):b-e):'—'}</td></tr>`).join('');
 const evidence=[['Accepted disc ellipses',c.n_disc],['PA RMS scatter',deg(c.pa_scatter)],['Ellipticity range',fmt(c.eps_span,3)],['Largest gap / span',`${fmt(c.max_gap_fraction*100,1)}%`],['Disc radial span',`${fmt(c.span_arcsec)}″`],['b/a',fmt(c.axis_ratio,3)],['Leave-one-out PA change',deg(c.leave_one_out_pa_change)],['Selected bar evidence',c.bar_grade??(S.settings.noBar?'No bar selected':'Not passed')],['Accepted bar ellipses',S.settings.noBar?'—':c.n_bar],['Bar PA scatter',S.settings.noBar?'—':deg(c.bar_scatter)],['Bar outer radius',S.settings.noBar?'—':`${fmt(S.settings.bar[1])}″ / ${fmt(S.settings.bar[1]/S.g.pixel_scale_arcsec,1)} native pixels`]];
 $('evidence').innerHTML=evidence.map(([k,v])=>`<div>${esc(k)}</div><strong>${esc(v)}</strong>`).join('');
 $('trialFlags').innerHTML=c.issues.length?c.issues.map(t=>`<span class="issue ${t.startsWith('Nearly')?'info':''}">${esc(t)}</span>`).join(''):'<span class="issue ok">None of these trial screens triggered</span>';
 $('poolNote').textContent=S.settings.pool==='marginal'?'Exploratory pool includes valid marginal candidates: stop 0/2, coverage ≥50%, ellipticity error <0.20, PA error <20°, positive intensity and a relaxed centre tolerance. Pink points were not pipeline-accepted. No ellipses are refitted.': 'Original intervals use stored pipeline selections. Edited intervals use accepted ellipses inside the new bounds; this may differ from the original brightness-based disc selection.';
 drawProfiles();drawImage();}

function plotMax(){const accepted=pool();return Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07;}
function drawProfiles(){for(const [id,field,maxY,title] of [['epsPlot','ellipticity',1,'Ellipticity ε = 1 − b/a'],['paPlot','pa_sky_deg',180,'Sky PA (degrees)']]){
 const w=660,h=215,left=48,right=18,top=22,bottom=36,pw=w-left-right,ph=h-top-bottom,xmax=plotMax();
 const x=v=>left+v/xmax*pw,y=v=>top+(1-v/maxY)*ph;let html='';
 for(const [kind,color] of [['bar','#f3bc62'],['disc','#86bf96']]){if(kind==='bar'&&S.settings.noBar)continue;const r=S.settings[kind];if(!r.every(finite))continue;html+=`<rect x="${x(r[0])}" y="${top}" width="${Math.max(0,x(r[1])-x(r[0]))}" height="${ph}" fill="${color}" opacity=".28"/>`;for(const edge of [0,1])html+=`<line x1="${x(r[edge])}" x2="${x(r[edge])}" y1="${top}" y2="${top+ph}" stroke="${kind==='disc'?'#348458':'#c17b19'}" stroke-width="${document.querySelector('input[name=editMode]:checked').value===kind?2:1}" opacity=".7"/>`;}
 for(let i=0;i<=4;i++){const vy=i/4*maxY;html+=`<line x1="${left}" x2="${w-right}" y1="${y(vy)}" y2="${y(vy)}" stroke="#dce5eb"/><text x="${left-8}" y="${y(vy)+4}" text-anchor="end">${maxY===1?vy.toFixed(2):Math.round(vy)}</text>`;const vx=i/4*xmax;html+=`<line x1="${x(vx)}" x2="${x(vx)}" y1="${top}" y2="${top+ph}" stroke="#e6edf1"/><text x="${x(vx)}" y="${top+ph+18}" text-anchor="middle">${vx.toFixed(xmax<3?2:1)}</text>`;}
 html+=`<text class="axis-title" x="${left}" y="14">${title}</text><text class="axis-title" x="${left+pw/2}" y="${h-2}" text-anchor="middle">Semi-major axis (arcsec)</text>`;
 const accepted=pool(),acceptedSet=new Set(accepted);let segments=[],current=[],previous=null;
 S.g.profile.forEach((p,i)=>{if(!acceptedSet.has(p)||!finite(p[field])||p.sma_arcsec>xmax){if(current.length)segments.push(current);current=[];previous=null;return;}if(previous&&field==='pa_sky_deg'&&Math.abs(p[field]-previous[field])>90){segments.push(current);current=[];}current.push(`${x(p.sma_arcsec)},${y(p[field])}`);previous=p;});if(current.length)segments.push(current);
 html+=segments.map(path=>`<polyline points="${path.join(' ')}" fill="none" stroke="#246f98" stroke-width="1.4"/>`).join('');
 for(const p of S.g.profile){const ok=acceptedSet.has(p);if((!ok&&!$('showRejected').checked)||!finite(p[field])||!finite(p.sma_arcsec)||p.sma_arcsec>xmax)continue;const color=ok?(p.used_for_geometry?'#246f98':'#b5598b'):'#a5adb2';html+=`<circle cx="${x(p.sma_arcsec)}" cy="${y(p[field])}" r="${ok?3.2:2.1}" fill="${color}"><title>${ok?'Accepted in this pool':'Excluded'}; radius ${fmt(p.sma_arcsec,3)} arcsec; ${field} ${fmt(p[field],3)}; PA error ${fmt(p.pa_error_deg)}°; stop ${p.stop_code}</title></circle>`;}
 html+=`<rect x="${left}" y="${top}" width="${pw}" height="${ph}" fill="none" stroke="#7e929f"/>`;
 $(id).innerHTML=html;$(id).dataset.xmax=xmax;}
}

function graphPointer(svg,event){const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;const x=point.matrixTransform(svg.getScreenCTM().inverse()).x;return clamp((x-48)/(660-48-18)*Number(svg.dataset.xmax),0,Number(svg.dataset.xmax));}
for(const id of ['epsPlot','paPlot']){const svg=$(id);svg.onpointerdown=e=>{if(!S.g)return;const kind=document.querySelector('input[name=editMode]:checked').value;if(kind==='bar'&&S.settings.noBar){toast('Uncheck “Treat as no convincing bar” to edit the bar interval.');return;}const x=graphPointer(svg,e),r=S.settings[kind];S.drag={kind,edge:Math.abs(x-r[0])<Math.abs(x-r[1])?0:1};svg.setPointerCapture(e.pointerId);moveGraph(svg,e);};svg.onpointermove=e=>{if(S.drag)moveGraph(svg,e);};svg.onpointerup=()=>{if(S.drag){S.drag=null;markDirty();}};svg.onpointercancel=()=>S.drag=null;}
function moveGraph(svg,e){const {kind,edge}=S.drag,r=S.settings[kind],value=graphPointer(svg,e);r[edge]=edge===0?Math.min(value,r[1]-.005):Math.max(value,r[0]+.005);S.settings['edited'+(kind==='disc'?'Disc':'Bar')]=true;$(kind+'Min').value=fmt(r[0],3);$(kind+'Max').value=fmt(r[1],3);recalculate();}

let offscreen=document.createElement('canvas'),renderPending=false;
function scheduleImage(){if(renderPending)return;renderPending=true;requestAnimationFrame(()=>{renderPending=false;stretchPixels();drawImage();});}
function stretchPixels(){if(!S.pixels)return;const m=S.imageMeta,d=S.settings.display,low=Number(d.minimum),high=Number(d.maximum),range=high-low;if(!(range>0))return;
 offscreen.width=m.width;offscreen.height=m.height;let context=offscreen.getContext('2d'),image=context.createImageData(m.width,m.height),dest=image.data;
 const gamma=1/clamp(Number(d.gamma)||1,.2,3);for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++){const value=S.pixels[y*m.width+x],at=((m.height-1-y)*m.width+x)*4;if(!finite(value)){dest[at]=35;dest[at+1]=38;dest[at+2]=55;dest[at+3]=255;continue;}let v=clamp((value-low)/range,0,1);if(d.stretch==='log')v=Math.log1p(99*v)/Math.log(100);else if(d.stretch==='asinh')v=Math.asinh(10*v)/Math.asinh(10);v=v**gamma;if(d.invert)v=1-v;const c=Math.round(v*255);dest[at]=dest[at+1]=dest[at+2]=c;dest[at+3]=255;}
 context.putImageData(image,0,0);}

function imageTransform(){const canvas=$('image'),rect=canvas.getBoundingClientRect(),view=S.imageMeta?.bounds??S.view;if(!view)return null;const ratio=(view[1]-view[0])/(view[3]-view[2]);let w=rect.width,h=w/ratio;if(h>rect.height){h=rect.height;w=h*ratio;}const left=(rect.width-w)/2,top=(rect.height-h)/2;return {w,h,left,top,rect,view,x:v=>left+(v-view[0])/(view[1]-view[0])*w,y:v=>top+(view[3]-v)/(view[3]-view[2])*h};}
function drawImage(){const canvas=$('image'),rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;if(canvas.width!==Math.round(rect.width*dpr)||canvas.height!==Math.round(rect.height*dpr)){canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);}const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#111b23';ctx.fillRect(0,0,rect.width,rect.height);if(!S.pixels||!S.g)return;const t=imageTransform();ctx.imageSmoothingEnabled=true;ctx.drawImage(offscreen,t.left,t.top,t.w,t.h);ctx.save();ctx.beginPath();ctx.rect(t.left,t.top,t.w,t.h);ctx.clip();
 if(S.settings.display.ellipses){const disc=new Set(S.calc.disc),bar=new Set(S.calc.bar);let points=pool().filter(p=>S.settings.display.overlayMode==='accepted'||disc.has(p)||bar.has(p));const stride=Math.max(1,Math.ceil(points.length/50));points=points.filter((p,i)=>i%stride===0||disc.has(p)||bar.has(p));for(const p of points){if(!finite(p.x_original_pix)||!finite(p.y_original_pix)||!finite(p.pa_pixel_deg))continue;const a=p.sma_arcsec/S.g.pixel_scale_arcsec,rx=a*t.w/(t.view[1]-t.view[0]),ry=rx*(1-p.ellipticity);ctx.beginPath();ctx.ellipse(t.x(p.x_original_pix),t.y(p.y_original_pix),Math.max(.1,rx),Math.max(.1,ry),-p.pa_pixel_deg*Math.PI/180,0,Math.PI*2);ctx.strokeStyle=disc.has(p)?'#65d095':bar.has(p)?'#ffc35d':'#65c6db';ctx.lineWidth=1.1;ctx.stroke();}}
 if(S.settings.display.centres){for(const [centre,color,cross] of [[S.g.catalogue_centre,'white',true],[S.g.centre,'#ff5d5d',false]]){if(!centre.every(finite))continue;const x=t.x(centre[0]),y=t.y(centre[1]),r=5;ctx.beginPath();if(cross){ctx.moveTo(x-r,y-r);ctx.lineTo(x+r,y+r);ctx.moveTo(x-r,y+r);ctx.lineTo(x+r,y-r);}else{ctx.moveTo(x-r,y);ctx.lineTo(x+r,y);ctx.moveTo(x,y-r);ctx.lineTo(x,y+r);}ctx.strokeStyle=color;ctx.lineWidth=1.7;ctx.stroke();}}
 // Native WCS compass, never a forced image rotation.
 const anchor=[t.left+45,t.top+t.h-45];ctx.strokeStyle='white';ctx.fillStyle='white';ctx.font='12px Segoe UI';for(const label of ['N','E']){const v=S.g.compass[label],dx=v[0]*27,dy=-v[1]*27;ctx.beginPath();ctx.moveTo(...anchor);ctx.lineTo(anchor[0]+dx,anchor[1]+dy);ctx.stroke();ctx.fillText(label,anchor[0]+dx*1.25-4,anchor[1]+dy*1.25+4);}
 const span=(t.view[1]-t.view[0])*S.g.pixel_scale_arcsec,target=span*.23,power=10**Math.floor(Math.log10(target)),scale=[1,2,5,10].map(x=>x*power).filter(x=>x<=target).pop()??power,px=scale/S.g.pixel_scale_arcsec*t.w/(t.view[1]-t.view[0]);ctx.beginPath();ctx.moveTo(t.left+t.w-20-px,t.top+t.h-22);ctx.lineTo(t.left+t.w-20,t.top+t.h-22);ctx.stroke();ctx.textAlign='center';ctx.fillText(`${scale<1?scale.toFixed(2):scale.toFixed(scale<3?1:0)}″`,t.left+t.w-20-px/2,t.top+t.h-29);ctx.restore();}

async function loadImage(newGalaxy=false){if(!S.g)return;const request=++S.imageRequest,id=S.id;S.imageAbort?.abort();const abort=new AbortController();S.imageAbort=abort;$('imageLoading').hidden=false;try{const q=new URLSearchParams({id,x0:S.view[0],x1:S.view[1],y0:S.view[2],y1:S.view[3]});const response=await fetch('/api/image?'+q,{signal:abort.signal});if(!response.ok){const body=await response.json();throw new Error(body.error);}const meta=JSON.parse(response.headers.get('X-Image-Meta')),buffer=await response.arrayBuffer();if(request!==S.imageRequest||id!==S.id)return;S.imageMeta=meta;S.pixels=new Float32Array(buffer);S.view=[...meta.bounds];if(newGalaxy&&(!finite(S.settings.display.minimum)||!finite(S.settings.display.maximum)))applyPreset('faint',false);else{stretchPixels();drawImage();}
 $('imageInfo').textContent=meta.factor===1?'Native pixels':`${meta.factor}× ${meta.method}`;
 }catch(e){if(e.name!=='AbortError')showError(e);}finally{if(request===S.imageRequest)$('imageLoading').hidden=true;}}
function applyPreset(name,dirty=true){if(!S.imageMeta)return;const s=S.imageMeta.stats,d=S.settings.display;d.minimum=s.median-s.noise;d.maximum=name==='faint'?s.median+15*s.noise:name==='core'?Math.max(s.percentiles.p999,s.median+30*s.noise):Math.max(s.percentiles.p995,s.median+15*s.noise);d.stretch=name==='core'?'log':'asinh';d.gamma=1;writeControls();stretchPixels();drawImage();if(dirty)saveDraft();}
function fitWindow(view){const [ny,nx]=S.g.shape;let w=clamp(view[1]-view[0],8,nx),h=clamp(view[3]-view[2],8,ny),x=clamp((view[0]+view[1])/2,w/2-.5,nx-.5-w/2),y=clamp((view[2]+view[3])/2,h/2-.5,ny-.5-h/2);return [x-w/2,x+w/2,y-h/2,y+h/2];}
function zoom(factor,anchor){if(!S.g)return;const v=S.imageMeta?.bounds??S.view,x=anchor?.[0]??(v[0]+v[1])/2,y=anchor?.[1]??(v[2]+v[3])/2;S.view=fitWindow([x+(v[0]-x)*factor,x+(v[1]-x)*factor,y+(v[2]-y)*factor,y+(v[3]-y)*factor]);clearTimeout(zoom.timer);zoom.timer=setTimeout(()=>{loadImage();saveDraft();},80);}
const canvas=$('image');let pan=null;
canvas.onwheel=e=>{e.preventDefault();const t=imageTransform();if(!t)return;const px=e.clientX-t.rect.left,py=e.clientY-t.rect.top;const anchor=[t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2])];zoom(e.deltaY>0?1.35:1/1.35,anchor);};
canvas.onpointerdown=e=>{if(!S.imageMeta)return;pan={x:e.clientX,y:e.clientY,view:[...S.imageMeta.bounds],transform:imageTransform()};canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{const t=imageTransform();if(!t||!S.pixels)return;const px=e.clientX-t.rect.left,py=e.clientY-t.rect.top,x=t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),y=t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2]);const ix=Math.floor((x-t.view[0])/(t.view[1]-t.view[0])*S.imageMeta.width),iy=Math.floor((y-t.view[2])/(t.view[3]-t.view[2])*S.imageMeta.height);if(ix>=0&&ix<S.imageMeta.width&&iy>=0&&iy<S.imageMeta.height){const value=S.pixels[iy*S.imageMeta.width+ix];$('pixelValue').textContent=`x ${x.toFixed(1)}, y ${y.toFixed(1)} · ${finite(value)?value.toPrecision(5):'masked'} ${S.g.units}`;}};
canvas.onpointerup=e=>{if(!pan)return;const dx=(e.clientX-pan.x)/pan.transform.w*(pan.view[1]-pan.view[0]),dy=(e.clientY-pan.y)/pan.transform.h*(pan.view[3]-pan.view[2]);if(Math.abs(e.clientX-pan.x)+Math.abs(e.clientY-pan.y)>4){S.view=fitWindow([pan.view[0]-dx,pan.view[1]-dx,pan.view[2]+dy,pan.view[3]+dy]);loadImage();saveDraft();}pan=null;};canvas.onpointercancel=()=>pan=null;

async function saveReview(next=false){if(!S.g)return;clearError();try{const calculation={...S.calc};delete calculation.disc;delete calculation.bar;const payload={object_id:S.id,...getForm(),settings:{...S.settings,view:S.view},calculation};$('save').disabled=$('saveNext').disabled=true;const result=await api('/api/review',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify(payload)});S.boot.reviews[S.id]=result.review;S.dirty=false;const all=drafts();delete all[S.id];localStorage.setItem(storageKey('drafts'),JSON.stringify(all));$('saveStatus').textContent='Review saved to disk';toast(result.warning??'Review saved');const current=S.id,index=S.filtered.findIndex(r=>r.object_id===current),nextId=S.filtered[index+1]?.object_id;queue();if(next){const target=$('unreviewed').checked?S.filtered[0]?.object_id:nextId;if(target)await loadGalaxy(target);else toast('You reached the end of this review group.');}}catch(e){showError(e);}finally{$('save').disabled=$('saveNext').disabled=false;}}

for(const id of fieldIds)$(id).onchange=()=>readGeometryControls(id);
for(const id of displayIds)$(id).oninput=()=>{if(!S.settings)return;const el=$(id),d=S.settings.display;d[id]=el.type==='checkbox'?el.checked:el.type==='number'||el.type==='range'?el.valueAsNumber:el.value;if(id==='showRejected')drawProfiles();else if(['ellipses','centres','overlayMode'].includes(id))drawImage();else scheduleImage();$('gammaValue').value=Number(d.gamma).toFixed(2);saveDraft();};
for(const id of reviewIds)$(id).oninput=markDirty;
document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>applyPreset(b.dataset.preset));
document.querySelectorAll('input[name=editMode]').forEach(r=>r.onchange=drawProfiles);
$('category').onchange=$('unreviewed').onchange=()=>{queue();if(!S.filtered.some(r=>r.object_id===S.id)&&S.filtered.length)loadGalaxy(S.filtered[0].object_id);};
$('prev').onclick=()=>{const i=S.filtered.findIndex(r=>r.object_id===S.id);if(i>0)loadGalaxy(S.filtered[i-1].object_id);};$('next').onclick=()=>{const i=S.filtered.findIndex(r=>r.object_id===S.id);if(i>=0&&i<S.filtered.length-1)loadGalaxy(S.filtered[i+1].object_id);};
$('resetGeometry').onclick=()=>{const defaults=defaultSettings(S.g);Object.assign(S.settings,{disc:defaults.disc,bar:defaults.bar,noBar:defaults.noBar,editedDisc:false,editedBar:false,pool:'pipeline'});writeControls();markDirty();recalculate();};
$('zoomIn').onclick=()=>zoom(.65);$('zoomOut').onclick=()=>zoom(1.5);$('galaxyView').onclick=()=>{S.view=[...S.g.default_window];loadImage();saveDraft();};$('fullView').onclick=()=>{S.view=[-.5,S.g.shape[1]-.5,-.5,S.g.shape[0]-.5];loadImage();saveDraft();};
$('save').onclick=()=>saveReview();$('saveNext').onclick=()=>saveReview(true);
$('search').oninput=()=>{const q=$('search').value.trim().toLowerCase();const matches=q.length>=3?S.boot.catalogue.filter(r=>r.object_id.includes(q)||r.name.toLowerCase().includes(q)).slice(0,12):[];$('searchResults').innerHTML=matches.map(r=>`<button data-id="${esc(r.object_id)}">${esc(r.name||r.object_id)}${r.name?` · ${esc(r.object_id)}`:''}</button>`).join('');$('searchResults').querySelectorAll('button').forEach(b=>b.onclick=()=>loadGalaxy(b.dataset.id));};
$('stop').onclick=async()=>{if(!confirm('Stop the local review server? Saved reviews remain on disk.'))return;try{await api('/api/stop',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:'{}'});toast('Server stopped. Double-click Start MER VIS Review to reopen.');}catch(e){showError(e);}};
window.addEventListener('resize',()=>{drawImage();});window.addEventListener('beforeunload',saveDraft);
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();saveReview(true);}else if(!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){if(e.key==='ArrowRight')$('next').click();if(e.key==='ArrowLeft')$('prev').click();}});

async function start(){try{S.boot=await api('/api/bootstrap');S.token=S.boot.token;for(const [value,label] of Object.entries(S.boot.categories))$('category').add(new Option(label,value));$('outputPath').textContent='Saved locally in: '+S.boot.output;if(S.boot.sample_source_changed)toast('The source manifest has changed since this sample was selected. Review provenance is retained.');queue();const remembered=localStorage.getItem(storageKey('last_galaxy')),id=S.boot.catalogue.some(r=>r.object_id===remembered)?remembered:S.boot.sample.find(r=>!S.boot.reviews[r.object_id])?.object_id??S.boot.sample[0].object_id;await loadGalaxy(id);}catch(e){showError(e);}}
// Exposed for repeatable numerical verification; no filesystem or pipeline mutations.
window.MER_VIS_REVIEW={state:S,calculate,axialMean,axialDifference,scatter,loadGalaxy};
start();
