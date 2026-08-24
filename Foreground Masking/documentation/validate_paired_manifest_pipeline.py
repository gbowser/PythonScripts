from pathlib import Path
from types import SimpleNamespace
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
OPT=ROOT/'Foreground Masking'/'Optimisation'
sys.path.insert(0,str(OPT)); sys.path.insert(0,str(ROOT/'Foreground Masking'/'Shared'))
import generate_paired_toy_manifest as gen
from paired_toy_common import SCHEMA_VERSION, sha256_file

out=ROOT/'Foreground Masking'/'documentation'/'paired_manifest_validation'
args=SimpleNamespace(
    source_manifest=ROOT/'Erwin_s4g_image_downloader'/'geometry_output'/'s4g_image_geometry_manifest.csv',
    pc='Desktop', toys_per_image=6, truth_dilation=1, toy_peak_sigma_min=6.0, toy_peak_sigma_max=30.0,
)
manifest={
    'schema_version':SCHEMA_VERSION,'fold_seed':202608150,'toy_configuration':{'peak_sigma_min':6.0,'peak_sigma_max':30.0},
    'injection_sets':{'cross_validation':gen.build_set(args,'cross_validation',202608299,['IC0600'],out)}
}
path=out/'paired_toy_injection_manifest.json'; path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(path); print(sha256_file(path))
