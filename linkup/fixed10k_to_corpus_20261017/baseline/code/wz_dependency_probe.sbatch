#!/bin/bash
#SBATCH --job-name=fx10k-base-probe
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/probe-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/probe-%j.err
set -eo pipefail
set +u
source /etc/profile
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
python - <<'PY'
import importlib, json, platform
result={"status":"pass","python":platform.python_version(),"modules":{}}
for name in ("numpy","scipy","sklearn","pyarrow"):
    try:
        mod=importlib.import_module(name); result["modules"][name]={"available":True,"version":getattr(mod,"__version__",None)}
    except Exception as exc:
        result["modules"][name]={"available":False,"error":type(exc).__name__+":"+str(exc)}; result["status"]="fail"
print(json.dumps(result,sort_keys=True))
raise SystemExit(0 if result["status"]=="pass" else 2)
PY
