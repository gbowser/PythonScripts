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
// Rational midtones transfer, shared with the earlier PixInsight-style viewer.
function midtonesTransfer(m,x){m=clamp(m,Number.EPSILON,1-Number.EPSILON);x=clamp(x,0,1);if(x<=0)return 0;if(x>=1)return 1;return ((m-1)*x)/((2*m-1)*x-m);}
function autoSTFParameters(stats,shadows=-2.8,target=.25){
 const minimum=stats.minimum,maximum=stats.maximum,span=maximum-minimum;
 if(!(span>Number.EPSILON))return {minimum,maximum:minimum+1,midtones:.5,constant:true};
 const centre=(stats.median-minimum)/span,sigma=stats.robust_sigma/span;
 const black=clamp(centre+clamp(shadows,-20,0)*sigma,0,1);
 const medianAfterBlack=clamp((centre-black)/Math.max(1-black,Number.EPSILON),0,1);
 return {minimum:minimum+black*span,maximum,midtones:midtonesTransfer(clamp(target,.01,.99),medianAfterBlack),constant:false};
}
function autoSTFValue(value,p){return p.constant?0:midtonesTransfer(p.midtones,(value-p.minimum)/Math.max(p.maximum-p.minimum,Number.EPSILON));}
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
const fieldIds=['discMin','discMax','barMin','barMax','noBar','pool','minDisc','maxGap','paThreshold','epsThreshold','barThreshold','sparseEnabled','paEnabled','epsEnabled','smallBarEnabled','centreEnabled','centreCap','centreFraction','centreFloor'];
const displayIds=['stretch','minimum','maximum','gamma','invert','ellipses','centres','overlayMode','excludedEllipses','paComparison','showRejected','showWarnings','unwrapPA','stfShadows','stfTarget'];
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

function resetGalaxyOverlays(settings){Object.assign(settings.display,{ellipses:false,excludedEllipses:false,paComparison:false,overlayMode:'selected',centres:true,showWarnings:false});}
function defaultSettings(g){const b=g.intervals.bar;return {
 disc:[...(g.intervals.disc.every(finite)?g.intervals.disc:[.5,Math.max(1,...g.profile.map(p=>p.sma_arcsec??0))])],
 bar:[...(b.every(finite)?b:[.5,1.5])],editedDisc:false,editedBar:false,noBar:!b.every(finite),pool:'pipeline',
 rules:{...S.boot.rules,sparse_enabled:true,pa_enabled:true,eps_enabled:true,small_bar_enabled:true,centre_enabled:g.centre_reference?.policy_enabled_default??!!g.centre_reference,centre_cap_native:3,centre_fraction:.05,centre_floor_native:1},
 display:{defaultVersion:2,stretch:'autostf',minimum:null,maximum:null,gamma:1,invert:false,ellipses:false,centres:true,excludedEllipses:false,paComparison:false,overlayMode:'selected',showRejected:true,showWarnings:false,unwrapPA:true,stfShadows:-2.8,stfTarget:.25}};}

const isReviewed = review => !!review && review.reviewed!==false;
function queue(){let list=S.boot.sample;const category=$('category').value;if(category!=='all')list=list.filter(r=>r.category===category);if($('unreviewed').checked)list=list.filter(r=>!isReviewed(S.boot.reviews[r.object_id]));S.filtered=list;
 let html='',last='';for(const row of list){if(last!==row.category){html+=`<div class="queue-category">${esc(row.category_label)}</div>`;last=row.category;}const name=S.boot.catalogue.find(r=>r.object_id===row.object_id)?.name;html+=`<div class="queue-row ${S.id===row.object_id?'active':''}"><button class="queue-item" data-id="${esc(row.object_id)}">${esc(row.object_id)}${name?`<span class="name">${esc(name)}</span>`:''}</button><input class="review-tick" type="checkbox" data-review-id="${esc(row.object_id)}" aria-label="Reviewed galaxy ${esc(row.object_id)}" title="Mark reviewed; untick to undo review status (notes are retained)" ${isReviewed(S.boot.reviews[row.object_id])?'checked':''}></div>`;}
 $('queue').innerHTML=html||'<p class="small">No examples remain in this view.</p>';
 $('queue').querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>loadGalaxy(b.dataset.id));
 $('queue').querySelectorAll('[data-review-id]').forEach(b=>b.onchange=()=>setReviewed(b.dataset.reviewId,b.checked,b));
 const n=S.boot.sample.filter(r=>isReviewed(S.boot.reviews[r.object_id])).length;$('progress').textContent=`${n} of ${S.boot.sample.length} sample galaxies reviewed`;
 const i=list.findIndex(r=>r.object_id===S.id);$('position').textContent=i>=0?`${i+1} / ${list.length} in this view`:'Additional galaxy';$('prev').disabled=i<=0;$('next').disabled=i<0||i>=list.length-1;
 reviewSummary();
}
function reviewSummary(){const rows=Object.entries(S.boot.categories).map(([key,name])=>{const sample=S.boot.sample.filter(r=>r.category===key),reviewed=sample.map(r=>S.boot.reviews[r.object_id]).filter(isReviewed);let actions={};reviewed.forEach(r=>actions[r.rule_action]=(actions[r.rule_action]??0)+1);return `<tr><td>${esc(name)}</td><td>${reviewed.length} / ${sample.length}</td><td>${Object.entries(actions).map(([k,n])=>`${esc(k)}: ${n}`).join('; ')||'—'}</td></tr>`;});$('reviewSummary').innerHTML=`<table><thead><tr><th>Group</th><th>Reviewed</th><th>Rule suggestions</th></tr></thead><tbody>${rows.join('')}</tbody></table><p class="small">These purposively selected examples do not estimate percentages across all 2,777 galaxies.</p>`;}

async function loadGalaxy(id,requestedRefit=undefined){saveDraft();clearError();const request=++S.galaxyRequest;try{
 $('galaxyTitle').textContent='Loading galaxy…';S.imageAbort?.abort();let g=await api('/api/galaxy?id='+encodeURIComponent(id));const draftBefore=drafts()[id],savedBefore=g.review;const refitId=requestedRefit!==undefined?requestedRefit:(draftBefore?.settings?.refit_id??savedBefore?.settings?.refit_id??JSON.parse(localStorage.getItem(storageKey('refits'))??'{}')[id]??g.latest_refit_id);if(refitId)g=await api('/api/galaxy?id='+encodeURIComponent(id)+'&refit='+encodeURIComponent(refitId));if(request!==S.galaxyRequest)return;
 S.id=id;S.g=g;S.drag=null;S.profileAxisFloor=null;S.pixels=null;S.imageMeta=null;S.dirty=false;S.settings=defaultSettings(g);
 const draft=drafts()[id],saved=g.review;if(saved?.settings)S.settings={...S.settings,...clone(saved.settings)};
 if(draft?.settings)S.settings={...S.settings,...clone(draft.settings)};
 const centreDefaults=defaultSettings(g).rules;S.settings.rules={...centreDefaults,...S.settings.rules};if(g.centre_reference&&S.settings.centre_policy_version!=='MER_VIS_centre_policy_v3_pilot_2026-10-28'){S.settings.rules.centre_enabled=centreDefaults.centre_enabled;S.settings.centre_policy_version='MER_VIS_centre_policy_v3_pilot_2026-10-28';}
 const priorRefit=S.settings.refit_id??null;if(priorRefit!==(g.refit?.job_id??null)){const defaults=defaultSettings(g);for(const key of ['disc','bar','editedDisc','editedBar','noBar','pool'])S.settings[key]=defaults[key];}S.settings.refit_id=g.refit?.job_id??null;
 if(S.settings.display.defaultVersion!==2){S.settings.display={...S.settings.display,defaultVersion:2,stretch:'autostf',gamma:1};}
 S.view=draft?.view??saved?.settings?.view??[...g.default_window];
 resetGalaxyOverlays(S.settings);
 setForm(draft?.form??saved);writeControls();
 $('galaxyTitle').textContent=`Galaxy ${id}`;
 $('previousReviewPanel').hidden=!g.previous_review;$('previousReviewText').textContent=g.previous_review?`Previous review: disc ${g.previous_review.disc_decision}; bar ${g.previous_review.bar_decision}; centre ${g.previous_review.centre_decision}; rule ${g.previous_review.rule_action}. Notes: ${g.previous_review.notes||'(no note)'}`:'';
 $('diagnosticLink').hidden=!g.refit?.job_id||!g.diagnostic_available;if(g.refit?.job_id)$('diagnosticLink').href='/api/refit/diagnostic?job='+g.refit.job_id;$('galaxyName').textContent=g.name||'';
 const item=S.boot.sample.find(r=>r.object_id===id);$('reason').textContent=item?`${item.category_label} · ${item.selection_reason}`:'Additional galaxy outside the review sample';
 $('originalFlags').textContent=(g.refit?'CENTRE-CONSTRAINED TRIAL · ':'')+(g.original.status==='fit_failed'?`Failed fit: ${g.fit_error||'No adopted geometry'} · `:'Pipeline issues: ')+(g.original.flags.map(f=>flagsLabel[f]??f).join(' · ')||(g.original.status==='fit_failed'?'No adopted geometry':'No counted geometry flags'))+(g.original.information?' · Nearly face-on (informational)':'');
 $('saveStatus').textContent=isReviewed(saved)?`Saved assessment: ${saved.reviewed_utc.replace('T',' ').replace('Z',' UTC')}`:'Not marked reviewed. Save an assessment or tick the galaxy in the left list.';
 initCentreControls();localStorage.setItem(storageKey('last_galaxy'),id);queue();recalculate();expandProfileView(false);await loadImage(true);
 }catch(e){if(e.name!=='AbortError')showError(e);}}

function writeControls(){const s=S.settings,d=s.display,r=s.rules;
 for(const [id,value] of Object.entries({discMin:s.disc[0],discMax:s.disc[1],barMin:s.bar[0],barMax:s.bar[1]}))$(id).value=fmt(value,3);
 $('noBar').checked=s.noBar;$('pool').value=s.pool;
 for(const [id,key] of [['minDisc','min_disc'],['maxGap','max_gap'],['paThreshold','pa_rms'],['epsThreshold','eps_span'],['barThreshold','small_bar'],['centreCap','centre_cap_native'],['centreFraction','centre_fraction'],['centreFloor','centre_floor_native']])$(id).value=r[key];
 for(const [id,key] of [['sparseEnabled','sparse_enabled'],['paEnabled','pa_enabled'],['epsEnabled','eps_enabled'],['smallBarEnabled','small_bar_enabled'],['centreEnabled','centre_enabled']])$(id).checked=r[key]!==false;
 for(const id of displayIds){const el=$(id);if(el.type==='checkbox')el.checked=d[id]??true;else if(d[id]!=null)el.value=d[id];}
 $('stfShadows').value=d.stfShadows??-2.8;$('stfTarget').value=d.stfTarget??.25;
 $('stfControls').hidden=d.stretch!=='autostf';$('minimum').disabled=$('maximum').disabled=d.stretch==='autostf';
 $('gammaValue').value=Number(d.gamma).toFixed(2);$('barMin').disabled=$('barMax').disabled=s.noBar;
 const failed=S.g.original.status==='fit_failed';for(const id of ['discMin','discMax','pool','noBar','resetGeometry'])$(id).disabled=failed;if(failed)$('barMin').disabled=$('barMax').disabled=true;
}
function readGeometryControls(changed){const s=S.settings;clearError();
 for(const kind of ['disc','bar'])if(changed===kind+'Min'||changed===kind+'Max'){const bounds=[...s[kind]];bounds[changed===kind+'Min'?0:1]=$(changed).valueAsNumber;if(!bounds.every(finite)||bounds[0]<0||bounds[1]<=bounds[0]){showError('Use finite, non-negative interval bounds with outer radius greater than inner radius.');return;}s[kind]=bounds;s['edited'+(kind==='disc'?'Disc':'Bar')]=true;}
 s.noBar=$('noBar').checked;s.pool=$('pool').value;
 for(const [id,key] of [['minDisc','min_disc'],['maxGap','max_gap'],['paThreshold','pa_rms'],['epsThreshold','eps_span'],['barThreshold','small_bar'],['centreCap','centre_cap_native'],['centreFraction','centre_fraction'],['centreFloor','centre_floor_native']]){const el=$(id);if(finite(el.valueAsNumber)){const value=clamp(el.valueAsNumber,Number(el.min),Number(el.max));s.rules[key]=value;el.value=value;}}
 for(const [id,key] of [['sparseEnabled','sparse_enabled'],['paEnabled','pa_enabled'],['epsEnabled','eps_enabled'],['smallBarEnabled','small_bar_enabled'],['centreEnabled','centre_enabled']])s.rules[key]=$(id).checked;
 if(s.rules.centre_floor_native>s.rules.centre_cap_native){showError('Centre floor must not exceed the absolute cap.');return;}
 $('barMin').disabled=$('barMax').disabled=s.noBar;markDirty();recalculate();expandProfileView();}
function centrePointStatus(p,g=S.g,settings=S.settings){
 if(!g?.centre_reference)return {accepted:true,available:false};const ref=g.centre_reference,r=settings.rules??{},scale=g.pixel_scale_arcsec,cap=r.centre_cap_native??3,fraction=r.centre_fraction??.05,floor=r.centre_floor_native??1;
 const valid=[p.x_original_pix,p.y_original_pix,p.sma_arcsec,ref.x,ref.y,scale,cap,fraction,floor].every(finite)&&scale>0&&p.sma_arcsec>0&&cap>=floor;
 if(!valid)return {accepted:false,available:false,reason:'Centre/radius coordinates unavailable or centre floor exceeds cap'};
 const offset=Math.hypot(p.x_original_pix-ref.x,p.y_original_pix-ref.y),limit=Math.min(cap,Math.max(floor,fraction*p.sma_arcsec/scale));return {accepted:offset<=limit+1e-9,available:true,offset,offset_arcsec:offset*scale,limit,limit_arcsec:limit*scale,reason:`Centre displacement ${fmt(offset,3)} native px (${fmt(offset*scale,3)}″); limit ${fmt(limit,3)} native px (${fmt(limit*scale,3)}″)`};
}
function numericalPool(g=S.g,settings=S.settings){if(g.original.status==='fit_failed')return [];return g.profile.filter(p=>p.used_for_geometry||(g.centre_reference&&(settings.rules?.centre_enabled!==false||g.centre_reference.policy_enabled_default)&&p.numerically_accepted_strict)||(settings.pool==='marginal'&&(p.marginal||(g.centre_reference&&(settings.rules?.centre_enabled!==false||g.centre_reference.policy_enabled_default)&&p.numerically_accepted_relaxed))));}
function pool(){return numericalPool().filter(p=>S.settings.rules?.centre_enabled===false||centrePointStatus(p).accepted);}

function selected(points,which){const s=S.settings;if(which==='bar'&&s.noBar)return [];const bounds=s[which];if(!bounds.every(finite)||bounds[1]<=bounds[0])return [];
 if(!s['edited'+(which==='disc'?'Disc':'Bar')]&&s.pool==='pipeline')return points.filter(p=>p['selected_'+which]);
 // Numeric controls display 0.001 arcsec; retain edge points that round to the entered boundary.
 return points.filter(p=>p.sma_arcsec>=bounds[0]-.00051&&p.sma_arcsec<=bounds[1]+.00051);}
function weightedPA(points){return points.length?axialMean(points.map(p=>p.pa_sky_deg),points.map(p=>1/Math.max(p.pa_error_deg??20,.3)**2)):null;}

function calculate(){const points=pool(),disc=selected(points,'disc'),bar=selected(points,'bar');let radii=disc.map(p=>p.sma_arcsec).sort((a,b)=>a-b);const span=radii.length?Math.max(...radii)-Math.min(...radii):0;
 const gap=radii.length>1?Math.max(...radii.slice(1).map((r,i)=>r-radii[i])):0,maxGap=span>0?gap/span:1;
 const q=disc.length?1-median(disc.map(p=>p.ellipticity)):null;
 const epsSpan=disc.length?Math.max(...disc.map(p=>p.ellipticity))-Math.min(...disc.map(p=>p.ellipticity)):null;
 const paPoints=disc.filter(p=>finite(p.pa_sky_deg)),pa=weightedPA(paPoints),paScatter=scatter(disc.map(p=>p.pa_sky_deg));
 const faceOn=q!==null&&q>.9,r=S.settings.rules,sparse=disc.length<r.min_disc||span<=0||maxGap>r.max_gap;
 const rawPoints=numericalPool(),rejectedDisc=selected(rawPoints,'disc').filter(p=>!points.includes(p)),rejectedBar=selected(rawPoints,'bar').filter(p=>!points.includes(p));
 let issues=[];if(paPoints.length<3)issues.push(paPoints.length?'Fewer than three disc ellipses: Disc PA provisional; inclination requires three selected ellipses':'Fewer than three disc ellipses: no usable Disc PA');
 if(faceOn)issues.push('Nearly face-on: PA ambiguity is informational');
 if(!faceOn){if(disc.length>=3&&r.sparse_enabled!==false&&sparse)issues.push('Sparse disc sampling');if(paPoints.length>=3&&r.pa_enabled!==false&&paScatter>r.pa_rms)issues.push('Disc PA varies across radius');}
 if(S.g.campaign_case&&(S.g.campaign_case.reference_uncertain||S.g.centre_reference?.provenance?.includes('unverified')))issues.push('Centre reference unverified: visual confirmation required');
 if(rejectedDisc.length||rejectedBar.length)issues.push(`Ellipse centre displacement: ${new Set([...rejectedDisc,...rejectedBar]).size} selected-range samples excluded`);
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
 return {disc_pa:paPoints.length?pa:null,n_disc_pa:paPoints.length,disc_pa_provisional:paPoints.length>0&&paPoints.length<3,bar_pa:!S.settings.noBar&&bar.length>=3?bpa:null,
  inclination:disc.length>=3?Math.acos(clamp(q,0,1))*180/Math.PI:null,n_disc:disc.length,n_bar:bar.length,
  centre_rejected_disc:rejectedDisc,centre_rejected_bar:rejectedBar,pa_scatter:paScatter,eps_span:epsSpan,max_gap_fraction:maxGap,span_arcsec:span,axis_ratio:q,face_on:faceOn,
  sparse,issues:S.g.original.status==='fit_failed'?['Fit failed: no adopted geometry; inspect the FITS image and failure reason']:issues,bar_grade:grade,bar_drop:drop,bar_peak:peak,bar_scatter:bscatter,
  leave_one_out_pa_change:leaveOut.length?Math.max(...leaveOut):null,disc,bar};}

function recalculate(){if(!S.g)return;S.calc=calculate();const c=S.calc,g=S.g;
 $('previousReviewHeader').hidden=!g.campaign_case;const base=g.pipeline_original??g.original;const rows=[['Disc PA',base.disc_pa,c.disc_pa,g.euclid.disc_pa,true],['Inclination',base.inclination,c.inclination,g.euclid.inclination,false],['Bar PA',base.bar_pa,c.bar_pa,null,true]];
 $('geometryTable').innerHTML=rows.map(([name,a,b,e,axial])=>`<tr><td>${name}</td><td>${deg(a)}</td>${g.campaign_case?`<td>${deg(g.previous_review?.calculation?.[name==='Disc PA'?'disc_pa':name==='Bar PA'?'bar_pa':'inclination'])}</td>`:''}<td>${deg(b)}${name==='Disc PA'&&c.disc_pa_provisional?` <span class="issue info" title="Based on ${c.n_disc_pa} usable selected ellipse(s)">Provisional: n=${c.n_disc_pa}</span>`:''}</td><td>${name==='Bar PA'?'Not provided':deg(e)}</td><td>${finite(b)&&finite(e)?deg(axial?axialDifference(b,e):b-e):'—'}</td></tr>`).join('');
 const evidence=[['Accepted disc ellipses',c.n_disc],['PA RMS scatter',c.n_disc_pa>=3?deg(c.pa_scatter):'Not assessed (<3 PA samples)'],['Ellipticity range',fmt(c.eps_span,3)],['Largest gap / span',`${fmt(c.max_gap_fraction*100,1)}%`],['Disc radial span',`${fmt(c.span_arcsec)}″`],['b/a',fmt(c.axis_ratio,3)],['Leave-one-out PA change',deg(c.leave_one_out_pa_change)],['Selected bar evidence',c.bar_grade??(S.settings.noBar?'No bar selected':'Not passed')],['Accepted bar ellipses',S.settings.noBar?'—':c.n_bar],['Bar PA scatter',S.settings.noBar?'—':deg(c.bar_scatter)],['Bar outer radius',S.settings.noBar?'—':`${fmt(S.settings.bar[1])}″ / ${fmt(S.settings.bar[1]/S.g.pixel_scale_arcsec,1)} native pixels`]];
 evidence.push(['Centre reference provenance',g.centre_reference?.provenance??'Legacy fit reference'],['Centre screen',S.settings.rules.centre_enabled!==false?`Cap ${fmt(S.settings.rules.centre_cap_native??3)} native px; ${fmt((S.settings.rules.centre_fraction??.05)*100,1)}% of radius`:'Disabled for exploration'],['Adopted centre X / Y',g.centre.every(finite)?g.centre.map(v=>fmt(v)).join(' / ')+' native pixels':'Not adopted'],['Centre offset from catalogue',fmt(g.original.centre_offset)+'″'],['Centre scatter',fmt(g.original.centre_scatter)+'″'+(g.refit?.lock_centre?' (centre fixed)':'')],['Accepted / measured isophotes',`${g.original.n_good??'—'} / ${g.original.n_isophotes??'—'}`],['Disc PA error estimate',deg(g.original.disc_pa_error)],['Bar ellipticity drop',fmt(g.original.bar_eps_drop,3)],['Masked fitting pixels',finite(g.original.masked_fraction)?fmt(g.original.masked_fraction*100,1)+'%':'—'],['Fit binning',finite(g.original.binning)?g.original.binning+' native pixels per fit pixel':'—'],['Fit method',g.original.method||'—'],['Fit time',finite(g.original.calculation_seconds)?fmt(g.original.calculation_seconds,1)+' s':'—']);
 $('evidence').innerHTML=evidence.map(([k,v])=>`<div>${esc(k)}</div><strong>${esc(v)}</strong>`).join('');
 $('trialFlags').innerHTML=c.issues.length?c.issues.map(t=>`<span class="issue ${t.startsWith('Nearly')?'info':''}">${esc(t)}</span>`).join(''):'<span class="issue ok">None of these trial screens triggered</span>';
 $('poolNote').textContent=g.original.status==='fit_failed'?'No adopted disc or bar geometry. Any grey profile points are rejected or unadopted measurements; interval trials are disabled for failed fits. You can still explore the FITS light and save your assessment.':S.settings.pool==='marginal'?'Exploratory pool includes valid marginal candidates: stop 0/2, coverage ≥50%, ellipticity error <0.20, PA error <20°, positive intensity and the same centre acceptance rule. Pink points were not pipeline-accepted. No ellipses are refitted.': 'Original intervals use stored selections from the displayed fit. Edited intervals use accepted ellipses inside the new bounds; this may differ from the original brightness-based disc selection.';
 drawProfiles();drawImage();}

function radiusAxis(maximum){
 const target=maximum/6,power=10**Math.floor(Math.log10(target)),step=[1,2,5,10].map(v=>v*power).find(v=>v>=target),max=Math.ceil(maximum/step)*step,ticks=[];
 for(let i=0;i<=Math.round(max/step);i++)ticks.push(i*step);
 return {max,step,ticks,decimals:Math.max(0,-Math.floor(Math.log10(step)))};
}
function plotMax(){if(S.drag&&finite(S.drag.axisMax))return S.drag.axisMax;
 const accepted=S.g.original.status==='fit_failed'?S.g.profile.filter(p=>finite(p.sma_arcsec)):pool(),bounds=[...(S.settings.disc??[]),...(S.settings.noBar?[]:(S.settings.bar??[]))].filter(finite),base=radiusAxis(Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07).max;
 return Math.max(base,Math.ceil(Math.max(0,...bounds)/2)*2,S.profileAxisFloor??0);
}
// Choose equivalent PA values separated by 180 degrees for display only.
function profilePAView(profile,accepted,xmax,enabled=true,showRejected=true){
 const values=new Map(),set=new Set(accepted),valid=p=>finite(p.pa_sky_deg)&&finite(p.sma_arcsec)&&p.sma_arcsec<=xmax;
 const ordered=accepted.filter(valid).slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec);let previous=null,wrapped=false;
 for(const p of ordered){const raw=p.pa_sky_deg;if(previous&&Math.abs(raw-previous.pa_sky_deg)>90)wrapped=true;values.set(p,previous?values.get(previous)+axialDifference(raw,previous.pa_sky_deg):raw);previous=p;}
 const unwrapped=enabled&&wrapped;
 for(const p of profile.filter(valid)){
  if(!unwrapped){values.set(p,p.pa_sky_deg);continue;}
  if(set.has(p))continue;
  // Excluded measurements never determine the accepted curve's branch.
  let upper=ordered.findIndex(z=>z.sma_arcsec>=p.sma_arcsec),reference;
  if(upper<=0)reference=values.get(ordered[upper===-1?ordered.length-1:0]);
  else{const a=ordered[upper-1],b=ordered[upper],t=(p.sma_arcsec-a.sma_arcsec)/Math.max(b.sma_arcsec-a.sma_arcsec,1e-12);reference=values.get(a)+(values.get(b)-values.get(a))*t;}
  values.set(p,p.pa_sky_deg+180*Math.round((reference-p.pa_sky_deg)/180));
 }
 if(!unwrapped)return {values,unwrapped:false,min:0,max:180,ticks:[0,45,90,135,180]};
 const shown=profile.filter(p=>valid(p)&&(set.has(p)||showRejected)).map(p=>values.get(p));
 const low=Math.min(...shown),high=Math.max(...shown),mid=(low+high)/2,span=Math.max(30,high-low),pad=Math.max(3,span*.12);
 const target=(span+2*pad)/4,step=[5,10,15,20,30,45,60,90,180,360,720].find(v=>v>=target)??Math.ceil(target/180)*180;
 const min=Math.floor((mid-span/2-pad)/step)*step,max=Math.ceil((mid+span/2+pad)/step)*step,ticks=[];
 for(let v=min;v<=max+step*.01;v+=step)ticks.push(v);
 return {values,unwrapped:true,min,max,ticks};
}
function ellipseInclination(p){return finite(p.ellipticity)&&p.ellipticity>=0&&p.ellipticity<=1?Math.acos(1-p.ellipticity)*180/Math.PI:null;}
function paReferenceLevels(reference,min,max){if(!finite(reference))return [];const levels=[];for(let k=Math.ceil((min-reference)/180);k<=Math.floor((max-reference)/180);k++)levels.push(reference+180*k);return levels;}
function thresholdDescription(value,limit,unit='',digits=3){if(!finite(value)||!finite(limit))return 'Comparison unavailable';const gap=value-limit;return `${fmt(value,digits)}${unit} ${gap>0?'>':gap<0?'<':'='} ${fmt(limit,digits)}${unit}; ${fmt(Math.abs(gap),digits)}${unit} ${gap>0?'above':gap<0?'below':'at'} the threshold${limit>0?`; ${fmt(value/limit*100,1)}% of the limit`:''}`;}
function profileWarningEvidence(g,settings,c){
 if(!c||!Array.isArray(c.disc)||!Array.isArray(c.bar))return [];
 const issues=c.issues??[],has=text=>issues.some(v=>v.startsWith(text)),warnings=[],disc=c.disc,bar=c.bar,r=settings.rules;
 const add=(code,label,detail,points=[],active=false,status=null)=>warnings.push({code,label,detail,points,active,status:status??(active?'Active warning':'Comparison — no active warning')});
 if(has('Fit failed')){add('failed','No adopted fit',g.fit_error||'No reliable geometry was adopted. Empty profiles do not establish that the galaxy has no bar.',[],true);return warnings;}
 const valid=disc.filter(p=>finite(p.ellipticity));if(valid.length){const low=valid.reduce((a,b)=>a.ellipticity<b.ellipticity?a:b),high=valid.reduce((a,b)=>a.ellipticity>b.ellipticity?a:b);add('ellipticity','Disc ellipticity range',`Selected ε low ${fmt(low.ellipticity,3)}, high ${fmt(high.ellipticity,3)}. Δε = ${thresholdDescription(c.eps_span,r.eps_span)}. The double-headed arrow joins the selected high and low values; excluded samples do not set these extremes.`,[low,high],has('Changing disc ellipticity'),r.eps_enabled===false?'Screen disabled':null);}
 {const ordered=disc.slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec);let gap=[];for(let i=1;i<ordered.length;i++)if(!gap.length||ordered[i].sma_arcsec-ordered[i-1].sma_arcsec>gap[1].sma_arcsec-gap[0].sma_arcsec)gap=[ordered[i-1],ordered[i]];
 const active=has('Sparse disc sampling')||has('Fewer than three disc ellipses');
 add('sampling','Disc sampling',`${c.n_disc} selected ellipses versus a minimum of ${r.min_disc}: ${Math.abs(c.n_disc-r.min_disc)} ${c.n_disc<r.min_disc?'fewer than':c.n_disc>r.min_disc?'more than':'from'} the minimum. ${c.n_disc<3?'Fewer than 3: a provisional Disc PA is shown when a usable ellipse exists; inclination still requires three selected ellipses. ':''}Largest gap / selected span = ${thresholdDescription(c.max_gap_fraction*100,r.max_gap*100,'%',1)}. Largest internal gap ${gap.length?fmt(gap[1].sma_arcsec-gap[0].sma_arcsec)+'″':'not measurable'}; selected radial span ${fmt(c.span_arcsec)}″. The horizontal double-headed arrow spans the largest gap.`,disc,active,c.n_disc<3?'Provisional PA; inclination unavailable':c.face_on?'Informational — nearly face-on exemption':r.sparse_enabled===false?'Screen disabled':null);warnings.at(-1).gap=gap;}
 if(finite(c.pa_scatter)&&disc.length>=3){add('pa','Disc PA variation',`Axial RMS = ${thresholdDescription(c.pa_scatter,r.pa_rms,'°',2)}, from ${disc.length} selected ellipses. The high–low arrow shows the plotted PA range; the RMS test uses all selected samples around their unweighted axial mean. Range and RMS are different quantities.`,disc,has('Disc PA varies across radius'),c.face_on?'Informational — nearly face-on exemption':r.pa_enabled===false?'Screen disabled':null);warnings.at(-1).mean=axialMean(disc.map(p=>p.pa_sky_deg));}
 if(g.centre_reference){const raw=[...new Set([...selected(numericalPool(g,settings),'disc'),...selected(numericalPool(g,settings),'bar')])],rejected=[...new Set([...(c.centre_rejected_disc??[]),...(c.centre_rejected_bar??[])])];add('centre','Ellipse centre consistency',`${c.centre_rejected_disc?.length??0} disc and ${c.centre_rejected_bar?.length??0} bar samples in the selected intervals excluded. Reference: ${g.centre_reference.provenance}. Pilot cap ${fmt(r.centre_cap_native??3)} native px, fractional limit ${fmt((r.centre_fraction??.05)*100,1)}%, floor ${fmt(r.centre_floor_native??1)} native px. The displacement plot compares centres with the tolerance curve. An unverified or previously uncertain reference requires visual confirmation before adopting geometry. ${g.refit?.lock_centre?'These ellipse centres are fixed by constraint; zero drift does not independently validate the supplied centre or fitted shape.':''}`,rejected.length?rejected:raw,rejected.length>0||has('Centre reference unverified'),r.centre_enabled===false?'Screen disabled':null);}

 if(!settings.noBar&&settings.bar.every(finite)){
  const radius=settings.bar[1],delta=radius-r.small_bar;add('smallbar','Bar size',`Bar outer radius ${fmt(radius)}″; screen ${fmt(r.small_bar)}″; ${fmt(Math.abs(delta))}″ ${delta<0?'below':delta>0?'above':'at'} the minimum. This tests outer radius, not interval width; the horizontal arrow shows the outer radius from zero.`,bar,has('Small candidate feature'),r.small_bar_enabled===false?'Screen disabled':null);
  add('bar','Bar signature evidence',`Grade ${c.bar_grade??'not accepted'}; ${bar.length} selected bar ellipses (minimum 3); PA RMS ${fmt(c.bar_scatter)}° (common limit 10°); smoothed peak ε ${fmt(c.bar_peak,3)} (minimum 0.20); outward drop ${fmt(c.bar_drop,3)}. The common screen needs drop ≥0.08, or ≥0.04 plus a ≥10° outer PA change. Class A additionally needs peak ≥0.30, drop ≥0.10 and RMS ≤5°. Stored grades refer to the original fit; these selected-interval metrics do not independently rerun the original bar search.`,bar,has('Selected bar interval does not pass')||has('Weaker B-style'));
 }
 for(const w of warnings){
  if(w.code==='ellipticity')w.comparison=`Δε = ${thresholdDescription(c.eps_span,r.eps_span)}`;
  if(w.code==='sampling')w.comparison=`n = ${c.n_disc} (minimum ${r.min_disc}); gap = ${fmt(c.max_gap_fraction*100,1)}% (limit ${fmt(r.max_gap*100,1)}%)`;
  if(w.code==='pa')w.comparison=`RMS = ${thresholdDescription(c.pa_scatter,r.pa_rms,'°',2)}`;
  if(w.code==='smallbar')w.comparison=`Outer radius ${fmt(settings.bar[1])}″; minimum ${fmt(r.small_bar)}″`;
  if(w.code==='bar'){w.comparison=`Grade ${c.bar_grade??'not accepted'}; peak ε ${fmt(c.bar_peak,3)}; drop ${fmt(c.bar_drop,3)}; PA RMS ${fmt(c.bar_scatter)}°`;
   const ordered=bar.slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec),smooth=ordered.map((p,i)=>median(ordered.slice(Math.max(0,i-1),Math.min(ordered.length,i+2)).map(z=>z.ellipticity)));
   if(ordered.length){const peak=ordered[smooth.indexOf(Math.max(...smooth))],beyond=g.profile.filter(p=>numericalPool(g,settings).includes(p)&&(settings.rules?.centre_enabled===false||centrePointStatus(p,g,settings).accepted)&&p.sma_arcsec>peak.sma_arcsec&&p.sma_arcsec<=Math.max(2.5*peak.sma_arcsec,peak.sma_arcsec+1));if(beyond.length){w.peak={p:peak,eps:Math.max(...smooth)};w.low={p:beyond.reduce((a,b)=>a.ellipticity<b.ellipticity?a:b)};}}
  }
 }
 return warnings;
}
function relevantProfileDiagnostics(g,diagnostics,sample=[]){
 const example=sample.find(row=>row.object_id===g.object_id),code={ellipticity:'ellipticity',sparse:'sampling',variation:'pa',bar:'smallbar',failed:'failed',centre_priority:'centre',centre_control:'centre',centre_validation:'centre'}[example?.category];
 return diagnostics.filter(d=>d.active||d.code===code);
}
function storedWarningNotes(g){const messages={
 centre_offset_large:`Recorded centre offset from the catalogue: ${fmt(g.original.centre_offset)}″. Inspect the centre markers on the FITS image; an offset alone does not prove the fitted centre is wrong.`,
 centre_unstable:`Recorded radial centre scatter: ${fmt(g.original.centre_scatter)}″. Inspect the ellipse centres on the image; ellipticity and PA curves alone cannot establish centre stability.`,
 relaxed_fit:'The stored fit used relaxed acceptance. This is fitting provenance, not a radial jump. Point tooltips show fit validity, coverage and errors.',
 iteration_limited_samples:'The stored fit includes iteration-limited samples. These did not meet normal convergence; point tooltips identify stop code 2.',
 star_mask_removed:'A recovery fit removed the star mask. Inspect the FITS image for stellar contamination; a smooth profile does not exclude it.',
 neighbour_mask_removed:'A recovery fit removed the neighbour mask. Inspect the FITS image for neighbouring-source contamination.',
 disc_range_fallback:'The stored fit used a fallback disc interval. The green region shows the current interval; its physical identification needs visual review.',
 small_disc:'The stored disc was small. Inspect the angular radii and resolution before interpreting the geometry.',
 bar_disc_ranges_close:'The stored disc and bar intervals were close. Compare the orange and green boundaries and inspect where the bar ends.',
 short_accepted_profile:'The stored fit had a short accepted profile. Inspect the selected sample counts and radial coverage.',
 high_inclination:'The stored inclination was high. The inclination profile shows the current disc-shape proxy; projection effects need review.',
 no_bar_detected:'The stored pipeline did not adopt a bar. This is not proof that a bar is absent; inspect the orange interval and image.'};
 return (g.original.flags??[]).filter(flag=>messages[flag]).map(flag=>({label:flagsLabel[flag]??flag,detail:messages[flag]}));
}
function drawWarningGraphics(warnings,{id,x,y,value,top,ph,left,right,xmax,paView}){
 let out='';const ring=(p,color)=>{const v=value(p);if(!finite(v)||!finite(p.sma_arcsec)||p.sma_arcsec>xmax)return '';return `<circle class="warning-point" cx="${x(p.sma_arcsec)}" cy="${y(v)}" r="5.5" fill="none" stroke="${color}" stroke-width="1.8"/>`;};
 const arrow=(x1,y1,x2,y2,color,cls)=>{const dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy);if(len<1)return '';const ux=dx/len,uy=dy/len,size=Math.min(5,len/3),head=(px,py,d)=>`M ${px+ux*size*d-uy*3} ${py+uy*size*d+ux*3} L ${px} ${py} L ${px+ux*size*d+uy*3} ${py+uy*size*d-ux*3}`;return `<path class="${cls}" d="M ${x1} ${y1} L ${x2} ${y2} ${head(x1,y1,1)} ${head(x2,y2,-1)}" fill="none" stroke="${color}" stroke-width="1.8"/>`;};
 const note=(px,py,text,color)=>`<text x="${clamp(px,left+3,right-120)}" y="${clamp(py,top+45,top+ph-5)}" style="fill:${color};stroke:white;stroke-width:3px;paint-order:stroke;font-size:12px">${esc(text)}</text>`;
 for(const w of warnings){let mark='';const color=w.active?(w.code==='ellipticity'?'#b13b79':'#ad5b00'):'#376b7f';
  if(w.code==='ellipticity'&&(id==='epsPlot'||id==='incPlot')){const [low,high]=w.points,a=value(low),b=value(high);if(finite(a)&&finite(b)){const bx=clamp(Math.max(x(low.sma_arcsec),x(high.sma_arcsec))+12,left+8,right-10);mark+=w.points.map(p=>ring(p,color)+`<line x1="${x(p.sma_arcsec)}" x2="${bx}" y1="${y(value(p))}" y2="${y(value(p))}" stroke="${color}" stroke-dasharray="2 3"/>`).join('');mark+=arrow(bx,y(a),bx,y(b),color,'warning-range');mark+=note(bx+8,(y(a)+y(b))/2,id==='epsPlot'?`Δε = ${fmt(Math.abs(b-a),3)}`:`Δi = ${fmt(Math.abs(b-a))}°`,color);}}
  if(w.code==='centre'){mark+=w.points.map(p=>ring(p,'#cf3434')).join('');mark+=note(left+8,top+ph-48,`Centre-rejected: ${w.points.length}`,'#cf3434');}
  if(w.code==='sampling'){mark+=w.points.map(p=>ring(p,color)).join('');if(w.gap?.length){const [a,b]=w.gap;mark+=`<rect class="warning-gap" x="${x(a.sma_arcsec)}" y="${top+ph-10}" width="${Math.max(0,x(b.sma_arcsec)-x(a.sma_arcsec))}" height="9" fill="${color}" opacity="${w.active?.35:.12}"/>`;mark+=arrow(x(a.sma_arcsec),top+ph-5,x(b.sma_arcsec),top+ph-5,color,'sampling-gap-arrow');}mark+=note(left+8,top+ph-16,`Disc n=${w.points.length}; gap ${fmt(S.calc.max_gap_fraction*100,0)}%`,color);}
  if(w.code==='pa'&&id==='paPlot'){const measured=w.points.map(p=>({p,v:value(p)})).filter(z=>finite(z.v));if(measured.length){const low=measured.reduce((a,b)=>a.v<b.v?a:b),high=measured.reduce((a,b)=>a.v>b.v?a:b),bx=clamp(Math.max(x(low.p.sma_arcsec),x(high.p.sma_arcsec))+12,left+8,right-10);mark+=arrow(bx,y(low.v),bx,y(high.v),color,'pa-range-arrow')+note(bx+8,(y(low.v)+y(high.v))/2,`ΔPA = ${fmt(high.v-low.v)}°`,color);}for(const p of w.points){const v=value(p);if(!finite(v))continue;const mean=w.mean+180*Math.round((v-w.mean)/180);mark+=ring(p,color)+`<line class="warning-pa-residual" x1="${x(p.sma_arcsec)}" x2="${x(p.sma_arcsec)}" y1="${y(v)}" y2="${y(clamp(mean,paView.min,paView.max))}" stroke="${color}" stroke-width="1.7"/>`;}mark+=note(left+8,top+ph-16,`Disc PA RMS ${fmt(S.calc.pa_scatter)}°`,color);}
  if((w.code==='smallbar'||w.code==='bar')&&(id==='epsPlot'||id==='paPlot')){const bounds=S.settings.bar,start=x(clamp(bounds[0],0,xmax)),end=x(clamp(bounds[1],0,xmax));mark+=`<rect class="warning-bar-range" x="${start}" y="${top+1}" width="${Math.max(0,end-start)}" height="${ph-2}" fill="none" stroke="${color}" stroke-width="1.6" stroke-dasharray="3 3"/>`;if(w.code==='smallbar'){mark+=arrow(x(0),top+ph-35,end,top+ph-35,color,'bar-radius-arrow');}if(id==='epsPlot')mark+=note(start,top+ph-(w.code==='smallbar'?32:48),w.code==='smallbar'?`Bar end ${fmt(bounds[1])}″ ${bounds[1]<S.settings.rules.small_bar?'<':'≥'} ${fmt(S.settings.rules.small_bar)}″`:w.label,color);}
  if(w.code==='bar'&&id==='epsPlot'&&w.peak&&w.low){const a=w.peak.eps,b=w.low.p.ellipticity,bx=clamp(x(w.low.p.sma_arcsec)+9,left+8,right-10);mark+=arrow(bx,y(a),bx,y(b),color,'bar-drop-arrow')+note(bx+7,(y(a)+y(b))/2,`Bar drop = ${fmt(a-b,3)}`,color);}
  if(mark)out+=`<g class="profile-warning" data-warning="${w.code}" data-active="${!!w.active}" style="pointer-events:none"><title>${esc(w.detail)}</title>${mark}</g>`;
 }
 return out;
}
function paComparisonDescription(g,c){
 const count=c?.n_disc_pa??c?.n_disc??0,parts=[];
 parts.push(finite(c?.disc_pa)?`Calculated Disc PA ${fmt(c.disc_pa)}° (green dashed; ${count} ellipse${count===1?'':'s'}${count<3?'; provisional':''}).`:'Calculated Disc PA unavailable: no usable selected ellipse.');
 parts.push(finite(g.euclid?.disc_pa)?`Euclid comparison ${fmt(g.euclid.disc_pa)}° (blue dotted on image; purple dotted on profile).`:'Euclid PA unavailable in the catalogue comparison.');
 if(!g.centre?.every(finite))parts.push('Image lines require an adopted fitted centre.');
 return parts.join(' ');
}
function drawProfiles(){
 $('paComparisonStatus').hidden=S.settings.display.paComparison!==true;$('paComparisonStatus').textContent=S.settings.display.paComparison===true?paComparisonDescription(S.g,S.calc):'';
 const warnings=relevantProfileDiagnostics(S.g,profileWarningEvidence(S.g,S.settings,S.calc),S.boot?.sample??[]),highlight=S.settings.display.showWarnings!==false;
 const stored=storedWarningNotes(S.g);
 $('profileWarnings').innerHTML=highlight?warnings.map(w=>`<details class="profile-warning-note ${w.active?'active':'comparison'}" ${w.active?'open':''}><summary><strong>${esc(w.label)}</strong> — ${esc(w.status)}${w.comparison?`<span class="diagnostic-comparison">${esc(w.comparison)}</span>`:''}</summary><p>${esc(w.detail)}</p></details>`).join('')+(!warnings.length&&!stored.length?'<p class="small">No active warnings or relevant boundary-case diagnostics for this selection.</p>':'')+(stored.length?`<details class="stored-warning-notes"><summary>Stored fit warnings (${stored.length}) — separate from current-selection annotations</summary>${stored.map(w=>`<p class="small"><strong>${esc(w.label)}:</strong> ${esc(w.detail)}</p>`).join('')}</details>`:''):'';
 const accepted=pool(),acceptedSet=new Set(accepted),xmax=plotMax(),paView=profilePAView(S.g.profile,accepted,xmax,S.settings.display.unwrapPA!==false,$('showRejected').checked);
 const centreAxis=radiusAxis(Math.max(4,...S.g.profile.filter(p=>p.sma_arcsec<=xmax).map(p=>centrePointStatus(p)).filter(z=>z.available).map(z=>z.offset)));
 for(const [id,field,maxY,title] of [['epsPlot','ellipticity',1,'Ellipticity ε = 1 − b/a'],['incPlot','inclination',90,'Inclination proxy (degrees; circular-disc assumption)'],['centrePlot','centre_offset',centreAxis.max,'Ellipse centre displacement (native pixels); dashed = limit'],['paPlot','pa_sky_deg',180,paView.unwrapped?'Disc / bar PA (degrees; continuous axis, labels wrap at 360°)':'Disc / bar PA (degrees)']]){
 const w=660,h=215,left=48,right=18,top=22,bottom=36,pw=w-left-right,ph=h-top-bottom;
 const discBounds=S.settings.disc,discVisible=S.g.original.status!=='fit_failed'&&discBounds?.length===2&&discBounds.every(finite)&&discBounds[1]>discBounds[0],inDisc=p=>discVisible&&p.sma_arcsec>=discBounds[0]&&p.sma_arcsec<=discBounds[1];
 const isPA=field==='pa_sky_deg',isInc=field==='inclination',isCentre=field==='centre_offset',reference=isPA?(S.settings.display.paComparison===true?S.g.euclid?.disc_pa:null):isInc?S.g.euclid?.inclination:null;
 let lo=isPA?paView.min:0,hi=isPA?paView.max:maxY,ticks=isPA?[...paView.ticks]:isInc?[0,15,30,45,60,75,90]:isCentre?centreAxis.ticks:[0,.25,.5,.75,1];
 if(isPA&&discVisible)for(const pa of [reference,...(S.settings.display.paComparison===true?[S.calc?.disc_pa]:[])].filter(finite)){const nearest=pa+180*Math.round(((lo+hi)/2-pa)/180),step=ticks[1]-ticks[0];while(nearest<lo){lo-=step;ticks.unshift(lo);}while(nearest>hi){hi+=step;ticks.push(hi);}}
 const value=p=>isPA?paView.values.get(p):isInc?(inDisc(p)?ellipseInclination(p):null):isCentre?(centrePointStatus(p).available?centrePointStatus(p).offset:null):p[field];
 const x=v=>left+v/xmax*pw,y=v=>top+(hi-v)/(hi-lo)*ph;let html='';
 for(const [kind,color] of [['bar','#f3bc62'],['disc','#86bf96']]){if(S.g.original.status==='fit_failed'||(kind==='bar'&&S.settings.noBar))continue;const r=S.settings[kind];if(!r.every(finite))continue;html+=`<rect x="${x(r[0])}" y="${top}" width="${Math.max(0,x(r[1])-x(r[0]))}" height="${ph}" fill="${color}" opacity=".28"/>`;for(const edge of [0,1])html+=`<line x1="${x(r[edge])}" x2="${x(r[edge])}" y1="${top}" y2="${top+ph}" stroke="${kind==='disc'?'#348458':'#c17b19'}" stroke-width="${S.drag?.kind===kind?2:1}" opacity=".7"/>`;}
 for(const vy of ticks)html+=`<line x1="${left}" x2="${w-right}" y1="${y(vy)}" y2="${y(vy)}" stroke="#dce5eb"/><text x="${left-8}" y="${y(vy)+4}" text-anchor="end">${isPA?((Math.round(vy)%360)+360)%360:isInc?Math.round(vy):isCentre?vy.toFixed(centreAxis.decimals):vy.toFixed(2)}</text>`;
 const radiusTicks=radiusAxis(xmax),visibleRadiusTicks=radiusTicks.ticks.filter(v=>v<=xmax+1e-9);if(xmax-visibleRadiusTicks.at(-1)>radiusTicks.step*.45)visibleRadiusTicks.push(xmax);for(const vx of visibleRadiusTicks){html+=`<line x1="${x(vx)}" x2="${x(vx)}" y1="${top}" y2="${top+ph}" stroke="#e6edf1"/><text x="${x(vx)}" y="${top+ph+18}" text-anchor="middle">${vx.toFixed(radiusTicks.decimals)}</text>`;}
 html+=`<text class="axis-title" x="${left}" y="14">${title}</text><text class="axis-title" x="${left+pw/2}" y="${h-2}" text-anchor="middle">Semi-major axis (arcsec)</text>`;
 if((isPA&&S.settings.display.paComparison===true)||isInc){
  const referenceLeft=discVisible?x(clamp(discBounds[0],0,xmax)):left,referenceRight=discVisible?x(clamp(discBounds[1],0,xmax)):left;
  const levels=!discVisible||referenceRight<=referenceLeft?[]:isPA?paReferenceLevels(reference,lo,hi):finite(reference)&&reference>=0&&reference<=90?[reference]:[];
  for(const level of levels){const label=isPA?'Euclid source PA':'Euclid inclination proxy',canonical=isPA?((reference%180)+180)%180:reference;
   html+=`<line class="euclid-reference" x1="${referenceLeft}" x2="${referenceRight}" y1="${y(level)}" y2="${y(level)}" stroke="#8a3996" stroke-width="1.6" stroke-dasharray="2 4"><title>${label}: ${fmt(canonical)}°${isPA?'; includes adopted +90° correction; equivalent axes repeat every 180°':''}</title></line>${referenceRight-referenceLeft>=130?`<text class="euclid-reference-label" x="${referenceRight-4}" y="${clamp(y(level)-5,top+12,top+ph-4)}" text-anchor="end" style="fill:#8a3996">Euclid: ${fmt(canonical)}°</text>`:''}`;
  }
  if(!levels.length)html+=`<text x="${w-right-4}" y="${top+12}" text-anchor="end" style="fill:#8a3996">${discVisible?'Euclid: unavailable':'No selected disc interval'}</text>`;
 }
 if(isPA&&discVisible&&S.settings.display.paComparison===true&&finite(S.calc?.disc_pa)){
  const start=x(clamp(discBounds[0],0,xmax)),end=x(clamp(discBounds[1],0,xmax));
  for(const level of paReferenceLevels(S.calc.disc_pa,lo,hi))html+=`<line class="disc-pa-reference" x1="${start}" x2="${end}" y1="${y(level)}" y2="${y(level)}" stroke="#3ddc84" stroke-width="1.8" stroke-dasharray="7 4"><title>Current-selection disc PA: ${fmt(S.calc.disc_pa)}°; equivalent axes repeat every 180°</title></line>${end-start>=130?`<text x="${end-4}" y="${clamp(y(level)+14,top+12,top+ph-4)}" text-anchor="end" style="fill:#19794c">Disc: ${fmt(S.calc.disc_pa)}°</text>`:''}`;
 }
 if(isCentre&&S.g.centre_reference){const path=[];for(let i=0;i<=80;i++){const radius=Math.max(.0001,xmax*i/80),ref=S.g.centre_reference,status=centrePointStatus({sma_arcsec:radius,x_original_pix:ref.x,y_original_pix:ref.y});if(status.available)path.push(`${x(radius)},${y(status.limit)}`);}html+=`<polyline class="centre-tolerance" points="${path.join(' ')}" fill="none" stroke="#cf3434" stroke-width="1.6" stroke-dasharray="5 4"><title>Centre tolerance in native pixels; samples above this curve are excluded while the centre screen is enabled.</title></polyline>`;}
 let segments=[],current=[],previous=null;
 S.g.profile.forEach(p=>{if(!acceptedSet.has(p)||!finite(value(p))||p.sma_arcsec>xmax){if(current.length)segments.push(current);current=[];previous=null;return;}if(previous&&isPA&&!paView.unwrapped&&Math.abs(p[field]-previous[field])>90){segments.push(current);current=[];}current.push(`${x(p.sma_arcsec)},${y(value(p))}`);previous=p;});if(current.length)segments.push(current);
 // Dashed segments expose rejected trends, with accepted neighbours as anchors.
 // They are visual evidence only and never enter pool() or calculate().
 if($('showRejected').checked){let previous=null;for(const p of S.g.profile.slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec)){
  if(!finite(value(p))||!finite(p.sma_arcsec)||p.sma_arcsec>xmax){previous=null;continue;}
  if(previous&&(!acceptedSet.has(previous)||!acceptedSet.has(p))&&!(isPA&&!paView.unwrapped&&Math.abs(p[field]-previous[field])>90))html+=`<line class="excluded-trend" x1="${x(previous.sma_arcsec)}" y1="${y(value(previous))}" x2="${x(p.sma_arcsec)}" y2="${y(value(p))}" stroke="#c84b4b" stroke-width="1.3" stroke-dasharray="5 4" opacity=".8"><title>Excluded-sample trend; not used in geometry calculations</title></line>`;
  previous=p;
 }}
 html+=segments.map(path=>`<polyline points="${path.join(' ')}" fill="none" stroke="#246f98" stroke-width="1.4"/>`).join('');
 for(const p of S.g.profile){const ok=acceptedSet.has(p);if((!ok&&!$('showRejected').checked)||!finite(value(p))||!finite(p.sma_arcsec)||p.sma_arcsec>xmax)continue;const centreStatus=centrePointStatus(p),color=ok?(p.used_for_geometry?'#246f98':'#b5598b'):'#a5adb2',shown=isPA&&paView.unwrapped?`; plotted as ${fmt(value(p),3)}° (equivalent modulo 180°)`:'';html+=`<circle cx="${x(p.sma_arcsec)}" cy="${y(value(p))}" r="${ok?3.2:2.1}" fill="${color}"><title>${ok?'Accepted in this pool':'Excluded'}; radius ${fmt(p.sma_arcsec,3)} arcsec; ${field} ${fmt(isInc?value(p):p[field],3)}${shown}; PA error ${fmt(p.pa_error_deg)}°; ellipticity error ${fmt(p.ellipticity_error,3)}; usable coverage ${fmt(p.sampled_fraction*100,1)}%; valid ${p.valid}; ${centreStatus.available?centreStatus.reason:'centre comparison unavailable'}; original fit-reference offset ${fmt(p.centre_offset_fit_pix)} fit pixels; stop ${p.stop_code}${!ok?(p.marginal?'; eligible for exploratory marginal pool':'; not eligible for exploratory marginal pool'):''}</title></circle>`;}
 if(highlight)html+=drawWarningGraphics(warnings,{id,x,y,value,top,ph,left,right:w-right,xmax,paView});
 html+=`<rect x="${left}" y="${top}" width="${pw}" height="${ph}" fill="none" stroke="#7e929f"/>`;
 if(S.g.original.status!=='fit_failed')for(const kind of ['bar','disc']){if(kind==='bar'&&S.settings.noBar)continue;const bounds=S.settings[kind];if(!bounds?.every(finite))continue;for(const edge of [0,1]){const handleY=top+(kind==='bar'?2:16);html+=`<rect class="interval-handle" data-interval-kind="${kind}" data-interval-edge="${edge}" x="${x(bounds[edge])-5}" y="${handleY}" width="10" height="10" rx="2" fill="${kind==='bar'?'#dc971f':'#348458'}" stroke="white" stroke-width="1" style="cursor:ew-resize"><title>${kind==='bar'?'Bar':'Disc'} ${edge===0?'inner':'outer'} boundary — drag horizontally</title></rect>`;}}

 $(id).innerHTML=html;$(id).dataset.xmax=xmax;if(id==='centrePlot')$(id).hidden=!(highlight&&warnings.some(w=>w.code==='centre'));}
}

function chooseProfileBoundary(settings,radius,axisMax,explicit=null){
 const available=['bar','disc'].filter(kind=>!(kind==='bar'&&settings.noBar)&&settings[kind]?.every(finite));
 if(explicit&&available.includes(explicit.kind)&&[0,1].includes(explicit.edge))return {...explicit,snap:true};
 const candidates=available.flatMap(kind=>[0,1].map(edge=>({kind,edge,distance:Math.abs(settings[kind][edge]-radius)}))).sort((a,b)=>a.distance-b.distance);
 if(candidates[0]?.distance<=axisMax*10/594)return {kind:candidates[0].kind,edge:candidates[0].edge,snap:true};
 return null;
}
function graphPointer(svg,event){const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;const x=point.matrixTransform(svg.getScreenCTM().inverse()).x;return clamp((x-48)/(660-48-18)*(S.drag?.axisMax??Number(svg.dataset.xmax)),0,(S.drag?.axisMax??Number(svg.dataset.xmax)));}
for(const id of ['epsPlot','incPlot','centrePlot','paPlot']){const svg=$(id);svg.onpointerdown=e=>{if(!S.g||S.g.original.status==='fit_failed')return;const handle=e.target?.closest?.('[data-interval-kind]'),explicit=handle?{kind:handle.dataset.intervalKind,edge:Number(handle.dataset.intervalEdge)}:null,x=graphPointer(svg,e),axisMax=Number(svg.dataset.xmax),choice=chooseProfileBoundary(S.settings,x,axisMax,explicit);
 if(!choice)return;const {kind,edge}=choice;
 S.drag={kind,edge,axisMax,grabOffset:choice.snap?x-S.settings[kind][edge]:0};svg.setPointerCapture(e.pointerId);moveGraph(svg,e);};svg.onpointermove=e=>{if(S.drag)moveGraph(svg,e);};svg.onpointerup=()=>finishProfileDrag(true);svg.onpointercancel=()=>finishProfileDrag(false);}
function finishProfileDrag(extend){if(!S.drag)return;const {kind,edge,axisMax}=S.drag;
 if(extend&&edge===1&&S.settings[kind][1]>=axisMax*.98)S.profileAxisFloor=axisMax+2;
 S.drag=null;recalculate();markDirty();expandProfileView();
}
function moveGraph(svg,e){const {kind,edge}=S.drag,r=S.settings[kind],value=clamp(graphPointer(svg,e)-(S.drag.grabOffset??0),0,S.drag.axisMax);r[edge]=edge===0?Math.min(value,r[1]-.005):Math.max(value,r[0]+.005);S.settings['edited'+(kind==='disc'?'Disc':'Bar')]=true;$(kind+'Min').value=fmt(r[0],3);$(kind+'Max').value=fmt(r[1],3);recalculate();}

let offscreen=document.createElement('canvas'),renderPending=false;
function scheduleImage(){if(renderPending)return;renderPending=true;requestAnimationFrame(()=>{renderPending=false;stretchPixels();drawImage();});}
function stretchPixels(){if(!S.pixels)return;const m=S.imageMeta,d=S.settings.display;
 const stf=d.stretch==='autostf'?autoSTFParameters(m.stats,Number(d.stfShadows??-2.8),Number(d.stfTarget??.25)):null;
 if(stf){d.minimum=stf.minimum;d.maximum=stf.maximum;$('minimum').value=stf.minimum;$('maximum').value=stf.maximum;$('stfInfo').textContent=`AutoSTF midtones ${stf.midtones.toPrecision(5)} · display black ${stf.minimum.toPrecision(5)} · white ${stf.maximum.toPrecision(5)}`;}
 const low=Number(d.minimum),high=Number(d.maximum),range=high-low;if(!(range>0))return;
 offscreen.width=m.width;offscreen.height=m.height;let context=offscreen.getContext('2d'),image=context.createImageData(m.width,m.height),dest=image.data;
 const gamma=1/clamp(Number(d.gamma)||1,.2,3);for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++){const value=S.pixels[y*m.width+x],at=((m.height-1-y)*m.width+x)*4;if(!finite(value)){dest[at]=35;dest[at+1]=38;dest[at+2]=55;dest[at+3]=255;continue;}let v=stf?autoSTFValue(value,stf):clamp((value-low)/range,0,1);if(d.stretch==='log')v=Math.log1p(99*v)/Math.log(100);else if(d.stretch==='asinh')v=Math.asinh(10*v)/Math.asinh(10);v=v**gamma;if(d.invert)v=1-v;const c=Math.round(v*255);dest[at]=dest[at+1]=dest[at+2]=c;dest[at+3]=255;}
 context.putImageData(image,0,0);}

function imageTransform(){const canvas=$('image'),rect=canvas.getBoundingClientRect(),view=S.imageMeta?.bounds??S.view;if(!view)return null;const ratio=(view[1]-view[0])/(view[3]-view[2]);let w=rect.width,h=w/ratio;if(h>rect.height){h=rect.height;w=h*ratio;}const left=(rect.width-w)/2,top=(rect.height-h)/2;return {w,h,left,top,rect,view,x:v=>left+(v-view[0])/(view[1]-view[0])*w,y:v=>top+(view[3]-v)/(view[3]-view[2])*h};}
// Local WCS pixel vectors retain projection scale and image handedness.
function skyPADirection(pa,basis){if(!finite(pa)||!basis?.N?.every(finite)||!basis?.E?.every(finite))return null;
 const angle=pa*Math.PI/180,dx=basis.N[0]*Math.cos(angle)+basis.E[0]*Math.sin(angle),dy=basis.N[1]*Math.cos(angle)+basis.E[1]*Math.sin(angle),length=Math.hypot(dx,dy);return length>0?[dx/length,dy/length]:null;
}
function drawImage(){const canvas=$('image'),rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;if(canvas.width!==Math.round(rect.width*dpr)||canvas.height!==Math.round(rect.height*dpr)){canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);}const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#111b23';ctx.fillRect(0,0,rect.width,rect.height);if(!S.pixels||!S.g)return;const t=imageTransform();ctx.imageSmoothingEnabled=true;ctx.drawImage(offscreen,t.left,t.top,t.w,t.h);ctx.save();ctx.beginPath();ctx.rect(t.left,t.top,t.w,t.h);ctx.clip();
 if(S.settings.display.ellipses){
  const disc=new Set(S.calc.disc),bar=new Set(S.calc.bar),accepted=pool(),acceptedSet=new Set(accepted);
  const usable=p=>finite(p.x_original_pix)&&finite(p.y_original_pix)&&finite(p.pa_pixel_deg)&&finite(p.sma_arcsec)&&p.sma_arcsec>0&&finite(p.ellipticity)&&p.ellipticity>=0&&p.ellipticity<1;
  const outline=(p,color,dashed)=>{const a=p.sma_arcsec/S.g.pixel_scale_arcsec,rx=a*t.w/(t.view[1]-t.view[0]),ry=rx*(1-p.ellipticity);ctx.beginPath();ctx.setLineDash(dashed?[5,4]:[]);ctx.ellipse(t.x(p.x_original_pix),t.y(p.y_original_pix),Math.max(.1,rx),Math.max(.1,ry),-p.pa_pixel_deg*Math.PI/180,0,Math.PI*2);ctx.strokeStyle=color;ctx.lineWidth=dashed?1.3:1.1;ctx.stroke();if(S.settings.display.centres){const cx=t.x(p.x_original_pix),cy=t.y(p.y_original_pix);ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(cx-2,cy);ctx.lineTo(cx+2,cy);ctx.moveTo(cx,cy-2);ctx.lineTo(cx,cy+2);ctx.stroke();}};
  // Same rejected pool and radial extent as the profile graphs; never adopted geometry.
  if(S.settings.display.excludedEllipses!==false&&S.settings.display.showRejected!==false){const rejected=S.g.profile.filter(p=>!acceptedSet.has(p)&&p.sma_arcsec<=plotMax()&&usable(p)),stride=Math.max(1,Math.ceil(rejected.length/50));for(const [i,p] of rejected.entries())if(i%stride===0)outline(p,'#e26060',true);}
  let points=accepted.filter(p=>S.settings.display.overlayMode==='accepted'||disc.has(p)||bar.has(p));const stride=Math.max(1,Math.ceil(points.length/50));points=points.filter((p,i)=>i%stride===0||i===points.length-1||disc.has(p)||bar.has(p));for(const p of points)if(usable(p))outline(p,disc.has(p)?'#65d095':bar.has(p)?'#ffc35d':'#65c6db',false);
  ctx.setLineDash([]);
 }
 if(S.g.centre?.every(finite))for(const [enabled,pa,color,dash] of [[S.settings.display.paComparison===true,S.g.euclid?.disc_pa,'#55aaff',[2,5]],[S.settings.display.paComparison===true,S.calc?.disc_pa,'#3ddc84',[7,4]]]){
  const direction=enabled?skyPADirection(pa,S.g.compass_pixel_basis??S.g.compass):null;
  if(direction){const cx=t.x(S.g.centre[0]),cy=t.y(S.g.centre[1]),dx=direction[0]*t.w/(t.view[1]-t.view[0]),dy=-direction[1]*t.h/(t.view[3]-t.view[2]),norm=Math.hypot(dx,dy),length=2*Math.hypot(t.w,t.h);
   ctx.beginPath();ctx.setLineDash(dash);ctx.moveTo(cx-dx/norm*length,cy-dy/norm*length);ctx.lineTo(cx+dx/norm*length,cy+dy/norm*length);ctx.strokeStyle=color;ctx.lineWidth=1.8;ctx.stroke();ctx.setLineDash([]);
  }
 }
 if(S.settings.display.centres){for(const [centre,color,cross] of [[S.g.catalogue_centre,'white',true],[S.g.centre,'#ff5d5d',false]]){if(!centre.every(finite))continue;const x=t.x(centre[0]),y=t.y(centre[1]),r=5;ctx.beginPath();if(cross){ctx.moveTo(x-r,y-r);ctx.lineTo(x+r,y+r);ctx.moveTo(x-r,y+r);ctx.lineTo(x+r,y-r);}else{ctx.moveTo(x-r,y);ctx.lineTo(x+r,y);ctx.moveTo(x,y-r);ctx.lineTo(x,y+r);}ctx.strokeStyle=color;ctx.lineWidth=1.7;ctx.stroke();}}
 if(S.settings.display.centres&&S.proposedCentre?.every(finite)){const [cx,cy]=S.proposedCentre,x=t.x(cx),y=t.y(cy);ctx.strokeStyle='#ffe347';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x-8,y);ctx.lineTo(x+8,y);ctx.moveTo(x,y-8);ctx.lineTo(x,y+8);ctx.stroke();}
 // Native WCS compass, never a forced image rotation.
 const anchor=[t.left+66,t.top+t.h-45];ctx.strokeStyle='white';ctx.fillStyle='white';ctx.font='12px Segoe UI';for(const label of ['N','E']){const v=S.g.compass[label],dx=v[0]*27,dy=-v[1]*27;ctx.beginPath();ctx.moveTo(...anchor);ctx.lineTo(anchor[0]+dx,anchor[1]+dy);ctx.stroke();ctx.textAlign='center';ctx.fillText(label==='N'?'N 0°':'E 90°',anchor[0]+dx*1.25,anchor[1]+dy*1.25+4);}
 const span=(t.view[1]-t.view[0])*S.g.pixel_scale_arcsec,target=span*.23,power=10**Math.floor(Math.log10(target)),scale=[1,2,5,10].map(x=>x*power).filter(x=>x<=target).pop()??power,px=scale/S.g.pixel_scale_arcsec*t.w/(t.view[1]-t.view[0]);ctx.beginPath();ctx.moveTo(t.left+t.w-20-px,t.top+t.h-22);ctx.lineTo(t.left+t.w-20,t.top+t.h-22);ctx.stroke();ctx.textAlign='center';ctx.fillText(`${scale<1?scale.toFixed(2):scale.toFixed(scale<3?1:0)}″`,t.left+t.w-20-px/2,t.top+t.h-29);ctx.restore();}

async function loadImage(newGalaxy=false){if(!S.g)return;const request=++S.imageRequest,id=S.id;S.imageAbort?.abort();const abort=new AbortController();S.imageAbort=abort;$('imageLoading').hidden=false;try{const q=new URLSearchParams({id,x0:S.view[0],x1:S.view[1],y0:S.view[2],y1:S.view[3]});const response=await fetch('/api/image?'+q,{signal:abort.signal});if(!response.ok){const body=await response.json();throw new Error(body.error);}const meta=JSON.parse(response.headers.get('X-Image-Meta')),buffer=await response.arrayBuffer();if(request!==S.imageRequest||id!==S.id)return;S.imageMeta=meta;S.pixels=new Float32Array(buffer);S.view=[...meta.bounds];if(newGalaxy&&(!finite(S.settings.display.minimum)||!finite(S.settings.display.maximum)))applyPreset(S.settings.display.stretch==='autostf'?'pixinsight':'faint',false);else{stretchPixels();drawImage();}
 $('imageInfo').textContent=meta.factor===1?'Native pixels':`${meta.factor}× ${meta.method}`;
 }catch(e){if(e.name!=='AbortError')showError(e);}finally{if(request===S.imageRequest)$('imageLoading').hidden=true;}}
function applyPreset(name,dirty=true){if(!S.imageMeta)return;const s=S.imageMeta.stats,d=S.settings.display;d.minimum=s.median-s.noise;d.maximum=name==='faint'?s.median+15*s.noise:name==='core'?Math.max(s.percentiles.p999,s.median+30*s.noise):Math.max(s.percentiles.p995,s.median+15*s.noise);d.stretch=name==='pixinsight'?'autostf':name==='core'?'log':'asinh';d.gamma=1;writeControls();stretchPixels();drawImage();if(dirty)saveDraft();}
// A profile radius is a semi-major axis: the image must cover twice that radius.
function profileImageWindow(g,settings,radius){
 const centre=g.centre?.every(finite)?g.centre:g.catalogue_centre,scale=g.pixel_scale_arcsec;
 if(!centre?.every(finite)||!(scale>0))return [...g.default_window];
 const r=radius/scale*1.06;let bounds=[centre[0]-r,centre[0]+r,centre[1]-r,centre[1]+r];
 // Include each fitted ellipse's own centre, orientation and projected extents.
 for(const p of g.profile){if(!(p.sma_arcsec<=radius)||![p.sma_arcsec,p.x_original_pix,p.y_original_pix,p.pa_pixel_deg,p.ellipticity].every(finite)||p.sma_arcsec<=0||p.ellipticity<0||p.ellipticity>=1)continue;
  const a=p.sma_arcsec/scale,b=a*(1-p.ellipticity),angle=p.pa_pixel_deg*Math.PI/180,c=Math.cos(angle),d=Math.sin(angle),dx=Math.hypot(a*c,b*d)*1.04,dy=Math.hypot(a*d,b*c)*1.04;
  bounds=[Math.min(bounds[0],p.x_original_pix-dx),Math.max(bounds[1],p.x_original_pix+dx),Math.min(bounds[2],p.y_original_pix-dy),Math.max(bounds[3],p.y_original_pix+dy)];
 }
 return bounds;
}
function expandProfileView(reload=true){if(!S.g||!S.view)return false;
 const required=profileImageWindow(S.g,S.settings,plotMax()),v=S.view;
 const desired=fitWindow([Math.min(v[0],required[0]),Math.max(v[1],required[1]),Math.min(v[2],required[2]),Math.max(v[3],required[3])]);
 if(desired.every((x,i)=>Math.abs(x-v[i])<.5))return false;
 S.view=desired;if(reload){clearTimeout(zoom.timer);loadImage();saveDraft();}return true;
}
function fitWindow(view){const [ny,nx]=S.g.shape;let w=clamp(view[1]-view[0],8,nx),h=clamp(view[3]-view[2],8,ny),x=clamp((view[0]+view[1])/2,w/2-.5,nx-.5-w/2),y=clamp((view[2]+view[3])/2,h/2-.5,ny-.5-h/2);return [x-w/2,x+w/2,y-h/2,y+h/2];}
function zoom(factor,anchor){if(!S.g)return;const v=S.imageMeta?.bounds??S.view,x=anchor?.[0]??(v[0]+v[1])/2,y=anchor?.[1]??(v[2]+v[3])/2;S.view=fitWindow([x+(v[0]-x)*factor,x+(v[1]-x)*factor,y+(v[2]-y)*factor,y+(v[3]-y)*factor]);clearTimeout(zoom.timer);zoom.timer=setTimeout(()=>{loadImage();saveDraft();},80);}
const canvas=$('image');let pan=null;
function imagePixel(t,clientX,clientY){const px=clientX-t.rect.left,py=clientY-t.rect.top;return [t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2])];}
canvas.onwheel=e=>{e.preventDefault();const t=imageTransform();if(!t)return;const px=e.clientX-t.rect.left,py=e.clientY-t.rect.top;const anchor=[t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2])];zoom(e.deltaY>0?1.35:1/1.35,anchor);};
canvas.onpointerdown=e=>{if(!S.imageMeta)return;if(S.pickingCentre){const [x,y]=imagePixel(imageTransform(),e.clientX,e.clientY);if(x<0||y<0||x>S.g.shape[1]-1||y>S.g.shape[0]-1){toast('Click inside the FITS image');return;}setProposedCentre(x,y);S.pickingCentre=false;$('pickCentre').textContent='Pick centre on image';canvas.style.cursor='';drawImage();return;}pan={x:e.clientX,y:e.clientY,view:[...S.imageMeta.bounds],transform:imageTransform()};canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{const t=imageTransform();if(!t||!S.pixels)return;const px=e.clientX-t.rect.left,py=e.clientY-t.rect.top,x=t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),y=t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2]);const ix=Math.floor((x-t.view[0])/(t.view[1]-t.view[0])*S.imageMeta.width),iy=Math.floor((y-t.view[2])/(t.view[3]-t.view[2])*S.imageMeta.height);if(ix>=0&&ix<S.imageMeta.width&&iy>=0&&iy<S.imageMeta.height){const value=S.pixels[iy*S.imageMeta.width+ix];$('pixelValue').textContent=`x ${x.toFixed(1)}, y ${y.toFixed(1)} · ${finite(value)?value.toPrecision(5):'masked'} ${S.g.units}`;}};
canvas.onpointerup=e=>{if(!pan)return;const dx=(e.clientX-pan.x)/pan.transform.w*(pan.view[1]-pan.view[0]),dy=(e.clientY-pan.y)/pan.transform.h*(pan.view[3]-pan.view[2]);if(Math.abs(e.clientX-pan.x)+Math.abs(e.clientY-pan.y)>4){S.view=fitWindow([pan.view[0]-dx,pan.view[1]-dx,pan.view[2]+dy,pan.view[3]+dy]);loadImage();saveDraft();}pan=null;};canvas.onpointercancel=()=>pan=null;


function setProposedCentre(x,y){S.proposedCentre=[x,y];$('centreX').value=x.toFixed(2);$('centreY').value=y.toFixed(2);S.settings.proposed_centre=[x,y];saveDraft();drawImage();}
function initCentreControls(){S.pickingCentre=false;pan=null;canvas.style.cursor='';$('pickCentre').textContent='Pick centre on image';S.proposedCentre=S.settings.proposed_centre??(S.g.refit?[S.g.refit.x,S.g.refit.y]:S.g.centre.every(finite)?S.g.centre:S.g.catalogue_centre);$('centreX').max=S.g.shape[1]-1;$('centreY').max=S.g.shape[0]-1;$('centreX').value=S.proposedCentre[0].toFixed(2);$('centreY').value=S.proposedCentre[1].toFixed(2);$('lockCentre').checked=S.g.refit?.lock_centre??true;const refits=JSON.parse(localStorage.getItem(storageKey('refits'))??'{}');if(S.g.latest_refit_id)refits[S.id]=S.g.latest_refit_id;localStorage.setItem(storageKey('refits'),JSON.stringify(refits));$('showRefit').hidden=!refits[S.id]||refits[S.id]===S.g.refit?.job_id;$('showOriginal').disabled=!S.g.refit;$('exportRefit').hidden=!S.g.refit;if(S.g.refit)$('exportRefit').href='/api/refit/export?job='+S.g.refit.job_id;$('refitStatus').textContent=S.g.refit?`Showing manual-centre refit from ${S.g.refit.requested_utc}. Status: ${S.g.original.status.replaceAll('_',' ')}. Updated profiles and metrics are saved separately.`:'Original pipeline result. Pick a centre and recompute; results are stored separately.';}
$('pickCentre').onclick=()=>{S.pickingCentre=!S.pickingCentre;if(S.pickingCentre){S.settings.display.centres=true;$('centres').checked=true;}$('pickCentre').textContent=S.pickingCentre?'Click nucleus in image — cancel':'Pick centre on image';canvas.style.cursor=S.pickingCentre?'crosshair':'';};
$('catalogueCentre').onclick=()=>setProposedCentre(...S.g.catalogue_centre);
for(const id of ['centreX','centreY'])$(id).onchange=()=>{const x=$('centreX').valueAsNumber,y=$('centreY').valueAsNumber;if(!finite(x)||!finite(y)||x<0||y<0||x>S.g.shape[1]-1||y>S.g.shape[0]-1){showError('Centre must be inside the original FITS image');return;}clearError();setProposedCentre(x,y);};
$('showOriginal').onclick=()=>loadGalaxy(S.id,null);
$('showRefit').onclick=()=>loadGalaxy(S.id,JSON.parse(localStorage.getItem(storageKey('refits'))??'{}')[S.id]);
$('runRefit').onclick=async()=>{
 const id=S.id,x=$('centreX').valueAsNumber,y=$('centreY').valueAsNumber;
 if(!finite(x)||!finite(y)){showError('Choose a finite centre first');return;}
 clearError();$('runRefit').disabled=true;S.pickingCentre=false;canvas.style.cursor='';$('pickCentre').textContent='Pick centre on image';
 try{const job=await api('/api/refit',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify({object_id:id,x,y,lock_centre:$('lockCentre').checked,centre_policy:{cap_native_pixels:S.settings.rules.centre_cap_native??3,fraction_radius:S.settings.rules.centre_fraction??.05,floor_native_pixels:S.settings.rules.centre_floor_native??1}})});
  S.settings.proposed_centre=[x,y];saveDraft();let finished=false;
  while(!finished){await new Promise(resolve=>setTimeout(resolve,1200));const status=await api('/api/refit?job='+job.job_id);if(S.id===id)$('refitStatus').textContent=status.message;
   if(status.status==='error')throw new Error(status.message);
   if(status.status==='complete'){finished=true;const refits=JSON.parse(localStorage.getItem(storageKey('refits'))??'{}');refits[id]=job.job_id;localStorage.setItem(storageKey('refits'),JSON.stringify(refits));if(S.id===id){await loadGalaxy(id,job.job_id);markDirty();}toast(status.galaxy.original.status==='fit_failed'?'Retry finished but fit still failed. Inspect the reason.':'New fit ready. Inspect the ellipses and flags, then save your assessment.');}
  }
 }catch(e){showError(e);$('refitStatus').textContent='Refit could not complete: '+e.message;}finally{$('runRefit').disabled=false;}
};

async function setReviewed(id,reviewed,box){box.disabled=true;clearError();try{
 const result=await api('/api/review-status',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify({object_id:id,reviewed})});
 S.boot.reviews[id]=result.review;queue();if(S.id===id){S.g.review=result.review;$('saveStatus').textContent=reviewed?'Marked reviewed; use Save assessment to save any form changes.':'Review status undone; saved notes and current edits are retained.';}
 toast(result.warning??(reviewed?'Marked reviewed':'Marked unreviewed; notes retained'));
 }catch(e){box.checked=!reviewed;showError(e);}finally{box.disabled=false;}}
async function saveReview(next=false){if(!S.g)return;clearError();try{const calculation={...S.calc};delete calculation.disc;delete calculation.bar;for(const key of ['centre_rejected_disc','centre_rejected_bar'])calculation[key]=(calculation[key]??[]).map(p=>({radius_arcsec:p.sma_arcsec,...centrePointStatus(p)}));const payload={object_id:S.id,...getForm(),settings:{...S.settings,view:S.view},calculation};$('save').disabled=$('saveNext').disabled=true;const result=await api('/api/review',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify(payload)});S.boot.reviews[S.id]=result.review;S.dirty=false;const all=drafts();delete all[S.id];localStorage.setItem(storageKey('drafts'),JSON.stringify(all));$('saveStatus').textContent='Review saved to disk';toast(result.warning??'Review saved');const current=S.id,index=S.filtered.findIndex(r=>r.object_id===current),nextId=S.filtered[index+1]?.object_id;queue();if(next){const target=$('unreviewed').checked?S.filtered[0]?.object_id:nextId;if(target)await loadGalaxy(target);else toast('You reached the end of this review group.');}}catch(e){showError(e);}finally{$('save').disabled=$('saveNext').disabled=false;}}

for(const id of fieldIds)$(id).onchange=()=>readGeometryControls(id);
for(const id of displayIds)$(id).oninput=()=>{if(!S.settings)return;const el=$(id),d=S.settings.display;d[id]=el.type==='checkbox'?el.checked:el.type==='number'||el.type==='range'?el.valueAsNumber:el.value;if(id==='stfShadows'||id==='stfTarget'){if(!finite(d[id]))return;d[id]=clamp(d[id],Number(el.min),Number(el.max));el.value=d[id];}if(id==='stretch'){if(d.stretch==='autostf')d.gamma=1;writeControls();}if(id==='showRejected'||id==='paComparison'){drawProfiles();drawImage();}else if(id==='unwrapPA'||id==='showWarnings')drawProfiles();else if(['ellipses','centres','overlayMode','excludedEllipses'].includes(id))drawImage();else scheduleImage();$('gammaValue').value=Number(d.gamma).toFixed(2);saveDraft();};
for(const id of reviewIds)$(id).oninput=markDirty;
document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>applyPreset(b.dataset.preset));
$('category').onchange=$('unreviewed').onchange=()=>{queue();if(!S.filtered.some(r=>r.object_id===S.id)&&S.filtered.length)loadGalaxy(S.filtered[0].object_id);};
$('prev').onclick=()=>{const i=S.filtered.findIndex(r=>r.object_id===S.id);if(i>0)loadGalaxy(S.filtered[i-1].object_id);};$('next').onclick=()=>{const i=S.filtered.findIndex(r=>r.object_id===S.id);if(i>=0&&i<S.filtered.length-1)loadGalaxy(S.filtered[i+1].object_id);};
$('resetGeometry').onclick=()=>{S.profileAxisFloor=null;const defaults=defaultSettings(S.g);Object.assign(S.settings,{disc:defaults.disc,bar:defaults.bar,noBar:defaults.noBar,editedDisc:false,editedBar:false,pool:'pipeline'});writeControls();markDirty();recalculate();expandProfileView();};
$('zoomIn').onclick=()=>zoom(.65);$('zoomOut').onclick=()=>zoom(1.5);$('galaxyView').onclick=()=>{S.view=fitWindow(profileImageWindow(S.g,S.settings,plotMax()));loadImage();saveDraft();};$('fullView').onclick=()=>{S.view=[-.5,S.g.shape[1]-.5,-.5,S.g.shape[0]-.5];loadImage();saveDraft();};
$('save').onclick=()=>saveReview();$('saveNext').onclick=()=>saveReview(true);
$('search').oninput=()=>{const q=$('search').value.trim().toLowerCase();const matches=q.length>=3?S.boot.catalogue.filter(r=>r.object_id.includes(q)||r.name.toLowerCase().includes(q)).slice(0,12):[];$('searchResults').innerHTML=matches.map(r=>`<button data-id="${esc(r.object_id)}">${esc(r.name||r.object_id)}${r.name?` · ${esc(r.object_id)}`:''}</button>`).join('');$('searchResults').querySelectorAll('button').forEach(b=>b.onclick=()=>loadGalaxy(b.dataset.id));};
$('stop').onclick=async()=>{if(!confirm('Stop the local review server? Saved reviews remain on disk.'))return;try{await api('/api/stop',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:'{}'});toast('Server stopped. Double-click Start MER VIS Review to reopen.');}catch(e){showError(e);}};
window.addEventListener('resize',()=>{drawImage();});window.addEventListener('beforeunload',saveDraft);
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();saveReview(true);}else if(!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){if(e.key==='ArrowRight')$('next').click();if(e.key==='ArrowLeft')$('prev').click();}});

async function start(){try{S.boot=await api('/api/bootstrap');S.token=S.boot.token;$('category').options[0].textContent=`All ${S.boot.sample.length} examples`;for(const [value,label] of Object.entries(S.boot.categories))$('category').add(new Option(label,value));$('outputPath').textContent='Saved locally in: '+S.boot.output;$('campaignBanner').hidden=!S.boot.campaign;$('campaignBanner').textContent=S.boot.campaign?`${S.boot.campaign.title}: ${S.boot.sample.length} examples. New trials are provisional. Previous reviews and notes are preserved; save a new assessment for this round. Centre limits are pilot settings requiring review.`:'';if(S.boot.sample_source_changed)toast('The source manifest has changed since this sample was selected. Review provenance is retained.');queue();const remembered=localStorage.getItem(storageKey('last_galaxy')),id=S.boot.catalogue.some(r=>r.object_id===remembered)?remembered:S.boot.sample.find(r=>!isReviewed(S.boot.reviews[r.object_id]))?.object_id??S.boot.sample[0].object_id;await loadGalaxy(id);}catch(e){showError(e);}}
// Exposed for repeatable numerical verification; no filesystem or pipeline mutations.
window.MER_VIS_REVIEW={state:S,calculate,centrePointStatus,numericalPool,paComparisonDescription,thresholdDescription,relevantProfileDiagnostics,profileWarningEvidence,drawWarningGraphics,resetGalaxyOverlays,radiusAxis,chooseProfileBoundary,skyPADirection,ellipseInclination,paReferenceLevels,profileImageWindow,expandProfileView,profilePAView,axialMean,axialDifference,scatter,loadGalaxy,imagePixel,midtonesTransfer,autoSTFParameters,autoSTFValue};
start();

