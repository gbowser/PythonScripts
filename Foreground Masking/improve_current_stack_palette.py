from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig')
s=s.replace("const pct=(n,d=2777)=>(100*n/d).toFixed(1)+'%';", "const pct=(n,d=2777)=>n>0&&100*n/d<.1?'<0.1%':(100*n/d).toFixed(1)+'%';")
s=s.replace("'#563b60','#ac4b47'", "'#563b60','#4a587a','#4e7b71','#a85050','#686868'").replace('Math.min(k,6)','Math.min(k,10)')
p.write_text(s,encoding='utf8')
