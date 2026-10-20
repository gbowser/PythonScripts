from pathlib import Path
from docx import Document
p=Path('MER_VIS_summary_build/output/Euclid_MER_VIS_outcomes_summary.docx')
d=Document(p)
for a in d.paragraphs:
 if a.text.startswith('Euclid documents raw POSITION_ANGLE'):
  a.text='Euclid documents raw POSITION_ANGLE as counterclockwise from image x, SExtractor THETA_IMAGE. Our original WCS conversion already changes that image reference to North towards East. The observed offset is consistent with POSITION_ANGLE being referenced to the detection image’s y-axis rather than the documented x-axis, assuming the same rotation sense and major-axis definition. Interpreting such a y-referenced value as x-referenced would introduce a quarter-turn, which our additional 90° adjustment would cancel modulo 180°. This is a plausible explanation for the additional correction, but has not been confirmed. We retain the tested correction for this Q1 comparison without asserting a documentation or pipeline error. The raw Euclid values and independently fitted Photutils angles remain unchanged.'
d.save(p)
p=Path('MER_VIS_summary_build/build_summary.mjs');s=p.read_text(encoding='utf-8-sig')
s=s.replace("'.codex-finalizer-PA-explicit'","'.codex-finalizer-PA-yaxis'").replace('Euclid_MER_VIS_outcomes_summary_PA_explicit.pptx','Euclid_MER_VIS_outcomes_summary_PA_yaxis.pptx')
s=s.replace('The WCS step already changes the reference axis. The extra +90° is a separate correction.','Possible explanation: catalogue angle from detection-image y rather than documented x (unconfirmed).')
s=s.replace('Its pipeline origin remains unresolved.', 'The observed offset is consistent with POSITION_ANGLE being referenced to the detection image y-axis rather than the documented x-axis, assuming the same rotation sense and major-axis definition. Interpreting a y-referenced value as x-referenced introduces a quarter-turn, cancelled by the additional 90-degree adjustment modulo180. This is a plausible explanation, not a confirmed documentation or pipeline error.')
p.write_text(s,encoding='utf-8')
