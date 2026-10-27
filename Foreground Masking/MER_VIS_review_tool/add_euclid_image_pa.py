from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('compass = {}\n            for angle', 'compass = {}\n            compass_pixel_basis = {}\n            for angle',1);s=s.replace('compass[label] = (vec/np.linalg.norm(vec)).tolist()', 'compass_pixel_basis[label] = vec.tolist()\n                compass[label] = (vec/np.linalg.norm(vec)).tolist()',1);s=s.replace('compass=compass, default_window=window, original=original,','compass=compass, compass_pixel_basis=compass_pixel_basis, default_window=window, original=original,',1);p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace("'excludedEllipses','showRejected'", "'excludedEllipses','euclidPAOverlay','showRejected'");s=s.replace("excludedEllipses:true,overlayMode", "excludedEllipses:true,euclidPAOverlay:true,overlayMode");pos=s.index('function drawImage(){');s=s[:pos]+'''// Local WCS pixel vectors retain projection scale and image handedness.
function skyPADirection(pa,basis){if(!finite(pa)||!basis?.N?.every(finite)||!basis?.E?.every(finite))return null;
 const angle=pa*Math.PI/180,dx=basis.N[0]*Math.cos(angle)+basis.E[0]*Math.sin(angle),dy=basis.N[1]*Math.cos(angle)+basis.E[1]*Math.sin(angle),length=Math.hypot(dx,dy);return length>0?[dx/length,dy/length]:null;
}
''' +s[pos:]
needle=' if(S.settings.display.centres){for(const [centre,color,cross]'
pos=s.index(needle)
s=s[:pos]+''' if(S.settings.display.euclidPAOverlay!==false&&S.g.centre?.every(finite)){
  const direction=skyPADirection(S.g.euclid?.disc_pa,S.g.compass_pixel_basis??S.g.compass);
  if(direction){const cx=t.x(S.g.centre[0]),cy=t.y(S.g.centre[1]),dx=direction[0]*t.w/(t.view[1]-t.view[0]),dy=-direction[1]*t.h/(t.view[3]-t.view[2]),norm=Math.hypot(dx,dy),length=2*Math.hypot(t.w,t.h);
   ctx.beginPath();ctx.setLineDash([2,5]);ctx.moveTo(cx-dx/norm*length,cy-dy/norm*length);ctx.lineTo(cx+dx/norm*length,cy+dy/norm*length);ctx.strokeStyle='#55aaff';ctx.lineWidth=1.8;ctx.stroke();ctx.setLineDash([]);
  }
 }
''' +s[pos:]
s=s.replace('const anchor=[t.left+45,t.top+t.h-45]', 'const anchor=[t.left+66,t.top+t.h-45]')
s=s.replace('ctx.fillText(label,anchor[0]+dx*1.25-4,anchor[1]+dy*1.25+4);', "ctx.textAlign='center';ctx.fillText(label==='N'?'N 0°':'E 90°',anchor[0]+dx*1.25,anchor[1]+dy*1.25+4);")
s=s.replace("'overlayMode','excludedEllipses'].includes(id)", "'overlayMode','excludedEllipses','euclidPAOverlay'].includes(id)")
s=s.replace('radiusAxis,ellipseInclination,','radiusAxis,skyPADirection,ellipseInclination,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<select id="overlayMode"', '<label class="check"><input id="euclidPAOverlay" type="checkbox" checked title="Blue dotted Euclid comparison PA through the adopted fitted centre"> Euclid PA (blue dotted)</label><select id="overlayMode"',1);s=s.replace('Green: selected disc.', 'Blue dotted line: Euclid comparison PA (including the adopted +90° adjustment), drawn through the adopted fitted centre; it follows the image WCS and is hidden if either value is unavailable. The yellow proposed centre does not move it until a refit is adopted. Compass: N 0°, E 90°. Green: selected disc.',1);p.write_text(s,encoding='utf8')
