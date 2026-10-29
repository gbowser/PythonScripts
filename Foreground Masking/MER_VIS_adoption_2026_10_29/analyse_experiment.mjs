import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const el=()=>({value:'disc',checked:true,dataset:{},style:{},getContext:()=>({}),addEventListener(){}}),nodes=new Map();
const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,el());return nodes.get(id)},createElement:el,querySelectorAll:()=>[],querySelector:el,addEventListener(){},activeElement:{tagName:'BODY'}};
const window={addEventListener(){}},ctx={document,window,localStorage:{getItem:()=>null,setItem(){}},console,URLSearchParams,setTimeout,clearTimeout,requestAnimationFrame(){},Option:function(){}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('MER_VIS_review_tool/app.js','utf8').replace(/start\(\);\s*$/,''),ctx);
const tool=window.MER_VIS_REVIEW,S=tool.state,input=JSON.parse(fs.readFileSync('MER_VIS_adoption_2026_10_29/experiment_input.json'));S.boot=input.snapshot.boot;
const compact=c=>Object.fromEntries(Object.entries(c).filter(([k])=>!['disc','bar','centre_rejected_disc','centre_rejected_bar'].includes(k)));
const calculate=(g,settings)=>{S.g=g;S.settings=structuredClone(settings);return compact(tool.calculate())};
const baseline={};for(const [id,g] of Object.entries(input.snapshot.galaxies)){
 const saved=input.source[id],settings={...ctx.defaultSettings(g),...saved.settings};baseline[id]=calculate(g,settings);
 for(const k of ['disc_pa','bar_pa','inclination','n_disc','n_bar','pa_scatter','eps_span','max_gap_fraction']){
  const a=baseline[id][k],b=saved.calculation[k];assert.ok(a===b||(a!==null&&b!==null&&Math.abs(a-b)<1e-9),id+' '+k+' changed');
 }
 if(g.centre_visually_confirmed)assert.ok(!baseline[id].issues.some(i=>i.startsWith('Centre reference unverified')));
}
const ids=[...new Set(input.probes.map(p=>p.id))],rows=[];
for(const id of ids){
 const g=input.snapshot.galaxies[id],saved=input.source[id],settings={...ctx.defaultSettings(g),...saved.settings},reference=baseline[id],centre=[],interval=[];
 for(const p of input.probes.filter(p=>p.id===id)){
  const trial={...g,profile:p.profile,centre_reference:p.reference,centre_visually_confirmed:false,original:{...g.original,status:p.status}};
  centre.push({probe:p.label,folder:p.folder,reference:p.reference,calculation:calculate(trial,{...settings,editedDisc:true,editedBar:true})});
 }
 const [lo,hi]=settings.disc,width=hi-lo,d=.1*width;
 for(const [label,a,b] of [['inner_in',lo-d,hi],['inner_out',lo+d,hi],['outer_in',lo,hi-d],['outer_out',lo,hi+d],['shift_in',lo-d,hi-d],['shift_out',lo+d,hi+d]]){
  interval.push({probe:label,bounds:[Math.max(0,a),b],calculation:calculate(g,{...settings,disc:[Math.max(0,a),b],editedDisc:true})});
 }
 const delta=(p,k)=>p.calculation[k]===null||reference[k]===null?null:k==='disc_pa'||k==='bar_pa'?Math.abs(tool.axialDifference(p.calculation[k],reference[k])):Math.abs(p.calculation[k]-reference[k]);
 const stats=probes=>{const vals=k=>probes.map(p=>delta(p,k)).filter(v=>v!==null);return {max_disc_pa_change_deg:Math.max(0,...vals('disc_pa')),max_inclination_change_deg:Math.max(0,...vals('inclination')),max_bar_pa_change_deg:vals('bar_pa').length?Math.max(...vals('bar_pa')):null,incomplete_disc_trials:probes.filter(p=>p.calculation.inclination===null).length,min_disc_samples:Math.min(...probes.map(p=>p.calculation.n_disc)),max_disc_samples:Math.max(...probes.map(p=>p.calculation.n_disc))}};
 const cs=stats(centre),is=stats(interval);
 rows.push({id,baseline:reference,centre_summary:cs,interval_summary:is,sensitivity_requires_attention:cs.max_disc_pa_change_deg>10||is.max_disc_pa_change_deg>10||cs.max_inclination_change_deg>5||is.max_inclination_change_deg>5||cs.incomplete_disc_trials>0||is.incomplete_disc_trials>0,centre_trials:centre,interval_trials:interval});
}
fs.writeFileSync('MER_VIS_adoption_2026_10_29/recomputed_selections.json',JSON.stringify(baseline,null,2));
fs.writeFileSync('MER_VIS_adoption_2026_10_29/MER_VIS_sensitivity_results.json',JSON.stringify(rows,null,2));
console.log('PASS: all 19 saved selections reproduced; matching visual centre confirmations resolve only the workflow warning.');
for(const r of rows)console.log(JSON.stringify({id:r.id,centre:r.centre_summary,interval:r.interval_summary}));
