from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace('return radiusAxis(Math.max(1,...accepted.map(p=>p.sma_arcsec??0))*1.07).max;', "const bounds=[...(S.settings.disc??[]),...(S.settings.noBar?[]:(S.settings.bar??[]))].filter(finite);return radiusAxis(Math.max(1,...accepted.map(p=>p.sma_arcsec??0),...bounds)*1.07).max;")
s=s.replace('recalculate();await loadImage(true);','recalculate();expandProfileView(false);await loadImage(true);',1)
s=s.replace("markDirty();recalculate();}\nfunction pool()", "markDirty();recalculate();expandProfileView();}\nfunction pool()",1)
s=s.replace("svg.onpointerup=()=>{if(S.drag){S.drag=null;markDirty();}}", "svg.onpointerup=()=>{if(S.drag){S.drag=null;markDirty();expandProfileView();}}")
needle='function fitWindow(view)'
pos=s.index(needle)
s=s[:pos]+'''// A profile radius is a semi-major axis: the image must cover twice that radius.
function profileImageWindow(g,settings,radius){
 const centre=g.centre?.every(finite)?g.centre:g.catalogue_centre,scale=g.pixel_scale_arcsec;
 if(!centre?.every(finite)||!(scale>0))return [...g.default_window];
 const r=radius/scale*1.06;let bounds=[centre[0]-r,centre[0]+r,centre[1]-r,centre[1]+r];
 // Include each fitted ellipse's own centre, orientation and projected extents.
 for(const p of g.profile){if(!(p.sma_arcsec<=radius)||![p.sma_arcsec,p.x_original_pix,p.y_original_pix,p.pa_pixel_deg,p.ellipticity].every(finite)||p.sma_arcsec<=0||p.ellipticity<0||p.ellipticity>=1)continue;
  const a=p.sma_arcsec/scale,b=a*(1-p.ellipticity),angle=p.pa_pixel_deg*Math.PI/180,c=Math.cos(angle),d=Math.sin(angle),dx=Math.hypot(a*c,b*d)*1.04,dy=Math.hypot(a*d,b*c)*1.04;
  bounds=[Math.min(bounds[0],p.x_original_pix-dx),Math.max(bounds[1],p.x_original_pix+dx),Math.min(bounds[2],p.y_original_pix-dy),Math.max(bounds[3],p.y_original_pix+dy)];
 }
 return bounds;
}
function expandProfileView(reload=true){if(!S.g||!S.view)return false;
 const required=profileImageWindow(S.g,S.settings,plotMax()),v=S.view;
 const desired=fitWindow([Math.min(v[0],required[0]),Math.max(v[1],required[1]),Math.min(v[2],required[2]),Math.max(v[3],required[3])]);
 if(desired.every((x,i)=>Math.abs(x-v[i])<.5))return false;
 S.view=desired;if(reload){clearTimeout(zoom.timer);loadImage();saveDraft();}return true;
}
''' +s[pos:]
s=s.replace("S.view=[...S.g.default_window];loadImage();saveDraft();", "S.view=fitWindow(profileImageWindow(S.g,S.settings,plotMax()));loadImage();saveDraft();")
s=s.replace('writeControls();markDirty();recalculate();};','writeControls();markDirty();recalculate();expandProfileView();};',1)
s=s.replace('state:S,calculate,radiusAxis,','state:S,calculate,radiusAxis,profileImageWindow,expandProfileView,');p.write_text(s,encoding='utf8')
