#!/bin/bash
#SBATCH --job-name=linkup-dcu-runtime-probe
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:08:00
#SBATCH --output=runtime-probe-%j.out
#SBATCH --error=runtime-probe-%j.err

set -uo pipefail
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }
show_cmd() {
  name=$1
  if command -v "${name}" >/dev/null 2>&1; then
    printf '%s=%s\n' "${name}" "$(command -v "${name}")"
  else
    printf '%s=MISSING\n' "${name}"
  fi
}

section allocation
printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'job_id=%s\n' "${SLURM_JOB_ID:-UNKNOWN}"
printf 'node=%s\n' "$(hostname)"
printf 'partition=%s\n' "${SLURM_JOB_PARTITION:-UNKNOWN}"
printf 'job_gres=%s\n' "${SLURM_JOB_GRES:-UNKNOWN}"
printf 'step_gpus=%s\n' "${SLURM_STEP_GPUS:-UNSET}"
printf 'cpus_per_task=%s\n' "${SLURM_CPUS_PER_TASK:-UNKNOWN}"
printf 'mem_per_node=%s\n' "${SLURM_MEM_PER_NODE:-UNKNOWN}"
scontrol show job "${SLURM_JOB_ID}" 2>&1 | sed -n '1,20p'

section host
uname -a
awk -F: '/model name/{sub(/^ +/,"",$2); print "cpu_model=" $2; exit}' /proc/cpuinfo
ldd --version 2>&1 | sed -n '1p'

section modules
if command -v module >/dev/null 2>&1; then
  module -t list 2>&1 || true
  module -t avail 2>&1 | grep -Ei '(^|/|[-_])(dtk|hip|rocm|hsa|cuda|dcu|torch|pytorch|tensorflow|llama|vllm|python|gcc|cmake)' | head -200 || true
else
  echo module=MISSING
fi

section commands
for executable in hy-smi hy_smi rocminfo rocm-smi hipcc amdclang amdclang++ clang clang++ gcc g++ cmake python python3 llama-cli llama-completion llama-server vllm; do
  show_cmd "${executable}"
done
for executable in hy-smi hy_smi rocminfo rocm-smi hipcc amdclang clang gcc cmake python3; do
  if command -v "${executable}" >/dev/null 2>&1; then
    printf '%s_version_begin\n' "${executable}"
    timeout 20 "${executable}" --version 2>&1 | sed -n '1,12p' || true
    printf '%s_version_end\n' "${executable}"
  fi
done

section device_nodes
for path in /dev/kfd /dev/dri /dev/dri/renderD* /dev/dri/card*; do
  if [ -e "${path}" ]; then ls -l "${path}"; else printf '%s=MISSING\n' "${path}"; fi
done
if command -v lspci >/dev/null 2>&1; then
  lspci -nn 2>&1 | grep -Ei 'display|vga|3d|hygon|amd|advanced micro|accelerator' | head -100 || true
fi

section accelerator_info
for executable in hy-smi hy_smi rocminfo rocm-smi; do
  if command -v "${executable}" >/dev/null 2>&1; then
    printf '%s_probe_begin\n' "${executable}"
    timeout 30 "${executable}" 2>&1 | sed -n '1,160p' || true
    printf '%s_probe_end\n' "${executable}"
  fi
done

section shared_libraries
ldconfig -p 2>/dev/null | grep -Ei 'lib(amdhip64|hiprtc|hsa-runtime64|rocblas|hipblas|miopen|rccl|hyhal|cuda|cudart)' | head -200 || true
for root in /opt /usr/local /public/software; do
  if [ -d "${root}" ]; then
    timeout 20 find "${root}" -maxdepth 5 -type f \( -name 'libamdhip64.so*' -o -name 'libhsa-runtime64.so*' -o -name 'librocblas.so*' -o -name 'libhipblas.so*' -o -name 'libMIOpen.so*' -o -name 'librccl.so*' -o -name 'hipcc' -o -name 'rocminfo' -o -name 'hy-smi' \) -print 2>/dev/null | head -300 || true
  fi
done

section installed_runtime_discovery
for root in "${HOME}/private/next_stage_20261004/local_inference_20261007" "${HOME}/.local/bin"; do
  if [ -d "${root}" ]; then
    timeout 20 find "${root}" -maxdepth 6 -type f \( -name 'llama-completion' -o -name 'llama-cli' -o -name 'llama-server' -o -name 'libggml-hip.so*' -o -name 'libggml-cuda.so*' \) -print 2>/dev/null | head -100 || true
  fi
done
runtime=$(timeout 20 find "${HOME}/private/next_stage_20261004/local_inference_20261007" -maxdepth 6 -type f -name 'llama-completion' -perm -u+x -print -quit 2>/dev/null || true)
if [ -n "${runtime}" ]; then
  printf 'existing_llama_runtime=%s\n' "${runtime/#${HOME}/\$HOME}"
  file "${runtime}" 2>&1 || true
  ldd "${runtime}" 2>&1 | sed -n '1,200p'
else
  echo existing_llama_runtime=MISSING
fi

section python_runtime_discovery
python_cmd=
if command -v python3 >/dev/null 2>&1; then python_cmd=python3; elif command -v python >/dev/null 2>&1; then python_cmd=python; fi
if [ -n "${python_cmd}" ]; then
  "${python_cmd}" - <<'PY'
import importlib.util
import sys
print("python_version=" + sys.version.replace("\n", " "))
for name in ("torch", "tensorflow", "onnxruntime", "vllm", "transformers", "llama_cpp"):
    spec = importlib.util.find_spec(name)
    print(f"python_module_{name}=" + (spec.origin if spec else "MISSING"))
PY
fi

section complete
printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
