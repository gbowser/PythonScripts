from pathlib import Path
p=Path('make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf8')
s=s.replace("if len(g):maxa=float(g.sma_arcsec.max())\n elif len(pr):maxa=float(pr.sma_arcsec.max())\n else:maxa=min(raw.shape)*scale*.25", "if len(g):maxa=float(g.sma_arcsec.max())\n elif len(pr):maxa=float(pr.sma_arcsec.max())\n else:maxa=min(raw.shape)*scale*.25\n if not np.isfinite(maxa) or maxa<=0:maxa=min(raw.shape)*scale*.25")
s=s.replace("name=f'{ordinal:02d}_Euclid_{oid}_MER_VIS_geometry_report.png';fig.savefig(out/name,dpi=250);plt.close(fig)","quality_issue=bool(failed or flaglist or partial)\n suffix='_QI' if quality_issue else ''\n name=f'{ordinal:04d}_Euclid_{oid}_MER_VIS_geometry_report{suffix}.png';fig.savefig(out/name,dpi=250);plt.close(fig)")
s=s.replace("return dict(order=ordinal,object_id=oid,png=name,", "return dict(order=ordinal,object_id=oid,png=name,quality_issue=quality_issue,")
s=s.replace("if partial:issues.append('COVERAGE: requested cutout is PARTIAL; inspect galaxy coverage.')", "if partial:issues.append('COVERAGE: requested cutout is PARTIAL; inspect galaxy coverage.')")
p.write_text(s,encoding='utf8')
