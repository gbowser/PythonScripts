from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
needle=' html+=`<rect x="${left}" y="${top}" width="${pw}" height="${ph}" fill="none" stroke="#7e929f"/>`;'
addition=''' if(S.g.original.status!=='fit_failed')for(const kind of ['bar','disc']){if(kind==='bar'&&S.settings.noBar)continue;const bounds=S.settings[kind];if(!bounds?.every(finite))continue;for(const edge of [0,1]){const handleY=top+(kind==='bar'?2:16);html+=`<rect class="interval-handle" data-interval-kind="${kind}" data-interval-edge="${edge}" x="${x(bounds[edge])-5}" y="${handleY}" width="10" height="10" rx="2" fill="${kind==='bar'?'#dc971f':'#348458'}" stroke="white" stroke-width="1" style="cursor:ew-resize"><title>${kind==='bar'?'Bar':'Disc'} ${edge===0?'inner':'outer'} boundary — drag horizontally</title></rect>`;}}
'''
assert needle in s;s=s.replace(needle,needle+'\n'+addition,1)
pos=s.index('function graphPointer(')
s=s[:pos]+'''function chooseProfileBoundary(settings,radius,axisMax,preferred,explicit=null){
 const available=['bar','disc'].filter(kind=>!(kind==='bar'&&settings.noBar)&&settings[kind]?.every(finite));
 if(explicit&&available.includes(explicit.kind)&&[0,1].includes(explicit.edge))return {...explicit,snap:true};
 const candidates=available.flatMap(kind=>[0,1].map(edge=>({kind,edge,distance:Math.abs(settings[kind][edge]-radius)}))).sort((a,b)=>a.distance-b.distance||(a.kind===preferred?-1:1));
 if(candidates[0]?.distance<=axisMax*10/594)return {kind:candidates[0].kind,edge:candidates[0].edge,snap:true};
 if(!available.includes(preferred))return null;
 return {kind:preferred,edge:Math.abs(radius-settings[preferred][0])<Math.abs(radius-settings[preferred][1])?0:1,snap:false};
}
''' +s[pos:]
a=s.index("const kind=document.querySelector('input[name=editMode]:checked').value;if(kind==='bar'",s.index("for(const id of ['epsPlot','incPlot','paPlot'])"))
b=s.index('svg.setPointerCapture(e.pointerId);',a)
s=s[:a]+'''const preferred=document.querySelector('input[name=editMode]:checked').value,handle=e.target?.closest?.('[data-interval-kind]'),explicit=handle?{kind:handle.dataset.intervalKind,edge:Number(handle.dataset.intervalEdge)}:null,x=graphPointer(svg,e),axisMax=Number(svg.dataset.xmax),choice=chooseProfileBoundary(S.settings,x,axisMax,preferred,explicit);
 if(!choice){toast('Uncheck “Treat as no convincing bar” to edit the bar interval.');return;}const {kind,edge}=choice;document.querySelector(`input[name=editMode][value="${kind}"]`).checked=true;
 S.drag={kind,edge,axisMax,grabOffset:choice.snap?x-S.settings[kind][edge]:0};''' +s[b:]
s=s.replace('value=graphPointer(svg,e);r[edge]', 'value=clamp(graphPointer(svg,e)-(S.drag.grabOffset??0),0,S.drag.axisMax);r[edge]',1)
s=s.replace('radiusAxis,skyPADirection,','radiusAxis,chooseProfileBoundary,skyPADirection,');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('Drag a shaded edge in any profile graph, or enter bounds below.', 'Drag a coloured boundary or its square handle in any profile graph, or enter bounds below. Orange bar handles are at the top; green disc handles are just below them, so coincident boundaries can be selected separately. Clicking near a boundary selects its interval automatically; elsewhere the Edit interval selector applies.');p.write_text(s,encoding='utf8')
