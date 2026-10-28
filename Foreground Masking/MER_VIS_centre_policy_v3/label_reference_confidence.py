from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');needle=" if(rejectedDisc.length||rejectedBar.length)issues.push"
s=s.replace(needle," if(S.g.campaign_case&&(S.g.campaign_case.reference_uncertain||S.g.centre_reference?.provenance?.includes('unverified')))issues.push('Centre reference unverified: visual confirmation required');\n"+needle,1)
s=s.replace("['Adopted centre X / Y',g.centre.every(finite)?", "['Centre reference provenance',g.centre_reference?.provenance??'Legacy fit reference'],['Centre screen',S.settings.rules.centre_enabled!==false?`Cap ${fmt(S.settings.rules.centre_cap_native??3)} native px; ${fmt((S.settings.rules.centre_fraction??.05)*100,1)}% of radius`:'Disabled for exploration'],['Adopted centre X / Y',g.centre.every(finite)?",1)
s=s.replace('rejected.length>0,r.centre_enabled===false?', "rejected.length>0||has('Centre reference unverified'),r.centre_enabled===false?",1)
s=s.replace('The displacement plot compares centres with the tolerance curve.', 'The displacement plot compares centres with the tolerance curve. An unverified or previously uncertain reference requires visual confirmation before adopting geometry.',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8').replace('"""Local, read-only FITS exploration and saved geometry reviews. No refitting."""','"""Local FITS review with isolated centre-constrained trials and separate review rounds."""',1);p.write_text(s,encoding='utf8')
