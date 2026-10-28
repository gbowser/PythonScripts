from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('import secrets\n', 'import secrets\nimport socket\n',1)
pos=s.index('\ndef main():');s=s[:pos]+'''
class LocalReviewServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR can let separate review rounds share a port.
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
''' +s[pos:]
s=s.replace('server=ThreadingHTTPServer(("127.0.0.1",port),Handler)', 'server=LocalReviewServer(("127.0.0.1",port),Handler)',1)
s=s.replace('return self.send(dict(app=APP_ID))', 'return self.send(dict(app=APP_ID,output=str(self.server.store.output),campaign_id=(self.server.store.campaign or {}).get("campaign_id"),pid=os.getpid()))',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/Start_MER_VIS_Review.ps1');s=p.read_text(encoding='utf8');s=s.replace("$saved = if ($useCampaign)", "$expectedCampaign = if ($useCampaign) { (Get-Content -LiteralPath $campaignPath -Raw | ConvertFrom-Json).campaign_id } else { $null }\n$saved = if ($useCampaign)",1)
s=s.replace("if ($health.app -eq 'MER_VIS_sample_review_v1') {", "if (($health.app -eq 'MER_VIS_sample_review_v1') -and ((-not $useCampaign) -or (($health.campaign_id -eq $expectedCampaign) -and ($health.output -eq $saved)))) {")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_centre_campaign.mjs');s=p.read_text(encoding='utf8').replace("const base='http://127.0.0.1:8788/'", "const base=process.argv[2]??'http://127.0.0.1:8788/'");p.write_text(s,encoding='utf8')
