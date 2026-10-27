from pathlib import Path
p=Path('MER_VIS_review_tool/app.js')
s=p.read_text(encoding='utf8')
needle=" html+=segments.map(path=>`<polyline"
pos=s.index(needle)
addition=''' // Dashed segments expose rejected trends, with accepted neighbours as anchors.
 // They are visual evidence only and never enter pool() or calculate().
 if($('showRejected').checked){let previous=null;for(const p of S.g.profile.slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec)){
  if(!finite(value(p))||!finite(p.sma_arcsec)||p.sma_arcsec>xmax){previous=null;continue;}
  if(previous&&(!acceptedSet.has(previous)||!acceptedSet.has(p))&&!(isPA&&!paView.unwrapped&&Math.abs(p[field]-previous[field])>90))html+=`<line class="excluded-trend" x1="${x(previous.sma_arcsec)}" y1="${y(value(previous))}" x2="${x(p.sma_arcsec)}" y2="${y(value(p))}" stroke="#c84b4b" stroke-width="1.3" stroke-dasharray="5 4" opacity=".8"><title>Excluded-sample trend; not used in geometry calculations</title></line>`;
  previous=p;
 }}
'''
s=s[:pos]+addition+s[pos:]
s=s.replace("; PA error ${fmt(p.pa_error_deg)}°; stop ${p.stop_code}</title>","; PA error ${fmt(p.pa_error_deg)}°; ellipticity error ${fmt(p.ellipticity_error,3)}; usable coverage ${fmt(p.sampled_fraction*100,1)}%; valid ${p.valid}; centre offset ${fmt(p.centre_offset_fit_pix)} fit pixels; stop ${p.stop_code}${!ok?(p.marginal?'; eligible for exploratory marginal pool':'; not eligible for exploratory marginal pool'):''}</title>")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('Lines break across excluded samples.','Solid blue lines show accepted samples and break at exclusions. Grey dots and red dashed segments show excluded measurements, joined to their nearest measured neighbours for comparison only. A continuous dashed trend does not automatically qualify a fit for use. Hover over points for fit diagnostics.');p.write_text(s,encoding='utf8')
