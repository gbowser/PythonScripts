#!/usr/bin/env bash
set -euo pipefail

# Run from the PythonScripts checkout.  Override MTOBJECTS_REPOSITORY if the
# MTObjects checkout lives elsewhere.
project_root="$(pwd)"
mtobjects_repository="${MTOBJECTS_REPOSITORY:-$(dirname "$project_root")/mtobjects}"
venv_path="${MTOBJECTS_VENV:-$project_root/.venv-azure-mtobjects}"

sudo apt-get update
sudo apt-get install -y build-essential git libgsl-dev python3 python3-tk python3-venv

if [[ ! -d "$mtobjects_repository/mtolib" ]]; then
  git clone https://github.com/CarolineHaigh/mtobjects.git "$mtobjects_repository"
fi

python3 -m venv "$venv_path"
"$venv_path/bin/python" -m pip install --upgrade pip
"$venv_path/bin/python" -m pip install -r \
  "$project_root/Foreground Masking/Azure/requirements-linux.txt"

# The upstream recompile.sh resolves ../src relative to the script path after
# changing directory, which lands one directory too high when invoked by an
# absolute path.  Build the same four libraries from the actual source folder.
mkdir -p "$mtobjects_repository/mtolib/lib"
(
  cd "$mtobjects_repository/mtolib/src"
  gcc -shared -fPIC -include main.h -o ../lib/mt_objects.so \
    mt_objects.c mt_heap.c mt_node_test_4.c -lgsl -lgslcblas
  gcc -shared -fPIC -include main.h -o ../lib/maxtree.so \
    maxtree.c mt_stack.c mt_heap.c
  gcc -shared -fPIC -include main_double.h -o ../lib/mt_objects_double.so \
    mt_objects.c mt_heap.c mt_node_test_4.c -lgsl -lgslcblas
  gcc -shared -fPIC -include main_double.h -o ../lib/maxtree_double.so \
    maxtree.c mt_stack.c mt_heap.c
)
export MTOBJECTS_ROOT="$mtobjects_repository"

"$venv_path/bin/python" - <<'PY'
import ctypes
import os
from pathlib import Path

import astropy
import numpy
import optuna
import scipy
import sep

root = Path(os.environ["MTOBJECTS_ROOT"])
libraries = (
    "maxtree.so",
    "maxtree_double.so",
    "mt_objects.so",
    "mt_objects_double.so",
)
for name in libraries:
    ctypes.CDLL(str(root / "mtolib" / "lib" / name))

print("Linux dependency check passed")
print(f"numpy={numpy.__version__}, scipy={scipy.__version__}, astropy={astropy.__version__}")
print(f"optuna={optuna.__version__}, sep={sep.__version__}")
print(f"MTObjects={root}")
PY

cat <<EOF

Setup complete. Before each run:
  source "$venv_path/bin/activate"
  export MTOBJECTS_ROOT="$mtobjects_repository"
EOF
