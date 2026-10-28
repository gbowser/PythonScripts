from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace("document.querySelector('input[name=editMode]:checked').value===kind", "S.drag?.kind===kind")
s=s.replace('function chooseProfileBoundary(settings,radius,axisMax,preferred,explicit=null){', 'function chooseProfileBoundary(settings,radius,axisMax,explicit=null){')
s=s.replace(".sort((a,b)=>a.distance-b.distance||(a.kind===preferred?-1:1))", ".sort((a,b)=>a.distance-b.distance)")
s=s.replace(" if(!available.includes(preferred))return null;\n return {kind:preferred,edge:Math.abs(radius-settings[preferred][0])<Math.abs(radius-settings[preferred][1])?0:1,snap:false};", " return null;")
s=s.replace("const preferred=document.querySelector('input[name=editMode]:checked').value,handle=", "const handle=")
s=s.replace('chooseProfileBoundary(S.settings,x,axisMax,preferred,explicit)', 'chooseProfileBoundary(S.settings,x,axisMax,explicit)')
s=s.replace('if(!choice){toast(\'Uncheck “Treat as no convincing bar” to edit the bar interval.\');return;}const {kind,edge}=choice;document.querySelector(`input[name=editMode][value="${kind}"]`).checked=true;', 'if(!choice)return;const {kind,edge}=choice;')
s=s.replace("document.querySelectorAll('input[name=editMode]').forEach(r=>r.onchange=drawProfiles);\n",'')
assert 'editMode' not in s
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<span>Edit interval</span><label><input name="editMode" type="radio" value="disc" checked> Disc</label><label><input name="editMode" type="radio" value="bar"> Bar</label>','');s=s.replace('Clicking near a boundary selects its interval automatically; elsewhere the Edit interval selector applies.', 'Dragging near a boundary selects it directly. Clicking elsewhere in a graph does not move any boundary.');assert 'editMode' not in s;p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_pa_continuity.mjs');s=p.read_text(encoding='utf8');s=s.replace("chooseProfileBoundary(S.settings,1,6,'disc')", "chooseProfileBoundary(S.settings,1,6)").replace("chooseProfileBoundary(S.settings,1,6,'disc',", "chooseProfileBoundary(S.settings,1,6,").replace("chooseProfileBoundary(S.settings,1,6,'bar',", "chooseProfileBoundary(S.settings,1,6,");s+='''
assert.equal(tool.chooseProfileBoundary(S.settings,3,6),null,'Clicking away from all boundaries must not move an interval');
assert.ok(!fs.readFileSync(new URL('./index.html',import.meta.url),'utf8').includes('name="editMode"'));
assert.ok(!fs.readFileSync(new URL('./app.js',import.meta.url),'utf8').includes('editMode'));
console.log('PASS: no interval-mode selector or code dependency; off-boundary clicks ignored, direct handles and numeric intervals retained.');
''';p.write_text(s,encoding='utf8')
