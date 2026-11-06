from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'Euclid/adaptive_MER_VIS/test_MER_VIS_synthetic_geometry.py'
source=p.read_text().replace("root=Path(__file__).parent/'synthetic_check'", "root=Path(r'"+str(ROOT/'laptop_setup/verification/synthetic')+"')")
exec(compile(source,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
