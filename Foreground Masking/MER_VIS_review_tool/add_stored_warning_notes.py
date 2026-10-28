from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
needle='function drawWarningGraphics(warnings,'
pos=s.index(needle)
s=s[:pos]+'''function storedWarningNotes(g){const messages={
 centre_offset_large:`Recorded centre offset from the catalogue: ${fmt(g.original.centre_offset)}″. Inspect the centre markers on the FITS image; an offset alone does not prove the fitted centre is wrong.`,
 centre_unstable:`Recorded radial centre scatter: ${fmt(g.original.centre_scatter)}″. Inspect the ellipse centres on the image; ellipticity and PA curves alone cannot establish centre stability.`,
 relaxed_fit:'The stored fit used relaxed acceptance. This is fitting provenance, not a radial jump. Point tooltips show fit validity, coverage and errors.',
 iteration_limited_samples:'The stored fit includes iteration-limited samples. These did not meet normal convergence; point tooltips identify stop code 2.',
 star_mask_removed:'A recovery fit removed the star mask. Inspect the FITS image for stellar contamination; a smooth profile does not exclude it.',
 neighbour_mask_removed:'A recovery fit removed the neighbour mask. Inspect the FITS image for neighbouring-source contamination.',
 disc_range_fallback:'The stored fit used a fallback disc interval. The green region shows the current interval; its physical identification needs visual review.',
 small_disc:'The stored disc was small. Inspect the angular radii and resolution before interpreting the geometry.',
 bar_disc_ranges_close:'The stored disc and bar intervals were close. Compare the orange and green boundaries and inspect where the bar ends.',
 short_accepted_profile:'The stored fit had a short accepted profile. Inspect the selected sample counts and radial coverage.',
 high_inclination:'The stored inclination was high. The inclination profile shows the current disc-shape proxy; projection effects need review.',
 no_bar_detected:'The stored pipeline did not adopt a bar. This is not proof that a bar is absent; inspect the orange interval and image.'};
 return (g.original.flags??[]).filter(flag=>messages[flag]).map(flag=>({label:flagsLabel[flag]??flag,detail:messages[flag]}));
}
''' +s[pos:]
s=s.replace("$('profileWarnings').innerHTML=highlight?warnings.map(w=>`<div class=\"profile-warning-note\"><strong>${esc(w.label)}:</strong> ${esc(w.detail)}</div>`).join(''):'';", """const stored=storedWarningNotes(S.g);
 $('profileWarnings').innerHTML=highlight?warnings.map(w=>`<div class="profile-warning-note"><strong>${esc(w.label)}:</strong> ${esc(w.detail)}</div>`).join('')+(stored.length?`<details class="stored-warning-notes"><summary>Stored fit warnings (${stored.length}) — separate from current-selection annotations</summary>${stored.map(w=>`<p class="small"><strong>${esc(w.label)}:</strong> ${esc(w.detail)}</p>`).join('')}</details>`:''):'';""")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('Drag a coloured boundary', '“Highlight warnings” marks the current selection’s triggering samples: magenta brackets show the ellipticity range (and corresponding inclination change); amber rings and a lower strip show sparse sampling; amber stems show PA residuals; outlined orange intervals identify bar concerns. Excluded grey points do not contribute unless admitted by the selected sample pool. Stored centre, masking and recovery warnings are explained separately below the plots. Drag a coloured boundary',1);p.write_text(s,encoding='utf8')
