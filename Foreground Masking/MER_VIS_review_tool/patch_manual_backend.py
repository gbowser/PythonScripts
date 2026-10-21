from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8').replace('import webbrowser','import webbrowser\nfrom refit_MER_VIS import ReviewRefits')
s=s.replace('class Store:', 'class Store(ReviewRefits):')
s=s.replace('    def galaxy(self, oid):','    def galaxy(self, oid, refit_id=None):')
s=s.replace('        row = self.byid[oid]\n        path =', '''        row = self.byid[oid]
        refit = None
        if refit_id:
            # Validate the opaque identifier before resolving any filesystem path.
            if len(refit_id)!=32 or any(c not in '0123456789abcdef' for c in refit_id):
                raise ValueError('Invalid refit identifier')
            folder=self.output/'refits'/refit_id
            request=json.loads((folder/'request.json').read_text(encoding='utf8'))
            if request['object_id']!=oid: raise ValueError('Refit belongs to a different galaxy')
            row=json.loads((folder/'result.json').read_text(encoding='utf8'))
            refit=dict(job_id=refit_id, x=request['row']['manual_centre_x_pix'], y=request['row']['manual_centre_y_pix'],
                       lock_centre=request['lock_centre'], requested_utc=request['requested_utc'], folder=str(folder))
        cache_key=(oid,refit_id)
        path =''',1)
s=s.replace('        if oid not in self.profile_cache:', "        if refit_id: path=self.output/'refits'/refit_id/'profiles'/path.name\n        if cache_key not in self.profile_cache:",1)
s=s.replace('self.profile_cache[oid] = converted','self.profile_cache[cache_key] = converted').replace('profile = self.profile_cache[oid]','profile = self.profile_cache[cache_key]')
s=s.replace('        return clean(dict(object_id=oid,', '        baseline=self.galaxy(oid)["original"] if refit_id else None\n        return clean(dict(refit=refit, pipeline_original=baseline, object_id=oid,',1)
s=s.replace('return self.send(self.server.store.galaxy(params.get("id",[""])[0]))','return self.send(self.server.store.galaxy(params.get("id",[""])[0],params.get("refit",[None])[0]))')
s=s.replace('            if route == "/api/image":','            if route == "/api/refit":\n                return self.send(self.server.store.refit_status(params.get("job",[""])[0]))\n            if route == "/api/image":')
s=s.replace('            if self.path == "/api/review":', '            if self.path == "/api/refit": return self.send(self.server.store.start_refit(payload))\n            if self.path == "/api/review":')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');needle='   <div class="stretch-grid">'
new='''   <details id="centrePanel"><summary>Update centre and recompute</summary>
    <p>Click <b>Pick centre</b>, then click the galaxy nucleus. Yellow + is your proposed centre. The new fit uses the native FITS pixels and recomputes ellipses, disc/bar selection, angles, inclination and quality flags.</p>
    <div class="row compact"><button id="pickCentre">Pick centre on image</button><button id="catalogueCentre" class="secondary">Use catalogue position</button></div>
    <div class="interval-grid"><label>Centre X native pixel<input id="centreX" type="number" min="0" step="0.1"></label><label>Centre Y native pixel<input id="centreY" type="number" min="0" step="0.1"></label></div>
    <p class="small">Coordinates are zero-based in the original FITS array; X increases right, Y increases upwards in this viewer.</p>
    <label class="check"><input id="lockCentre" type="checkbox" checked> Keep this centre fixed during fitting</label>
    <div class="row compact"><button id="runRefit" class="primary">Recompute from this centre</button><button id="showOriginal" class="secondary">Show original fit</button><button id="showRefit" class="secondary" hidden>Show last refit</button></div>
    <p id="refitStatus" role="status">A retry is stored separately. Original results and FITS files are preserved. It may take several minutes.</p>
   </details>
'''
s=s.replace(needle,new+needle)
s=s.replace('It does not refit ellipses or overwrite the pipeline manifest, images or reports.','The centre retry refits ellipses into a separate review folder. It does not overwrite the pipeline manifest, images or reports.')
s=s.replace('These are local what-if calculations, not changes to the pipeline.','These are local what-if calculations, not changes to the pipeline.')
s=s.replace('<th>Pipeline</th>','<th>Original pipeline</th>').replace('<th>This selection</th>','<th>Current selection</th>')
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/requirements_MER_VIS_review.txt');s=p.read_text();s+='scipy>=1.16\nphotutils>=2.3\n';p.write_text(s)
