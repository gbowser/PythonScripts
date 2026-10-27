from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('function drawProfiles(){','''function ellipseInclination(p){return finite(p.ellipticity)&&p.ellipticity>=0&&p.ellipticity<=1?Math.acos(1-p.ellipticity)*180/Math.PI:null;}
function paReferenceLevels(reference,min,max){if(!finite(reference))return [];const levels=[];for(let k=Math.ceil((min-reference)/180);k<=Math.floor((max-reference)/180);k++)levels.push(reference+180*k);return levels;}
function drawProfiles(){''',1)
s=s.replace("['paPlot','pa_sky_deg',180,", "['incPlot','inclination',90,'Inclination proxy (degrees; circular-disc assumption)'],['paPlot','pa_sky_deg',180,",1)
s=s.replace("const isPA=field==='pa_sky_deg',lo=isPA?paView.min:0,hi=isPA?paView.max:maxY,ticks=isPA?paView.ticks:[0,.25,.5,.75,1],value=p=>isPA?paView.values.get(p):p[field];", """const isPA=field==='pa_sky_deg',isInc=field==='inclination',reference=isPA?S.g.euclid?.disc_pa:isInc?S.g.euclid?.inclination:null;
 let lo=isPA?paView.min:0,hi=isPA?paView.max:maxY,ticks=isPA?[...paView.ticks]:isInc?[0,15,30,45,60,75,90]:[0,.25,.5,.75,1];
 if(isPA&&finite(reference)){const nearest=reference+180*Math.round(((lo+hi)/2-reference)/180),step=ticks[1]-ticks[0];while(nearest<lo){lo-=step;ticks.unshift(lo);}while(nearest>hi){hi+=step;ticks.push(hi);}}
 const value=p=>isPA?paView.values.get(p):isInc?ellipseInclination(p):p[field];""")
s=s.replace("${isPA?((Math.round(vy)%360)+360)%360:vy.toFixed(2)}", "${isPA?((Math.round(vy)%360)+360)%360:isInc?Math.round(vy):vy.toFixed(2)}")
needle=" let segments=[],current=[],previous=null;"
addition=''' if(isPA||isInc){
  const levels=isPA?paReferenceLevels(reference,lo,hi):finite(reference)&&reference>=0&&reference<=90?[reference]:[];
  for(const level of levels){const label=isPA?'Euclid source PA':'Euclid inclination proxy',canonical=isPA?((reference%180)+180)%180:reference;
   html+=`<line class="euclid-reference" x1="${left}" x2="${w-right}" y1="${y(level)}" y2="${y(level)}" stroke="#8a3996" stroke-width="1.6" stroke-dasharray="2 4"><title>${label}: ${fmt(canonical)}°${isPA?'; includes adopted +90° correction; equivalent axes repeat every 180°':''}</title></line><text class="euclid-reference-label" x="${w-right-4}" y="${clamp(y(level)-5,top+12,top+ph-4)}" text-anchor="end" style="fill:#8a3996">${label}: ${fmt(canonical)}°</text>`;
  }
  if(!levels.length)html+=`<text x="${w-right-4}" y="${top+12}" text-anchor="end" style="fill:#8a3996">Euclid: unavailable</text>`;
 }
'''
s=s.replace(needle,addition+needle,1)
s=s.replace('${field} ${fmt(p[field],3)}','${field} ${fmt(isInc?value(p):p[field],3)}')
s=s.replace("for(const id of ['epsPlot','paPlot'])", "for(const id of ['epsPlot','incPlot','paPlot'])")
s=s.replace('radiusAxis,profileImageWindow,','radiusAxis,ellipseInclination,paReferenceLevels,profileImageWindow,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<svg id="paPlot"','<svg id="incPlot" viewBox="0 0 660 215" aria-label="Inclination proxy profile"></svg><svg id="paPlot"',1)
s=s.replace('Drag a shaded edge in either graph,','Drag a shaded edge in any profile graph,')
s=s.replace('Solid blue lines show accepted samples', 'Purple dotted lines show the saved Euclid catalogue comparison: detection-shape inclination proxy and adjusted source PA (not a Euclid bar PA). Missing values are labelled unavailable. The inclination profile is calculated as i = acos(1 − ε), assuming a thin circular disc; values in the bar region are shape proxies, not disc-tilt measurements. Solid blue lines show accepted samples',1)
p.write_text(s,encoding='utf8')
