from pathlib import Path
import re,json,hashlib
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
SRC=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\README_MER_VIS_REVIEW.md')
OUT=Path('MER_VIS_review_word_guide');source=SRC.read_text(encoding='utf-8-sig');d=Document();sec=d.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11);sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.72);sec.left_margin=Inches(.8);sec.right_margin=Inches(.8);sec.header_distance=Inches(.3);sec.footer_distance=Inches(.3)
normal=d.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(11);normal.font.color.rgb=RGBColor(25,25,25);normal.paragraph_format.line_spacing=1.12;normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.widow_control=True
for name,size in [('Title',25),('Heading 1',15),('Heading 2',12)]:
 s=d.styles[name];s.font.name='Calibri';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0);s.font.underline=False;s.paragraph_format.keep_with_next=True;s.paragraph_format.space_before=Pt(14 if name!='Title' else 0);s.paragraph_format.space_after=Pt(7)
 if name!='Title':s.font.bold=True
for name in ['Title','Title Char','Subtitle','Subtitle Char']:
 if name in d.styles:
  style=d.styles[name];style.font.color.rgb=RGBColor(0,0,0);style.font.underline=False
  for border in list(style.element.xpath('./w:pPr/w:pBdr')):border.getparent().remove(border)
d.styles['Subtitle'].font.name='Calibri';d.styles['Subtitle'].font.size=Pt(12);d.styles['Subtitle'].font.italic=False;d.styles['Subtitle'].paragraph_format.space_after=Pt(12)
for name in ['List Paragraph','List Bullet']:
 s=d.styles[name];s.font.name='Calibri';s.font.size=Pt(11);s.paragraph_format.space_after=Pt(5);s.paragraph_format.line_spacing=1.1
# Modest running header and page numbering, without decorative lines.
h=sec.header.paragraphs[0];h.text='EUCLID  •  MER VIS REVIEW GUIDE';h.style='Normal';h.paragraph_format.space_after=Pt(0)
for r in h.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=f.add_run('MER VIS sample review  |  ');r.font.size=Pt(8);r.font.color.rgb=RGBColor(80,80,80)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');f._p.append(field)
# Real Word numbering, restarted for each numbered procedure.
def numbered_id():
 root=d.part.numbering_part.element;nums=[int(x.get(qn('w:numId'))) for x in root.findall(qn('w:num'))];abstracts=[int(x.get(qn('w:abstractNumId'))) for x in root.findall(qn('w:abstractNum'))];aid=max(abstracts,default=-1)+1;nid=max(nums,default=0)+1
 a=OxmlElement('w:abstractNum');a.set(qn('w:abstractNumId'),str(aid));lvl=OxmlElement('w:lvl');lvl.set(qn('w:ilvl'),'0')
 for tag,val in [('start','1'),('numFmt','decimal'),('lvlText','%1.'),('lvlJc','left')]:
  e=OxmlElement('w:'+tag);e.set(qn('w:val'),val);lvl.append(e)
 ppr=OxmlElement('w:pPr');tabs=OxmlElement('w:tabs');tab=OxmlElement('w:tab');tab.set(qn('w:val'),'num');tab.set(qn('w:pos'),'360');tabs.append(tab);ppr.append(tabs);ind=OxmlElement('w:ind');ind.set(qn('w:left'),'360');ind.set(qn('w:hanging'),'360');ppr.append(ind);lvl.append(ppr);a.append(lvl);root.append(a)
 n=OxmlElement('w:num');n.set(qn('w:numId'),str(nid));e=OxmlElement('w:abstractNumId');e.set(qn('w:val'),str(aid));n.append(e);root.append(n);return nid
pattern=re.compile(r'(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')
content_blocks=[]
def inline(p,text):
 for part in pattern.split(text):
  if not part:continue
  if part.startswith('**'):
   r=p.add_run(part[2:-2]);r.bold=True
  elif part.startswith('`'):
   r=p.add_run(part[1:-1]);r.font.name='Consolas';r.font.size=Pt(9.5)
  elif part.startswith('['):
   m=re.match(r'\[([^\]]+)\]\(([^)]+)\)',part);label,url=m.groups();rel=p.part.relate_to(url,RT.HYPERLINK,is_external=True);link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rel);run=OxmlElement('w:r');props=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'23556D');props.append(color);underline=OxmlElement('w:u');underline.set(qn('w:val'),'single');props.append(underline);run.append(props);t=OxmlElement('w:t');t.text=label;run.append(t);link.append(run);p._p.append(link)
  else:p.add_run(part)
blocks=re.split(r'\n\s*\n',source.strip());in_list=False;list_id=None;section_order=[]
for block in blocks:
 lines=block.splitlines()
 if block.startswith('# '):
  title=block[2:].strip();p=d.add_paragraph(title,style='Title');d.add_paragraph('Interactive galaxy review tool',style='Subtitle');in_list=False;continue
 if block.startswith('## '):
  heading=block[3:].strip();p=d.add_paragraph(heading,style='Heading 1');section_order.append(heading);in_list=False;continue
 if all(re.match(r'^\d+\. ',x) for x in lines):
  list_id=numbered_id()
  for line in lines:
   text=re.sub(r'^\d+\. ','',line);p=d.add_paragraph(style='List Paragraph');pr=p._p.get_or_add_pPr();num=OxmlElement('w:numPr');ilvl=OxmlElement('w:ilvl');ilvl.set(qn('w:val'),'0');ni=OxmlElement('w:numId');ni.set(qn('w:val'),str(list_id));num.append(ilvl);num.append(ni);pr.append(num);inline(p,text);content_blocks.append(text)
  continue
 if all(x.startswith('- ') for x in lines):
  for line in lines:
   text=line[2:];p=d.add_paragraph(style='List Bullet');inline(p,text);content_blocks.append(text)
  continue
 text=' '.join(lines);p=d.add_paragraph();inline(p,text);content_blocks.append(text)
# Improve heading-page balance without changing the source wording or section order.
for p in d.paragraphs:
 if p.style.name=='Heading 1' and p.text in ['What is saved','PixInsight AutoSTF view','Correct a centre and recompute']:
  p.paragraph_format.page_break_before=True
# Remove any title border/theme residue in the final OOXML.
for p in d.paragraphs:
 if p.style.name=='Title':
  for b in list(p._p.xpath('./w:pPr/w:pBdr')):b.getparent().remove(b)
  for r in p.runs:r.font.color.rgb=RGBColor(0,0,0);r.font.underline=False
# Verify each text block survived formatting, including hyperlink labels.
visible=[''.join(node.text or '' for node in p._p.xpath('.//w:t')) for p in d.paragraphs]
for text in content_blocks:
 plain=pattern.sub(lambda m: m.group(0)[2:-2] if m.group(0).startswith('**') else m.group(0)[1:-1] if m.group(0).startswith('`') else re.match(r'\[([^\]]+)\]',m.group(0)).group(1),text)
 # XML itertext can duplicate run contents; deterministic paragraph texts are checked below.
 assert plain in visible,plain[:80]
d.core_properties.title='MER VIS sample review';d.core_properties.subject='User guide for reviewing Euclid galaxy fits and correcting centres';d.core_properties.comments='Converted from README_MER_VIS_REVIEW.md on 26 October 2026. Source instructions retained.'
path=OUT/'README_MER_VIS_REVIEW.docx';d.save(path)
(OUT/'source_provenance.json').write_text(json.dumps(dict(source=str(SRC),source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),sections=section_order,content_blocks=len(content_blocks)),indent=2),encoding='utf8')
print(path.resolve());print('Content blocks:',len(content_blocks))
