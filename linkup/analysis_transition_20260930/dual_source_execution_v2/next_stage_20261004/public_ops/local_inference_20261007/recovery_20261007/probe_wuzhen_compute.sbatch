#!/bin/bash
#SBATCH --job-name=linkup-llm-wz-probe
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/probe-%j.out
#SBATCH --error=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/probe-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u

printf 'timestamp=%s\n' "$(date -Is)"
printf 'host=%s\n' "$(hostname)"
printf 'cpu_model='
awk -F: '/model name/{sub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo
printf 'glibc='
ldd --version 2>&1 | sed -n '1p'
for executable in llama-cli cmake g++ gcc git curl sha256sum python python3; do
  if command -v "${executable}" >/dev/null 2>&1; then
    printf '%s=%s\n' "${executable}" "$(command -v "${executable}")"
  else
    printf '%s=MISSING\n' "${executable}"
  fi
done
printf 'cmake_version='
cmake --version 2>/dev/null | sed -n '1p' || true
printf 'gxx_version='
g++ --version 2>/dev/null | sed -n '1p' || true
printf 'toolsets='
find /opt/rh -maxdepth 2 -type f -name enable -path '*/devtoolset-*/*' -printf '%h,' 2>/dev/null | sort || true
printf '\n'
printf 'module_candidates='
module -t avail gcc cmake 2>&1 | tr '\n' ',' || true
printf '\n'

tmpdir=$(mktemp -d)
trap 'rm -rf "${tmpdir}"' EXIT
cat > "${tmpdir}/cxx17.cpp" <<'EOF'
#include <filesystem>
#include <iostream>
int main() { std::cout << std::filesystem::path("ok").string() << "\n"; }
EOF
if g++ -std=c++17 "${tmpdir}/cxx17.cpp" -lstdc++fs -o "${tmpdir}/cxx17" >/dev/null 2>&1 && [ "$("${tmpdir}/cxx17")" = ok ]; then
  echo cxx17_filesystem=PASS
else
  echo cxx17_filesystem=FAIL
fi

source "${HOME}/proxy.sh"
for item in \
  'cmake_sha|https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-SHA-256.txt' \
  'llama_source|https://github.com/ggml-org/llama.cpp/archive/42b021b4dc42be573f1e1463528532fc8294c650.tar.gz' \
  'model_api|https://huggingface.co/api/models/Qwen/Qwen3-8B-GGUF/revision/main'; do
  label=${item%%|*}
  url=${item#*|}
  status=$(curl -L -sS --connect-timeout 15 --max-time 45 -o /dev/null -w '%{http_code}' "${url}" || true)
  printf 'network_%s_http=%s\n' "${label}" "${status}"
done
