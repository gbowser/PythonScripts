"""Update the existing Word reports while preserving their page layouts and examples."""
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
import json
ROOT=Path(__file__).parent
DATA=json.loads((ROOT/'current_report/report_data.json').read_text(encoding='utf8'))
s=DATA['summary'];labels=DATA['flag_labels'];out=ROOT/'current_report/output'
source=ROOT/'bar_class_update'
for name in ['Euclid_MER_VIS_outcomes_summary.docx','Euclid_MER_VIS_disc_PA_and_inclination_explained.docx']:
 d=Document(source/name)
 for p in d.paragraphs:
  t=p.text;new=t
  if t.startswith('All 2777 cutouts have been reprocessed'):
   new=f"The sample contains 2,777 galaxy cutouts. Disc geometry is available for {s['fits']} galaxies; {s['failures']} have no adopted geometry. A returned measurement is provisional: the selected light contours still need physical interpretation as disc or bar."
  new=new.replace('What changed and how centres are checked','How centres are checked').replace('Updated report collection','Galaxy report collection')
  new=new.replace('A missing accepted bar no longer discards a usable disc result.','A missing accepted bar does not discard a usable disc result.')
  new=new.replace('The old unstable-bar-PA category is not carried forward as an accepted bar: unstable plateaus are rejected by the new bar test.','Bar plateaus with excessive PA variation are rejected.')
  new=new.replace('This guide explains the revised adaptive v2 pipeline and shows current examples. It replaces the earlier fixed-centre explanation.','This guide explains how the disc and bar geometry are measured and shows galaxy examples.')
  new=new.replace('Counts overlap. New recovery and selection flags make these counts unsuitable for a direct numerical ranking against the old flags.','Counts overlap; a galaxy can have several review issues.')
  if 'The original run had' in new:new=new.split(' The original run had')[0]
  new=new.replace(' A reproducibility record retains the original summary manifest as an audit baseline; superseded presentation reports and image/PDF collections have been replaced.','')
  if t.startswith('Unstable disc PA:'):
   new='Disc PA varies across radius: Accepted disc sky PA scatter exceeds 10°, with at least six selected accepted ellipses and no radial gap exceeding half the selected span. Nearly-face-on discs are exempt. This is a screening rule, not a calibrated confidence test.'
  if t.startswith('Small selected bar interval:'):
   new='Bar identification uncertain because of a small interval: The selected candidate interval ends below 1.5 arcsec. This may be an unresolved bar or a bulge, spiral arm or noise feature. It does not establish the presence of a bar.'
  if new!=t:p.text=new
 # Update tables without replacing the rest of their design.
 for table in d.tables:
  head=[c.text for c in table.rows[0].cells]
  if head==['Result','Galaxies','Share of all 2777']:
   values=[s['fits'],s['clean'],s['fits']-s['clean'],s['failures']]
   for row,n in zip(table.rows[1:],values):row.cells[1].text=str(n);row.cells[2].text=f'{n/2777:.1%}'
  if head==['Output','Count']:
   values=[2777,s['verification']['groups']['QI'],s['verification']['groups']['NoQI'],s['verification']['PDF_files'],s['verification']['PDF_pages']]
   for row,n in zip(table.rows[1:],values):row.cells[1].text=str(n)
  if head==['Counted issue','Galaxies','Share of returned fits']:
   # Reuse styled rows and add one for the new sparse-sampling category.
   items=sorted(s['flags'].items(),key=lambda z:-z[1])
   while len(table.rows)<len(items)+1:table.add_row()
   for row,(key,n) in zip(table.rows[1:],items):
    for c,v in zip(row.cells,[labels.get(key,key),str(n),'<0.1%' if n/s['fits']<.001 else f'{n/s["fits"]:.1%}']):c.text=v
 # Replace the four good and two poor illustrated examples with current-card crops and captions.
 if 'explained' in name:
  current=None;await_caption=False
  for p in d.paragraphs:
   if p.text.startswith('Example ') and 'with no counted geometry issues' in p.text:current=DATA['good_examples'][int(p.text.split()[1])-1]
   elif p.text.startswith('Example ') and 'requiring disc orientation review' in p.text:current=DATA['poor_examples'][int(p.text.split()[1])-1]
   elif p.style.name.startswith('Heading') and not p.text.startswith('Example '):current=None
   if current and p._p.xpath('.//a:blip'):
    for b in p._p.xpath('.//a:blip'):
     d.part.related_parts[b.get(qn('r:embed'))]._blob=Path(current['image']).read_bytes()
    await_caption=True
   elif current and await_caption and p.text.startswith('Galaxy '):
    def val(k):return 'Unavailable' if current.get(k) is None else f'{current[k]:.2f}°'
    p.text=f"Galaxy {current['id']}. Disc PA {val('disc')}; bar PA {val('bar')}; inclination {val('inc')}. Accepted disc ellipses: {current['n_disc']}. Flags: {', '.join(labels.get(f,f) for f in current['flags']) or 'none'}. Centre offset {current['centre_offset']:.3f} arcsec."
    await_caption=False
   elif current and p.text.startswith('Disc PA scatter is '):p.text=f"Disc PA scatter is {current['disc_scatter']:.2f}°. The well-sampled accepted outer contours change direction. Inspect the image and profile to distinguish a systematic twist from scatter, spiral structure, contamination or centre movement."
 d.add_page_break();d.add_heading('Reading the profiles and assessing disc sampling',level=1)
 for title,text in [
 ('Accepted and rejected points','Blue points are accepted ellipse measurements. Grey points fail one or more acceptance checks and are excluded from the adopted disc PA and its scatter. Green shading identifies the selected radial interval; it does not mean that all points inside it are accepted. Lines connect accepted points only and now break across rejected samples. They are visual guides, not fitted curves.'),
 ('Sparse sampling is distinct from PA variation','For non-face-on discs, the PA variation screen requires at least six selected accepted ellipses and no radial gap greater than half the selected span. Otherwise sparse disc sampling is flagged, while numerical PA and scatter remain in the manifest. With adequate sampling, scatter above 10° raises the radial PA variation flag. Nearly-face-on discs are exempt from both PA flags. These operational thresholds require validation; neighbouring ellipses are correlated and the count is not a number of independent observations.'),
 ('Examples discussed during review','Galaxy -518633776290631360 has three selected accepted disc ellipses in the stored interval and a largest gap of about 78% of its span. A point beside the green boundary can appear to be a fourth; selection uses the stored radii. Its label is now sparse disc sampling. Galaxy -601121275504424227 has seven selected accepted disc ellipses and a largest gap of about 22%; its sustained PA change is retained as radial PA variation.'),
 ('Bar candidates and failed fit displays','Galaxy Zoo and Zoobot identify bar candidates. A small selected bar interval can be a real unresolved bar or a different feature. Class A/B describes the ellipse-profile evidence, not physical bar strength or confirmation. Failed fits have no adopted centre, PA or inclination. Their report images now omit fallback centre markers and rejected ellipse overlays, which previously looked misleadingly like adopted geometry. Raw FITS pixels are unchanged.')]:
  d.add_heading(title,level=2);d.add_paragraph(text)
 if 'explained' in name:
  # Keep the complete glossary near its current location without overcrowding it.
  for p in d.paragraphs:
   if p.text.startswith('Disc PA varies across radius:'):
    p.insert_paragraph_before('Sparse disc sampling: Fewer than six selected accepted disc ellipses, or a largest radial gap above half the span. PA stability is not confidently assessed; see the final explanation page.')
 for tree in [d._element,d.styles.element]:
  for b in list(tree.iter(qn('w:pBdr'))):b.getparent().remove(b)
 d.add_heading('Established catalogue identifiers',level=2)
 d.add_paragraph('A coordinate cross-match against SIMBAD and VizieR HyperLEDA VII/237 found 227 secure positional identifications: 224 through SIMBAD and three additional VizieR matches. These have one galaxy identity within 5 arcsec and an adopted separation no greater than 2 arcsec from the Euclid catalogue coordinates. Their identifiers and match separations appear on the PNGs. No Messier, NGC or IC identifier was returned among the accepted matches. One ambiguous case and 13 candidates outside the secure radius remain unassigned. A non-match means no secure identity in these searches, not absence from all catalogues. The manifest records source, separation, link and query date; the full candidate results are retained.')
 d.save(out/name)
 print('Saved',name)
