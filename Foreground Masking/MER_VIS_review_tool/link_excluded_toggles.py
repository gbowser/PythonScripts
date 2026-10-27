from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('if(S.settings.display.excludedEllipses!==false){','if(S.settings.display.excludedEllipses!==false&&S.settings.display.showRejected!==false){');s=s.replace("if(id==='showRejected'||id==='unwrapPA')drawProfiles();", "if(id==='showRejected'){drawProfiles();drawImage();}else if(id==='unwrapPA')drawProfiles();");p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('id="showRejected" type="checkbox" checked','id="showRejected" type="checkbox" checked title="Show or hide excluded points and dashed trends in the graphs, and excluded dashed ellipses on the FITS image"');s=s.replace('Red dashed ellipses: excluded measurements,','Red dashed ellipses: also controlled by “Show grey excluded points”; excluded measurements,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_excluded_ellipses.mjs');s=p.read_text(encoding='utf8');s+='''
S.settings.display.ellipses=true;S.settings.display.excludedEllipses=true;
let profileRedraws=0;c.drawProfiles=()=>{profileRedraws++};c.saveDraft=()=>{};
const toggle=nodes.get('showRejected');toggle.type='checkbox';toggle.checked=false;strokes.length=0;toggle.oninput();
assert.equal(profileRedraws,1);assert.equal(S.settings.display.showRejected,false);assert.ok(!strokes.some(x=>x.color==='#e26060'));assert.ok(strokes.some(x=>x.color==='#65d095'));
toggle.checked=true;strokes.length=0;toggle.oninput();assert.equal(profileRedraws,2);assert.ok(strokes.some(x=>x.color==='#e26060'));
S.settings.display.excludedEllipses=false;strokes.length=0;toggle.oninput();assert.ok(!strokes.some(x=>x.color==='#e26060'));
console.log('PASS: Show grey excluded points redraws both views and gates red ellipses while preserving the image-specific switch.');
''';p.write_text(s,encoding='utf8')
