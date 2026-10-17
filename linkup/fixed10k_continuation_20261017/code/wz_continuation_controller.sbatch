#!/bin/bash
# DEPRECATED: this process only checks readiness, submits sbatch work, and polls
# sacct. Use the single login-node nohup coordinator to avoid idle DCU use.
echo "deprecated: run continuation_controller.py as the single login-node nohup coordinator" >&2
exit 2
