from pathlib import Path
s=Path('compare_supplied_geometry.py').read_text(encoding='utf-8-sig')
s=s.replace("Path('MER_VIS_external_comparison')", "Path(__file__).parent/'current_report'/'comparison'")
s=s.replace("out.mkdir(exist_ok=True)","out.mkdir(exist_ok=True,parents=True)")
s=s.replace("Euclid_MER_VIS_geometry\\MER_VIS_local_geometry_manifest.csv", "Euclid_MER_VIS_geometry_v2\\MER_VIS_local_geometry_manifest.csv")
s=s.replace("~m.codex_quality_flags.fillna('').str.contains('nearly_face_on_PA_uncertain')", "~m.codex_information.fillna('').str.contains('nearly_face_on')")
Path('MER_VIS_pipeline_v2/compare_current_MER_VIS_with_supplied.py').write_text(s,encoding='utf8')
