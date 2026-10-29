'use strict';
const $ = id => document.getElementById(id);
let config, galaxy, result, labels, image, overlay, segmentImage, reference;
let selected = new Set(), history = [], accepted = null, dirty = false, busy = false;
let view, jobTimer, loadVersion = 0, maskVersion = 0;
let objectPage = 0;
let displayPixels, displayMeta, proposedEllipses = [], sweepViews = [], displayTimer;
const clamp = (x,a,b) => Math.max(a,Math.min(b,x));
// Same rational midtones transfer and monochrome AutoSTF as the centre reviewer.
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
function stretchDisplay(){
  if(!displayPixels||!displayMeta)return;
  const {width,height,stats}=displayMeta, mode=$('stretch').value;
  const gamma=clamp(Number($('gamma').value)||1,.2,3);
  const stf=autoSTFParameters(stats,Number($('stfShadows').value),Number($('stfTarget').value));
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
  const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(width,height);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const raw=displayPixels[y*width+x],at=((height-1-y)*width+x)*4;
    let value=0;if(Number.isFinite(raw)){value=mode==='autostf'?autoSTFValue(raw,stf):clamp((raw-stats.minimum)/Math.max(stats.maximum-stats.minimum,Number.EPSILON),0,1);
      if(mode==='asinh')value=Math.asinh(15*value)/Math.asinh(15);value=value**(1/gamma);}
    const c=Math.round(255*value);pixels.data[at]=pixels.data[at+1]=pixels.data[at+2]=c;pixels.data[at+3]=255;
  }
  ctx.putImageData(pixels,0,0);image=canvas;if(reference)reference.image=image;
  $('gammaValue').value=gamma.toFixed(2);
  $('displayInfo').textContent=`${mode==='autostf'?'PixInsight-style AutoStretch':'Display stretch'} · gamma ${gamma.toFixed(2)} · preview ${width} × ${height} (sampling ${displayMeta.factor} native px). Detection and measurements use unchanged science pixels.`;
  render();
}
const canvases = ['original','segmentation','masked','reference'].map($);
const advanced = {alpha:['Significance alpha',1e-6,'any'],min_distance:['Minimum distance',0,'any'],
  gaussian_fwhm:['Smoothing FWHM (px)',1,.1], bg_mean:['Background mean (blank = auto)','','any'],
  bg_variance:['Background variance (blank = auto)','','any'],gain:['Effective gain',1,'any'],soft_bias:['Soft bias',0,'any']};
for(const [id,[name,value,step]] of Object.entries(advanced)){
  const label=document.createElement('label');label.textContent=name;
  const input=document.createElement('input');Object.assign(input,{id,type:'number',value,step});
  if(id==='alpha')input.readOnly=true;
  label.append(input);$('advanced').append(label);
}
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
async function api(path,body){
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||response.statusText);return data;
}
function file(kind,id,name){return `/api/file?kind=${kind}&id=${id}&name=${name}`;}
async function picture(src){const im=new Image();im.src=src;await im.decode();return im;}
function safe(fn){return async(...args)=>{try{await fn(...args);}catch(e){status(e.message,true);}};}
function params(){const p={move_factor:Number($('moveNumber').value),detect_on:$('detect_on').value};
  for(const key of ['dilation','minarea','residual_sigma','residual_max_area',...Object.keys(advanced)])p[key]=$(key).value===''?null:Number($(key).value);
  return p;
}
function setParams(p){$('move').value=$('moveNumber').value=p.move_factor;$('moveValue').value=Number(p.move_factor).toFixed(2);
  for(const key of ['dilation','minarea',...Object.keys(advanced)])$(key).value=p[key]??'';
  $('detect_on').value=p.detect_on||'original';$('residual_sigma').value=p.residual_sigma??3;
  $('residual_max_area').value=p.residual_max_area??100;
  dirty=false;$('dirty').hidden=true;
}
function changed(){dirty=true;$('dirty').hidden=false;updateButtons();}
function updateButtons(){for(const id of ['detect','sweep','showComparison','galaxy','previous','next','restore','resetParams','projectedPreset'])$(id).disabled=busy;
  $('save').disabled=busy||!result||dirty||!$('confirm').checked;
  $('refit').disabled=busy||!accepted||dirty;
  for(const id of ['undo','resetObjects','pin'])$(id).disabled=busy||!result;
}
function unsaved(){return result && !accepted;}
function clearAcceptance(){accepted=null;$('confirm').checked=false;$('saved').textContent='Mask decisions have not been saved.';updateButtons();}
async function loadGalaxy(){
  const version=++loadVersion;const oid=$('galaxy').value;
  status('Loading native image…');result=null;labels=null;overlay=null;segmentImage=null;reference=null;image=null;displayPixels=null;sweepViews=[];
  $('referenceSection').hidden=true;$('sweepSection').hidden=true;$('refitSection').hidden=true;accepted=null;
  $('notes').value='';$('confirm').checked=false;$('saved').textContent='';$('objects').replaceChildren();$('metrics').replaceChildren();
  galaxy=await api('/api/galaxy?id='+encodeURIComponent(oid));if(version!==loadVersion)return;
  const response=await fetch('/api/display?id='+encodeURIComponent(oid));
  if(!response.ok)throw Error((await response.json()).error);
  const meta=JSON.parse(response.headers.get('X-Image-Meta')),buffer=await response.arrayBuffer();
  if(version!==loadVersion)return;
  displayMeta=meta;displayPixels=new Float32Array(buffer);proposedEllipses=galaxy.proposed_ellipses||[];
  $('showEllipses').value='off';
  const bounds=galaxy.processing_bounds;
  $('processingInfo').textContent=`MTO processes the Fit galaxy rectangle: X ${bounds.x0}–${bounds.x1-1}, Y ${bounds.y0}–${bounds.y1-1} (native pixels). Display zoom and pan do not change this processing area.`;
  $('stretch').value='autostf';$('gamma').value=1;$('stfShadows').value=-2.8;$('stfTarget').value=.25;
  setParams(config.defaults);
  for(const key of ['bar_min','bar_max','disc_min','disc_max'])$(key).value=galaxy.geometry[key]??'';
  const target=config.targets.find(t=>t.object_id===oid);
  $('targetInfo').textContent=target.status+(target.challenge?' · Close-pair challenge; inclination remains provisional.':'');
  $('restore').disabled=!galaxy.latest;fitView();stretchDisplay();updateButtons();
  status('Image ready. Adjust the move factor, then run MTO. Saved reviews can be restored.');
}
function fitView(){if(!galaxy)return;const b=galaxy.processing_bounds;
  view={x:(b.x0+b.x1-1)/2,y:(b.y0+b.y1-1)/2,span:Math.max(b.x1-b.x0,b.y1-b.y0)};render();}
function fullView(){if(!galaxy)return;view={x:(galaxy.shape[1]-1)/2,y:(galaxy.shape[0]-1)/2,span:Math.max(...galaxy.shape)};render();}
function xy(canvas,event){const box=canvas.getBoundingClientRect();return {x:view.x+(event.clientX-box.left)/box.width*view.span-view.span/2,
  y:view.y+view.span/2-(event.clientY-box.top)/box.height*view.span};}
function drawCanvas(canvas,base,mask){
  if(!base||!view)return;const size=Math.max(300,Math.round(canvas.clientWidth*devicePixelRatio));
  if(canvas.width!==size){canvas.width=size;canvas.height=size;}
  const ctx=canvas.getContext('2d');ctx.fillStyle='#080d13';ctx.fillRect(0,0,size,size);ctx.imageSmoothingEnabled=false;
  const scale=size/view.span, left=(galaxy.shape[1]/2-.5-view.x)*scale+size/2, top=(view.y-(galaxy.shape[0]/2-.5))*scale+size/2;
  const width=galaxy.shape[1]*scale,height=galaxy.shape[0]*scale;
  ctx.drawImage(base,left-width/2,top-height/2,width,height);
  if(mask)ctx.drawImage(mask,left-width/2,top-height/2,width,height);
  const sx=x=>(x-view.x)*scale+size/2, sy=y=>(view.y-y)*scale+size/2;
  function ellipse(e,m,color,width=1.2){ctx.strokeStyle=color;ctx.lineWidth=width*devicePixelRatio;ctx.beginPath();
    for(let i=0;i<=180;i++){const angle=i*Math.PI/90,u=e.a*m*Math.cos(angle),v=e.a*e.q*m*Math.sin(angle);
      const x=sx(e.x+u*Math.cos(e.theta)-v*Math.sin(e.theta)),y=sy(e.y+u*Math.sin(e.theta)+v*Math.cos(e.theta));if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y);}ctx.stroke();}
  for(const e of visibleEllipses())ellipse(e,1,e.kind==='disc'?'#80ef95':'#64b4ff');
  const centre=galaxy.geometry;ctx.strokeStyle='#ffe073';ctx.beginPath();ctx.moveTo(sx(centre.x)-7,sy(centre.y));ctx.lineTo(sx(centre.x)+7,sy(centre.y));ctx.moveTo(sx(centre.x),sy(centre.y)-7);ctx.lineTo(sx(centre.x),sy(centre.y)+7);ctx.stroke();
}
function visibleEllipses(){const mode=$('showEllipses').value;if(mode==='off')return [];
  const chosen=[];for(const kind of ['disc','bar']){if(mode!=='both'&&mode!==kind)continue;
    const low=Number($(kind+'_min').value),high=Number($(kind+'_max').value);
    for(const e of proposedEllipses)if(e.sma_arcsec>=low&&e.sma_arcsec<=high)chosen.push({...e,kind});}
  return chosen;
}
function render(){if(!galaxy||!image)return;
  $('ellipseInfo').textContent=$('showEllipses').value==='off'?'Measured bar/disc ellipses: Off. Green = disc; blue = bar.':`${visibleEllipses().length} measured ellipses in the current intervals · green: disc · blue: bar. ${proposedEllipses.length?'':'No measured profile available; no ellipse shapes have been invented.'}`;
  drawCanvas($('original'),image,null);drawCanvas($('segmentation'),segmentImage||image,null);drawCanvas($('masked'),image,overlay);
  if(reference)drawCanvas($('reference'),reference.image,reference.overlay);
  redrawSweep();
}
function makeSegments(){const [ny,nx]=result.shape;const canvas=document.createElement('canvas');canvas.width=nx;canvas.height=ny;
  const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(nx,ny);
  for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const label=labels[y*nx+x],i=((ny-1-y)*nx+x)*4;
    const color=label===result.target?[255,207,92]:label?[60+(label*67)%185,60+(label*113)%185,60+(label*41)%185]:[8,13,19];
    pixels.data[i]=color[0];pixels.data[i+1]=color[1];pixels.data[i+2]=color[2];pixels.data[i+3]=255;}
  ctx.putImageData(pixels,0,0);segmentImage=canvas;
}
async function useResult(r,saved=null){
  if(busy)return;
  if(r.processing_policy!=='fit_galaxy_crop_v1')throw Error('Run MTO again to process the Fit galaxy crop. Earlier files are preserved.');
  result=r;objectPage=0;$('findLabel').value='';setParams(r.params);selected=new Set(saved?.selected||r.objects.filter(o=>o.mask).map(o=>o.label));history=[];
  const buffer=await fetch(file('runs',r.run_id,'labels.bin')).then(r=>r.arrayBuffer());
  labels=new Uint32Array(buffer);makeSegments();clearAcceptance();
  if(saved){accepted=saved;$('confirm').checked=true;$('notes').value=saved.notes||'';$('saved').textContent='Restored saved mask '+saved.review_id;
    if(saved.display){$('stretch').value=saved.display.stretch;$('gamma').value=saved.display.gamma;$('stfShadows').value=saved.display.shadows;$('stfTarget').value=saved.display.target;stretchDisplay();}}
  drawObjects();await updateMask();updateButtons();
}
function drawObjects(){const body=$('objects');body.replaceChildren();if(!result)return;
  if(!result.sortedObjects)result.sortedObjects=[...result.objects].sort((a,b)=>Number(b.target)-Number(a.target)||Number(b.intersects_aoi)-Number(a.intersects_aoi)||b.pixels-a.pixels);
  const filter=$('findLabel').value;const objects=filter?result.sortedObjects.filter(o=>o.label===Number(filter)):result.sortedObjects;
  objectPage=Math.min(objectPage,Math.max(0,Math.ceil(objects.length/100)-1));
  $('objectCount').textContent=`${objects.length} objects · page ${objectPage+1} of ${Math.max(1,Math.ceil(objects.length/100))}. Largest objects first after target/AOI labels.`;
  $('objectsPrevious').disabled=objectPage===0;$('objectsNext').disabled=(objectPage+1)*100>=objects.length;
  for(const obj of objects.slice(objectPage*100,objectPage*100+100)){const row=document.createElement('tr');for(const value of [obj.label,obj.pixels,obj.intersects_aoi?'Inside / intersects':'Outside']){const td=document.createElement('td');td.textContent=value;row.append(td);}
    const td=document.createElement('td'),button=document.createElement('button');button.textContent=(selected.has(obj.label)?'Mask':'Retain')+(obj.target?' · centre label':'');button.disabled=busy;
    button.onclick=safe(()=>toggle(obj.label));td.append(button);row.append(td);body.append(row);}
}
async function updateMask(){if(!result)return;const version=++maskVersion;const summary=await api('/api/mask',{run_id:result.run_id,selected:[...selected]});
  const im=await picture('data:image/png;base64,'+summary.png);if(version!==maskVersion)return;overlay=im;
  $('metrics').replaceChildren();for(const [title,value] of [['Move factor',result.params.move_factor.toFixed(2)],['Masked in Fit galaxy area',(100*summary.aoi_masked_fraction).toFixed(1)+'%'],['Background σ',result.background.sigma.toPrecision(4)],['Detected objects',result.objects.length]]){
    const div=document.createElement('div');div.className='metric';div.textContent=title;const strong=document.createElement('strong');strong.textContent=value;div.append(strong);$('metrics').append(div);}
  render();
}
async function toggle(label){if(!result||busy)return;
  history.push([...selected]);if(selected.has(label))selected.delete(label);else selected.add(label);clearAcceptance();drawObjects();await updateMask();
  if(label===result.target&&selected.has(label))status('Centre label selected for masking. This excludes its entire connected segment; inspect how much galaxy light it contains.');}
async function start(action){
  if(action==='detect'&&unsaved()&&!window.confirm('Replace the current unsaved segmentation and object decisions?'))return;
  if(action==='refit'&&!accepted)throw Error('Accept and save a reviewed mask first.');
  const payload={action,object_id:galaxy.object_id,params:params()};
  if(action==='refit'){payload.review_id=accepted.review_id;payload.bounds={};for(const key of ['bar_min','bar_max','disc_min','disc_max'])payload.bounds[key]=Number($(key).value);}
  const job=await api('/api/job',payload);busy=true;updateButtons();drawObjects();
  if(action==='sweep'){$('sweepSection').hidden=false;$('sweepResults').replaceChildren();sweepViews=[];$('sweepProgress').textContent='Calculating 5 move-factor settings…';$('sweepSection').scrollIntoView({behavior:'smooth',block:'start'});}
  status('Calculating in an isolated worker…');poll(job.job_id);
}
async function poll(id){try{const job=await api('/api/job');if(job.job_id!==id)throw Error('Calculation was replaced by another browser session.');
  status(job.progress||'Calculation running…');
  if(job.action==='sweep')$('sweepProgress').textContent=`${job.results.length} of 5 calculations complete. ${job.progress||''}`;
  if(job.status==='running'){jobTimer=setTimeout(()=>poll(id),700);return;}
  busy=false;updateButtons();drawObjects();
  if(job.status==='failed'){if(job.results.length&&job.action==='sweep')await showSweep(job.results);throw Error(job.error);}
  if(job.object_id!==galaxy.object_id)return;
  if(job.action==='refit')showRefit(job.results[0]);else if(job.action==='sweep')await showSweep(job.results);else await useResult(job.results[0]);
  status(job.action==='refit'?'Refit complete. Inspect the provisional geometry below.':job.action==='sweep'?'Five move-factor previews are shown in the comparison panel. Choose Use result to inspect one.':'MTO complete. Review object decisions and the proposed mask before accepting.');
}catch(e){busy=false;updateButtons();status(e.message,true);}}
function redrawSweep(){if(!image||!galaxy||!view)return;for(const {r,img,mask} of sweepViews){
    const c=document.createElement('canvas');c.width=320;c.height=320;const ctx=c.getContext('2d');
    const scale=320/view.span,left=(-.5-view.x)*scale+160,top=(view.y-r.shape[0]+.5)*scale+160;
    const width=r.shape[1]*scale,height=r.shape[0]*scale;
    ctx.fillStyle='#080d13';ctx.fillRect(0,0,320,320);ctx.imageSmoothingEnabled=false;
    ctx.drawImage(image,left,top,width,height);
    ctx.drawImage(mask,left,top,width,height);img.src=c.toDataURL();
  }}
async function showSweep(results){$('sweepSection').hidden=false;$('sweepResults').replaceChildren();sweepViews=[];
  for(const r of results){const figure=document.createElement('figure'),caption=document.createElement('figcaption');caption.textContent='Move '+r.params.move_factor;
    const img=document.createElement('img');const summary=await api('/api/mask',{run_id:r.run_id,selected:r.objects.filter(o=>o.mask).map(o=>o.label)});
    const mask=await picture('data:image/png;base64,'+summary.png);sweepViews.push({r,img,mask});
    const stats=document.createElement('p');stats.className='hint';stats.textContent=`${(100*summary.aoi_masked_fraction).toFixed(1)}% masked · ${r.objects.length} objects`;
    const button=document.createElement('button');button.textContent='Use result';button.onclick=safe(async()=>{if(unsaved()&&!confirm('Replace unsaved object decisions?'))return;await useResult(r);status('Comparison result loaded. Review before saving.');});
    figure.append(caption,img,stats,button);$('sweepResults').append(figure);}redrawSweep();
  const p=results[0]?.params;
  $('sweepProgress').textContent=`${results.length} comparison results ready. Only move factor differs. Detection: ${p?.detect_on==='original+residual'?'Original + galaxy residual':'Original image'}; MTO FWHM ${p?.gaussian_fwhm}; dilation ${p?.dilation}; minimum area ${p?.minarea}${p?.detect_on==='original+residual'?'; galaxy sigma '+p.residual_sigma+'; compact residual maximum '+(p.residual_max_area??'not automatically proposed'):''}.`;
  $('sweepSection').scrollIntoView({behavior:'smooth',block:'start'});
}
function showRefit(r){$('refitSection').hidden=false;$('refitImage').src=file('refits',r.artifact_id,'geometry.png');
  if(r.proposed_ellipses){proposedEllipses=r.proposed_ellipses;render();}
  const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['Measurement','Previous reviewed value','Masked refit']){const th=document.createElement('th');th.textContent=label;head.append(th);}table.append(head);
  const format=value=>value===null||value===undefined||value===''?'Unavailable':Number(value).toFixed(2);
  for(const [label,key,old] of [['Disc PA (deg)','disc_pa_deg','adopted_disc_pa_deg'],['Inclination (deg)','inclination_deg','adopted_inclination_deg'],['Bar PA (deg)','bar_pa_deg','adopted_bar_pa_deg'],['Disc ellipticity','disc_ellipticity',null],['Accepted disc samples','n_disc',null],['Accepted bar samples','n_bar',null]]){
    const tr=document.createElement('tr');for(const value of [label,old?format(r.original_geometry[old]):'—',format(r[key])]){const td=document.createElement('td');td.textContent=value;tr.append(td);}table.append(tr);}
  $('refitMetrics').replaceChildren(table);for(const caution of r.cautions){const p=document.createElement('p');p.className='notice';p.textContent=caution;$('refitMetrics').append(p);}
  $('refitLinks').replaceChildren();for(const name of ['ellipse_profile.csv','result.json','geometry.png']){const a=document.createElement('a');a.href=file('refits',r.artifact_id,name);a.download=name;a.textContent=name;a.style.marginRight='18px';$('refitLinks').append(a);}
}
for(const canvas of canvases){let drag=null;
  canvas.addEventListener('wheel',event=>{if(!view)return;event.preventDefault();const before=xy(canvas,event),factor=event.deltaY>0?1.15:1/1.15;
    view.span=Math.min(Math.max(...galaxy.shape)*3,Math.max(8,view.span*factor));const after=xy(canvas,event);view.x+=before.x-after.x;view.y+=before.y-after.y;render();},{passive:false});
  canvas.addEventListener('pointerdown',event=>{if(!view)return;drag={x:event.clientX,y:event.clientY,startX:view.x,startY:view.y,moved:false};canvas.setPointerCapture(event.pointerId);});
  canvas.addEventListener('pointermove',event=>{if(!drag)return;const box=canvas.getBoundingClientRect(),dx=event.clientX-drag.x,dy=event.clientY-drag.y;
    if(Math.hypot(dx,dy)>4)drag.moved=true;if(drag.moved){view.x=drag.startX-dx/box.width*view.span;view.y=drag.startY+dy/box.height*view.span;render();}});
  canvas.addEventListener('pointerup',safe(async event=>{const moved=drag?.moved;drag=null;if(moved||!labels||!['segmentation','masked'].includes(canvas.id))return;
    const point=xy(canvas,event),x=Math.round(point.x),y=Math.round(point.y);if(x<0||y<0||x>=result.shape[1]||y>=result.shape[0])return;
    const label=labels[y*result.shape[1]+x];if(label)await toggle(label);else status('Background pixel: no detected object here.');}));
}
$('move').oninput=()=>{$('moveNumber').value=$('move').value;$('moveValue').value=Number($('move').value).toFixed(2);changed();};
$('moveNumber').oninput=()=>{$('move').value=$('moveNumber').value;$('moveValue').value=Number($('moveNumber').value).toFixed(2);changed();};
for(const id of ['dilation','minarea','detect_on','residual_sigma','residual_max_area',...Object.keys(advanced)])$(id).oninput=changed;
$('resetParams').onclick=()=>{setParams(config.defaults);changed();};
$('projectedPreset').onclick=()=>{setParams({...config.defaults,detect_on:'original+residual',residual_sigma:3,gaussian_fwhm:0,move_factor:.9,minarea:5,dilation:2,min_distance:0,residual_max_area:100});changed();status('Projected-source preset loaded. Click Run MTO to calculate a new proposed mask, including compact residual detections.');};
$('detect').onclick=safe(()=>start('detect'));$('sweep').onclick=safe(()=>start('sweep'));$('refit').onclick=safe(()=>start('refit'));
$('showComparison').onclick=safe(async()=>{const job=await api('/api/job');if(job.action!=='sweep'||job.object_id!==galaxy.object_id||!job.results?.length)throw Error('No comparison results are available for this galaxy in the current server session. Click Compare move to calculate them.');await showSweep(job.results);status(job.status==='complete'?'Last comparison reopened. Choose Use result to inspect a candidate.':'Showing the completed candidates from the last comparison.');});
$('galaxy').onchange=safe(async()=>{if(unsaved()&&!confirm('Leave the unsaved mask decisions?')){$('galaxy').value=galaxy.object_id;return;}await loadGalaxy();});
for(const [id,step] of [['previous',-1],['next',1]])$(id).onclick=safe(async()=>{if(unsaved()&&!confirm('Leave the unsaved mask decisions?'))return;const options=$('galaxy').options;$('galaxy').selectedIndex=($('galaxy').selectedIndex+step+options.length)%options.length;await loadGalaxy();});
$('restore').onclick=safe(async()=>{if(!galaxy.latest)throw Error('No saved review for this target.');if(unsaved()&&!confirm('Replace unsaved decisions with the saved review?'))return;
  const r=await api('/api/result?id='+galaxy.latest.run_id);await useResult(r,galaxy.latest);status('Saved mask and exact detection parameters restored.');});
$('undo').onclick=safe(async()=>{if(history.length){selected=new Set(history.pop());clearAcceptance();drawObjects();await updateMask();}});
$('resetObjects').onclick=safe(async()=>{history.push([...selected]);selected=new Set(result.objects.filter(o=>o.mask).map(o=>o.label));clearAcceptance();drawObjects();await updateMask();});
$('pin').onclick=()=>{reference={image,overlay};$('referenceSection').hidden=false;$('referenceInfo').textContent=`Move ${result.params.move_factor}; ${selected.size} masked labels. Frozen at time of pinning.`;render();};
$('unpin').onclick=()=>{reference=null;$('referenceSection').hidden=true;};
$('findLabel').oninput=()=>{objectPage=0;drawObjects();};
$('objectsPrevious').onclick=()=>{objectPage=Math.max(0,objectPage-1);drawObjects();};
$('objectsNext').onclick=()=>{objectPage++;drawObjects();};
$('confirm').onchange=updateButtons;
$('save').onclick=safe(async()=>{if(dirty)throw Error('Run MTO to apply the changed controls before saving.');accepted=await api('/api/save',{run_id:result.run_id,selected:[...selected],confirm:$('confirm').checked,notes:$('notes').value,
  display:{stretch:$('stretch').value,gamma:Number($('gamma').value),shadows:Number($('stfShadows').value),target:Number($('stfTarget').value)}});galaxy.latest=accepted;
  $('saved').replaceChildren(document.createTextNode('Saved. '));for(const name of ['mask.fits','review.json','mask_review.png']){const a=document.createElement('a');a.href=file('reviews',accepted.review_id,name);a.download=name;a.textContent=name+' ';$('saved').append(a);}updateButtons();status('Reviewed mask saved. The geometry refit can now use this exact mask.');});
$('fitView').onclick=fitView;$('fullView').onclick=fullView;$('zoomIn').onclick=()=>{view.span=Math.max(8,view.span/1.4);render();};$('zoomOut').onclick=()=>{view.span*=1.4;render();};
for(const id of ['stretch','gamma','stfShadows','stfTarget'])$(id).oninput=()=>{clearTimeout(displayTimer);displayTimer=setTimeout(stretchDisplay,80);};
$('resetDisplay').onclick=()=>{$('stretch').value='autostf';$('gamma').value=1;$('stfShadows').value=-2.8;$('stfTarget').value=.25;stretchDisplay();};
$('showEllipses').onchange=render;
for(const id of ['bar_min','bar_max','disc_min','disc_max'])$(id).oninput=render;
window.addEventListener('resize',render);window.addEventListener('beforeunload',event=>{if(unsaved()){event.preventDefault();event.returnValue='';}});
safe(async()=>{config=await api('/api/config');$('outputPath').textContent='Saved locally: '+config.output;
  for(const target of config.targets){const option=document.createElement('option');option.value=target.object_id;option.textContent=(target.name||target.object_id)+(target.challenge?' · close pair':'');$('galaxy').append(option);}await loadGalaxy();})();
