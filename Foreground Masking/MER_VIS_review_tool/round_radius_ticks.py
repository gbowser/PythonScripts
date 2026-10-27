from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('function plotMax(){const accepted=pool();return Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07;}', '''function radiusAxis(maximum){
 const target=maximum/6,power=10**Math.floor(Math.log10(target)),step=[1,2,5,10].map(v=>v*power).find(v=>v>=target),max=Math.ceil(maximum/step)*step,ticks=[];
 for(let i=0;i<=Math.round(max/step);i++)ticks.push(i*step);
 return {max,step,ticks,decimals:Math.max(0,-Math.floor(Math.log10(step)))};
}
function plotMax(){const accepted=pool();return radiusAxis(Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07).max;}''')
s=s.replace('for(let i=0;i<=4;i++){const vx=i/4*xmax;', 'const radiusTicks=radiusAxis(xmax);for(const vx of radiusTicks.ticks){')
s=s.replace('${vx.toFixed(xmax<3?2:1)}','${vx.toFixed(radiusTicks.decimals)}')
s=s.replace('i%stride===0||disc.has(p)||bar.has(p)','i%stride===0||i===points.length-1||disc.has(p)||bar.has(p)')
s=s.replace('state:S,calculate,profilePAView,','state:S,calculate,radiusAxis,profilePAView,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('Green: selected disc. Orange: selected candidate bar.','Green: selected disc. Orange: selected candidate bar. Cyan: other accepted ellipses (choose “All accepted” to show these, including points outside the selected intervals).');p.write_text(s,encoding='utf8')
