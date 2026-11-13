from pathlib import Path
p=Path('MER_VIS_pipeline_v2/report_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace("im.plot(xc,yc,'+',color='#f34848',ms=6,mew=1.1);", "im.plot(h['CENX']-1-xa,h['CENY']-1-ya,'x',color='white',ms=4,mew=.8);im.plot(xc,yc,'+',color='#f34848',ms=6,mew=1.1);")
s=s.replace("if info:issues.append('INFO: Nearly face-on; disc PA uncertain, not a quality defect.')", "if info:issues.append('INFO: Nearly face-on; disc PA uncertain, not a quality defect.')\n centreoffset=number(r.get('codex_centre_offset_arcsec'));method=str(r.get('codex_method',''))\n if np.isfinite(centreoffset):issues.append(f'Centre offset {centreoffset:.2f} arcsec; method {method}. Red + fitted; white x catalogue.')")
s=s.replace("partial=partial,photutils_disc", "partial=partial,centre_offset_arcsec=centreoffset if np.isfinite(centreoffset) else None,method=method,bar_status=str(r.get('codex_bar_status','')),photutils_disc")
p.write_text(s,encoding='utf8')
