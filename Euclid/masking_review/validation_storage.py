"""Machine-specific research location for disposable validation products."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from machine_paths import detect_pc, research_folder


def validation_output():
    root = research_folder(detect_pc(ROOT))
    if not root.is_dir():
        raise RuntimeError(f'Research storage unavailable: {root}')
    return root / 'Euclid/masking_review/validation_output'
