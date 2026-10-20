from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig');s=s.replace("const fmt=x=>x==null?'unavailable':Number(x).toFixed(2);", "const fmt=x=>x==null?'unavailable':Number(x).toFixed(2);const angle=x=>x==null?'unavailable':Number(x).toFixed(2)+'°';")
s=s.replace('Disc ${fmt(e.disc)}°; bar ${fmt(e.bar)}°; i ${fmt(e.inc)}°','Disc ${angle(e.disc)}; bar ${angle(e.bar)}; i ${angle(e.inc)}')
p.write_text(s,encoding='utf8')
