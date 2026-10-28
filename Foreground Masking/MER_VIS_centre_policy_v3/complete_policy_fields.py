from pathlib import Path
p=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');s=p.read_text(encoding='utf8');i=s.index(' return out',s.index('def profile_rows'));s=s[:i]+''' for point in out:
  point.update(centre_measurement(point,REFERENCE_CENTRE,NATIVE_SCALE,CENTRE_POLICY))
  point.update(numerically_accepted_strict=numerical_acceptance(point),numerically_accepted_relaxed=numerical_acceptance(point,True))
''' +s[i:];p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace("['barThreshold','small_bar']]){", "['barThreshold','small_bar'],['centreCap','centre_cap_native'],['centreFraction','centre_fraction'],['centreFloor','centre_floor_native']]){",1).replace("['smallBarEnabled','small_bar_enabled']])s.rules", "['smallBarEnabled','small_bar_enabled'],['centreEnabled','centre_enabled']])s.rules",1)
s=s.replace(" $('barMin').disabled=$('barMax').disabled=s.noBar;markDirty();recalculate();expandProfileView();}", " if(s.rules.centre_floor_native>s.rules.centre_cap_native){showError('Centre floor must not exceed the absolute cap.');return;}\n $('barMin').disabled=$('barMax').disabled=s.noBar;markDirty();recalculate();expandProfileView();}",1)
p.write_text(s,encoding='utf8')
