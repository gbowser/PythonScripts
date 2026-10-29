import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const el=()=>({value:'disc',checked:true,dataset:{},style:{},getContext:()=>({}),addEventListener(){}}),nodes=new Map(),document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,el());return nodes.get(id)},createElement:el,querySelectorAll:()=>[],querySelector:el,addEventListener(){},activeElement:{tagName:'BODY'}},window={addEventListener(){}};
const ctx={document,window,localStorage:{getItem:()=>null,setItem(){}},console,URLSearchParams,setTimeout,clearTimeout,requestAnimationFrame(){},Option:function(){}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('MER_VIS_review_tool/app.js','utf8').replace(/start\(\);\s*$/,''),ctx);
const tool=window.MER_VIS_REVIEW,boot=await(await fetch('http://127.0.0.1:8768/api/bootstrap')).json();tool.state.boot=boot;const saved=boot.reviews;assert.equal(Object.values(saved).filter(r=>r.reviewed).length,19);let confirmed=0,withheld=0;
for(const [id,r] of Object.entries(saved)){
 const g=await(await fetch('http://127.0.0.1:8768/api/galaxy?id='+id+'&refit='+r.settings.refit_id)).json();assert.ok(!g.error);if(g.centre_visually_confirmed)confirmed++;
 const S=tool.state;S.g=g;S.settings={...ctx.defaultSettings(g),...r.settings};S.settings.display.showWarnings=true;S.calc=tool.calculate();
 ctx.drawProfiles();for(const graph of ['epsPlot','incPlot','paPlot','centrePlot'])assert.ok(!nodes.get(graph).innerHTML?.includes('NaN'),id+' invalid graph');
 if(g.centre_visually_confirmed)assert.ok(!S.calc.issues.some(i=>i.startsWith('Centre reference unverified')));
 if(r.disc_decision==='uncertain'){assert.equal(g.saved_adoption.adoption_status,'withheld_disc_uncertain');withheld++;}
 if(id==='2697242050653408730'){assert.equal(S.calc.n_disc,2);assert.equal(S.calc.inclination,null);assert.equal(g.saved_adoption.adoption_status,'provisional_incomplete_disc')}
}
const csv=await(await fetch('http://127.0.0.1:8768/api/export')).text();assert.ok(csv.includes('automatic_deprojection_ready'));assert.equal(confirmed,18);assert.equal(withheld,4);
fs.writeFileSync('MER_VIS_adoption_2026_10_29/live_verification.json',JSON.stringify({reviewed:19,confirmed,withheld,numerical_graphs:'19 complete graph sets; no invalid coordinates',csv_adoption_fields:true},null,2));console.log('PASS: installed tool retains 19 reviews, confirms 18 centres, withholds 4 uncertain discs, keeps last galaxy incomplete, renders profiles and exports adoption fields.');
