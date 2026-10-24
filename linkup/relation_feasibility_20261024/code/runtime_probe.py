#!/usr/bin/env python3
"""Record one installed runtime in scheduled compute; no installs or inference."""
import importlib
import json
import os
import platform
import sys
from pathlib import Path


def main():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("scheduled SCNet execution required")
    packages = {}
    for name in ("torch", "transformers", "tokenizers", "sentencepiece"):
        try:
            package = importlib.import_module(name)
            packages[name] = {"importable": True, "version": getattr(package, "__version__", "unknown")}
        except Exception as error:
            packages[name] = {"importable": False, "error_type": type(error).__name__, "error": str(error)[:500]}
    accelerator = {}
    if packages["torch"]["importable"]:
        import torch
        accelerator = {"hip_version": getattr(torch.version, "hip", None),
                       "cuda_version": getattr(torch.version, "cuda", None)}
        try:
            accelerator.update(available=bool(torch.cuda.is_available()), count=torch.cuda.device_count())
        except Exception as error:
            accelerator.update(error_type=type(error).__name__, error=str(error)[:500])
    report = {"scheduler_job_id": os.environ["SLURM_JOB_ID"], "python": platform.python_version(),
              "packages": packages, "accelerator": accelerator,
              "purpose": "One existing module availability probe; not model loading, training or throughput evidence"}
    with Path(sys.argv[1]).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
