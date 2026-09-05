#!/bin/bash -l
#$ -N yax_rr2_pdf
#$ -pe omp 1
#$ -l h_rt=01:00:00
#$ -l mem_per_core=4G
#$ -j y
#$ -o /projectnb/econdept/qluo/yax-major-revision-20260905/pdf_build.log

set -euo pipefail
cd /projectnb/econdept/qluo/yax-major-revision-20260905/paper
mkdir -p build

build_with_bib() {
  local source="$1"
  local job="$2"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  bibtex "build/$job"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  ./scripts/check_latex_log.sh "build/$job.log"
}

build_without_bib() {
  local source="$1"
  local job="$2"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build -jobname="$job" "$source"
  ./scripts/check_latex_log.sh "build/$job.log"
}

build_with_bib main/working.tex YAX_WORKING_PAPER_MAJOR_REVISION
build_without_bib appendix/appendix.tex YAX_ONLINE_APPENDIX_MAJOR_REVISION
build_without_bib revision/referee_response.tex YAX_REFEREE_RESPONSE_MAJOR_REVISION
build_without_bib revision/revision_diagnosis.tex YAX_REVISION_DIAGNOSIS_MAJOR_REVISION
sha256sum \
  build/YAX_WORKING_PAPER_MAJOR_REVISION.pdf \
  build/YAX_ONLINE_APPENDIX_MAJOR_REVISION.pdf \
  build/YAX_REFEREE_RESPONSE_MAJOR_REVISION.pdf \
  build/YAX_REVISION_DIAGNOSIS_MAJOR_REVISION.pdf \
  > build/MAJOR_REVISION_PDF_SHA256.txt
