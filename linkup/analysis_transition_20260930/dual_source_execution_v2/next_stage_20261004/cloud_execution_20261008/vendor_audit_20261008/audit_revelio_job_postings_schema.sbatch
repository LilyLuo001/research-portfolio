#!/bin/bash
#SBATCH --job-name=revelio-jp-schema
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00

set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38${PYTHONPATH:+:${PYTHONPATH}}

: "${AUDIT_RUN_ROOT:?AUDIT_RUN_ROOT is required}"
SOURCE_ROOT=/work/home/lilysharp/Revelio_Job_Postings
OUTPUT=${AUDIT_RUN_ROOT}/REVELIO_JOB_POSTINGS_SCHEMA_PUBLIC.json
umask 077
mkdir -p "${AUDIT_RUN_ROOT}"

python - "${SOURCE_ROOT}" "${OUTPUT}" <<'PY'
import datetime
import json
import os
import pathlib
import re
import socket
import sys

import pyarrow
import pyarrow.parquet as pq

source_root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
pattern = re.compile(r"Job_Postings_(20(?:0[8-9]|1[0-9]|2[0-6]))[.]parquet$")
files = []
for path in sorted(source_root.glob("Job_Postings_*.parquet")):
    match = pattern.fullmatch(path.name)
    if match:
        files.append((int(match.group(1)), path))

expected_years = list(range(2008, 2027))
observed_years = [year for year, _ in files]
if observed_years != expected_years:
    raise SystemExit("expected exactly annual files 2008-2026")

year_metadata = []
schema_signatures = {}
for year, path in files:
    parquet = pq.ParquetFile(str(path))
    metadata = parquet.metadata
    arrow_schema = parquet.schema_arrow
    fields = [{"name": field.name, "type": str(field.type), "nullable": field.nullable}
              for field in arrow_schema]
    signature = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    schema_signatures.setdefault(signature, []).append(year)
    year_metadata.append({
        "year": year,
        "file_name": path.name,
        "file_bytes": path.stat().st_size,
        "rows": metadata.num_rows,
        "row_groups": metadata.num_row_groups,
        "columns": metadata.num_columns,
        "fields": fields,
    })

result = {
    "schema_version": "linkup-revelio-job-postings-footer-audit-v1",
    "status": "complete",
    "purpose": "scheduled metadata-only audit of delivered Revelio Job Postings Parquet footers",
    "execution_location": "Wuzhen scheduled compute node",
    "job_id": os.environ.get("SLURM_JOB_ID"),
    "node": socket.gethostname(),
    "partition": os.environ.get("SLURM_JOB_PARTITION"),
    "resources": {
        "cpus": int(os.environ.get("SLURM_CPUS_PER_TASK", "1")),
        "memory_mb": int(os.environ.get("SLURM_MEM_PER_NODE", "0")),
        "scheduler_required_dcu": 1,
        "accelerator_computation_performed": False,
        "wall_limit": "00:10:00",
    },
    "audited_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python_version": sys.version.split()[0],
    "pyarrow_version": pyarrow.__version__,
    "source_root": str(source_root),
    "years": expected_years,
    "annual_file_count": len(files),
    "total_file_bytes": sum(item[1].stat().st_size for item in files),
    "total_rows_across_annual_files": sum(item["rows"] for item in year_metadata),
    "schema_variant_count": len(schema_signatures),
    "schema_variants": [
        {"years": years, "fields": json.loads(signature)}
        for signature, years in schema_signatures.items()
    ],
    "annual_metadata": year_metadata,
    "read_scope": "Parquet footer metadata and filesystem sizes only; no row columns or text values read",
    "inference_performed": False,
    "historical_representation_claim_authorized": False,
    "interpretation": "File years are delivery partitions. This audit does not establish posting-time representativeness, version history, or historical text validity.",
}
temporary = output.with_suffix(output.suffix + ".tmp")
temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
temporary.replace(output)
PY

sha256sum "${OUTPUT}" > "${OUTPUT}.sha256"
