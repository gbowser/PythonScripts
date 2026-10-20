from pathlib import Path
p=Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf8');s=s.replace("im=fig.add_axes([.045,.44,.415,.38]);", "name=str(r.get('catalogue_name','')).strip()\n if name and name!='nan':fig.text(.045,.848,f'Catalogue: {name}   ({r.get(\"catalogue_match_source\",\"\")}; {float(r[\"catalogue_match_separation_arcsec\"]):.2f} arcsec)',fontsize=10.2,color='#20577c')\n im=fig.add_axes([.045,.44,.415,.38]);")
p.write_text(s,encoding='utf8')
