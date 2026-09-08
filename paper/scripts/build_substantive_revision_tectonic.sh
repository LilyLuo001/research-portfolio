#!/usr/bin/env bash
set -euo pipefail

repo_root="${YAX_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "${repo_root}/paper"
mkdir -p build

# Tectonic resolves stdin inputs from the working directory, matching the
# paper's root-relative \input contract. A fresh generic job is used for every
# document so auxiliary files cannot leak across outputs.
build_one() {
  local source="$1"
  local job="$2"
  rm -f \
    build/texput.aux build/texput.bbl build/texput.blg \
    build/texput.log build/texput.out build/texput.pdf
  tectonic -X compile - --outdir build --keep-logs --keep-intermediates < "${source}"
  mv build/texput.pdf "build/${job}.pdf"
  mv build/texput.log "build/${job}.log"
  ./scripts/check_latex_log.sh "build/${job}.log"
}

git diff --no-ext-diff --no-color 6b8d85e -- \
  main appendix tables revision \
  ':(exclude)revision/source_diff.txt' \
  | sed -E 's/[[:space:]]+$//' \
  > revision/source_diff.txt

build_one main/working.tex YAX_REVISED_MANUSCRIPT
build_one appendix/appendix.tex YAX_FOCUSED_ONLINE_APPENDIX
build_one revision/referee_response.tex YAX_REFEREE_RESPONSE
build_one revision/revision_diagnosis.tex YAX_REVISION_DIAGNOSIS
build_one revision/source_diff.tex YAX_SOURCE_DIFF

shasum -a 256 \
  build/YAX_REVISED_MANUSCRIPT.pdf \
  build/YAX_FOCUSED_ONLINE_APPENDIX.pdf \
  build/YAX_REFEREE_RESPONSE.pdf \
  build/YAX_REVISION_DIAGNOSIS.pdf \
  build/YAX_SOURCE_DIFF.pdf \
  > build/SUBSTANTIVE_REVISION_PDF_SHA256.txt
