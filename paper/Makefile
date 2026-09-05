LATEXMK := latexmk
FLAGS := -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build

# Pin PDF metadata so clean builds are byte-for-byte reproducible.
export SOURCE_DATE_EPOCH := 1788577652
export FORCE_SOURCE_DATE := 1
export TZ := UTC

.PHONY: restat working appendix cover all clean check

restat:
	$(LATEXMK) $(FLAGS) -jobname=YAX_RESTAT_SUBMISSION main/restat.tex
	@./scripts/check_latex_log.sh build/YAX_RESTAT_SUBMISSION.log

working:
	$(LATEXMK) $(FLAGS) -jobname=YAX_WORKING_PAPER main/working.tex
	@./scripts/check_latex_log.sh build/YAX_WORKING_PAPER.log

appendix:
	$(LATEXMK) $(FLAGS) -jobname=YAX_ONLINE_APPENDIX appendix/appendix.tex
	@./scripts/check_latex_log.sh build/YAX_ONLINE_APPENDIX.log

cover:
	$(LATEXMK) $(FLAGS) -jobname=YAX_RESTAT_COVER_LETTER submission/cover_letter_restat.tex
	@./scripts/check_latex_log.sh build/YAX_RESTAT_COVER_LETTER.log

all: restat working appendix cover

check:
	@for log in build/*.log; do ./scripts/check_latex_log.sh "$$log"; done

clean:
	$(LATEXMK) -C -outdir=build main/restat.tex main/working.tex appendix/appendix.tex submission/cover_letter_restat.tex
	@find build -type f ! -name '.gitkeep' -delete
