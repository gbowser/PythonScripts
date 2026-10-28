from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('if(finite(c.pa_scatter)&&disc.length){', 'if(finite(c.pa_scatter)&&disc.length>=3){',1)
needle=' return warnings;\n}\nfunction storedWarningNotes'
addition=''' for(const w of warnings){
  if(w.code==='ellipticity')w.comparison=`Δε = ${thresholdDescription(c.eps_span,r.eps_span)}`;
  if(w.code==='sampling')w.comparison=`n = ${c.n_disc} (minimum ${r.min_disc}); gap = ${fmt(c.max_gap_fraction*100,1)}% (limit ${fmt(r.max_gap*100,1)}%)`;
  if(w.code==='pa')w.comparison=`RMS = ${thresholdDescription(c.pa_scatter,r.pa_rms,'°',2)}`;
  if(w.code==='smallbar')w.comparison=`Outer radius ${fmt(settings.bar[1])}″; minimum ${fmt(r.small_bar)}″`;
  if(w.code==='bar'){w.comparison=`Grade ${c.bar_grade??'not accepted'}; peak ε ${fmt(c.bar_peak,3)}; drop ${fmt(c.bar_drop,3)}; PA RMS ${fmt(c.bar_scatter)}°`;
   const ordered=bar.slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec),smooth=ordered.map((p,i)=>median(ordered.slice(Math.max(0,i-1),Math.min(ordered.length,i+2)).map(z=>z.ellipticity)));
   if(ordered.length){const peak=ordered[smooth.indexOf(Math.max(...smooth))],beyond=g.profile.filter(p=>(p.used_for_geometry||(settings.pool==='marginal'&&p.marginal))&&p.sma_arcsec>peak.sma_arcsec&&p.sma_arcsec<=Math.max(2.5*peak.sma_arcsec,peak.sma_arcsec+1));if(beyond.length){w.peak={p:peak,eps:Math.max(...smooth)};w.low={p:beyond.reduce((a,b)=>a.ellipticity<b.ellipticity?a:b)};}}
  }
 }
 return warnings;
}
function storedWarningNotes'''
assert needle in s;s=s.replace(needle,addition,1)
s=s.replace('${esc(w.label)}</strong> — ${esc(w.status)}</summary>', '${esc(w.label)}</strong> — ${esc(w.status)}${w.comparison?`<span class="diagnostic-comparison">${esc(w.comparison)}</span>`:\'\'}</summary>')
needle="  if(mark)out+=`<g class=\"profile-warning\""
addition='''  if(w.code==='bar'&&id==='epsPlot'&&w.peak&&w.low){const a=w.peak.eps,b=w.low.p.ellipticity,bx=clamp(x(w.low.p.sma_arcsec)+9,left+8,right-10);mark+=arrow(bx,y(a),bx,y(b),color,'bar-drop-arrow')+note(bx+7,(y(a)+y(b))/2,`Bar drop = ${fmt(a-b,3)}`,color);}
'''
assert needle in s;s=s.replace(needle,addition+needle,1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/style.css');s=p.read_text(encoding='utf8');s+='\n.diagnostic-comparison{display:block;margin:3px 0 0 15px;color:#405966;font-size:11px}\n';p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_warning_profiles.mjs');s=p.read_text(encoding='utf8');s=s.replace("includes('Δε 0.250')", "includes('Δε = 0.250')");s=s.replace("assert.ok(!tool.profileWarningEvidence(g,S.settings,S.calc).some(w=>w.code==='ellipticity'));", "assert.equal(tool.profileWarningEvidence(g,S.settings,S.calc).find(w=>w.code==='ellipticity').status,'Screen disabled');assert.equal(tool.profileWarningEvidence(g,S.settings,S.calc).find(w=>w.code==='ellipticity').active,false);");p.write_text(s,encoding='utf8')
