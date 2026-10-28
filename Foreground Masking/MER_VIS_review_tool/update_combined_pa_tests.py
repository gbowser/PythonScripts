from pathlib import Path
for name in ['test_pa_continuity.mjs','test_excluded_ellipses.mjs']:
 p=Path('MER_VIS_review_tool')/name;s=p.read_text(encoding='utf8');s=s.replace('euclidPAOverlay','paComparison').replace('discPAOverlay','paComparison').replace("'paComparison','paComparison'","'paComparison'").replace('paComparison:true,paComparison:true','paComparison:true');
 if name=='test_pa_continuity.mjs':s=s.replace('S.g.euclid={disc_pa:7,inclination:32.5};const referenceInput', 'S.g.euclid={disc_pa:7,inclination:32.5};S.settings.display.paComparison=true;const referenceInput',1)
 p.write_text(s,encoding='utf8')
