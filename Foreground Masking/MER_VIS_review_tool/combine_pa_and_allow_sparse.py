from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace("'euclidPAOverlay','discPAOverlay'", "'paComparison'",1)
s=s.replace('euclidPAOverlay:false,discPAOverlay:false','paComparison:false')
s=s.replace('const pa=weightedPA(disc),paScatter=', 'const paPoints=disc.filter(p=>finite(p.pa_sky_deg)),pa=weightedPA(paPoints),paScatter=')
s=s.replace("if(disc.length<3)issues.push('Fewer than three disc ellipses: no trial disc geometry');", "if(paPoints.length<3)issues.push(paPoints.length?'Fewer than three disc ellipses: Disc PA provisional; inclination requires three selected ellipses':'Fewer than three disc ellipses: no usable Disc PA');")
s=s.replace('return {disc_pa:disc.length>=3?pa:null,', 'return {disc_pa:paPoints.length?pa:null,n_disc_pa:paPoints.length,disc_pa_provisional:paPoints.length>0&&paPoints.length<3,')
s=s.replace('<td>${deg(b)}</td><td>${name===', '<td>${deg(b)}${name===\'Disc PA\'&&c.disc_pa_provisional?` <span class="issue info" title="Based on ${c.n_disc_pa} usable selected ellipse(s)">Provisional: n=${c.n_disc_pa}</span>`:\'\'}</td><td>${name===',1)
s=s.replace("['PA RMS scatter',deg(c.pa_scatter)]", "['PA RMS scatter',c.n_disc_pa>=3?deg(c.pa_scatter):'Not assessed (<3 PA samples)']",1)
s=s.replace('Fewer than 3: no trial disc geometry. ', 'Fewer than 3: a provisional Disc PA is shown when a usable ellipse exists; inclination still requires three selected ellipses. ')
s=s.replace('S.settings.display.discPAOverlay!==false', 'S.settings.display.paComparison===true')
s=s.replace('S.settings.display.euclidPAOverlay!==false', 'S.settings.display.paComparison===true')
s=s.replace("if(isPA||isInc){", "if((isPA&&S.settings.display.paComparison===true)||isInc){",1)
s=s.replace("reference=isPA?S.g.euclid?.disc_pa:isInc?S.g.euclid?.inclination:null", "reference=isPA?(S.settings.display.paComparison===true?S.g.euclid?.disc_pa:null):isInc?S.g.euclid?.inclination:null",1)
s=s.replace("if(id==='showRejected'||id==='discPAOverlay')", "if(id==='showRejected'||id==='paComparison')")
s=s.replace(",'euclidPAOverlay'].includes(id)", "].includes(id)")
pos=s.index('function drawProfiles(){');s=s[:pos]+'''function paComparisonDescription(g,c){
 const count=c?.n_disc_pa??c?.n_disc??0,parts=[];
 parts.push(finite(c?.disc_pa)?`Calculated Disc PA ${fmt(c.disc_pa)}° (green dashed; ${count} ellipse${count===1?'':'s'}${count<3?'; provisional':''}).`:'Calculated Disc PA unavailable: no usable selected ellipse.');
 parts.push(finite(g.euclid?.disc_pa)?`Euclid comparison ${fmt(g.euclid.disc_pa)}° (blue dotted on image; purple dotted on profile).`:'Euclid PA unavailable in the catalogue comparison.');
 if(!g.centre?.every(finite))parts.push('Image lines require an adopted fitted centre.');
 return parts.join(' ');
}
''' +s[pos:]
s=s.replace("function drawProfiles(){\n const warnings=", "function drawProfiles(){\n $('paComparisonStatus').hidden=S.settings.display.paComparison!==true;$('paComparisonStatus').textContent=S.settings.display.paComparison===true?paComparisonDescription(S.g,S.calc):'';\n const warnings=",1)
s=s.replace('calculate,thresholdDescription,', 'calculate,paComparisonDescription,thresholdDescription,',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');a=s.index('<label class="check"><input id="euclidPAOverlay"');b=s.index('<select id="overlayMode"',a);s=s[:a]+'''<label class="check"><input id="paComparison" type="checkbox" title="Show both Euclid and current-selection Disc PA lines on the image and PA profile"> Disc PA comparison (Euclid + calculated)</label>'''+s[b:]
row=next(line for line in s.splitlines() if 'id="paComparison"' in line);s=s.replace(row,row+'\n   <p id="paComparisonStatus" class="small" role="status" hidden></p>',1)
s=s.replace('It updates with the selected ellipses and is hidden when no disc PA is available.', 'One usable selected ellipse is sufficient for Disc PA; one- and two-ellipse results are labelled provisional. The shared Disc PA comparison checkbox controls both calculated and Euclid PA lines on the image and PA profile. It updates with the selected ellipses and is hidden when no disc PA is available.')
p.write_text(s,encoding='utf8')
