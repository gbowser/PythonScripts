import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const element=()=>({value:'disc',checked:true,dataset:{},style:{},getContext:()=>({}),addEventListener(){}});
const nodes=new Map();const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},createElement:()=>element(),querySelectorAll:()=>[],querySelector:()=>element(),addEventListener(){},activeElement:{tagName:'BODY'}};
const window={addEventListener(){}};const localStorage={getItem:()=>null,setItem(){}};
const context={document,window,localStorage,console,URLSearchParams,setTimeout,clearTimeout,requestAnimationFrame(){},Option:function(){}};
vm.createContext(context);const source=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8').replace(/start\(\);\s*$/,'');vm.runInContext(source,context);
const tool=window.MER_VIS_REVIEW;
const sample=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
tool.state.boot={rules:{min_disc:6,max_gap:.5,pa_rms:10,eps_span:.15,small_bar:1.5}};
let tested=0;
for(const g of sample){tool.state.g=g;tool.state.settings=context.defaultSettings(g);const c=tool.calculate();
 for(const [key,original] of [['disc_pa','disc_pa'],['bar_pa','bar_pa'],['inclination','inclination']]){
  const a=c[key],b=g.original[original];if(b==null)continue;
  assert.ok(a!==null,`${g.object_id} missing ${key}`);const diff=key.includes('pa')?Math.abs(tool.axialDifference(a,b)):Math.abs(a-b);
  assert.ok(diff<1e-7,`${g.object_id} ${key} differs by ${diff}`);
 }
 assert.equal(c.n_disc,g.original.n_disc,`${g.object_id} disc sample count`);tested++;
 if(g.original.bar_status==='detected_A')assert.equal(c.bar_grade,'A (stored)');
 if(g.original.bar_status==='detected_B')assert.equal(c.bar_grade,'B (stored)');
}
const g=sample.find(g=>g.object_id==='-518633776290631360');assert.ok(g);
tool.state.g=g;tool.state.settings=context.defaultSettings(g);let c=tool.calculate();assert.ok(c.issues.includes('Sparse disc sampling'));
tool.state.settings.rules.min_disc=3;tool.state.settings.rules.max_gap=.9;c=tool.calculate();assert.ok(!c.issues.includes('Sparse disc sampling'));assert.ok(c.issues.includes('Disc PA varies across radius'));
tool.state.settings.rules.pa_enabled=false;c=tool.calculate();assert.ok(!c.issues.includes('Disc PA varies across radius'));
tool.state.settings.noBar=true;c=tool.calculate();assert.equal(c.bar_pa,null);assert.ok(c.disc_pa!==null);
tool.state.settings.disc=[2, g.intervals.disc[1]];tool.state.settings.editedDisc=true;c=tool.calculate();assert.equal(c.n_disc,4);
assert.ok(Math.abs(tool.axialDifference(tool.axialMean([179,1]),0))<1e-8);
if(process.argv[3]){
 const vectors=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));let samples=0;
 for(const c of vectors){const p=tool.autoSTFParameters(c.stats,c.shadows,c.target);assert.ok(Number.isFinite(p.midtones));
  c.probes.forEach((x,i)=>{const value=tool.autoSTFValue(x,p);assert.ok(Math.abs(value-c.expected[i])<1e-9,`AutoSTF mismatch: ${value} vs ${c.expected[i]}`);samples++;});
 }
 assert.equal(tool.midtonesTransfer(.5,0),0);assert.equal(tool.midtonesTransfer(.5,1),1);
 console.log(`PASS: AutoSTF matches the earlier Python viewer on ${vectors.length} frames/settings and ${samples} sample values.`);
}
console.log(`PASS: ${tested} baseline galaxies reproduce stored PA, inclination and selected-disc counts; threshold, no-bar and axial-wrap checks passed.`);

const transform={rect:{left:100,top:50},left:20,top:10,w:400,h:200,view:[700,900,800,900]};
assert.deepEqual(Array.from(tool.imagePixel(transform,320,160)),[800,850]);
assert.deepEqual(Array.from(tool.imagePixel(transform,120,60)),[700,900]);
assert.deepEqual(Array.from(tool.imagePixel(transform,520,260)),[900,800]);
assert.equal(context.defaultSettings(g).display.stretch,'autostf');
console.log('PASS: screen-to-native-pixel centre mapping at zoomed view boundaries and centre.');
