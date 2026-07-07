.PHONY: plan digest brief reap leases init cron selfcheck ci
plan:    ; python ops/runner/runner.py --plan
selfcheck:; python ops/runner/selfcheck.py
ci:      ; python ops/runner/selfcheck.py && python ops/runner/runner.py --plan   # same gate CI runs
digest:  ; python ops/runner/runner.py --digest
reap:    ; python ops/runner/runner.py --reap
leases:  ; python ops/runner/lease.py list
brief:   ; python ops/runner/runner.py --brief $(T)
complete:; python ops/runner/runner.py --complete $(T)
gate:    ; python ops/runner/runner.py --gate $(T) $(V)
init:    ; git init -q && git add -A && git commit -q -m "portfolio bootstrap" && echo "repo initialized"
# add to crontab on your always-on box:
#   */30 * * * *  cd /path/repo && python ops/runner/runner.py --reap
#   0 21  * * *   cd /path/repo && python ops/runner/runner.py --digest   # evening digest
