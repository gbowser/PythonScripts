from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.27);sec.page_height=Inches(11.69)
sec.top_margin=sec.bottom_margin=Inches(.7)
sec.left_margin=sec.right_margin=Inches(.75)
for name in ('Normal','Title','Subtitle','Heading 1','Heading 2'):
    st=doc.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(11)
doc.styles['Normal'].paragraph_format.space_after=Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing=1.08
doc.styles['Title'].font.size=Pt(25)
doc.styles['Heading 1'].font.size=Pt(18)
doc.styles['Heading 2'].font.size=Pt(13)
footer=sec.footer.paragraphs[0]
footer.text='Euclid Q1 barred galaxy workflow  •  '
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
footer.runs[0].font.size=Pt(9)
def p(s):doc.add_paragraph(s)
def h(s):doc.add_heading(s,2)
def page(s):doc.add_page_break();doc.add_heading(s,1)
def code(s):
    for line in s.splitlines():
        a=doc.add_paragraph();a.paragraph_format.space_after=Pt(1)
        a.paragraph_format.line_spacing=1
        r=a.add_run(line);r.font.name='Consolas';r.font.size=Pt(9)
def bullet(s):doc.add_paragraph(s,style='List Bullet')

doc.add_paragraph('Euclid Q1 barred spiral galaxy processing',style='Title')
p('A practical guide to selecting candidate galaxies, preparing manual FITS downloads, estimating disc and bar geometry, and producing native and deprojected cutouts. This documents the Python scripts in the Euclid folder as used on 13 October 2026.')
p('The catalogue selection and ellipse measurements are provisional. Visual review is needed to confirm a bar, select the outer disc, and adopt geometry for scientific measurements. The current scripts do not provide a complete census of Q1 barred spirals.')
doc.add_heading('1 Build the galaxy list',1)
h('Set up the working folder')
p('Run PowerShell commands from C:\\Users\\gordo\\Documents\\Github\\PythonScripts. The existing .venv supplies the astronomy packages; the code is in the Euclid subfolder.')
code("Set-Location 'C:\\Users\\gordo\\Documents\\Github\\PythonScripts'\n& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\compile_q1_VIS_barred_spirals.py' --candidates 25 --overwrite")
h('Select morphology candidates')
p('compile_q1_VIS_barred_spirals.py streams the Galaxy Zoo Euclid Q1 morphology catalogue from Zenodo record 15106473. It takes the first 25 qualifying entries in catalogue order, rather than scanning the whole catalogue or ranking the largest galaxies.')
bullet('Require release_name = Q1_R1 and warning_galaxy_fails_training_cuts = false.')
bullet('Require fractions ≥ 0.8 for featured or disc, not edge-on, spiral arms, and strong bar plus weak bar.')
bullet('Keep the exact object_id as a string, ICRS centre in decimal degrees, morphology scores and display cutout width. The generated Euclid_… label is not an NGC or Messier name.')
p('These Zoobot morphology fractions are conditional on the classification questions; they are not unconditional probabilities that an object is a barred spiral. The search radius is half the catalogue display width: radius_arcmin = cutout_width_arcsec / 120. It is not a measured bar radius.')
h('Verify individual frame availability')
p('For each candidate, the script queries sedm.calibrated_frame through Euclid TAP. It requires VIS, DpdVisCalibratedQuadFrame, Q1_R1, a cone intersecting the frame footprint, and the galaxy centre inside that footprint. TOP 1 records one example exposure. This does not prove that the centre lies on an actual science quadrant or that the whole galaxy is covered.')
p('Outputs in Euclid\\q1_barred_spirals: availability_checks.csv records all checks; verified_barred_spirals.csv contains available candidates; galaxy_cones.csv contains centres and radii; manual_download_top5.sql supplies a bounded archive query. Network errors are reported separately from no match.')

page('2 Build the download links')
p('The archive ADQL query returns metadata. Exporting a VOTable or CSV downloads the result table, not the FITS pixel data. Several galaxies can share an exposure, so deduplicate file_name before preparing image downloads.')
h('Retrieve the selected exposure rows')
p('For the existing 25 candidate list, five example frame identifiers were recorded. The prepared download_all_25_galaxies.sql uses these identifiers; the “25” refers to targets, not 25 distinct image files.')
code("SELECT TOP 5 f.*\nFROM sedm.calibrated_frame AS f\nWHERE f.instrument_name = 'VIS'\n  AND f.product_type = 'DpdVisCalibratedQuadFrame'\n  AND f.release_name = 'Q1_R1'\n  AND f.calibrated_frame_oid IN (1925,1958,1966,1973,2641)\nORDER BY f.calibrated_frame_oid")
p('Submit this in the Euclid Archive ADQL console and retain the result table. These identifiers belong to the current shortlist; regenerate them from the new verified list if the targets change. The compiler generates manual_download_top5.sql, but does not automatically regenerate the exact-identifier SQL or FITS_DOWNLOAD_LINKS.md.')
h('Construct a file URL from each filename')
code('https://eas.esac.esa.int/sas-dd/data?RETRIEVAL_TYPE=FILE\n&FILE_NAME=<URL-encoded file_name>&RELEASE=sedm')
p('Join the two lines above into one URL. RELEASE=sedm selects the download service namespace; the query’s release_name=Q1_R1 selects the data release. Do not substitute Q1_R1 for sedm in this URL.')
p('For a refreshed shortlist, the following Python code creates a Markdown link file from the verified CSV. Save it as a small helper in Euclid and run it from PythonScripts. This constructs links only; it does not download images.')
code("import csv\nfrom pathlib import Path\nfrom urllib.parse import urlencode\nfolder = Path('Euclid/q1_barred_spirals')\nwith (folder / 'verified_barred_spirals.csv').open() as f:\n    rows = list(csv.DictReader(f))\nnames = sorted({r['file_name'] for r in rows\n                if r.get('file_name')})\nlinks = ['# FITS download links', '']\nfor name in names:\n    params = urlencode({'RETRIEVAL_TYPE': 'FILE',\n                        'FILE_NAME': name, 'RELEASE': 'sedm'})\n    url = 'https://eas.esac.esa.int/sas-dd/data?' + params\n    links.append(f'- [{name}]({url})')\n(folder / 'FITS_DOWNLOAD_LINKS.md').write_text(\n    '\\n'.join(links) + '\\n', encoding='utf-8')")
h('Download manually')
p('Open FITS_DOWNLOAD_LINKS.md in VS Code and press Ctrl+Shift+V for the clickable preview. Download each distinct file into the Euclid Download Data folder listed on page 6. The five current files are each 7,315,678,080 bytes, about 36.6 GB in total. They are single calibrated exposures with multiple detector extensions, not merged images or galaxy-centred cutouts.')

page('3 Estimate the disc and bar geometry')
p('First create native cutouts using stage 4A. Then run the Photutils fitter on those cutouts. The practical execution order is list → links → downloads → native cutouts → geometry review → deprojection.')
code("& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\fit_euclid_VIS_geometry.py' --previews")
h('Understand the three angles')
bullet('Disc position angle is the apparent outer-disc major-axis direction, measured from north towards east, modulo 180 degrees.')
bullet('Bar position angle is the apparent bar direction on the sky, measured with the same convention. It must be transformed during deprojection before alignment.')
bullet('Inclination is the disc tilt: 0 degrees is face-on and 90 degrees is edge-on. It is inferred from the outer-disc axis ratio under a circular-disc assumption.')
h('Prepare the fitting image')
p('fit_euclid_VIS_geometry.py uses photutils.isophote, implementing iterative elliptical isophote fitting. The Q1 catalogue centre is fixed during fitting; it is not independently refined. The fitter averages valid pixels in 2 × 2 blocks for speed, without changing the native FITS cutout.')
p('It subtracts a sigma-clipped local background, masks selected VIS quality bits, and uses SciPy connected components to mask disconnected neighbouring sources. It rejects VIS bits 0–19, 21 and 22, while retaining OBJECTS, STITCHBLOCK and CTICORRECTION. Connected companions are not deblended. Outliers are clipped on the fitted ellipses; several starting ellipses are tried.')
h('Fit a radial ellipse profile')
p('Each ellipse provides a semi-major axis, ellipticity, position angle, formal errors, intensity and fit diagnostics. Only valid fits with stop code 0, at least 70 percent sampling coverage, positive intensity and intensity greater than five times its formal error enter the geometry selection. At least ten reliable ellipses are required overall and three in each selected bar and disc range.')
p('Photutils measures an image-plane angle from the pixel x-axis. The code maps its direction through the local FITS WCS into east and north on the sky; simply relabelling the pixel angle as a sky PA would be incorrect. This accounts for detector rotation and sky-axis orientation.')
h('Select the bar and outer disc')
p('Automatic selection searches for the largest inner ellipticity between 12 and 55 percent of the largest reliable semi-major axis. It selects a bar range from 0.75 to 1.15 times that peak radius. The disc range begins at the greater of 1.25 times the bar upper bound and 65 percent of the maximum radius, and extends to the last reliable ellipse.')
p('This is a starting hypothesis. Check that the inner elongation is a bar and that the outer range follows the disc rather than a ring, arm, bulge or companion. A visually satisfactory overlay matters more than a converged fit alone.')

page('3 Review the geometry and calculate inclination')
h('Compute the adopted values')
p('The disc axis ratio q = b/a is 1 minus the median disc ellipticity. Disc PA and bar PA are axial circular means of the sky angles in their respective ranges. Axial means handle the equivalence of 0 and 180 degrees correctly.')
code('Thin circular disc:  i = arccos(q)\nFinite thickness:    cos²(i) = (q² − q0²) / (1 − q0²)')
p('The default q0 is zero, giving the thin-disc formula. --q0 sets an assumed intrinsic thickness; for example, --q0 0.2 is a modelling choice, not a universal value. Record the adopted thickness and its effect on the estimate. If q is at or below q0, the code flags the estimate even though the numerical expression is clipped to a valid range.')
h('Review the diagnostic files')
bullet('*_ellipse_overlay.png shows fitted ellipses and the fixed centre, including unsuccessful geometry selections.')
bullet('*_geometry_review.png shows the galaxy overlay, radial ellipticity and sky PA, with the proposed bar and disc ranges highlighted.')
bullet('*_ellipse_profile.csv retains the measurements and formal errors. photutils_geometry_manifest.csv records candidate geometry, ranges, radial scatter, assumptions and quality flags.')
bullet('photutils_fit_errors.csv records failed fits or insufficient radial samples. Some very early failures may have no profile or overlay.')
p('Current quality flags include PA scatter above 10 degrees, disc ellipticity range above 0.15, q above 0.9, inclination of 80 degrees or more, median bar ellipticity below 0.25, and a bar-range upper bound below 1.5 arcseconds. Small bars can be sensitive to binning and the PSF. Radial scatter is not a calibrated uncertainty on the final geometry.')
h('Supply reviewed radial ranges')
p('Create my_ranges.csv in Euclid with the header below and one row per object. Enter values from the diagnostic plots. Require 0 < bar_min < bar_max < disc_min < disc_max. A row applies to all exposures of that object, so check that the ranges work in each exposure.')
code('object_id,bar_min_arcsec,bar_max_arcsec,disc_min_arcsec,disc_max_arcsec')
code("& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\fit_euclid_VIS_geometry.py' `\n  --ranges-csv '.\\Euclid\\my_ranges.csv'")
p('The fitter labels supplied ranges as reviewed_ranges only when its numerical flags are clear. This does not certify the morphology or produce a final scientific measurement. Keep a separate adopted geometry CSV after review; do not silently treat every automatic candidate as accepted.')
h('Compare repeat observations')
p('The geometry manifest contains one row per cutout, and some object IDs repeat across exposures. Compare those estimates before choosing one adopted set per galaxy. The existing batch deprojector indexes geometry by object_id; if a CSV contains duplicates, its last row wins. Do not feed the repeated candidate manifest directly into a final batch run without resolving duplicates.')

page('4 Extract deproject and rotate the galaxy')
h('A Extract native galaxy cutouts')
code("& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\extract_calibrated_VIS_galaxies.py' --overwrite")
p('The extractor reads verified_barred_spirals.csv and searches every downloaded FITS exposure. It maps all catalogue centres through each SCI extension’s celestial WCS. If several quadrants contain a centre, it selects the one with the greatest edge margin.')
p('It converts the catalogue display width to pixels using the WCS pixel scales, takes a square requested section around the centre, and trims it to the selected quadrant. The primary output contains SCI, with matching RMS and FLG extensions. The sliced celestial WCS is retained and the recovered centre is checked. No rotation, deprojection, interpolation or exposure combination occurs at this stage.')
p('PARTIAL means that the requested surrounding sky box was trimmed. Inspect the image to decide whether the galaxy itself is truncated. The code does not stitch neighbouring quadrants. The single_galaxy_manifest.csv records source exposure, extension, cutout centre, dimensions and coverage status. A frame footprint match can still leave a centre in a detector gap.')
h('B Produce provisional aligned previews')
p('Running the fitter with --previews creates *_provisional_bar_aligned.fits only for candidates without numerical quality flags. GEOMSTAT is PROVISIONAL. Candidates failing the checks are retained in the reports. A previous preview invalidated on a rerun is renamed *_rejected_bar_aligned.fits and marked REJECTED.')
h('C Deproject using adopted geometry')
p('Prepare adopted_geometry.csv with one row per distinct galaxy and these fields: object_id, disk_pa_deg, inclination_deg, bar_pa_deg, radius_arcsec, geometry_source. Use reviewed values and a meaningful provenance label. The batch command requires a complete valid geometry row for every native cutout in its output folder; place a selected subset in a separate folder when only some galaxies are ready.')
code("& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\extract_calibrated_VIS_galaxies.py' `\n  --deproject-existing `\n  --geometry-csv '.\\Euclid\\adopted_geometry.csv'")
p('The transform maps detector pixels into local west and north offsets, expands the disc minor-axis direction by 1/cos(i), transforms the observed bar direction through the same expansion, and rotates the resulting bar onto the x-axis. A 180-degree sign choice follows the original display convention.')
p('The output is a square in deprojected angular coordinates. Its centre is at radius_pixels + 1 in FITS coordinates, and its WCS uses LINEAR arcsecond offsets rather than RA and Dec. The fitter’s provisional radius is max(3 × bar_max, 45 arcseconds); bar_max is the selected range boundary, not a measured bar end. The deprojector accepts inclination below 85 degrees and radii above zero up to 600 arcseconds.')
p('SCI is bilinearly resampled; RMS is propagated assuming independent input pixels; FLG is the bitwise OR of contributing flags. COVERAGE records interpolation support and unsupported SCI pixels become NaN. The science output is not masked using the fitting mask, so contaminating sources and flagged pixels remain represented. Interpolation introduces correlated noise; no integrated-flux correction is applied.')

page('Paths outputs and verification')
h('Project and data locations')
p('Code and documentation')
code('C:\\Users\\gordo\\Documents\\Github\\PythonScripts\\Euclid')
p('Download and output folders share this base path')
code('D:\\Dropbox\\Public Documents\\UCLAN\\MSc Research\\Euclid')
bullet('Euclid Download Data contains the original individual calibrated FITS exposures.')
bullet('Euclid Single Galaxies contains native cutouts, diagnostic PNGs, profiles, geometry reports and aligned outputs.')
p('The older extract_euclid_VIS_bars.py workflow uses S4G catalogue geometry and separate sample images. This guide concerns extract_calibrated_VIS_galaxies.py and fit_euclid_VIS_geometry.py for the Q1 single-frame downloads; do not confuse their input files or geometry sources.')
h('Current processing snapshot')
p('Five downloaded frames produced 23 native cutouts covering 20 distinct objects from the 25-target shortlist. Five centres were not on the inspected science quadrants. There were 17 candidate geometry rows and six failed fits. Two cutouts passed the numerical checks for provisional aligned previews; they remain subject to visual and scientific review. Repeat exposures account for the difference between cutout and distinct-galaxy counts.')
h('Verify a run')
bullet('Check that metadata and geometry manifests use exact object IDs; avoid spreadsheet rounding of large integer identifiers.')
bullet('Inspect native cutouts for missing galaxy light, foreground objects and quadrant edges; inspect every adopted geometry overlay and radial profile.')
bullet('Compare estimates across repeat exposures and record the chosen centre, disc range, bar range, q0, adopted angles and provenance.')
bullet('Check FITS checksums, output centre and coverage. Keep original downloads and native cutouts to reproduce each transform.')
p('The existing test_euclid_VIS_geometry.py checks ellipse recovery on a synthetic galaxy and sky-angle conventions. The processed native and provisional FITS files passed checksum verification. These checks establish numerical consistency, not that an automatic disc or bar selection is physically correct.')
code("& '.\\.venv\\Scripts\\python.exe' `\n  '.\\Euclid\\test_euclid_VIS_geometry.py'")
h('Sources and further detail')
for text in [
'Galaxy Zoo Euclid Q1 morphology catalogue: https://zenodo.org/records/15106473',
'Morphology paper: https://doi.org/10.1051/0004-6361/202555140',
'Euclid Archive and guides: https://eas.esac.esa.int/sas/',
'VIS processing and FITS products: https://doi.org/10.1051/0004-6361/202554594',
'Photutils isophote fitting: https://photutils.readthedocs.io/en/latest/user_guide/isophote.html',
'VIS flag definitions: https://euclid.esac.esa.int/msp/dpdd/v1.1/visdpd/dpcards/vis_flagmap.html',
'Local implementation notes: Euclid/PHOTUTILS_GEOMETRY.md and Euclid/q1_barred_spirals/README.md.']:
    a=doc.add_paragraph(text);a.paragraph_format.space_after=Pt(4)
    for r in a.runs:r.font.size=Pt(9)
doc.core_properties.title='Euclid Q1 barred spiral galaxy processing'
doc.core_properties.subject='Selection downloads geometry fitting and deprojection'
doc.core_properties.author=''
# Remove inherited Word title rules from the default template.
for root in (doc._element,doc.styles.element):
    for border in list(root.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.save('Euclid_Q1_processing_guide.docx')
