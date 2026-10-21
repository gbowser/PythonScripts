from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace('async function loadGalaxy(id){saveDraft();','async function loadGalaxy(id,requestedRefit=undefined){saveDraft();')
s=s.replace("const g=await api('/api/galaxy?id='+encodeURIComponent(id));if(request!==S.galaxyRequest)return;", "let g=await api('/api/galaxy?id='+encodeURIComponent(id));const draftBefore=drafts()[id],savedBefore=g.review;const refitId=requestedRefit!==undefined?requestedRefit:(draftBefore?.settings?.refit_id??savedBefore?.settings?.refit_id??JSON.parse(localStorage.getItem(storageKey('refits'))??'{}')[id]);if(refitId)g=await api('/api/galaxy?id='+encodeURIComponent(id)+'&refit='+encodeURIComponent(refitId));if(request!==S.galaxyRequest)return;")
s=s.replace(" if(S.settings.display.defaultVersion!==2)", " const priorRefit=S.settings.refit_id??null;if(priorRefit!==(g.refit?.job_id??null)){const defaults=defaultSettings(g);for(const key of ['disc','bar','editedDisc','editedBar','noBar','pool'])S.settings[key]=defaults[key];}S.settings.refit_id=g.refit?.job_id??null;\n if(S.settings.display.defaultVersion!==2)")
s=s.replace(" localStorage.setItem(storageKey('last_galaxy'),id);queue();", " initCentreControls();localStorage.setItem(storageKey('last_galaxy'),id);queue();")
s=s.replace("$('originalFlags').textContent=(g.original.status", "$('originalFlags').textContent=(g.refit?'MANUAL CENTRE REFIT · ':'')+(g.original.status")
s=s.replace("const rows=[['Disc PA',g.original.disc_pa,c.disc_pa,g.euclid.disc_pa,true],['Inclination',g.original.inclination,c.inclination,g.euclid.inclination,false],['Bar PA',g.original.bar_pa,c.bar_pa,null,true]];", "const base=g.pipeline_original??g.original;const rows=[['Disc PA',base.disc_pa,c.disc_pa,g.euclid.disc_pa,true],['Inclination',base.inclination,c.inclination,g.euclid.inclination,false],['Bar PA',base.bar_pa,c.bar_pa,null,true]];")
s=s.replace("const canvas=$('image');let pan=null;", "const canvas=$('image');let pan=null;\nfunction imagePixel(t,clientX,clientY){const px=clientX-t.rect.left,py=clientY-t.rect.top;return [t.view[0]+(px-t.left)/t.w*(t.view[1]-t.view[0]),t.view[3]-(py-t.top)/t.h*(t.view[3]-t.view[2])];}")
s=s.replace("canvas.onpointerdown=e=>{if(!S.imageMeta)return;pan=", "canvas.onpointerdown=e=>{if(!S.imageMeta)return;if(S.pickingCentre){const [x,y]=imagePixel(imageTransform(),e.clientX,e.clientY);if(x<0||y<0||x>S.g.shape[1]-1||y>S.g.shape[0]-1){toast('Click inside the FITS image');return;}setProposedCentre(x,y);S.pickingCentre=false;$('pickCentre').textContent='Pick centre on image';canvas.style.cursor='';drawImage();return;}pan=")
s=s.replace(" // Native WCS compass, never a forced image rotation.", " if(S.proposedCentre?.every(finite)){const [cx,cy]=S.proposedCentre,x=t.x(cx),y=t.y(cy);ctx.strokeStyle='#ffe347';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x-8,y);ctx.lineTo(x+8,y);ctx.moveTo(x,y-8);ctx.lineTo(x,y+8);ctx.stroke();}\n // Native WCS compass, never a forced image rotation.")
insert='''
function setProposedCentre(x,y){S.proposedCentre=[x,y];$('centreX').value=x.toFixed(2);$('centreY').value=y.toFixed(2);S.settings.proposed_centre=[x,y];saveDraft();drawImage();}
function initCentreControls(){S.pickingCentre=false;pan=null;canvas.style.cursor='';$('pickCentre').textContent='Pick centre on image';S.proposedCentre=S.settings.proposed_centre??(S.g.refit?[S.g.refit.x,S.g.refit.y]:S.g.centre.every(finite)?S.g.centre:S.g.catalogue_centre);$('centreX').max=S.g.shape[1]-1;$('centreY').max=S.g.shape[0]-1;$('centreX').value=S.proposedCentre[0].toFixed(2);$('centreY').value=S.proposedCentre[1].toFixed(2);$('lockCentre').checked=S.g.refit?.lock_centre??true;const refits=JSON.parse(localStorage.getItem(storageKey('refits'))??'{}');$('showRefit').hidden=!refits[S.id]||refits[S.id]===S.g.refit?.job_id;$('showOriginal').disabled=!S.g.refit;$('refitStatus').textContent=S.g.refit?`Showing manual-centre refit from ${S.g.refit.requested_utc}. Status: ${S.g.original.status}. Full metrics and provenance saved in ${S.g.refit.folder}`:'Original pipeline result. Pick a centre and recompute; results are stored separately.';}
$('pickCentre').onclick=()=>{S.pickingCentre=!S.pickingCentre;$('pickCentre').textContent=S.pickingCentre?'Click nucleus in image — cancel':'Pick centre on image';canvas.style.cursor=S.pickingCentre?'crosshair':'';};
$('catalogueCentre').onclick=()=>setProposedCentre(...S.g.catalogue_centre);
for(const id of ['centreX','centreY'])$(id).onchange=()=>{const x=$('centreX').valueAsNumber,y=$('centreY').valueAsNumber;if(!finite(x)||!finite(y)||x<0||y<0||x>S.g.shape[1]-1||y>S.g.shape[0]-1){showError('Centre must be inside the original FITS image');return;}clearError();setProposedCentre(x,y);};
$('showOriginal').onclick=()=>loadGalaxy(S.id,null);
$('showRefit').onclick=()=>loadGalaxy(S.id,JSON.parse(localStorage.getItem(storageKey('refits'))??'{}')[S.id]);
$('runRefit').onclick=async()=>{
 const id=S.id,x=$('centreX').valueAsNumber,y=$('centreY').valueAsNumber;
 if(!finite(x)||!finite(y)){showError('Choose a finite centre first');return;}
 clearError();$('runRefit').disabled=true;S.pickingCentre=false;canvas.style.cursor='';$('pickCentre').textContent='Pick centre on image';
 try{const job=await api('/api/refit',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify({object_id:id,x,y,lock_centre:$('lockCentre').checked})});
  S.settings.proposed_centre=[x,y];saveDraft();let finished=false;
  while(!finished){await new Promise(resolve=>setTimeout(resolve,1200));const status=await api('/api/refit?job='+job.job_id);if(S.id===id)$('refitStatus').textContent=status.message;
   if(status.status==='error')throw new Error(status.message);
   if(status.status==='complete'){finished=true;const refits=JSON.parse(localStorage.getItem(storageKey('refits'))??'{}');refits[id]=job.job_id;localStorage.setItem(storageKey('refits'),JSON.stringify(refits));if(S.id===id){await loadGalaxy(id,job.job_id);markDirty();}toast(status.galaxy.original.status==='fit_failed'?'Retry finished but fit still failed. Inspect the reason.':'New fit ready. Inspect the ellipses and flags, then save your assessment.');}
  }
 }catch(e){showError(e);$('refitStatus').textContent='Refit could not complete: '+e.message;}finally{$('runRefit').disabled=false;}
};
'''
s=s.replace("async function saveReview(next=false)",insert+"\nasync function saveReview(next=false)")
s=s.replace('loadGalaxy,midtonesTransfer','loadGalaxy,imagePixel,midtonesTransfer')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('                        information=row.get', '''                        n_good=number(row.get('codex_n_good')), n_isophotes=number(row.get('codex_n_isophotes')),
                        centre_offset=number(row.get('codex_centre_offset_arcsec')), centre_scatter=number(row.get('codex_centre_scatter_arcsec')),
                        radius=number(row.get('codex_radius_arcsec')), method=row.get('codex_method',''),
                        n_bar=number(row.get('codex_n_bar')), binning=number(row.get('codex_binning')),
                        masked_fraction=number(row.get('codex_masked_fraction')), calculation_seconds=number(row.get('calculation_seconds')),
                        information=row.get''');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace(" $('evidence').innerHTML=evidence.map", " evidence.push(['Adopted centre X / Y',g.centre.every(finite)?g.centre.map(v=>fmt(v)).join(' / ')+' native pixels':'Not adopted'],['Centre offset from catalogue',deg(null).replace('—',fmt(g.original.centre_offset)+'″')],['Centre scatter',fmt(g.original.centre_scatter)+'″'],['Accepted / measured isophotes',`${g.original.n_good??'—'} / ${g.original.n_isophotes??'—'}`],['Fit method',g.original.method||'—'],['Fit time',finite(g.original.calculation_seconds)?fmt(g.original.calculation_seconds,1)+' s':'—']);\n $('evidence').innerHTML=evidence.map")
p.write_text(s,encoding='utf8')
