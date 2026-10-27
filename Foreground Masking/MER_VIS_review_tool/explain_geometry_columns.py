from pathlib import Path
from html.parser import HTMLParser
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8')
s=s.replace('<th>Original pipeline</th><th>Current selection</th><th>Euclid</th><th>Selection − Euclid</th>', '<th title="Our saved automatic Photutils fit before interactive review">Original pipeline<br><span class="small">Our automatic fit</span></th><th title="Recalculated from the displayed fit using the intervals and sample pool selected above">Current selection<br><span class="small">Your selected ellipses</span></th><th title="Comparison values derived from the Euclid MER source catalogue">Euclid<br><span class="small">Catalogue comparison</span></th><th>Δ Selection − Euclid</th>')
needle='<tbody id="geometryTable"></tbody></table>'
helptext='''<div class="small" id="geometryColumnHelp">
<p><strong>Original pipeline:</strong> our automatic Photutils ellipse-fitting results, saved in <code>MER_VIS_local_geometry_manifest.csv</code> before your interactive changes. These are our measurements of the FITS image, not Euclid catalogue measurements. This column stays as the original baseline even when you display a manual-centre refit.</p>
<p><strong>Current selection:</strong> our values recalculated from the displayed fit using your current disc/bar intervals and ellipse sample pool. A centre refit supplies a new fitted profile; changing intervals selects from that profile. Display stretch and zoom do not affect these values.</p>
<p><strong>Euclid:</strong> comparison values already stored in the manifest from the Euclid MER source catalogue. The PA is derived from its detection <code>POSITION_ANGLE</code>, converted to sky coordinates with the project’s adopted +90° adjustment. The inclination is a proxy inferred from the catalogue detection shape, assuming a thin circular disc; it is not a direct inclination measurement. This is a whole-source detection comparison, not an independent measurement of the outer disc. No Euclid bar PA is supplied here. The app reads these saved values; it does not query Euclid live.</p>
<p><strong>Δ Selection − Euclid:</strong> current-selection value minus the Euclid comparison, in degrees. Positive means the selection is higher; negative means lower. PA differences use the shortest signed difference between equivalent axes (modulo 180°). An em dash means a comparison is unavailable.</p>
</div>'''
assert s.count(needle)==1
s=s.replace(needle,needle+helptext)
assert 'Δ Selection − Euclid' in s and s.count('id="geometryColumnHelp"')==1
HTMLParser().feed(s)
p.write_text(s,encoding='utf8');print('Updated column labels and source/method explanations; retained geometry table ID.')
