from pathlib import Path
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8').replace('<p id="refitStatus" role="status">','<a id="exportRefit" class="button secondary" hidden>Download refit metrics CSV</a><p id="refitStatus" role="status">');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8').replace("$('showOriginal').disabled=!S.g.refit;", "$('showOriginal').disabled=!S.g.refit;$('exportRefit').hidden=!S.g.refit;if(S.g.refit)$('exportRefit').href='/api/refit/export?job='+S.g.refit.job_id;")
s=s.replace("Original intervals use stored pipeline selections. Edited intervals use accepted ellipses inside the new bounds; this may differ from the original brightness-based disc selection.", "Original intervals use stored selections from the displayed fit. Edited intervals use accepted ellipses inside the new bounds; this may differ from the original brightness-based disc selection.")
p.write_text(s,encoding='utf8')
