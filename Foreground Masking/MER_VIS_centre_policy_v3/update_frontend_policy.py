from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace("'smallBarEnabled'];", "'smallBarEnabled','centreEnabled','centreCap','centreFraction','centreFloor'];",1)
s=s.replace("rules:{...S.boot.rules,sparse_enabled:true,pa_enabled:true,eps_enabled:true,small_bar_enabled:true}", "rules:{...S.boot.rules,sparse_enabled:true,pa_enabled:true,eps_enabled:true,small_bar_enabled:true,centre_enabled:!!g.centre_reference,centre_cap_native:3,centre_fraction:.05,centre_floor_native:1}",1)
needle=" const priorRefit=S.settings.refit_id??null;"
s=s.replace(needle," const centreDefaults=defaultSettings(g).rules;S.settings.rules={...centreDefaults,...S.settings.rules};if(g.centre_reference&&S.settings.centre_policy_version!=='MER_VIS_centre_policy_v3_pilot_2026-10-28'){S.settings.rules.centre_enabled=true;S.settings.centre_policy_version='MER_VIS_centre_policy_v3_pilot_2026-10-28';}\n"+needle,1)
s=s.replace("['smallBarEnabled','small_bar_enabled']", "['smallBarEnabled','small_bar_enabled'],['centreEnabled','centre_enabled']",1)
s=s.replace("['barThreshold','small_bar']", "['barThreshold','small_bar'],['centreCap','centre_cap_native'],['centreFraction','centre_fraction'],['centreFloor','centre_floor_native']",1)
# Show editable centre pilot settings with the other rule controls.
needle=" $('gammaValue').value="
# writeControls has its own fixed rule mapping; modify mappings everywhere above plus missing defaults.
s=s.replace("['small_bar','barThreshold']", "['small_bar','barThreshold'],['centre_cap_native','centreCap'],['centre_fraction','centreFraction'],['centre_floor_native','centreFloor']")
s=s.replace("function pool(){if(S.g.original.status==='fit_failed')return [];return S.g.profile.filter(p=>p.used_for_geometry||(S.settings.pool==='marginal'&&p.marginal));}", '''function centrePointStatus(p,g=S.g,settings=S.settings){
 if(!g?.centre_reference)return {accepted:true,available:false};const ref=g.centre_reference,r=settings.rules??{},scale=g.pixel_scale_arcsec,cap=r.centre_cap_native??3,fraction=r.centre_fraction??.05,floor=r.centre_floor_native??1;
 const valid=[p.x_original_pix,p.y_original_pix,p.sma_arcsec,ref.x,ref.y,scale,cap,fraction,floor].every(finite)&&scale>0&&p.sma_arcsec>0&&cap>=floor;
 if(!valid)return {accepted:false,available:false,reason:'Centre/radius coordinates unavailable or centre floor exceeds cap'};
 const offset=Math.hypot(p.x_original_pix-ref.x,p.y_original_pix-ref.y),limit=Math.min(cap,Math.max(floor,fraction*p.sma_arcsec/scale));return {accepted:offset<=limit+1e-9,available:true,offset,offset_arcsec:offset*scale,limit,limit_arcsec:limit*scale,reason:`Centre displacement ${fmt(offset,3)} native px (${fmt(offset*scale,3)}″); limit ${fmt(limit,3)} native px (${fmt(limit*scale,3)}″)`};
}
function numericalPool(g=S.g,settings=S.settings){if(g.original.status==='fit_failed')return [];return g.profile.filter(p=>p.used_for_geometry||(g.centre_reference&&p.numerically_accepted_strict)||(settings.pool==='marginal'&&(p.marginal||(g.centre_reference&&p.numerically_accepted_relaxed))));}
function pool(){return numericalPool().filter(p=>S.settings.rules?.centre_enabled===false||centrePointStatus(p).accepted);}
''')
s=s.replace("let issues=[];if(paPoints.length<3)", "const rawPoints=numericalPool(),rejectedDisc=selected(rawPoints,'disc').filter(p=>!points.includes(p)),rejectedBar=selected(rawPoints,'bar').filter(p=>!points.includes(p));\n let issues=[];if(paPoints.length<3)",1)
a=s.index(' else if(faceOn)issues.push');b=s.index(" if(r.eps_enabled",a)
s=s[:a]+''' if(faceOn)issues.push('Nearly face-on: PA ambiguity is informational');
 if(!faceOn){if(disc.length>=3&&r.sparse_enabled!==false&&sparse)issues.push('Sparse disc sampling');if(paPoints.length>=3&&r.pa_enabled!==false&&paScatter>r.pa_rms)issues.push('Disc PA varies across radius');}
 if(rejectedDisc.length||rejectedBar.length)issues.push(`Ellipse centre displacement: ${new Set([...rejectedDisc,...rejectedBar]).size} selected-range samples excluded`);
''' +s[b:]
s=s.replace('pa_scatter:paScatter,eps_span:', 'centre_rejected_disc:rejectedDisc,centre_rejected_bar:rejectedBar,pa_scatter:paScatter,eps_span:',1)
# Bar-drop diagnostics must use the same filtered pool.
s=s.replace("(p.used_for_geometry||(settings.pool==='marginal'&&p.marginal))&&p.sma_arcsec", "numericalPool(g,settings).includes(p)&&(settings.rules?.centre_enabled===false||centrePointStatus(p,g,settings).accepted)&&p.sma_arcsec")
needle=" if(!settings.noBar&&settings.bar.every(finite)){"
s=s.replace(needle," if((c.centre_rejected_disc?.length??0)+(c.centre_rejected_bar?.length??0)>0){add('centre','Ellipse centres displaced',`${c.centre_rejected_disc?.length??0} disc and ${c.centre_rejected_bar?.length??0} bar samples in the selected intervals were excluded by the common centre reference. Pilot cap ${fmt(r.centre_cap_native??3)} native px; fractional limit ${fmt((r.centre_fraction??.05)*100,1)}%; small-radius floor ${fmt(r.centre_floor_native??1)} native px. Excluded points retain a red outline and displacement details in the tooltip.`,[...new Set([...(c.centre_rejected_disc??[]),...(c.centre_rejected_bar??[])])],true);}\n"+needle,1)
s=s.replace("if(w.code==='sampling'){mark+=", "if(w.code==='centre'){mark+=w.points.map(p=>ring(p,'#cf3434')).join('');mark+=note(left+8,top+ph-48,`Centre-rejected: ${w.points.length}`,'#cf3434');}\n  if(w.code==='sampling'){mark+=",1)
s=s.replace("const color=ok?(p.used_for_geometry?", "const centreStatus=centrePointStatus(p),color=ok?(p.used_for_geometry?",1)
s=s.replace("; centre offset ${fmt(p.centre_offset_fit_pix)} fit pixels;", "; ${centreStatus.available?centreStatus.reason:'centre comparison unavailable'}; original fit-reference offset ${fmt(p.centre_offset_fit_pix)} fit pixels;")
s=s.replace("calculate,paComparisonDescription,", "calculate,centrePointStatus,numericalPool,paComparisonDescription,",1)
# Send the same policy used by the interactive pool into every new refit.
s=s.replace("lock_centre:$('lockCentre').checked", "lock_centre:$('lockCentre').checked,centre_policy:{cap_native_pixels:S.settings.rules.centre_cap_native??3,fraction_radius:S.settings.rules.centre_fraction??.05,floor_native_pixels:S.settings.rules.centre_floor_native??1}")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');needle='  <div><label class="check"><input id="smallBarEnabled"';a=s.index(needle);b=s.index('\n',a)
s=s[:b]+'''\n  <div><label class="check"><input id="centreEnabled" type="checkbox" checked> Centre acceptance screen</label><label>Absolute cap (native pixels)<input id="centreCap" type="number" min="0.5" max="20" step="0.5" value="3"></label><label>Fraction of ellipse radius<input id="centreFraction" type="number" min="0.005" max="0.5" step="0.005" value="0.05"></label><label>Small-radius floor (native pixels)<input id="centreFloor" type="number" min="0" max="5" step="0.25" value="1"></label><p class="small">Pilot settings: offset ≤ min(cap, max(floor, fraction × radius)). Same reference and centre limit for accepted and marginal pools. Fixed-centre fits have zero drift by constraint and still need image review.</p></div>''' +s[b:]
s=s.replace('These are review screens, not calibrated confidence tests.', 'Centre acceptance uses the displayed explicit reference, in native pixels; displaced samples are excluded from the calculation. The centre limits are pilot settings for review. Other screens describe uncertainty, not calibrated confidence tests.')
p.write_text(s,encoding='utf8')
