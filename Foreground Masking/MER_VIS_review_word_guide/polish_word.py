from pathlib import Path
p=Path('MER_VIS_review_word_guide/convert_readme.py');s=p.read_text(encoding='utf8')
s=s.replace("for name in ['List Paragraph','List Bullet']:", "for name in ['Title','Title Char','Subtitle','Subtitle Char']:\n if name in d.styles:\n  style=d.styles[name];style.font.color.rgb=RGBColor(0,0,0);style.font.underline=False\n  for border in list(style.element.xpath('./w:pPr/w:pBdr')):border.getparent().remove(border)\nd.styles['Subtitle'].font.name='Calibri';d.styles['Subtitle'].font.size=Pt(12);d.styles['Subtitle'].font.italic=False;d.styles['Subtitle'].paragraph_format.space_after=Pt(12)\nfor name in ['List Paragraph','List Bullet']:")
s=s.replace("r.font.size=Pt(8);r.font.color.rgb=RGBColor(80,80,80)\nf=", "r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)\nf=")
s=s.replace("visible='\\n'.join(''.join(p._p.itertext()) for p in d.paragraphs)","visible=[''.join(node.text or '' for node in p._p.xpath('.//w:t')) for p in d.paragraphs]")
s=s.replace("assert plain[:30] in visible,plain[:80]", "assert plain in visible,plain[:80]")
p.write_text(s,encoding='utf8')
