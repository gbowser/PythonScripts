import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const cwd=process.cwd();
const SKILL='C:/Users/gordo/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const PY='C:/Users/gordo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const ink='#142633',blue='#205f7a',muted='#526673';
const source='Sources: MER_VIS_local_geometry_manifest.csv; MER_VIS_report_summary.json and MER_VIS_report_verification.json in D:/Dropbox/Public Documents/UCLAN/MSc Research/Euclid/MER_VIS_galaxy_reports/all_2777; completed PA and inclination comparison statistics from the revised fitting report. Run completed October 2026.';
function text(s,t,x,y,w,h,size=26,color=ink,bold=false){let z=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=t;z.text.style={typeface:'Arial',fontSize:size,color,bold};return z;}
function slide(title,n){let s=p.slides.add();s.background.fill='#ffffff';text(s,title,64,42,1152,90,44,ink,true);text(s,`${n} / 13`,1140,680,76,22,16,muted);s.speakerNotes.text=source;return s;}
function table(s,values,x,y,w,h,widths,size=24){let t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});t.borders.assign({fill:'#d6e0e5',width:.7,style:'solid'});for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){let cell=t.getCell(r,c);cell.fill=r===0?'#e8f0f4':'#ffffff';cell.text.style={typeface:'Arial',fontSize:size,color:ink,bold:r===0};}return t;}
let s=slide('Euclid MER VIS geometry outcomes',1);
text(s,'2,777 galaxy cutouts',64,208,1100,100,60,blue,true);
text(s,'Completed fitting and grouped review reports',64,336,1100,65,32);
text(s,'2,250 reports carry a quality issue label\n527 reports have no detected issue',64,440,1100,110,30);
text(s,'Updated 20 October 2026',64,612,700,40,22,muted);
s.speakerNotes.text=source+' QI includes any geometry flag, failed fit or partial requested coverage. NoQI is a screening label and does not certify physical geometry.';
s=slide('Fitting outcomes by number of flags',2);
text(s,'Percentage of all 2,777 galaxies',64,136,760,40,25,muted);
const colors=['#367a8c','#e5bb66','#cc9637','#a66b24','#72441c','#ac4b47'];
const defs=[['No counted flags',[0.216421,0,0]],['1 flag',[0,0.346777,0]],['2 flags',[0,0.167807,0]],['3 flags',[0,0.063378,0]],['4 flags',[0,0.000360,0]],['Failed',[0,0,0.205258]]];
const chart=s.charts.add('bar',{position:{left:64,top:185,width:780,height:400},categories:['No counted flags','Flagged fit','Failed fit'],series:defs.map((d,i)=>({name:d[0],values:d[1],fill:colors[i],valuesFormatCode:'0.0%'})),hasLegend:false,barOptions:{direction:'column',grouping:'stacked',overlap:100,gapWidth:90},xAxis:{textStyle:{fontSize:21}},yAxis:{textStyle:{fontSize:20},numberFormatCode:'0%',majorGridlines:{fill:'#e3e9ec',width:1,style:'solid'}}});applyPresentationChartFont(chart,{fontFamily:'Arial'});
text(s,'Flagged fit: 57.8% total',870,180,345,52,27,blue,true);
for(let j=1;j<=4;j++)text(s,`${j} flag${j===1?'':'s'}: ${[963,466,176,1][j-1]} (${(j===4?'<0.1':([963,466,176,1][j-1]/2777*100).toFixed(1))}%)`,870,245+(j-1)*55,345,46,25,colors[j],true);
text(s,'No counted flags: 21.6% (601)\nFailed: 20.5% (570)',870,490,345,82,24);
text(s,'Chart excludes face-on flag and disc PA instability for face-on galaxies. Source QI labels unchanged.',64,608,1135,60,23,muted);
s.speakerNotes.text=source+' Revised chart policy: remove nearly_face_on_PA_uncertain from all counts, and discard disc_PA_unstable for the 200 nearly-face-on fits. Counts now 0=601,1=963,2=466,3=176,4=1;flagged1606. Original source flags and QI/NoQI review groups remain unchanged. Previous calculation for provenance: Flag multiplicity computed directly from non-empty semicolon-separated codex_quality_flags for provisional_fit rows: 0=546,1=850,2=497,3=291,4=23. Flagged subtotal1661. All stacked segments use denominator2777. Failed fits are separate and not classified by flag count. Partial coverage is not counted as a geometry flag.';
s=slide('Quality flags and reasons for failure',3);
text(s,'Counted flags among completed fits',64,138,665,42,27,blue,true);
const fc=s.charts.add('bar',{position:{left:52,top:197,width:690,height:360},categories:['Small bar interval','Unstable disc PA*','Changing disc shape','Unstable bar PA','Weak bar signature'],series:[{name:'Share of fitted galaxies',values:[1210/2207,609/2007,573/2207,28/2207,7/2207].map(v=>Math.round(v*1000000)/1000000),fill:'#c18b28',valuesFormatCode:'0.0%'}],hasLegend:false,barOptions:{direction:'bar',grouping:'clustered',gapWidth:55},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:19}},xAxis:{textStyle:{fontSize:20}},yAxis:{numberFormatCode:'0%',textStyle:{fontSize:18}}});applyPresentationChartFont(fc,{fontFamily:'Arial'});
text(s,'*Disc PA: 609 / 2,007 non-face-on fits (30.3%).\nOther bars: denominator 2,207. Flags overlap.',64,570,650,65,22,muted);
text(s,'570 failed fits: recorded reasons',770,138,455,65,26,blue,true);
const fail=s.charts.add('bar',{position:{left:765,top:210,width:455,height:265},categories:['Interval','Short profile','Centre'],series:[{name:'Share of failures',values:[0.756140,0.242105,0.001754],fill:'#ac4b47',valuesFormatCode:'0.0%'}],hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:70},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:19}},xAxis:{textStyle:{fontSize:18}},yAxis:{numberFormatCode:'0%',textStyle:{fontSize:17}}});applyPresentationChartFont(fail,{fontFamily:'Arial'});
text(s,'431: fewer than 3 reliable ellipses in the selected bar or disc interval.\n138: fewer than 10 reliable ellipses overall.\n1: centre outside a detected galaxy.',770,486,445,155,21);
text(s,'Failure categories are mutually exclusive: 431 + 138 + 1 = 570.',64,650,1080,28,21,muted);
s.speakerNotes.text=source+' Revised flag display: remove face-on category. Exclude 200 face-on fits from the disc PA eligible population, including 182 with disc_PA_unstable. Remaining disc PA instability609/2007=30.3%. Other flag percentages retain denominator2207. Failure chart unchanged. Previous counts retained here for provenance only. Failure counts are grouped directly from codex_error for codex_fit_status=fit_failed. 431 entries say ValueError: Insufficient bar/disc isophotes in selected radial ranges, triggered when either selected interval has fewer than three reliable isophotes. 138 say Only N reliable isophotes; inspect profile, with N<10. One says Catalogue centre is not on a detected galaxy. These are recorded failure stages, not an independent diagnosis of physical cause. Left chart denominator2207, overlapping flags. Right chart denominator570, exclusive failures. Quality flag counts1210,791,573,200,28,7. 62 partial requested cutouts separately trigger QI.';
s=slide('Comparison with Euclid geometry',4);
text(s,'Adopted rule: adjusted Euclid sky PA = (WCS-converted PA + 90°) mod 180°\nPossible explanation: catalogue angle from detection-image y rather than documented x (unconfirmed).',64,140,1150,88,23,blue,true);
table(s,[['Median absolute difference','All 2,207 fits','546 unflagged'],['Adjusted detection PA','7.07°','3.72°'],['Detection inclination proxy','4.28°','2.71°'],['Sérsic inclination proxy','8.41°','6.76°']],64,250,1152,250,[620,266,266],25);
text(s,'79.3% of unflagged fits agree with adjusted Euclid PA within 10°.',64,535,1130,55,28);
text(s,'Codex PA: North towards East. N = 0°, NE = 45°, E = 90° (mod 180°).\nCounterclockwise on a North-up, East-left image. Pixel angles first pass through WCS.',64,606,1150,66,22,muted);
s.speakerNotes.text=source+' The unflagged comparison includes 546 fits, including 19 partial cutouts, and differs from the 527 NoQI group. Codex fits Photutils isophotes, converts their pixel major-axis vectors using the local FITS WCS, and calculates degrees(atan2(East, North)) modulo 180. It uses axial means in selected disc and bar radial ranges. These are observed sky PAs before deprojection. North towards East is counterclockwise on a North-up East-left display, clockwise if East is right. Euclid documents raw POSITION_ANGLE as CCW from image x (SExtractor THETA_IMAGE), not necessarily celestial East. Our +90 adjustment follows the WCS conversion. For North-up East-left images, sky PA = (CCW image angle from +x +90) modulo180. This reference change is ALREADY included in the original WCS conversion. The adopted ADDITIONAL +90 follows that conversion and cannot be explained by counting the same reference change again. The observed offset is consistent with POSITION_ANGLE being referenced to the detection image y-axis rather than the documented x-axis, assuming the same rotation sense and major-axis definition. Interpreting a y-referenced value as x-referenced introduces a quarter-turn, cancelled by the additional 90-degree adjustment modulo180. This is a plausible explanation, not a confirmed documentation or pipeline error. The 2777 local North offsets have median absolute 0.141 degrees and maximum 0.604 degrees. No additional thumbnail rotation is applied. We adopt the correction without asserting an official Euclid North/East reference change. Euclid source: https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/dpcards/mer_finalcatalog.html#mer-main-catalog-fits. Inclinations assume a circular thin disc, q0=0. No separate disc-component b/a values are populated. These are consistency checks, not independent true outer-disc measurements.';
s=slide('Why image review remains necessary',5);
s.images.add({blob:new Uint8Array(await fs.readFile(path.resolve(cwd,'../MER_VIS_explanation_work/example_5.png'))),contentType:'image/png',alt:'Native image and ellipse profiles of galaxy -515488559271594427 showing unstable outer-disc PA',fit:'contain',position:{left:50,top:170,width:765,height:459}});
text(s,'Example QI galaxy',850,172,360,45,29,blue,true);
text(s,'−515488559271594427',850,229,360,55,24);
text(s,'Disc PA varies strongly across the outer interval.',850,307,360,105,28);
text(s,'The small bar interval also raises a resolution warning.',850,440,360,115,27);
text(s,'A close mean PA match can coexist with unstable fitted geometry.',64,643,1120,40,23,muted);
s.speakerNotes.text=source+' Image source: MER_VIS_explanation_work/example_5.png, prepared from this galaxy native FITS cutout and saved ellipse profile. Disc PA 151.1468 degrees, inclination 27.2469 degrees, disc PA scatter 35.4256 degrees. Original flags: disc_PA_unstable;small_bar_sensitive_to_resolution. Orange and green identify selected bar and disc intervals. The close adjusted Euclid mean PA does not remove radial instability.';
s=slide('Review collection and next steps',6);
table(s,[['Review group','Galaxies','PDF batches'],['QI','2,250','38'],['NoQI','527','9']],64,158,1152,190,[650,250,252],26);
text(s,'47 PDFs contain 463 pages at six galaxies per page.',64,381,1140,56,30,blue,true);
text(s,'Review QI warnings and failures using the image and profiles.\nCheck physical component identification in the 527 NoQI cases.\nRecord accepted geometry before final deprojection.',64,465,1140,160,27);
text(s,'The galaxy index gives the PNG path, PDF batch, page and position.',64,644,1120,36,22,muted);
s.speakerNotes.text=source+' Output root: D:/Dropbox/Public Documents/UCLAN/MSc Research/Euclid/MER_VIS_galaxy_reports/all_2777. QI = 1661 flagged fits + 570 failures + 19 otherwise unflagged partial cases. NoQI = 527. Each PDF contains at most 60 galaxies. Index: MER_VIS_report_review_index.csv. The source FITS files and fitting manifest remain unchanged. All fitted geometry remains provisional until physical review.';
await fs.mkdir(path.resolve(cwd,'renders'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.resolve(cwd,'renders',`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));}
const exampleGroups=JSON.parse(await fs.readFile(path.resolve(cwd,'example_selection.json'),'utf8'));
const titles=['Small bar interval','Unstable disc PA','Changing disc ellipticity','Unstable bar PA','Weak ellipse bar signature','Failed fit: selected interval','Failed fit: short reliable profile'];
const interpretations=[
 'The selected bar interval ends below 1.5 arcsec. This warns about resolution and range selection, not a measured physical bar length.',
 'The sky PA changes across the green disc interval. The outer contours do not give one stable disc direction.',
 'Ellipticity changes across the green disc interval. Inclination depends on which outer contours are used.',
 'The PA changes across the orange bar interval. A single adopted bar direction is uncertain.',
 'Ellipses in the orange interval are relatively round. This weakens the ellipse-based bar signature, rather than proving there is no bar.',
 'There are at least ten reliable ellipses overall, but fewer than three in at least one selected bar/disc interval. Candidate ranges are not accepted geometry.',
 'Fewer than ten ellipses pass the reliability checks overall. The fit stops before adopting bar/disc geometry. Grey samples were rejected.'
];
for(let k=0;k<exampleGroups.length;k++){
 const group=exampleGroups[k];s=slide(titles[k],k+7);
 text(s,k<5?'Each galaxy has exactly this ONE original geometry flag; neither cutout is partial.':'Two examples of this recorded failure type; neither cutout is partial.',64,134,1150,50,23,blue,true);
 for(let j=0;j<2;j++){
  const e=group.examples[j];const x=64+j*584;
  text(s,`Galaxy ${e.id}`,x,195,560,40,22,ink,true);
  s.images.add({blob:new Uint8Array(await fs.readFile(path.resolve(cwd,e.image))),contentType:'image/png',alt:`Galaxy ${e.id}: native image, fitted ellipses, ellipticity and sky PA profiles`,fit:'contain',position:{left:x,top:235,width:560,height:260}});
  text(s,e.detail,x,510,550,90,23,ink,true);
 }
 text(s,interpretations[k],64,615,1150,54,23,muted);
 s.speakerNotes.text=source+' Two examples selected from the original fitting manifest with exactly one nonempty original geometry flag, no partial coverage, and no secondary informational flag. Failed cases selected by recorded error and have no adopted geometry. Orange=bar interval; green=disc interval; blue=reliable samples; grey=rejected samples. Image and profiles are crops from the existing full-resolution report cards; no refitting or image rotation. Interpretation concerns the numerical trigger, not a confirmed physical cause. '+group.examples.map(e=>`Galaxy ${e.id}: ${e.detail} Original flag: ${e.original_flags||'none; failed fit'}. Source: ${e.source}`).join(' ');
}

for(let i=6;i<p.slides.items.length;i++){const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.resolve(cwd,'renders',`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));}
