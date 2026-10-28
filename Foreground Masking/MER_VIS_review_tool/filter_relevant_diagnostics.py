from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');pos=s.index('function storedWarningNotes(')
s=s[:pos]+'''function relevantProfileDiagnostics(g,diagnostics,sample=[]){
 const example=sample.find(row=>row.object_id===g.object_id),code={ellipticity:'ellipticity',sparse:'sampling',variation:'pa',bar:'smallbar',failed:'failed'}[example?.category];
 return diagnostics.filter(d=>d.active||d.code===code);
}
''' +s[pos:]
s=s.replace('const warnings=profileWarningEvidence(S.g,S.settings,S.calc),highlight=', 'const warnings=relevantProfileDiagnostics(S.g,profileWarningEvidence(S.g,S.settings,S.calc),S.boot?.sample??[]),highlight=',1)
s=s.replace("`).join('')+(stored.length?", "`).join('')+(!warnings.length&&!stored.length?'<p class=\"small\">No active warnings or relevant boundary-case diagnostics for this selection.</p>':'')+(stored.length?",1)
s=s.replace('calculate,thresholdDescription,profileWarningEvidence,','calculate,thresholdDescription,relevantProfileDiagnostics,profileWarningEvidence,',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('“Show diagnostic ranges” displays measured evidence even below a warning threshold.', '“Show diagnostic ranges” displays only active warnings and the specific diagnostic this galaxy was selected to illustrate. A relevant boundary case remains visible below threshold; unrelated passing checks are hidden.');p.write_text(s,encoding='utf8')
