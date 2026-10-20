import json
s=json.load(open('MER_VIS_external_comparison/summary.json'))
for name in ['common','codex_revised_unflagged','both_unflagged','codex_original_unflagged','non_face_on']:
 print(name, s['statistics'][name])
print('q0=.2 residual',s['supplied_inclination_q0_02_residual'])
