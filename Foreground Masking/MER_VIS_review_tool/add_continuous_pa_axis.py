from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
start=s.index('function drawProfiles(){');end=s.index('\nfunction graphPointer',start)
replacement='''// Choose equivalent PA values separated by 180 degrees for display only.
function profilePAView(profile,accepted,xmax,enabled=true,showRejected=true){
 const values=new Map(),set=new Set(accepted),valid=p=>finite(p.pa_sky_deg)&&finite(p.sma_arcsec)&&p.sma_arcsec<=xmax;
 const ordered=accepted.filter(valid).slice().sort((a,b)=>a.sma_arcsec-b.sma_arcsec);let previous=null,wrapped=false;
 for(const p of ordered){const raw=p.pa_sky_deg;if(previous&&Math.abs(raw-previous.pa_sky_deg)>90)wrapped=true;values.set(p,previous?values.get(previous)+axialDifference(raw,previous.pa_sky_deg):raw);previous=p;}
 const unwrapped=enabled&&wrapped;
 for(const p of profile.filter(valid)){
  if(!unwrapped){values.set(p,p.pa_sky_deg);continue;}
  if(set.has(p))continue;
  // Excluded measurements never determine the accepted curve's branch.
  let upper=ordered.findIndex(z=>z.sma_arcsec>=p.sma_arcsec),reference;
  if(upper<=0)reference=values.get(ordered[upper===-1?ordered.length-1:0]);
  else{const a=ordered[upper-1],b=ordered[upper],t=(p.sma_arcsec-a.sma_arcsec)/Math.max(b.sma_arcsec-a.sma_arcsec,1e-12);reference=values.get(a)+(values.get(b)-values.get(a))*t;}
  values.set(p,p.pa_sky_deg+180*Math.round((reference-p.pa_sky_deg)/180));
 }
 if(!unwrapped)return {values,unwrapped:false,min:0,max:180,ticks:[0,45,90,135,180]};
 const shown=profile.filter(p=>valid(p)&&(set.has(p)||showRejected)).map(p=>values.get(p));
 const low=Math.min(...shown),high=Math.max(...shown),mid=(low+high)/2,span=Math.max(30,high-low),pad=Math.max(3,span*.12);
 const target=(span+2*pad)/4,step=[5,10,15,20,30,45,60,90,180,360,720].find(v=>v>=target)??Math.ceil(target/180)*180;
 const min=Math.floor((mid-span/2-pad)/step)*step,max=Math.ceil((mid+span/2+pad)/step)*step,ticks=[];
 for(let v=min;v<=max+step*.01;v+=step)ticks.push(v);
 return {values,unwrapped:true,min,max,ticks};
}
function drawProfiles(){
 const accepted=pool(),acceptedSet=new Set(accepted),xmax=plotMax(),paView=profilePAView(S.g.profile,accepted,xmax,S.settings.display.unwrapPA!==false,$('showRejected').checked);
 for(const [id,field,maxY,title] of [['epsPlot','ellipticity',1,'Ellipticity ε = 1 − b/a'],['paPlot','pa_sky_deg',180,paView.unwrapped?'Sky PA (degrees; continuous axis)':'Sky PA (degrees)']]){
 const w=660,h=215,left=48,right=18,top=22,bottom=36,pw=w-left-right,ph=h-top-bottom;
 const isPA=field==='pa_sky_deg',lo=isPA?paView.min:0,hi=isPA?paView.max:maxY,ticks=isPA?paView.ticks:[0,.25,.5,.75,1],value=p=>isPA?paView.values.get(p):p[field];
 const x=v=>left+v/xmax*pw,y=v=>top+(hi-v)/(hi-lo)*ph;let html='';
 for(const [kind,color] of [['bar','#f3bc62'],['disc','#86bf96']]){if(S.g.original.status==='fit_failed'||(kind==='bar'&&S.settings.noBar))continue;const r=S.settings[kind];if(!r.every(finite))continue;html+=`<rect x="${x(r[0])}" y="${top}" width="${Math.max(0,x(r[1])-x(r[0]))}" height="${ph}" fill="${color}" opacity=".28"/>`;for(const edge of [0,1])html+=`<line x1="${x(r[edge])}" x2="${x(r[edge])}" y1="${top}" y2="${top+ph}" stroke="${kind==='disc'?'#348458':'#c17b19'}" stroke-width="${document.querySelector('input[name=editMode]:checked').value===kind?2:1}" opacity=".7"/>`;}
 for(const vy of ticks)html+=`<line x1="${left}" x2="${w-right}" y1="${y(vy)}" y2="${y(vy)}" stroke="#dce5eb"/><text x="${left-8}" y="${y(vy)+4}" text-anchor="end">${isPA?Math.round(vy):vy.toFixed(2)}</text>`;
 for(let i=0;i<=4;i++){const vx=i/4*xmax;html+=`<line x1="${x(vx)}" x2="${x(vx)}" y1="${top}" y2="${top+ph}" stroke="#e6edf1"/><text x="${x(vx)}" y="${top+ph+18}" text-anchor="middle">${vx.toFixed(xmax<3?2:1)}</text>`;}
 html+=`<text class="axis-title" x="${left}" y="14">${title}</text><text class="axis-title" x="${left+pw/2}" y="${h-2}" text-anchor="middle">Semi-major axis (arcsec)</text>`;
 let segments=[],current=[],previous=null;
 S.g.profile.forEach(p=>{if(!acceptedSet.has(p)||!finite(value(p))||p.sma_arcsec>xmax){if(current.length)segments.push(current);current=[];previous=null;return;}if(previous&&isPA&&!paView.unwrapped&&Math.abs(p[field]-previous[field])>90){segments.push(current);current=[];}current.push(`${x(p.sma_arcsec)},${y(value(p))}`);previous=p;});if(current.length)segments.push(current);
 html+=segments.map(path=>`<polyline points="${path.join(' ')}" fill="none" stroke="#246f98" stroke-width="1.4"/>`).join('');
 for(const p of S.g.profile){const ok=acceptedSet.has(p);if((!ok&&!$('showRejected').checked)||!finite(value(p))||!finite(p.sma_arcsec)||p.sma_arcsec>xmax)continue;const color=ok?(p.used_for_geometry?'#246f98':'#b5598b'):'#a5adb2',shown=isPA&&paView.unwrapped?`; plotted as ${fmt(value(p),3)}° (equivalent modulo 180°)`:'';html+=`<circle cx="${x(p.sma_arcsec)}" cy="${y(value(p))}" r="${ok?3.2:2.1}" fill="${color}"><title>${ok?'Accepted in this pool':'Excluded'}; radius ${fmt(p.sma_arcsec,3)} arcsec; ${field} ${fmt(p[field],3)}${shown}; PA error ${fmt(p.pa_error_deg)}°; stop ${p.stop_code}</title></circle>`;}
 html+=`<rect x="${left}" y="${top}" width="${pw}" height="${ph}" fill="none" stroke="#7e929f"/>`;
 $(id).innerHTML=html;$(id).dataset.xmax=xmax;}
}
'''
s=s[:start]+replacement+s[end:]
s=s.replace("'showRejected','stfShadows'","'showRejected','unwrapPA','stfShadows'")
s=s.replace("showRejected:true,stfShadows", "showRejected:true,unwrapPA:true,stfShadows")
s=s.replace("if(id==='showRejected')drawProfiles()", "if(id==='showRejected'||id==='unwrapPA')drawProfiles()")
s=s.replace('calculate,axialMean,','calculate,profilePAView,axialMean,')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8')
s=s.replace('<h2>Ellipse profiles</h2><label', '<h2>Ellipse profiles</h2><label class="check"><input id="unwrapPA" type="checkbox" checked title="Continue equivalent position angles across the 180-degree boundary"> Continuous PA axis</label><label')
s=s.replace('Lines break across excluded samples and the 0°/180° PA boundary.', 'Lines break across excluded samples. Continuous PA axis adds or subtracts 180° where needed to keep the accepted PA profile continuous. For example, 2° may be plotted as 182°; tables and saved angles stay in the standard 0–180° convention.')
p.write_text(s,encoding='utf8')
