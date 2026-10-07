#!/bin/bash
#SBATCH --job-name=linkup-gcc11-probe
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/gcc11-%j.out
#SBATCH --error=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/gcc11-%j.err
set -euo pipefail

BASE=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery
RPMS=${BASE}/toolchain_rpms
STAGE=${BASE}/toolchain_gcc11_payload_v2
KEY=${BASE}/keys/RPM-GPG-KEY-CentOS-SIG-SCLo
RPMDB=${BASE}/rpmdb
mkdir -p "${STAGE}"
test "$(sha256sum "${KEY}" | awk '{print $1}')" = 1402b1ea263cd0e51e7fe77c89ab98d64dd08fdc54e7a4afe27b2782ddfc351c
mkdir -p "${RPMDB}"
rpm --dbpath "${RPMDB}" --initdb
rpm --dbpath "${RPMDB}" --import "${KEY}"

verify() {
  expected=$1
  file=$2
  test "$(sha256sum "${file}" | awk '{print $1}')" = "${expected}"
  rpm --dbpath "${RPMDB}" -K "${file}"
}

verify ac350205a9316c777f842fa3451dc786ba9b058ca997776b73e4aa221908c84e "${RPMS}/devtoolset-11-runtime-11.1-2.el7.x86_64.rpm"
verify dde2f4b967e4a379caf1c38f756029799d610d8911f0c13b1f4f94a5d7a93561 "${RPMS}/devtoolset-11-binutils-2.36.1-1.el7.2.x86_64.rpm"
verify 7049c0fdcee4412cf0e2570e2ed90e4879019aa58b9c7d1112e85260ead0ec30 "${RPMS}/devtoolset-11-gcc-11.2.1-9.1.el7.x86_64.rpm"
verify adbf4b0743fa1227da7d93ef8236e20aa7ea5bda67965baadf782095bfee540f "${RPMS}/devtoolset-11-gcc-c++-11.2.1-9.1.el7.x86_64.rpm"
verify b42d3c7ff9f4da0f7fedd354051b002fe68dbb56dc59c713c61bdf92773b3d9c "${RPMS}/devtoolset-11-libstdc++-devel-11.2.1-9.1.el7.x86_64.rpm"

for rpm_file in \
  "${RPMS}/devtoolset-11-binutils-2.36.1-1.el7.2.x86_64.rpm" \
  "${RPMS}/devtoolset-11-gcc-11.2.1-9.1.el7.x86_64.rpm" \
  "${RPMS}/devtoolset-11-gcc-c++-11.2.1-9.1.el7.x86_64.rpm" \
  "${RPMS}/devtoolset-11-libstdc++-devel-11.2.1-9.1.el7.x86_64.rpm"; do
  (cd "${STAGE}" && rpm2cpio "${rpm_file}" | cpio -idmu --quiet)
done

TOOLROOT=${STAGE}/opt/rh/devtoolset-11/root/usr
export PATH=${TOOLROOT}/bin:${PATH}
export LD_LIBRARY_PATH=${TOOLROOT}/lib64:${TOOLROOT}/lib:${LD_LIBRARY_PATH:-}
unset CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH INCLUDE LIBRARY_PATH
printf 'gxx_path=%s\n' "$(command -v g++)"
g++ --version | sed -n '1p'

tmpdir=$(mktemp -d)
trap 'rm -rf "${tmpdir}"' EXIT
cat > "${tmpdir}/cxx17.cpp" <<'EOF'
#include <filesystem>
#include <iostream>
int main() { std::cout << std::filesystem::path("ok").string() << "\n"; }
EOF
g++ -std=c++17 "${tmpdir}/cxx17.cpp" -o "${tmpdir}/cxx17"
test "$("${tmpdir}/cxx17")" = ok
echo cxx17_filesystem=PASS
echo private_toolchain_bytes=$(du -sb "${STAGE}" | awk '{print $1}')
