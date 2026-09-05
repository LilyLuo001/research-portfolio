#!/bin/bash -l

set -euo pipefail

echo "Gate 2 is disabled by the P1 data-contract checkpoint; no job may be launched."
exit 78
