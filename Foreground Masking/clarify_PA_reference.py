from pathlib import Path
from docx import Document
p=Path('MER_VIS_summary_build/output/Euclid_MER_VIS_outcomes_summary.docx')
d=Document(p)
for a in d.paragraphs:
 if a.text.startswith('A constant 90° offset can represent'):
  a.text='On a North-up, East-left image, the positive x-axis points West and the positive y-axis points North. For an axial orientation, the conversion is sky PA = (image angle measured counterclockwise from +x + 90°) modulo 180°. For example, a horizontal axis has image angle 0° and sky PA 90°; a vertical axis has image angle 90° and sky PA 0°. The perpendicular image and sky reference axes therefore explain a 90° difference between these two angle definitions.'
 if a.text.startswith('Euclid documents raw POSITION_ANGLE'):
  a.text='Euclid documents raw POSITION_ANGLE as counterclockwise from image x, SExtractor THETA_IMAGE. Crucially, our original WCS conversion already changes that image reference to North towards East. The adopted additional +90° correction is applied AFTER that conversion. It cannot therefore be explained simply as the same East–West to North–South reference change again. We retain this tested additional correction for the Q1 comparison, while leaving its pipeline origin unresolved. The raw Euclid values and independently fitted Photutils angles remain unchanged.'
 if a.text.startswith('On a North-up, East-left astronomical display'):
  a.text='On a North-up, East-left astronomical display the reported North-towards-East direction is COUNTERCLOCKWISE. If East is displayed on the right, it is CLOCKWISE. The thumbnails preserve the deliberately North-up mosaic grid without additional rotation. Across all 2777 galaxy centres, local North differs from pixel vertical by a median 0.141° and a maximum 0.604°, owing to sky projection. WCS conversion accounts for this local difference.'
d.save(p)
p=Path('MER_VIS_summary_build/build_summary.mjs');s=p.read_text(encoding='utf-8-sig')
s=s.replace("'.codex-finalizer-PA'","'.codex-finalizer-PA-explicit'").replace('Euclid_MER_VIS_outcomes_summary_PA_updated.pptx','Euclid_MER_VIS_outcomes_summary_PA_explicit.pptx')
s=s.replace('A constant 90 offset is consistent with perpendicular reference axes or major/minor axes but does not uniquely prove the cause.', 'For North-up East-left images, sky PA = (CCW image angle from +x +90) modulo180. This reference change is ALREADY included in the original WCS conversion. The adopted ADDITIONAL +90 follows that conversion and cannot be explained by counting the same reference change again. Its pipeline origin remains unresolved. The 2777 local North offsets have median absolute 0.141 degrees and maximum 0.604 degrees. No additional thumbnail rotation is applied.')
s=s.replace("text(s,'Adopted rule: adjusted Euclid sky PA = (converted PA + 90°) mod 180°',64,146,1150,68,27,blue,true);", "text(s,'Adopted rule: adjusted Euclid sky PA = (WCS-converted PA + 90°) mod 180°\\nThe WCS step already changes the reference axis. The extra +90° is a separate correction.',64,140,1150,88,23,blue,true);")
p.write_text(s,encoding='utf-8')
