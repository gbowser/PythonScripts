from pathlib import Path
import hashlib,json,difflib
original=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\refit_MER_VIS.py').read_text(encoding='utf8')
s=original.replace("    engine.MANUAL_LOCK=request['lock_centre']", "    engine.MANUAL_LOCK=request['lock_centre']\n    from centre_policy_MER_VIS import checked_policy\n    engine.CENTRE_POLICY=checked_policy(request.get('centre_policy'))")
s=s.replace("source_manifest_sha256=self.digest,\n                           engine_sha256", "source_manifest_sha256=self.digest,\n                           centre_policy=__import__('centre_policy_MER_VIS').checked_policy(payload.get('centre_policy')),\n                           reference_provenance=payload.get('reference_provenance','manual_selection'),\n                           engine_sha256",1)
s=s.replace("manual_refit_requires_visual_review=True)", "manual_refit_requires_visual_review=True,centre_reference_provenance=request.get('reference_provenance','manual_selection'),centre_policy=engine.CENTRE_POLICY)",1)
base=Path('MER_VIS_centre_policy_v3');job=json.loads((base/'jobs.json').read_text())[0];expected=json.loads(Path(job['request']).read_text())['worker_sha256'];s=s.replace('\n','\r\n');actual=hashlib.sha256(s.encode()).hexdigest();print('actual',actual,'expected',expected)
if actual==expected:(base/'round_output'/'provenance'/f'worker_{actual[:12]}.py').write_bytes(s.encode('utf8'))
else:raise RuntimeError('Worker reconstruction mismatch')

