from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
s=s.replace("display:{stretch:'asinh',", "display:{defaultVersion:2,stretch:'autostf',")
s=s.replace(" S.view=draft?.view", " if(S.settings.display.defaultVersion!==2){S.settings.display={...S.settings.display,defaultVersion:2,stretch:'autostf',gamma:1};}\n S.view=draft?.view")
s=s.replace("applyPreset('faint',false)","applyPreset(S.settings.display.stretch==='autostf'?'pixinsight':'faint',false)")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<option value="asinh">Asinh</option><option value="log">Log</option><option value="linear">Linear</option><option value="autostf">PixInsight AutoSTF</option>', '<option value="autostf" selected>PixInsight AutoSTF</option><option value="asinh">Asinh</option><option value="log">Log</option><option value="linear">Linear</option>');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/README_MER_VIS_REVIEW.md');s=p.read_text(encoding='utf8');s+='\nPixInsight AutoSTF is the default view and the first Stretch option. Existing display drafts are migrated to this default once; subsequent display choices are remembered per galaxy. Assessments, geometry intervals and science files are unchanged.\n';p.write_text(s,encoding='utf8')
