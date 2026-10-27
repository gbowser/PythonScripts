from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
p=Path('MER_VIS_review_tool/index.html');before=p.read_text(encoding='utf8');lines=before.splitlines()
controls=next(line for line in lines if 'id="ellipses"' in line)
legend=next(line for line in lines if 'Green: selected disc.' in line)
helptext=next(line for line in lines if 'Drag a shaded edge' in line)
s=before
for line in [controls,legend,helptext]:s=s.replace(line+'\n','',1)
marker=next(line for line in lines if '<svg id="epsPlot"' in line)
s=s.replace(marker,marker+'\n'+controls,1)
poolnote=next(line for line in lines if '<p id="poolNote"' in line)
s=s.replace(poolnote,poolnote+'\n   <div class="profile-help">\n'+helptext+'\n'+legend+'\n   </div>',1)
class Inspect(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.stack=[];self.panels={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='section':self.stack.append(a.get('class',''))
  if 'id' in a:self.ids.append(a['id']);self.panels[a['id']]=self.stack[-1] if self.stack else ''
 def handle_endtag(self,tag):
  if tag=='section':self.stack.pop()
a=Inspect();a.feed(before);b=Inspect();b.feed(s)
assert Counter(a.ids)==Counter(b.ids)
for key in ['ellipses','excludedEllipses','overlayMode','centres']:assert 'profile-panel' in b.panels[key]
assert s.index('id="paPlot"')<s.index('id="ellipses"')<s.index('id="resetGeometry"')<s.index('id="poolNote"')<s.index('Drag a shaded edge')<s.index('Green: selected disc.')
p.write_text(s,encoding='utf8')
print('PASS: controls moved below both plots; explanations at right panel bottom; all element IDs retained exactly once.')
