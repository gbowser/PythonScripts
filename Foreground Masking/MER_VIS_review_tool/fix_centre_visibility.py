from pathlib import Path
for folder in [Path('MER_VIS_review_tool')]:
 p=folder/'app.js';s=p.read_text(encoding='utf8');assert 'if(S.proposedCentre?.every(finite))' in s;s=s.replace('if(S.proposedCentre?.every(finite))','if(S.settings.display.centres&&S.proposedCentre?.every(finite))')
 s=s.replace("S.pickingCentre=!S.pickingCentre;$('pickCentre').textContent", "S.pickingCentre=!S.pickingCentre;if(S.pickingCentre){S.settings.display.centres=true;$('centres').checked=true;}$('pickCentre').textContent")
 p.write_text(s,encoding='utf8')
 p=folder/'index.html';s=p.read_text(encoding='utf8');s=s.replace('id="centres" type="checkbox" checked','id="centres" type="checkbox" checked title="Show or hide all centre crosses, including the yellow proposed centre"');s=s.replace('white ×: catalogue position. Display stretch', 'white ×: catalogue position; yellow +: proposed centre for a retry. Centre markers shows or hides all three. Display stretch');p.write_text(s,encoding='utf8')
