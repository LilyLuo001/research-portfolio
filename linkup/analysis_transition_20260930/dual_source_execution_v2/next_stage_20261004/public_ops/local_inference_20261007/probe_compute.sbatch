#!/bin/bash
#SBATCH --job-name=linkup-llm-probe
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/local-inference-probe-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/local-inference-probe-%j.err
set -euo pipefail

printf 'timestamp=%s\n' "$(date -Is)"
printf 'host=%s\n' "$(hostname)"
printf 'cpu_model='
awk -F: '/model name/{sub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo
printf 'cpu_count=%s\n' "$(nproc)"
printf 'memory_kb='
awk '/MemTotal/{print $2; exit}' /proc/meminfo
printf 'os='
sed -n 's/^PRETTY_NAME=//p' /etc/os-release | head -1
for executable in llama-cli llama-server cmake g++ gcc git curl wget sha256sum; do
  if command -v "${executable}" >/dev/null 2>&1; then
    printf '%s=%s\n' "${executable}" "$(command -v "${executable}")"
  else
    printf '%s=MISSING\n' "${executable}"
  fi
done
printf 'cmake_version='
cmake --version 2>/dev/null | head -1 || true
printf 'gxx_version='
g++ --version 2>/dev/null | head -1 || true
printf 'git_version='
git --version 2>/dev/null | head -1 || true
printf 'module_gcc_candidates='
source /etc/profile.d/modules.sh
module -t avail gcc 2>&1 | tr '\n' ',' || true
printf '\n'
for path in \
  "${HOME}/llama.cpp/build/bin/llama-cli" \
  "${HOME}/.cache/llama.cpp" \
  "${HOME}/.cache/huggingface/hub/models--Qwen--Qwen3-8B-GGUF"; do
  if [ -e "${path}" ]; then
    printf 'existing=%s\n' "${path}"
  fi
done
printf 'proxy_script=%s\n' "$(test -r "${HOME}/proxy.sh" && echo PRESENT || echo MISSING)"
