from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace("'euclidPAOverlay','showRejected'", "'euclidPAOverlay','discPAOverlay','showRejected'");s=s.replace('euclidPAOverlay:true,overlayMode', 'euclidPAOverlay:true,discPAOverlay:true,overlayMode')
s=s.replace("if(isPA&&discVisible&&finite(reference)){const nearest=reference+180*Math.round(((lo+hi)/2-reference)/180),step=ticks[1]-ticks[0];while(nearest<lo){lo-=step;ticks.unshift(lo);}while(nearest>hi){hi+=step;ticks.push(hi);}}", "if(isPA&&discVisible)for(const pa of [reference,...(S.settings.display.discPAOverlay!==false?[S.calc?.disc_pa]:[])].filter(finite)){const nearest=pa+180*Math.round(((lo+hi)/2-pa)/180),step=ticks[1]-ticks[0];while(nearest<lo){lo-=step;ticks.unshift(lo);}while(nearest>hi){hi+=step;ticks.push(hi);}}")
needle=' let segments=[],current=[],previous=null;'
addition=''' if(isPA&&discVisible&&S.settings.display.discPAOverlay!==false&&finite(S.calc?.disc_pa)){
  const start=x(clamp(discBounds[0],0,xmax)),end=x(clamp(discBounds[1],0,xmax));
  for(const level of paReferenceLevels(S.calc.disc_pa,lo,hi))html+=`<line class="disc-pa-reference" x1="${start}" x2="${end}" y1="${y(level)}" y2="${y(level)}" stroke="#3ddc84" stroke-width="1.8" stroke-dasharray="7 4"><title>Current-selection disc PA: ${fmt(S.calc.disc_pa)}°; equivalent axes repeat every 180°</title></line>${end-start>=130?`<text x="${end-4}" y="${clamp(y(level)+14,top+12,top+ph-4)}" text-anchor="end" style="fill:#19794c">Disc: ${fmt(S.calc.disc_pa)}°</text>`:''}`;
 }
'''
assert needle in s;s=s.replace(needle,addition+needle,1)
a=s.index(' if(S.settings.display.euclidPAOverlay!==false&&S.g.centre?.every(finite)){');b=s.index('\n if(S.settings.display.centres)',a)
s=s[:a]+''' if(S.g.centre?.every(finite))for(const [enabled,pa,color,dash] of [[S.settings.display.euclidPAOverlay!==false,S.g.euclid?.disc_pa,'#55aaff',[2,5]],[S.settings.display.discPAOverlay!==false,S.calc?.disc_pa,'#3ddc84',[7,4]]]){
  const direction=enabled?skyPADirection(pa,S.g.compass_pixel_basis??S.g.compass):null;
  if(direction){const cx=t.x(S.g.centre[0]),cy=t.y(S.g.centre[1]),dx=direction[0]*t.w/(t.view[1]-t.view[0]),dy=-direction[1]*t.h/(t.view[3]-t.view[2]),norm=Math.hypot(dx,dy),length=2*Math.hypot(t.w,t.h);
   ctx.beginPath();ctx.setLineDash(dash);ctx.moveTo(cx-dx/norm*length,cy-dy/norm*length);ctx.lineTo(cx+dx/norm*length,cy+dy/norm*length);ctx.strokeStyle=color;ctx.lineWidth=1.8;ctx.stroke();ctx.setLineDash([]);
  }
 }''' +s[b:]
s=s.replace("if(id==='showRejected'){drawProfiles();drawImage();}", "if(id==='showRejected'||id==='discPAOverlay'){drawProfiles();drawImage();}")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<select id="overlayMode"','<label class="check"><input id="discPAOverlay" type="checkbox" checked title="Current-selection disc PA, green dashed on the FITS image and PA profile"> Disc PA (green dashed)</label><select id="overlayMode"',1);s=s.replace('Blue dotted line: Euclid comparison PA', 'Green dashed line: current-selection Disc PA from the table, through the adopted fitted centre on the image and restricted to the green disc interval in the PA profile. It updates with the selected ellipses and is hidden when no disc PA is available. Blue dotted line: Euclid comparison PA',1);p.write_text(s,encoding='utf8')
