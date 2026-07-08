.PHONY: plan digest brief reap leases init cron selfcheck ci smoke replicate decisions fail
plan:    ; python ops/runner/runner.py --plan
selfcheck:; python ops/runner/selfcheck.py
ci:      ; python ops/runner/selfcheck.py && python ops/runner/runner.py --plan   # same gate CI runs
smoke:   ; python ops/runner/dispatch.py --smoke                                  # L1 overnight-layer self-test (SH-l1-smoke)
replicate:; python ops/runner/selfcheck.py && python -m pytest -q && python ops/runner/dispatch.py --smoke  # weekly portfolio-wide replay (arch §5 / DAX-W11 pattern)
digest:  ; python ops/runner/runner.py --digest
decisions:; python ops/runner/runner.py --apply-decisions
reap:    ; python ops/runner/runner.py --reap
leases:  ; python ops/runner/lease.py list
brief:   ; python ops/runner/runner.py --brief $(T)
complete:; python ops/runner/runner.py --complete $(T)
fail:    ; python ops/runner/runner.py --fail $(T)
gate:    ; python ops/runner/runner.py --gate $(T) $(V)
init:    ; git init -q && git add -A && git commit -q -m "portfolio bootstrap" && echo "repo initialized"
# add to crontab on your always-on box:
#   */30 * * * *  cd /path/repo && python ops/runner/runner.py --reap
#   0 21  * * *   cd /path/repo && python ops/runner/runner.py --digest   # evening digest
