from pathlib import Path
p=Path('MER_VIS_summary_build/build_summary.mjs');s=p.read_text(encoding='utf-8-sig');s=s.replace('`${n} / 6`','`${n} / 13`')
pos=s.index('const staging=')
extra='''const exampleGroups=JSON.parse(await fs.readFile(path.resolve(cwd,'example_selection.json'),'utf8'));
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
  s.images.add({blob:new Uint8Array(await fs.readFile(path.resolve(cwd,e.image))),contentType:'image/png',alt:`Galaxy ${e.id}: native image, fitted ellipses, ellipticity and sky PA profiles`,fit:'contain',position:{left:x,top:245,width:560,height:225}});
  text(s,e.detail,x,485,550,105,23,ink,true);
 }
 text(s,interpretations[k],64,592,1150,66,23,muted);
 s.speakerNotes.text=source+' Two examples selected from the original fitting manifest with exactly one nonempty original geometry flag, no partial coverage, and no secondary informational flag. Failed cases selected by recorded error and have no adopted geometry. Orange=bar interval; green=disc interval; blue=reliable samples; grey=rejected samples. Image and profiles are crops from the existing full-resolution report cards; no refitting or image rotation. Interpretation concerns the numerical trigger, not a confirmed physical cause. '+group.examples.map(e=>`Galaxy ${e.id}: ${e.detail} Original flag: ${e.original_flags||'none; failed fit'}. Source: ${e.source}`).join(' ');
}
'''
s=s[:pos]+extra+s[pos:]
s=s.replace("'.codex-finalizer-faceon-final'","'.codex-finalizer-examples'").replace('Euclid_MER_VIS_outcomes_summary_faceon_final.pptx','Euclid_MER_VIS_outcomes_summary_with_examples.pptx').replace('explicitTotalSlideCount:6','explicitTotalSlideCount:13').replace('Six-slide deck saved','Thirteen-slide deck saved')
p.write_text(s,encoding='utf-8')
