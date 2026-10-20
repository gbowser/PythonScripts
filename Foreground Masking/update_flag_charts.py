from pathlib import Path
p=Path('MER_VIS_summary_build/build_summary.mjs');s=p.read_text(encoding='utf-8-sig')
a=s.index("s=slide('Fitting outcomes',2);");b=s.index("s=slide('Comparison with Euclid geometry',4);",a)
s=s[:a]+'''s=slide('Fitting outcomes by number of flags',2);
text(s,'Percentage of all 2,777 galaxies',64,136,760,40,25,muted);
const colors=['#367a8c','#e5bb66','#cc9637','#a66b24','#72441c','#ac4b47'];
const defs=[['No flags',[546/2777,0,0]],['1 flag',[0,850/2777,0]],['2 flags',[0,497/2777,0]],['3 flags',[0,291/2777,0]],['4 flags',[0,23/2777,0]],['Failed',[0,0,570/2777]]];
const chart=s.charts.add('bar',{position:{left:64,top:185,width:780,height:400},categories:['No geometry flags','Flagged fit','Failed fit'],series:defs.map((d,i)=>({name:d[0],values:d[1],fill:colors[i],valuesFormatCode:'0.0%'})),hasLegend:false,barOptions:{direction:'column',grouping:'stacked',overlap:100,gapWidth:90},xAxis:{textStyle:{fontSize:21}},yAxis:{textStyle:{fontSize:20},numberFormatCode:'0%',majorGridlines:{fill:'#e3e9ec',width:1,style:'solid'}}});applyPresentationChartFont(chart,{fontFamily:'Arial'});
text(s,'Flagged fit: 59.8% total',870,180,345,52,27,blue,true);
for(let j=1;j<=4;j++)text(s,`${j} flag${j===1?'':'s'}: ${[850,497,291,23][j-1]} (${([850,497,291,23][j-1]/2777*100).toFixed(1)}%)`,870,245+(j-1)*55,345,46,25,colors[j],true);
text(s,'No flags: 19.7% (546)\\nFailed: 20.5% (570)',870,490,345,82,24);
text(s,'Segment percentages use the full sample, not just flagged fits. Maximum observed: four flags.',64,608,1135,60,23,muted);
s.speakerNotes.text=source+' Flag multiplicity computed directly from non-empty semicolon-separated codex_quality_flags for provisional_fit rows: 0=546,1=850,2=497,3=291,4=23. Flagged subtotal1661. All stacked segments use denominator2777. Failed fits are separate and not classified by flag count. Partial coverage is not counted as a geometry flag.';
s=slide('Quality flags and reasons for failure',3);
text(s,'Flags among 2,207 completed fits',64,138,665,42,27,blue,true);
const fc=s.charts.add('bar',{position:{left:52,top:197,width:690,height:360},categories:['Small bar interval','Unstable disc PA','Changing disc shape','Nearly face on','Unstable bar PA','Weak bar signature'],series:[{name:'Share of fitted galaxies',values:[1210,791,573,200,28,7].map(v=>v/2207),fill:'#c18b28',valuesFormatCode:'0.0%'}],hasLegend:false,barOptions:{direction:'bar',grouping:'clustered',gapWidth:55},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:19}},xAxis:{textStyle:{fontSize:20}},yAxis:{numberFormatCode:'0%',textStyle:{fontSize:18}}});applyPresentationChartFont(fc,{fontFamily:'Arial'});
text(s,'Flags overlap. One galaxy can appear in several bars.',64,570,650,65,22,muted);
text(s,'570 failed fits: recorded reasons',770,138,455,65,26,blue,true);
const fail=s.charts.add('bar',{position:{left:765,top:210,width:455,height:265},categories:['Interval','Short profile','Centre'],series:[{name:'Share of failures',values:[431/570,138/570,1/570],fill:'#ac4b47',valuesFormatCode:'0.0%'}],hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:70},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:19}},xAxis:{textStyle:{fontSize:18}},yAxis:{numberFormatCode:'0%',textStyle:{fontSize:17}}});applyPresentationChartFont(fail,{fontFamily:'Arial'});
text(s,'431: fewer than 3 reliable ellipses in the selected bar or disc interval.\\n138: fewer than 10 reliable ellipses overall.\\n1: centre outside a detected galaxy.',770,486,445,155,21);
text(s,'Failure categories are mutually exclusive: 431 + 138 + 1 = 570.',64,650,1080,28,21,muted);
s.speakerNotes.text=source+' Failure counts are grouped directly from codex_error for codex_fit_status=fit_failed. 431 entries say ValueError: Insufficient bar/disc isophotes in selected radial ranges, triggered when either selected interval has fewer than three reliable isophotes. 138 say Only N reliable isophotes; inspect profile, with N<10. One says Catalogue centre is not on a detected galaxy. These are recorded failure stages, not an independent diagnosis of physical cause. Left chart denominator2207, overlapping flags. Right chart denominator570, exclusive failures. Quality flag counts1210,791,573,200,28,7. 62 partial requested cutouts separately trigger QI.';
''' +s[b:]
s=s.replace("'.codex-finalizer-PA-yaxis'","'.codex-finalizer-flag-charts'").replace('Euclid_MER_VIS_outcomes_summary_PA_yaxis.pptx','Euclid_MER_VIS_outcomes_summary_flag_charts.pptx')
s=s.replace("'--require-native-table-slide','3',",'').replace('requiredNativeChartOwnerSlides:[2]','requiredNativeChartOwnerSlides:[2,3]').replace('requiredNativeTableOwnerSlides:[3,4,6]','requiredNativeTableOwnerSlides:[4,6]')
p.write_text(s,encoding='utf-8')
