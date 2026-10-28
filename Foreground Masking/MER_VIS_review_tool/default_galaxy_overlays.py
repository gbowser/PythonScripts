from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('function defaultSettings(g)', '''function resetGalaxyOverlays(settings){Object.assign(settings.display,{ellipses:false,excludedEllipses:false,euclidPAOverlay:false,discPAOverlay:false,overlayMode:'selected',centres:true});}
function defaultSettings(g)''',1);s=s.replace("invert:false,ellipses:true,centres:true,excludedEllipses:true,euclidPAOverlay:true,discPAOverlay:true", "invert:false,ellipses:false,centres:true,excludedEllipses:false,euclidPAOverlay:false,discPAOverlay:false",1);s=s.replace(' setForm(draft?.form??saved);writeControls();',' resetGalaxyOverlays(S.settings);\n setForm(draft?.form??saved);writeControls();',1);s=s.replace('state:S,calculate,radiusAxis,','state:S,calculate,resetGalaxyOverlays,radiusAxis,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');
for key in ['ellipses','excludedEllipses','euclidPAOverlay','discPAOverlay']:s=s.replace(f'id="{key}" type="checkbox" checked',f'id="{key}" type="checkbox"')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_pa_continuity.mjs');s=p.read_text(encoding='utf8');s+='''
const overlaySettings={disc:[2,4],bar:[.5,1],display:{ellipses:true,excludedEllipses:true,euclidPAOverlay:true,discPAOverlay:true,overlayMode:'accepted',centres:false,stretch:'log',gamma:.8,showRejected:false}};
const savedOriginal=JSON.stringify(overlaySettings);tool.resetGalaxyOverlays(overlaySettings);
for(const key of ['ellipses','excludedEllipses','euclidPAOverlay','discPAOverlay'])assert.equal(overlaySettings.display[key],false);
assert.equal(overlaySettings.display.centres,true);assert.equal(overlaySettings.display.overlayMode,'selected');assert.equal(overlaySettings.display.stretch,'log');assert.equal(overlaySettings.display.gamma,.8);assert.equal(overlaySettings.display.showRejected,false);assert.deepEqual(overlaySettings.disc,[2,4]);
const sourceText=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');assert.ok(sourceText.indexOf('resetGalaxyOverlays(S.settings);')>sourceText.indexOf('if(draft?.settings)'));
console.log('PASS: galaxy-opening overlay defaults override restored settings, retain centre markers, and preserve stretch, intervals and profile settings.');
''';p.write_text(s,encoding='utf8')
