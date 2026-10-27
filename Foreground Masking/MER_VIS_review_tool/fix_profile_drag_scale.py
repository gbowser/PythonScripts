from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('S.id=id;S.g=g;S.pixels=null;', 'S.id=id;S.g=g;S.drag=null;S.profileAxisFloor=null;S.pixels=null;',1)
start=s.index('function plotMax(){');end=s.index('\n',start)
s=s[:start]+'''function plotMax(){if(S.drag&&finite(S.drag.axisMax))return S.drag.axisMax;
 const accepted=pool(),bounds=[...(S.settings.disc??[]),...(S.settings.noBar?[]:(S.settings.bar??[]))].filter(finite),base=radiusAxis(Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07).max;
 return Math.max(base,Math.ceil(Math.max(0,...bounds)/2)*2,S.profileAxisFloor??0);
}''' +s[end:]
s=s.replace('const radiusTicks=radiusAxis(xmax);for(const vx of radiusTicks.ticks){', 'const radiusTicks=radiusAxis(xmax),visibleRadiusTicks=radiusTicks.ticks.filter(v=>v<=xmax+1e-9);if(xmax-visibleRadiusTicks.at(-1)>radiusTicks.step*.45)visibleRadiusTicks.push(xmax);for(const vx of visibleRadiusTicks){')
s=s.replace('Number(svg.dataset.xmax),0,Number(svg.dataset.xmax)', '(S.drag?.axisMax??Number(svg.dataset.xmax)),0,(S.drag?.axisMax??Number(svg.dataset.xmax))')
s=s.replace("S.drag={kind,edge:Math.abs(x-r[0])<Math.abs(x-r[1])?0:1}", "S.drag={kind,edge:Math.abs(x-r[0])<Math.abs(x-r[1])?0:1,axisMax:Number(svg.dataset.xmax)}")
s=s.replace("svg.onpointerup=()=>{if(S.drag){S.drag=null;markDirty();expandProfileView();}};svg.onpointercancel=()=>S.drag=null;", "svg.onpointerup=()=>finishProfileDrag(true);svg.onpointercancel=()=>finishProfileDrag(false);")
pos=s.index('function moveGraph(');s=s[:pos]+'''function finishProfileDrag(extend){if(!S.drag)return;const {kind,edge,axisMax}=S.drag;
 if(extend&&edge===1&&S.settings[kind][1]>=axisMax*.98)S.profileAxisFloor=axisMax+2;
 S.drag=null;recalculate();markDirty();expandProfileView();
}
''' +s[pos:]
s=s.replace("$('resetGeometry').onclick=()=>{const defaults", "$('resetGeometry').onclick=()=>{S.profileAxisFloor=null;const defaults")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('Drag a shaded edge in any profile graph, or enter bounds below.', 'Drag a shaded edge in any profile graph, or enter bounds below. The radius scale stays fixed while dragging. Release an outer edge near the right border to add 2 arcsec of space, then drag again to extend farther. Reset intervals restores the original range.');p.write_text(s,encoding='utf8')
