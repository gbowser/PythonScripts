from pathlib import Path
import json,urllib.request
state=Path('MER_VIS_review_tool/qa_state/server.json')
if state.exists():
 data=json.loads(state.read_text());url=data['url'];boot=json.loads(urllib.request.urlopen(url+'api/bootstrap').read());req=urllib.request.Request(url+'api/stop',data=b'{}',headers={'Content-Type':'application/json','Origin':url.rstrip('/'),'X-Review-Token':boot['token']});urllib.request.urlopen(req).read();print('Isolated QA server stopped')
