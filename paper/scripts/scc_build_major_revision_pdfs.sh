#!/bin/bash -l
#$ -N yax_r3_pdf
#$ -pe omp 1
#$ -l h_rt=01:00:00
#$ -l mem_per_core=4G
#$ -j y
#$ -o yax_r3_pdf.log

set -euo pipefail
repo_root="${YAX_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "${repo_root}/paper"
mkdir -p build
git diff --no-ext-diff --no-color 6b8d85e -- main appendix tables revision > revision/source_diff.txt

build_with_bib() {
  local source="$1"
  local job="$2"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  bibtex "build/$job"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  ./scripts/check_latex_log.sh "build/$job.log"
}

build_without_bib() {
  local source="$1"
  local job="$2"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  ./scripts/check_latex_log.sh "build/$job.log"
}

build_with_bib main/working.tex YAX_REVISED_MANUSCRIPT
build_without_bib appendix/appendix.tex YAX_FOCUSED_ONLINE_APPENDIX
build_without_bib revision/referee_response.tex YAX_REFEREE_RESPONSE
build_without_bib revision/revision_diagnosis.tex YAX_REVISION_DIAGNOSIS
build_without_bib revision/source_diff.tex YAX_SOURCE_DIFF
sha256sum \
  build/YAX_REVISED_MANUSCRIPT.pdf \
  build/YAX_FOCUSED_ONLINE_APPENDIX.pdf \
  build/YAX_REFEREE_RESPONSE.pdf \
  build/YAX_REVISION_DIAGNOSIS.pdf \
  build/YAX_SOURCE_DIFF.pdf \
  > build/SUBSTANTIVE_REVISION_PDF_SHA256.txt
