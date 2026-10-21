from pathlib import Path
p=Path('MER_VIS_review_tool/style.css');s=p.read_text(encoding='utf8');s+='\n#centrePanel{margin:10px 0 16px;padding:12px 0;border-top:1px solid #d6e0e7;border-bottom:1px solid #d6e0e7}#centrePanel>summary{font-weight:600;cursor:pointer;color:#265a72}#centrePanel>p{margin-top:10px}#centrePanel .row{flex-wrap:wrap}#centrePanel .interval-grid{margin:10px 0}#centrePanel #exportRefit{display:inline-block;margin-top:8px}\n';p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8').replace("['Centre scatter',fmt(g.original.centre_scatter)+'″']", "['Centre scatter',fmt(g.original.centre_scatter)+'″'+(g.refit?.lock_centre?' (centre fixed)':'')]")
s=s.replace("Status: ${S.g.original.status}. Full metrics and provenance saved in ${S.g.refit.folder}", "Status: ${S.g.original.status.replaceAll('_',' ')}. Updated profiles and metrics are saved separately.")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/README_MER_VIS_REVIEW.md');s=p.read_text(encoding='utf8').replace('Recomputed files are stored automatically even before an assessment is saved.', 'Recomputed files are stored automatically even before an assessment is saved. **Download refit metrics CSV** exports the complete updated row, including the recalculated Euclid differences and disc sampling statistics.')
p.write_text(s,encoding='utf8')
