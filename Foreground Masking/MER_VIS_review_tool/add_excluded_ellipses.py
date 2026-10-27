from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace("'ellipses','centres','overlayMode','showRejected'","'ellipses','centres','overlayMode','excludedEllipses','showRejected'")
s=s.replace("centres:true,overlayMode:'selected'","centres:true,excludedEllipses:true,overlayMode:'selected'")
start=s.index(' if(S.settings.display.ellipses){const disc=')
end=s.index('\n if(S.settings.display.centres)',start)
s=s[:start]+''' if(S.settings.display.ellipses){
  const disc=new Set(S.calc.disc),bar=new Set(S.calc.bar),accepted=pool(),acceptedSet=new Set(accepted);
  const usable=p=>finite(p.x_original_pix)&&finite(p.y_original_pix)&&finite(p.pa_pixel_deg)&&finite(p.sma_arcsec)&&p.sma_arcsec>0&&finite(p.ellipticity)&&p.ellipticity>=0&&p.ellipticity<1;
  const outline=(p,color,dashed)=>{const a=p.sma_arcsec/S.g.pixel_scale_arcsec,rx=a*t.w/(t.view[1]-t.view[0]),ry=rx*(1-p.ellipticity);ctx.beginPath();ctx.setLineDash(dashed?[5,4]:[]);ctx.ellipse(t.x(p.x_original_pix),t.y(p.y_original_pix),Math.max(.1,rx),Math.max(.1,ry),-p.pa_pixel_deg*Math.PI/180,0,Math.PI*2);ctx.strokeStyle=color;ctx.lineWidth=dashed?1.3:1.1;ctx.stroke();};
  // Same rejected pool and radial extent as the profile graphs; never adopted geometry.
  if(S.settings.display.excludedEllipses!==false){const rejected=S.g.profile.filter(p=>!acceptedSet.has(p)&&p.sma_arcsec<=plotMax()&&usable(p)),stride=Math.max(1,Math.ceil(rejected.length/50));for(const [i,p] of rejected.entries())if(i%stride===0)outline(p,'#e26060',true);}
  let points=accepted.filter(p=>S.settings.display.overlayMode==='accepted'||disc.has(p)||bar.has(p));const stride=Math.max(1,Math.ceil(points.length/50));points=points.filter((p,i)=>i%stride===0||disc.has(p)||bar.has(p));for(const p of points)if(usable(p))outline(p,disc.has(p)?'#65d095':bar.has(p)?'#ffc35d':'#65c6db',false);
  ctx.setLineDash([]);
 }''' +s[end:]
s=s.replace("['ellipses','centres','overlayMode'].includes(id)","['ellipses','centres','overlayMode','excludedEllipses'].includes(id)")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<select id="overlayMode"','<label class="check"><input id="excludedEllipses" type="checkbox" checked> Excluded (red dashed)</label><select id="overlayMode"');s=s.replace('Green: selected disc. Orange: selected candidate bar.','Green: selected disc. Orange: selected candidate bar. Red dashed ellipses: excluded measurements, using each measurement’s fitted centre and angle; these are not adopted geometry. Up to 50 excluded outlines are shown within the profile graph’s radial extent.');p.write_text(s,encoding='utf8')
