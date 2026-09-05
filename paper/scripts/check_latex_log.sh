#!/usr/bin/env bash
set -euo pipefail
log="${1:?usage: check_latex_log.sh LOG}"
test -s "$log"
if grep -Eiq 'undefined references|citation.+undefined|undefined citations|multiply defined|LaTeX Error|Package .* Error|File .* not found|There were undefined references' "$log"; then
  grep -Ein 'undefined references|citation.+undefined|undefined citations|multiply defined|LaTeX Error|Package .* Error|File .* not found|There were undefined references' "$log"
  exit 1
fi
if grep -Eq 'Overfull \\[hv]box' "$log"; then
  grep -En 'Overfull \\[hv]box' "$log"
  exit 1
fi
