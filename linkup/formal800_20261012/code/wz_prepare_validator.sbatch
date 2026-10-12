#!/bin/bash
#SBATCH --job-name=formal800-jsonschema
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/jsonschema-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/private/jsonschema-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
source /work/home/lilysharp/proxy.sh >/dev/null 2>&1
set -u
umask 077
F800=/work/home/lilysharp/private/formal800_20261012
python3 -m pip install --disable-pip-version-check --quiet --index-url https://pypi.org/simple --target "$F800/runtime_jsonschema" 'jsonschema==4.19.2' > "$F800/private/jsonschema-install.log" 2>&1
PYTHONPATH="$F800/runtime_jsonschema" python3 -c 'import jsonschema, importlib.metadata, json, os; jsonschema.Draft202012Validator({}); print(json.dumps({"status":"pass","job_id":os.environ.get("SLURM_JOB_ID"),"jsonschema":importlib.metadata.version("jsonschema"),"purpose":"format validation dependency only"}))' > "$F800/public/JSONSCHEMA_RUNTIME_RECEIPT.json"
