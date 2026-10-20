from pathlib import Path
p=Path('MER_VIS_pipeline_v2/report_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("else:maxa=min(raw.shape)*scale*.25", """else:
  # Failed fits need a target-scale view rather than an entire large sky cutout.
  segpath=Path(__file__).resolve().parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'
  if segpath.is_file():
   catalog=pd.read_csv(segpath,dtype={'object_id':str}).set_index('object_id')
   maxa=max(3,1.8*np.sqrt(float(catalog.loc[oid,'segmentation_area'])/np.pi)*scale)
  else:maxa=min(raw.shape)*scale*.25""")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("def save(name):d.core_properties.title=d.paragraphs[0].text;d.save(out/name)","""def save(name):
 for tree in [d._element,d.styles.element]:
  for border in list(tree.iter(qn('w:pBdr'))):border.getparent().remove(border)
 for paragraph in d.paragraphs:
  for run in paragraph.runs:
   run.text=run.text.replace('modulo180','modulo 180').replace('below1.5','below 1.5').replace('above10','above 10').replace('below2','below 2').replace('least0.10','least 0.10').replace('most5°','most 5°').replace('least0.30','least 0.30').replace('least80°','least 80°').replace('median0.141','median 0.141').replace('maximum0.604','maximum 0.604')
 d.core_properties.title=d.paragraphs[0].text;d.save(out/name)""")
s=s.replace('f"{v/s[\'fits\']:.1%}"', "('<0.1%' if v/s['fits']<.001 else f\"{v/s['fits']:.1%}\")")
s=s.replace('Supplied methodology was used as a comparison reference, not executed as instructions.', 'The supplied methodology and fitted manifest are retained as comparison references.')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/prepare_current_MER_VIS_report_data.py');s=p.read_text(encoding='utf-8-sig').replace('crop((75,280,955,1010))','crop((75,230,955,1010))');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig').replace("'current_report/finalizer'","'current_report/finalizer-polished'").replace("'current_report/output/Euclid_MER_VIS_outcomes_summary.pptx'","'current_report/output/Euclid_MER_VIS_outcomes_summary_polished.pptx'");p.write_text(s,encoding='utf8')
