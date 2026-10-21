from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text()
s=s.replace('"control": "No Quality Issues",','"control": "No Quality Issues",\n    "failed": "Failed galaxies",')
pos=s.index('\ndef select_sample(rows):')
s=s[:pos]+'''
def add_failed_galaxies(sample, rows):
    """Include every failed fit, preserving the existing review sample."""
    byid = {r['object_id']: r for r in rows}
    used = {s['object_id'] for s in sample}
    for r in rows:
        if r['codex_fit_status'] != 'fit_failed':
            continue
        item = next((s for s in sample if s['object_id'] == r['object_id']), None)
        if item is None:
            item = dict(object_id=r['object_id'])
            sample.append(item)
        item.update(category='failed', category_label=CATEGORIES['failed'],
                    selection_reason=r.get('codex_error') or 'No adopted geometry')
    return sample

'''+s[pos:]
s=s.replace('    return chosen\n','    return add_failed_galaxies(chosen, rows)\n',1)
s=s.replace('self.sample = expand_reference_group(self.sample, self.rows)','self.sample = add_failed_galaxies(expand_reference_group(self.sample, self.rows), self.rows)')
s=s.replace('sample_revision=2','sample_revision=3').replace('54 purposively stratified examples, including 12 No Quality Issues references; not a prevalence sample','Stratified review examples, 12 No Quality Issues references and all failed galaxies; not a prevalence sample')
s=s.replace('            display_centre = centre if all(v is not None for v in centre) else cat','            if row["codex_fit_status"] == "fit_failed":\n                centre = [None, None]  # Failed trial centres are not adopted geometry.\n            display_centre = centre if all(v is not None for v in centre) else cat')
s=s.replace('        original = dict(disc_pa=', '        if row["codex_fit_status"] == "fit_failed":\n            window = [-.5, shape[1]-.5, -.5, shape[0]-.5]\n        original = dict(disc_pa=')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text()
s=s.replace("function pool(){return S.g.profile.filter", "function pool(){if(S.g.original.status==='fit_failed')return [];return S.g.profile.filter")
s=s.replace("$('originalFlags').textContent='Pipeline issues: '+", "$('originalFlags').textContent=(g.original.status==='fit_failed'?`Failed fit: ${g.fit_error||'No adopted geometry'} · `:'Pipeline issues: ')+")
s=s.replace("||'No counted geometry flags')+(g.original.information", "||(g.original.status==='fit_failed'?'No adopted geometry':'No counted geometry flags'))+(g.original.information")
s=s.replace("$('barMin').disabled=$('barMax').disabled=s.noBar;\n}", "$('barMin').disabled=$('barMax').disabled=s.noBar;\n const failed=S.g.original.status==='fit_failed';for(const id of ['discMin','discMax','pool','noBar','resetGeometry'])$(id).disabled=failed;if(failed)$('barMin').disabled=$('barMax').disabled=true;\n}",1)
s=s.replace("$('poolNote').textContent=S.settings.pool", "$('poolNote').textContent=g.original.status==='fit_failed'?'No adopted disc or bar geometry. Any grey profile points are rejected or unadopted measurements; interval trials are disabled for failed fits. You can still explore the FITS light and save your assessment.':S.settings.pool")
s=s.replace("function calculate(){const points=", "function calculate(){const points=")
s=s.replace("  sparse,issues,bar_grade:","  sparse,issues:S.g.original.status==='fit_failed'?['Fit failed: no adopted geometry; inspect the FITS image and failure reason']:issues,bar_grade:")
s=s.replace("if(kind==='bar'&&S.settings.noBar)continue;", "if(S.g.original.status==='fit_failed'||(kind==='bar'&&S.settings.noBar))continue;")
s=s.replace("svg.onpointerdown=e=>{if(!S.g)return;", "svg.onpointerdown=e=>{if(!S.g||S.g.original.status==='fit_failed')return;")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_review_MER_VIS.py');s=p.read_text().replace('),54)', '),58)').replace('control=12))','control=12,failed=4))')
s=s.replace("old=[r for r in self.store.sample if not (", "old=[r for r in self.store.sample if r['category']!='failed' and not (")
s=s.replace('    def test_native_pixels_and_byte_orientation(self):','''    def test_all_failed_galaxies_are_reviewable(self):
        failed=[r for r in self.store.rows if r['codex_fit_status']=='fit_failed']
        group={s['object_id'] for s in self.store.sample if s['category']=='failed'}
        self.assertEqual(group,{r['object_id'] for r in failed})
        for row in failed:
            galaxy=self.get('/api/galaxy?id='+row['object_id'])
            self.assertEqual(galaxy['original']['status'],'fit_failed')
            self.assertTrue(galaxy['fit_error'])
            self.assertEqual(galaxy['centre'],[None,None])
            self.assertIsNone(galaxy['original']['disc_pa'])
            meta,body=self.store.image(row['object_id'],dict(x0=['0'],x1=['30'],y0=['0'],y1=['30']))
            self.assertGreater(len(body),0)
            self.assertGreater(meta['width'],0)

    def test_native_pixels_and_byte_orientation(self):''')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/README_MER_VIS_REVIEW.md');s=p.read_text().replace('54 unique examples','58 unique examples').replace('all 54','all 58')
s+='\n## Failed galaxies\n\nChoose **Failed galaxies** in Review group. This includes all four failed fits in the current manifest, not a sample of failures. The failure reason is shown above the image. The full cutout opens initially, with the usual stretch, zoom and pan controls. No red adopted-centre marker or accepted ellipse overlays are shown for failed fits; any grey profile measurements are unadopted. Disc/bar interval trials are disabled, but assessments and notes can still be saved. Existing sample IDs and saved reviews are preserved.\n'
p.write_text(s,encoding='utf8')
