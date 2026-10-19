import json,math
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
root=Path('MER_VIS_explanation_work');ex=json.loads((root/'examples.json').read_text());doc=Document();s=doc.sections[0];s.page_width=Inches(8.27);s.page_height=Inches(11.69);s.top_margin=s.bottom_margin=Inches(.65);s.left_margin=s.right_margin=Inches(.7)
for n in ['Normal','Title','Heading 1','Heading 2','Subtitle']:
 st=doc.styles[n];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(10.5);doc.styles['Normal'].paragraph_format.space_after=Pt(7);doc.styles['Normal'].paragraph_format.line_spacing=1.04;doc.styles['Title'].font.size=Pt(24);doc.styles['Heading 1'].font.size=Pt(17);doc.styles['Heading 2'].font.size=Pt(12)
f=s.footer.paragraphs[0];f.text='Euclid MER VIS disc geometry explained  •  ';fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');f._p.append(fld)
for r in f.runs:r.font.size=Pt(8)
def p(t):doc.add_paragraph(t)
def h(t):doc.add_heading(t,2)
def page(t):doc.add_page_break();doc.add_heading(t,1)
def pic(n,cap):
 doc.add_picture(str(root/n),width=Inches(6.85));z=doc.add_paragraph(cap)
 for r in z.runs:r.font.size=Pt(8.5)
def table(head,rows,widths):
 t=doc.add_table(rows=1,cols=len(head));t.autofit=False
 for c,w in zip(t.columns,widths):c.width=Inches(w)
 for c,v in zip(t.rows[0].cells,head):c.text=v
 for vals in rows:
  for c,v in zip(t.add_row().cells,vals):c.text=str(v)
 for j,row in enumerate(t.rows):
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  for c,w in zip(row.cells,widths):
   c.width=Inches(w);sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E9EEF2' if j==0 else 'FFFFFF');c._tc.get_or_add_tcPr().append(sh)
   for a in c.paragraphs:
    a.paragraph_format.space_after=Pt(4)
    for r in a.runs:r.font.size=Pt(9);r.bold=(j==0)
 doc.add_paragraph().paragraph_format.space_after=Pt(0)
def fmt(x,n=2):return f'{float(x):.{n}f}'
doc.add_heading('How disc inclination and position angle are calculated',0)
p('A guide to the local Euclid MER VIS ellipse fitting results')
p('Prepared 19 October 2026 from the completed run of 18 October 2026. The sample contains 2777 galaxy cutouts. This document explains the actual code and uses six real galaxies from your output, with their images and fitted radial profiles.')
h('What the measurements mean')
p('Disc inclination measures how far a galaxy disc is tilted away from face on. Disc position angle, usually shortened to disc PA, measures the direction of its long axis on the sky. They describe different aspects of the same projected disc. A galaxy can have any disc PA at a particular inclination.')
p('The program estimates both quantities from nested ellipses fitted to the galaxy light. It treats the selected outer ellipses as the projected disc. Their flattening gives inclination; their direction gives disc PA. This is a geometric estimate under assumptions about the disc, rather than a direct measurement of its three dimensional orientation.')
table(['Quantity','Convention used here'],[['Inclination i','Degrees; 0° face on and 90° edge on.'],['Disc PA','Degrees east of north, modulo 180°; north 0°, east 90°.'],['Bar PA','Same sky convention, but measured from selected inner ellipses. It is the observed bar PA before deprojection.'],['Axis ratio q','Minor axis divided by major axis, b/a; dimensionless.'],['Ellipticity ε','1 − q; dimensionless. A circle has ε = 0.']],[1.35,5.5])
h('The main interpretation')
p('Four worked examples have convincing, stable outer-disc fits on visual and numerical inspection. They are good candidates for further use, not independently validated inclinations. The two poor examples show why a completed calculation and an empty flag list must be interpreted carefully. Flags identify reasons for caution; they are not marks awarded to the galaxy.')
p('The calculations discussed here do not alter your native FITS cutouts. Deprojection and bar alignment are later operations that depend on the geometry being credible.')
page('Why a tilted disc looks like an ellipse')
p('Imagine a circular, thin disc. Viewed directly from above, it looks circular. Tilt it away from you and its apparent width decreases along one direction. Its long dimension remains a; its short dimension becomes b. These are semi axes, measured from the centre to the edge. Full widths give the same ratio.')
pic('inclination.png','Ideal circular thin discs shown at three inclinations. These are explanatory sketches, not fits to the example galaxies.')
h('From flattening to inclination')
p('For an intrinsically circular, infinitely thin disc, q = b/a = cos(i). Therefore i = arccos(q). The program first takes the median ellipticity of the selected reliable disc ellipses, then uses q = 1 − median(ε). Finally it converts arccos(q) into degrees. It does not average the inclinations of individual ellipses.')
p('For example, median ε = 0.400 means q = 0.600 and i = arccos(0.600) = 53.13°. An inclination of 53° describes the tilt of the disc, not a rotation angle to apply directly to the image.')
h('Allowing for finite disc thickness')
p('The code can use an assumed intrinsic thickness q₀ through cos²(i) = (q² − q₀²)/(1 − q₀²). The expression is clipped to the physical range 0 to 1 before taking the square root and inverse cosine. Your completed run used q₀ = 0, so it used the thin-disc equation. With q = 0.600 and q₀ = 0.200 the estimate would instead be about 54.74°.')
h('The assumptions matter')
p('The chosen light contours must trace the disc, which is assumed circular before projection. Spiral arms, a ring, a bar extending into the chosen range, dust, a tidal distortion or a companion can violate that assumption. Bulge light and image blurring can make the fitted shape rounder. A consistent ellipse is therefore evidence of a measurable shape, but it does not by itself establish the physical disc geometry.')
p('Near face on, a small change in q can change the inferred inclination appreciably, while the direction of a nearly circular ellipse is poorly defined. Near edge on, thickness and dust become especially important and deprojection requires a very large stretch.')
page('How the image becomes an ellipse profile')
h('Preparation of each cutout')
p('The centre comes from CENX and CENY in the FITS header and remains fixed during fitting. The code does not search for a new centre. A wrong catalogue centre can therefore affect every ellipse. It averages 2 by 2 native pixels for the fitting calculation only; at the nominal 0.1 arcsec native scale, this gives about 0.2 arcsec per fitting pixel.')
p('Nonfinite pixels are rejected. Where a FLG extension exists, selected detector flag bits are also rejected, but your science-only MER cutouts do not contain that extension. The program estimates a local background and noise using sigma clipping in the outer part of the cutout, then subtracts the clipped mean background.')
p('A smoothed detection image identifies connected sources above three times the background noise. The component at the catalogue centre is retained. Other detected components are masked, with the mask expanded by three fitting pixels. Objects connected to the target are not automatically separated. The smoothing is used for detection and starting estimates, not as the image on which all isophotes are fitted.')
h('Fitting nested contours of light')
p('An isophote is a contour of equal surface brightness. Photutils iteratively adjusts an ellipse to describe the light around a chosen radius. The program allows ellipticity and orientation to vary with radius while keeping the centre fixed. Photutils uses the established iterative isophote method described by Jedrzejewski; see its official guide in the sources section.')
p('The local settings use roughly 8 percent spacing in semi major axis, a minimum semi major axis of three fitting pixels, three sigma clipping passes and up to 80 iterations per ellipse. Several starting ellipses are tried if necessary. The outer limit depends on the detected extent and distance to the image boundary, rather than a known catalogue disc radius.')
h('Which ellipses are trusted numerically')
p('A profile point is retained only if Photutils marks it valid, its stop_code is 0, its usable sampling fraction is at least 0.70, its background-subtracted intensity is positive, and intensity exceeds five times its reported intensity error. At least ten such reliable isophotes are required overall. These checks assess fitting behaviour and signal; they do not identify which physical component an ellipse traces.')
p('Each saved ellipse profile contains radius, ellipticity, pixel PA, sky PA, formal errors, intensity, stop code, validity and sampling fraction. Grey points in this document failed one or more reliability checks; blue points passed. Lines merely connect samples to help you see trends.')
page('How the disc range and sky PA are chosen')
h('Separating the inner bar from the outer disc')
p('The automatic selector finds the largest ellipticity among reliable points between 12 and 55 percent of the largest reliable radius. Calling its radius a_peak, it selects a provisional bar interval from 0.75 a_peak to 1.15 a_peak. This peak can sometimes belong to a ring or spiral structure, so the interval needs visual review.')
p('The disc interval starts at the larger of 1.25 times the bar upper bound and 65 percent of the largest reliable radius. It ends just beyond that largest radius. At least three reliable points must fall in each interval. This is an automatic rule, not a guarantee of reaching an undisturbed outer disc. Reviewed, nonoverlapping bar and disc intervals can be supplied instead.')
h('Converting a direction in pixels to a direction on the sky')
p('Photutils supplies the direction of an ellipse relative to the image pixel axes. That direction cannot simply be called a sky PA: FITS images can have rotated or reversed axes. The program uses the FITS World Coordinate System, or WCS, locally at the galaxy centre to map the ellipse direction into west and north offsets. It then computes atan2(east, north) and expresses the result from 0° up to 180°.')
p('The native thumbnails here are not forced north up. Their apparent tilt on the page need not match a protractor angle measured from the top of the page. The PA plots and numerical values use the sky convention.')
h('Averaging axes rather than arrows')
p('An ellipse axis at 1° is almost the same orientation as an axis at 179°. Their ordinary arithmetic mean, 90°, would be wrong. The code doubles each selected sky angle, averages its sine and cosine, halves the resulting direction and wraps it into the range 0° to 180°. This is an equal-weight axial circular mean; it is not weighted by the formal errors.')
p('The saved disc PA scatter is the root mean square of the selected angles’ shortest signed differences from that mean, allowing for 180° equivalence. It describes variation with radius. It is not a confidence interval on the final PA. Per-ellipse formal errors, radial scatter and systematic uncertainty are three different things.')
h('Using these values to make a face on image')
p('Disc PA determines the direction of the disc long axis. Deprojection stretches the perpendicular direction by 1/cos(i), after accounting for the WCS. The bar direction must then be transformed into that deprojected frame before the final rotation places it along the x axis. Using the observed bar PA as a final face-on rotation without this transformation would generally be incorrect.')
page('What the geometry quality flags mean')
p('These are warning strings generated by our geometry code. A raised flag means that its stated condition occurred; it does not necessarily mean every measurement is unusable. Several flags may appear together, separated by semicolons. An empty list means none of these eight thresholds was crossed. It does not mean the result has been approved for scientific use.')
table(['Flag name and count','Exact trigger','Meaning and response'],[
['disc_PA_unstable\n791 fits','Disc PA radial scatter > 10°','The outer ellipse direction changes substantially. Check arms, neighbours, centre and disc interval before trusting the orientation.'],
['bar_PA_unstable\n28 fits','Bar PA radial scatter > 10°','The selected bar direction is not consistent with radius. Review the bar identification and interval.'],
['disc_axis_ratio_unstable\n573 fits','Disc ellipticity maximum minus minimum > 0.15','Outer flattening varies. The median may combine different structures, making inclination unreliable.'],
['nearly_face_on_PA_uncertain\n200 fits','Disc q > 0.90','With q₀ = 0 this is i < 25.84°. A nearly circular shape has a poorly defined long-axis direction.'],
['high_inclination\n0 fits','Inclination ≥ 80°','Large deprojection stretch; thickness and dust become important. Review or exclude from bar analysis.'],
['weak_ellipse_bar_signature\n7 fits','Median bar ellipticity < 0.25','The chosen interval is not strongly elongated. This is not a physical bar-strength or torque measurement.'],
['axis_ratio_below_thickness\n0 fits','Disc q ≤ assumed q₀','The measured flattening reaches or exceeds the thickness model limit. Reconsider the measurement or model.'],
['small_bar_sensitive_to_resolution\n1210 fits','Bar upper radial bound < 1.5 arcsec','Small selected bar interval; binning, blurring and sampling deserve attention. The bound is not a measured full bar length.']
],[2.05,1.65,3.15])
p('Counts refer to the 2207 completed provisional fits and overlap. They cannot be added to obtain the number of affected galaxies. No severity score is assigned by the code, and the thresholds are practical screening rules rather than calibrated probabilities of error.')
page('Statuses warnings and flags are different')
table(['Output or message','How to interpret it'],[['provisional_fit','The numerical calculation returned geometry. The physical interpretation still requires review, whether or not flags are present.'],['fit_failed','No complete usable geometry was returned. Read codex_error. Blank angles mean unavailable, not 0°. A failed row can have an empty quality flag list.'],['reviewed_ranges','A fitter label available when manual ranges were provided and no geometry flags arose. It is not an independent validation certificate. This completed run has provisional fits.'],['Photutils warning','A library message from an attempted fit. Some starting trials can fail before a later trial succeeds. Inspect the final result and diagnostics; a warning alone is not the final outcome.'],['Profile valid and stop_code','Per-ellipse numerical diagnostics used in filtering. They differ from the galaxy-level quality flag strings.'],['cutout_partial or FITS PARTIAL','A separate warning that the requested cutout area was not fully covered. It does not prove that the visible galaxy itself is truncated.'],['Euclid Sérsic flags','Catalogue model-fit diagnostics from Euclid, with their own definitions. A Euclid flag value of zero does not certify our outer-disc selection.']],[1.6,5.25])
h('What happened in your run')
p('All 2777 target rows were retained. There were 2207 provisional fits, including 546 with no geometry flags and 1661 with one or more flags. Another 570 galaxies failed to return complete geometry. Thus 19.7 percent of the entire sample had a completed fit without these flags; this is a screening outcome, not the fraction of scientifically correct galaxies.')
p('Of the failures, 431 lacked enough reliable samples in the selected bar or disc intervals, 138 had fewer than ten reliable isophotes overall, and one catalogue centre was not on a detected galaxy. Retrying with reviewed intervals can help some objects, but cannot create signal or a well-defined disc where neither is present.')
h('Good or bad')
p('A flag is useful diagnostic information about a potential problem. Its presence is a reason to investigate the affected measurement. For example, an uncertain bar interval does not automatically invalidate an otherwise stable disc inclination. Conversely, a stable disc PA does not establish that the bar PA is correct. Interpret each quantity separately, and keep a record of visual decisions.')
notes=[
('The outer ellipses follow a coherent elongated envelope. In the green disc interval, ellipticity forms a nearly level plateau and the PA stays close to 43°. These are favourable signs for the disc geometry.','The inner orange interval is less clearly separated from the outer elongation, and a bright knot lies within the galaxy. This is a good disc example, but it should not be used as independent proof that the automatic bar interval is physically correct.'),
('The outer-disc ellipticity settles near 0.42 and the selected PA points lie near north. The apparent jump from near 180° to near 0° is mostly angle wrapping: those directions are equivalent for an ellipse axis. The selected disc points themselves are tightly clustered.','A bright compact source overlaps the outer light on the upper right of the thumbnail. Review its effect and test a mask before final scientific use. Grey points beyond the selected disc range are not extra independent reliable disc measurements.'),
('The inner light is more elongated than the outer envelope. Past the transition, the green interval has an approximately constant PA near 101° and a much rounder shape than the inner region. This supports treating the selected outer light as a different component from the bar.','The selected outer ellipticity varies by about 0.06, below the 0.15 warning threshold. That is still real radial variation; no flag does not mean that every outer ellipse is identical.'),
('The selected outer ellipses have a consistent direction near 64° and a narrow range of ellipticity. The bright inner structure is more elongated, while the outer envelope becomes rounder. The numerical measurements and the overlay are mutually plausible.','Only three reliable disc points enter the final estimate, exactly the allowed minimum. This is a good fit in the displayed interval, but the small number of samples limits how strongly it establishes a persistent outer-disc plateau.')]
for k,r in enumerate(ex[:4]):
 page(f'Good disc example {k+1}')
 p('Galaxy ID '+r['object_id']);p('FITS file '+r['fits_filename'])
 pic(f'example_{k+1}.png','Orange marks the automatic bar interval; green marks the disc interval. Cyan ellipses are other radii. Blue points pass the reliability checks; grey points do not. Red cross marks the fixed centre. Image scale is nominally 0.1 arcsec per native pixel.')
 lo,hi=r['plot_disc_min'],r['plot_disc_max'];eps=1-float(r['codex_disc_axis_ratio'])
 table(['Selected disc interval','Shape calculation','Orientation calculation'],[[f'{lo:.2f} to {hi:.2f} arcsec\n{r["n_disc"]} reliable ellipses',f'Median ε = {eps:.4f}\nq = {float(r["codex_disc_axis_ratio"]):.4f}\ni = {float(r["codex_inclination_deg"]):.2f}°',f'Disc PA = {float(r["codex_disc_pa_sky_deg"]):.2f}°\nRadial scatter = {float(r["codex_disc_pa_scatter_deg"]):.2f}°\nNo geometry flags']],[2.1,2.35,2.4])
 p(notes[k][0]);p(notes[k][1])
 p(f'Worked inclination: i = arccos(1 − {eps:.6f}) = {float(r["codex_inclination_deg"]):.2f}°. The reported bar PA is {float(r["codex_bar_pa_sky_deg"]):.2f}° in the observed sky frame; it is a separate estimate.')
 if k==0:
  table(['Disc radius arcsec','Ellipticity','Sky PA degrees'],[[f'{z["sma_arcsec"]:.2f}',f'{z["ellipticity"]:.4f}',f'{z["pa_sky_deg"]:.2f}'] for z in r['disc_samples']],[2.1,2.35,2.4])
page('Poor example with returned but unstable geometry')
r=ex[4];p('Galaxy ID '+r['object_id']);p('FITS file '+r['fits_filename']);pic('example_5.png','The near-round outer light has a changing fitted direction. The low final PA point lies inside the selected green interval and contributes to the large scatter. The displayed native image is strongly enlarged.')
p(f'The run returned provisional_fit, disc PA {float(r["codex_disc_pa_sky_deg"]):.2f}° and inclination {float(r["codex_inclination_deg"]):.2f}°. Five reliable disc ellipses enter the estimate, but their axial PA scatter is {float(r["codex_disc_pa_scatter_deg"]):.2f}°, far above the 10° threshold. The quality flags are disc_PA_unstable and small_bar_sensitive_to_resolution.')
h('Why the returned angle is not reassuring')
p('An average can always be computed from inconsistent directions. Here the selected PA changes markedly with radius, while the outer light is nearly round and has structure from neighbouring light. The mean PA does not describe a single convincing disc axis. A mathematically returned value is therefore not enough to justify deprojection.')
p(f'The median q is {float(r["codex_disc_axis_ratio"]):.4f}. This does not trigger nearly_face_on_PA_uncertain, because it falls just below the strict q > 0.90 threshold. That does not make the direction secure: the independent disc_PA_unstable test correctly warns about the measured variation.')
p(f'The ellipticity span is {r["eps_span"]:.3f}, below the 0.15 instability threshold, so disc_axis_ratio_unstable is not raised. This illustrates why different flags answer different questions. The current inclination is also provisional because the selected contours may not represent an undisturbed disc.')
p('Recommended treatment: withhold automatic deprojection, inspect the centre and contamination, and try a physically justified disc interval and improved mask. If no stable outer disc can be identified, leave the geometry unavailable rather than promoting the mean.')
page('Poor example where the calculation stopped')
r=ex[5];p('Galaxy ID '+r['object_id']);p('FITS file '+r['fits_filename']);pic('example_6.png','The orange interval contains only two reliable samples. The green interval shows the disc range reconstructed from the saved profile and the code’s automatic rules; no final geometry row was accepted.')
p('The status is fit_failed. The recorded error is Insufficient bar/disc isophotes in selected radial ranges. This galaxy has 20 reliable ellipses overall, so it passes the ten-point global requirement. However, only two lie within the selected bar interval, below the requirement of three. Four lie in the selected disc interval.')
h('A failure can occur even when the image looks usable')
p('The light is clearly detected, but the bar selection is too sparsely sampled under the current rule. The outer ellipticity also rises substantially across the green interval, and the ellipse orientation changes. Thus simply widening the orange interval until the calculation runs would not by itself validate the disc.')
p(f'The reconstructed disc ellipticity span is {r["eps_span"]:.3f}, larger than 0.15. If the code had reached its final flag checks using this same interval, this would satisfy disc_axis_ratio_unstable. It did not reach those checks: this is a diagnostic observation, not a flag stored for this failed galaxy.')
p('The output angles are blank and the galaxy-level quality flag list is empty. This is not a good result with zero warnings. The exception stopped the calculation before final geometry flags were assigned. Always check codex_fit_status before filtering on an empty quality flag list.')
p('Recommended treatment: inspect the galaxy, centre, mask and reliable profile; choose defensible bar and disc intervals if available, then rerun and review. Do not fill blank geometry with zero, and do not infer that the galaxy lacks a bar merely because this particular fitting procedure failed.')
page('How to review and use the measurements')
h('A practical review order')
p('First check codex_fit_status and codex_error. Next inspect the ellipse overlay: does the fixed centre match the galaxy nucleus, are nearby sources influencing the contours, and do the outer ellipses follow the disc rather than a bar, ring or arm? Check cutout_partial and whether enough galaxy light is actually covered.')
p('Then examine ellipticity and PA together. A plausible outer disc should have a reasonably persistent flattening and direction over a defensible radial interval. Check the number of reliable samples and compare neighbouring interval choices. A barely passing interval with three points deserves more caution than a long stable plateau. Use flags to guide this inspection, rather than deleting all flagged rows indiscriminately.')
p('For reviewed objects, record the chosen intervals, reasons, remaining limitations and any revised centre or mask. Rerun the geometry before generating final face-on images. Keep provisional and approved measurements distinguishable. The current pipeline does not provide calibrated final uncertainty intervals or a physical disc and bar decomposition.')
h('Comparing with Euclid morphology')
p('Euclid detection ellipticity and single Sérsic axis ratio describe whole-object shapes. Applying arccos(q) gives inclination proxies under the same thin-disc assumption; these are not automatically independent outer-disc inclinations. The available manifest has no Euclid bar PA and no populated separate disc-component axis ratio for these targets.')
p('The earlier output report also identified an unresolved PA convention issue in the converted Euclid detection PA column, with many differences near 90°. Do not use that column as a validated sky-PA comparison until its definition and conversion have been resolved. No blanket correction has been applied here. The four good examples were selected from our profiles and images, not by agreement with that column.')
h('Source files and further reading')
p('The primary method source is Euclid/datalabs_MER_VIS/fit_MER_VIS_geometry_portable.py, particularly fit_one, sky_pa, axial_mean and axial_scatter. The local runner is Euclid/calculate_local_MER_VIS_geometry.py. Numerical examples come from MER_VIS_local_geometry_manifest.csv and the matching ellipse_profile.csv files in the local geometry output folder. This guide documents the code and run available on 19 October 2026.')
p('Photutils official isophote guide explains the library and links to the underlying method: https://photutils.readthedocs.io/en/latest/user_guide/isophote.html')
p('Euclid Q1 morphology cookbook explains the catalogue quantities and model context: https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/mermorphologycookbook.html')
p('For the full run statistics and the PA convention audit, see the accompanying Euclid MER VIS geometry fitting report dated 18 October 2026. The present guide focuses on understanding how the local estimates and their warning flags are produced.')
# Remove inherited title borders and any direct paragraph borders.
for tree in [doc._element,doc.styles.element]:
 for e in list(tree.iter(qn('w:pBdr'))):e.getparent().remove(e)
output=root/'Euclid_MER_VIS_disc_PA_and_inclination_explained.docx';doc.save(output);print(output.resolve())
