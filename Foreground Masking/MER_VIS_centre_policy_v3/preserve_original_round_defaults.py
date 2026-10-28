from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('version=POLICY_VERSION,policy=DEFAULT_POLICY)', 'version=POLICY_VERSION,policy=DEFAULT_POLICY,policy_enabled_default=bool(self.campaign or row.get("centre_policy_version")==POLICY_VERSION))',1);p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('centre_enabled:!!g.centre_reference', 'centre_enabled:g.centre_reference?.policy_enabled_default??!!g.centre_reference',1).replace('S.settings.rules.centre_enabled=true;S.settings.centre_policy_version=', 'S.settings.rules.centre_enabled=centreDefaults.centre_enabled;S.settings.centre_policy_version=',1)
s=s.replace("(g.centre_reference&&p.numerically_accepted_strict)", "(g.centre_reference&&(settings.rules?.centre_enabled!==false||g.centre_reference.policy_enabled_default)&&p.numerically_accepted_strict)")
s=s.replace("(g.centre_reference&&p.numerically_accepted_relaxed)", "(g.centre_reference&&(settings.rules?.centre_enabled!==false||g.centre_reference.policy_enabled_default)&&p.numerically_accepted_relaxed)")
p.write_text(s,encoding='utf8')
