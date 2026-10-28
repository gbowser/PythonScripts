import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const nodes=new Map(),element=()=>({value:'disc',checked:true,dataset:{},style:{},innerHTML:'',getContext:()=>({}),addEventListener(){}});
const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},createElement:()=>element(),querySelectorAll:()=>[],querySelector:()=>element(),addEventListener(){},activeElement:{tagName:'BODY'}};
const window={addEventListener(){}},context={document,window,localStorage:{getItem:()=>null,setItem(){}},console,URLSearchParams,setTimeout,clearTimeout,requestAnimationFrame(){},Option:function(){}};vm.createContext(context);vm.runInContext(fs.readFileSync(new URL('./app.js',import.meta.url),'utf8').replace(/start\(\);\s*$/,''),context);
const tool=window.MER_VIS_REVIEW,point=(a,i,ok=true)=>({pa_sky_deg:a,sma_arcsec:i+1,used_for_geometry:ok,ellipticity:.4,pa_error_deg:1,stop_code:0});
for(const [raw,expected] of [[[170,178,2,8],[170,178,182,188]],[[10,2,178,170],[10,2,-2,-10]],[[150,155,160],[150,155,160]],[[179,1,179,1],[179,181,179,181]]]){
 const p=raw.map((v,i)=>point(v,i)),before=JSON.stringify(p),v=tool.profilePAView(p,p,10);assert.deepEqual(p.map(x=>v.values.get(x)),expected);assert.equal(JSON.stringify(p),before);assert.ok(v.min<=Math.min(...expected)&&v.max>=Math.max(...expected));
 const rawView=tool.profilePAView(p,p,10,false);assert.deepEqual(p.map(x=>rawView.values.get(x)),raw);assert.equal(rawView.min,0);assert.equal(rawView.max,180);
}
const p=[point(170,0),point(80,.5,false),point(178,1),point(2,2),point(8,3)],good=p.filter(x=>x.used_for_geometry);const v=tool.profilePAView(p,good,10);assert.deepEqual(good.map(x=>v.values.get(x)),[170,178,182,188]);
const S=tool.state;S.g={profile:good,original:{status:'provisional_fit'}};S.settings={disc:[2,4],bar:[1,1.5],noBar:true,pool:'pipeline',display:{unwrapPA:true}};context.drawProfiles();let svg=nodes.get('paPlot').innerHTML;assert.equal((svg.match(/<polyline/g)||[]).length,1);assert.ok(svg.includes('plotted as 182.000'));assert.ok(svg.includes('continuous axis'));
S.g.profile=p;context.drawProfiles();svg=nodes.get('paPlot').innerHTML;assert.equal((svg.match(/<polyline/g)||[]).length,2,'Rejected samples must still break lines');
S.g.profile=good;S.settings.display.unwrapPA=false;context.drawProfiles();assert.equal((nodes.get('paPlot').innerHTML.match(/<polyline/g)||[]).length,2);
console.log('PASS: both PA wrap directions, repeated crossings, raw-axis toggle, excluded-point independence, SVG continuity, rejected gaps and unchanged input angles.');
S.g.profile=[point(170,0),point(178,1,false),point(2,2,false),point(8,3)];S.settings.display.unwrapPA=true;
const before=JSON.stringify(S.g.profile);context.drawProfiles();
svg=nodes.get('paPlot').innerHTML;assert.equal((svg.match(/class="excluded-trend"/g)||[]).length,3);assert.ok(svg.includes('stroke-dasharray="5 4"'));assert.equal(JSON.stringify(S.g.profile),before);
nodes.get('showRejected').checked=false;context.drawProfiles();assert.ok(!nodes.get('paPlot').innerHTML.includes('excluded-trend'));assert.ok(!nodes.get('epsPlot').innerHTML.includes('excluded-trend'));
nodes.get('showRejected').checked=true;S.settings.display.unwrapPA=false;context.drawProfiles();assert.equal((nodes.get('paPlot').innerHTML.match(/class="excluded-trend"/g)||[]).length,2,'Raw PA wraps must not be joined');
S.g.profile=[point(10,0),point(NaN,1,false),point(12,2)];context.drawProfiles();assert.ok(!nodes.get('paPlot').innerHTML.includes('excluded-trend'),'Missing angles must break dashed lines');
console.log('PASS: rejected trend anchors, display toggle, raw wrap and missing-angle gaps; original acceptance unchanged.');
assert.deepEqual(Array.from(tool.radiusAxis(6.4).ticks),[0,2,4,6,8]);assert.equal(tool.radiusAxis(6.4).decimals,0);
assert.deepEqual(Array.from(tool.radiusAxis(4.8).ticks),[0,1,2,3,4,5]);assert.equal(tool.radiusAxis(.9).step,.2);
console.log('PASS: convenient 1/2 arcsec ticks, rounded axis endpoints and fractional ticks for small galaxies.');
// Matching image coverage: an axis radius of 6 arcsec needs at least 12 arcsec across.
const imageGalaxy={original:{status:'provisional_fit'},centre:[500,500],catalogue_centre:[500,500],pixel_scale_arcsec:.1,shape:[1000,1000],default_window:[470,530,470,530],profile:[]};
let windowBounds=tool.profileImageWindow(imageGalaxy,{},6);assert.ok(windowBounds[0]<440&&windowBounds[1]>560);assert.ok(windowBounds[2]<440&&windowBounds[3]>560);
S.g=imageGalaxy;S.g.profile=[point(4,0)];S.settings={disc:[1,6],bar:[.5,1],noBar:false,display:{}};S.view=[470,530,470,530];assert.equal(tool.expandProfileView(false),true);assert.ok((S.view[1]-S.view[0])*.1>=12);assert.equal(tool.expandProfileView(false),false);
const expanded=S.view.slice();S.view=[0,999,0,999];assert.equal(tool.expandProfileView(false),false,'Do not shrink a deliberately wider view');
S.g.profile.push({sma_arcsec:5,x_original_pix:570,y_original_pix:500,pa_pixel_deg:0,ellipticity:.4});windowBounds=tool.profileImageWindow(S.g,S.settings,6);assert.ok(windowBounds[1]>=622,'Include offset ellipse centres and their major axes');
S.settings.disc=[1,12];assert.ok(context.plotMax()>=12,'Profile axis includes an expanded interval');
S.g.centre=[4,4];S.g.profile=[];S.view=[0,10,0,10];tool.expandProfileView(false);assert.ok(S.view[0]>=-.5&&S.view[2]>=-.5);assert.ok(S.view[1]<=999.5&&S.view[3]<=999.5);
console.log('PASS: image covers twice the profile radius, expands on interval changes, includes offset ellipse extents, preserves wider views and stays within FITS bounds.');

S.g={profile:[179,1,80,159,179].map((a,i)=>point(a,i)),original:{status:'provisional_fit'}};S.settings={disc:[2,5],bar:[1,2],noBar:true,pool:'pipeline',display:{unwrapPA:true}};nodes.get('showRejected').checked=true;context.drawProfiles();svg=nodes.get('paPlot').innerHTML;assert.ok(svg.includes('>60</text>'));assert.ok(!svg.includes('>420</text>'));assert.ok(!svg.includes('>360</text>'));assert.ok(svg.includes('>0</text>'));assert.equal((svg.match(/<polyline/g)||[]).length,1);
console.log('PASS: continuous PA curve retained while 420 and 360 degree tick labels display as 60 and 0.');

assert.equal(tool.ellipseInclination({ellipticity:0}),0);assert.ok(Math.abs(tool.ellipseInclination({ellipticity:.5})-60)<1e-10);assert.equal(tool.ellipseInclination({ellipticity:1}),90);for(const e of [null,NaN,-.1,1.1])assert.equal(tool.ellipseInclination({ellipticity:e}),null);
assert.deepEqual(Array.from(tool.paReferenceLevels(7,120,420)),[187,367]);
S.g.euclid={disc_pa:7,inclination:32.5};S.settings.display.paComparison=true;const referenceInput=JSON.stringify(S.g);context.drawProfiles();let incl=nodes.get('incPlot').innerHTML;svg=nodes.get('paPlot').innerHTML;assert.ok(incl.includes('Inclination proxy'));assert.ok(incl.includes('Euclid inclination proxy: 32.50°'));assert.ok(incl.includes('class="euclid-reference"'));assert.ok(svg.includes('Euclid source PA: 7.00°'));assert.equal((svg.match(/class="euclid-reference"/g)||[]).length,2);assert.ok(!nodes.get('epsPlot').innerHTML.includes('class="euclid-reference"'));assert.equal(nodes.get('incPlot').dataset.xmax,nodes.get('paPlot').dataset.xmax);assert.equal(JSON.stringify(S.g),referenceInput);assert.equal(typeof nodes.get('incPlot').onpointerdown,'function');
S.g.euclid={disc_pa:null,inclination:null};context.drawProfiles();for(const id of ['incPlot','paPlot']){assert.ok(nodes.get(id).innerHTML.includes('Euclid: unavailable'));assert.ok(!nodes.get(id).innerHTML.includes('class="euclid-reference"'));}
console.log('PASS: inclination conversion, invalid shapes, Euclid proxy/PA reference values, axial branches, shared radius axes, interval controls, missing data and unchanged input geometry.');
S.g.euclid={disc_pa:7,inclination:32.5};S.settings.disc=[2,4];S.g.original.status='provisional_fit';nodes.get('showRejected').checked=true;context.drawProfiles();
const referenceExtent=id=>{const match=nodes.get(id).innerHTML.match(/class="euclid-reference" x1="([^"]+)" x2="([^"]+)"/);return match&&match.slice(1).map(Number)};
let max=context.plotMax(),left=48+2/max*594,right=48+4/max*594;for(const id of ['incPlot','paPlot'])assert.deepEqual(referenceExtent(id),[left,right]);
let circles=[...nodes.get('incPlot').innerHTML.matchAll(/<circle cx="([^"]+)"/g)].map(m=>Number(m[1]));assert.equal(circles.length,3);assert.ok(circles.every(x=>x>=left&&x<=right));assert.equal((nodes.get('paPlot').innerHTML.match(/<circle/g)||[]).length,5);
S.settings.disc=[3,4];context.drawProfiles();assert.equal((nodes.get('incPlot').innerHTML.match(/<circle/g)||[]).length,2);assert.equal(referenceExtent('paPlot')[0],48+3/max*594);
S.g.original.status='fit_failed';context.drawProfiles();assert.ok(!nodes.get('incPlot').innerHTML.includes('<circle'));for(const id of ['incPlot','paPlot'])assert.ok(!nodes.get(id).innerHTML.includes('class="euclid-reference"'));
console.log('PASS: inclination samples and Euclid reference lines restricted to green bounds, respond to interval edits, retain full PA profile, and disappear when no disc is adopted.');
// Repeated mousemove events at a stationary right border must not inflate the scale.
S.g={profile:[point(4,0)],original:{status:'provisional_fit'}};S.settings={disc:[2,4],bar:[1,2],noBar:true,pool:'pipeline',display:{}};S.profileAxisFloor=null;S.drag=null;
const dragSVG=nodes.get('paPlot');dragSVG.dataset.xmax=6;dragSVG.createSVGPoint=()=>({x:0,y:0,matrixTransform(){return {x:this.x,y:this.y}}});dragSVG.getScreenCTM=()=>({inverse:()=>({})});
context.recalculate=()=>{for(const id of ['epsPlot','incPlot','paPlot'])nodes.get(id).dataset.xmax=context.plotMax()};context.markDirty=()=>{};context.expandProfileView=()=>{};
S.drag={kind:'disc',edge:1,axisMax:6};for(let i=0;i<1000;i++)context.moveGraph(dragSVG,{clientX:642,clientY:0});assert.equal(S.settings.disc[1],6);assert.equal(context.plotMax(),6);context.finishProfileDrag(true);assert.equal(context.plotMax(),8);
S.drag={kind:'disc',edge:1,axisMax:8};for(let i=0;i<1000;i++)context.moveGraph(dragSVG,{clientX:642,clientY:0});assert.equal(S.settings.disc[1],8);assert.equal(context.plotMax(),8);context.finishProfileDrag(true);assert.equal(context.plotMax(),10);
S.drag={kind:'disc',edge:1,axisMax:10};context.moveGraph(dragSVG,{clientX:345,clientY:0});context.finishProfileDrag(true);assert.equal(context.plotMax(),10,'Release away from border must not add space');
S.drag={kind:'disc',edge:1,axisMax:10};context.moveGraph(dragSVG,{clientX:642,clientY:0});context.finishProfileDrag(false);assert.equal(context.plotMax(),10,'Cancelled pointer must not add space');
console.log('PASS: 2000 stationary drag events cannot inflate radius; releasing at border adds exactly 2 arcsec once, other releases/cancellations add nothing.');
S.settings={disc:[.9,4.2],bar:[.55,1],noBar:false,pool:'pipeline',display:{}};S.g.original.status='provisional_fit';S.profileAxisFloor=null;S.drag=null;
let choice=tool.chooseProfileBoundary(S.settings,1,6);assert.equal(choice.kind,'bar');assert.equal(choice.edge,1);
S.settings.disc[0]=1;choice=tool.chooseProfileBoundary(S.settings,1,6,{kind:'bar',edge:1});assert.equal(choice.kind,'bar');choice=tool.chooseProfileBoundary(S.settings,1,6,{kind:'disc',edge:0});assert.equal(choice.kind,'disc');
S.settings.disc[0]=.9;dragSVG.dataset.xmax=6;dragSVG.setPointerCapture=()=>{};const oldDisc=[...S.settings.disc];
dragSVG.onpointerdown({clientX:48+594/6,clientY:24,pointerId:1,target:{closest:()=>({dataset:{intervalKind:'bar',intervalEdge:'1'}})}});assert.equal(S.drag.kind,'bar');assert.equal(S.drag.edge,1);assert.equal(S.settings.bar[1],1,'Handle pickup must not jump');
context.moveGraph(dragSVG,{clientX:48+.8/6*594,clientY:24});assert.ok(Math.abs(S.settings.bar[1]-.8)<1e-10);assert.deepEqual(S.settings.disc,oldDisc);context.finishProfileDrag(true);
S.settings.noBar=true;assert.notEqual(tool.chooseProfileBoundary(S.settings,1,6,{kind:'bar',edge:1})?.kind,'bar');
console.log('PASS: nearest bar boundary overrides Disc mode, explicit staggered handles resolve coincident boundaries, dragging bar leaves disc untouched, no pickup jump, and no-bar guard remains.');
S.g={profile:[170,175,1,5,10].map((a,i)=>point(a,i)),original:{status:'provisional_fit'},euclid:{disc_pa:7,inclination:30}};S.settings={disc:[2,4],bar:[.5,1],noBar:true,pool:'pipeline',display:{unwrapPA:true,paComparison:true}};S.calc={disc_pa:3};S.profileAxisFloor=null;S.drag=null;context.drawProfiles();svg=nodes.get('paPlot').innerHTML;let green=svg.match(/class="disc-pa-reference" x1="([^"]+)" x2="([^"]+)"/);assert.ok(green);assert.equal(Number(green[1]),48+2/context.plotMax()*594);assert.equal(Number(green[2]),48+4/context.plotMax()*594);assert.ok(svg.includes('Current-selection disc PA: 3.00°'));assert.ok(svg.includes('stroke-dasharray="7 4"'));assert.ok(!nodes.get('epsPlot').innerHTML.includes('disc-pa-reference'));assert.ok(!nodes.get('incPlot').innerHTML.includes('disc-pa-reference'));
S.calc.disc_pa=42;context.drawProfiles();assert.ok(nodes.get('paPlot').innerHTML.includes('Current-selection disc PA: 42.00°'));S.settings.display.paComparison=false;context.drawProfiles();assert.ok(!nodes.get('paPlot').innerHTML.includes('class="disc-pa-reference"'));S.settings.display.paComparison=true;S.calc.disc_pa=null;context.drawProfiles();assert.ok(!nodes.get('paPlot').innerHTML.includes('class="disc-pa-reference"'));
console.log('PASS: green current-selection PA reference confined to disc interval, updates with geometry, shares axial wrap, and respects visibility/missing values.');

assert.equal(tool.chooseProfileBoundary(S.settings,3,6),null,'Clicking away from all boundaries must not move an interval');
assert.ok(!fs.readFileSync(new URL('./index.html',import.meta.url),'utf8').includes('name="editMode"'));
assert.ok(!fs.readFileSync(new URL('./app.js',import.meta.url),'utf8').includes('editMode'));
console.log('PASS: no interval-mode selector or code dependency; off-boundary clicks ignored, direct handles and numeric intervals retained.');

const overlaySettings={disc:[2,4],bar:[.5,1],display:{ellipses:true,excludedEllipses:true,paComparison:true,overlayMode:'accepted',centres:false,stretch:'log',gamma:.8,showRejected:false}};
const savedOriginal=JSON.stringify(overlaySettings);overlaySettings.display.showWarnings=true;tool.resetGalaxyOverlays(overlaySettings);assert.equal(overlaySettings.display.showWarnings,false);
for(const key of ['ellipses','excludedEllipses','paComparison'])assert.equal(overlaySettings.display[key],false);
assert.equal(overlaySettings.display.centres,true);assert.equal(overlaySettings.display.overlayMode,'selected');assert.equal(overlaySettings.display.stretch,'log');assert.equal(overlaySettings.display.gamma,.8);assert.equal(overlaySettings.display.showRejected,false);assert.deepEqual(overlaySettings.disc,[2,4]);
const sourceText=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');assert.ok(sourceText.indexOf('resetGalaxyOverlays(S.settings);')>sourceText.indexOf('if(draft?.settings)'));
console.log('PASS: galaxy-opening overlay defaults override restored settings, retain centre markers, and preserve stretch, intervals and profile settings.');
