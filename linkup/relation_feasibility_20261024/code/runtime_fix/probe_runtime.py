#!/usr/bin/env python3
"""Bounded, synthetic runtime qualification; no research inputs or model weights."""
import importlib
import json
import os
import platform
import sys
import traceback


def main():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("scheduled compute required")
    report = {
        "purpose": "Existing runtime imports and synthetic tensor execution only",
        "scheduler_job_id": os.environ["SLURM_JOB_ID"],
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "requested_resources": {"partition": "wzhdtest", "cpus": 2,
                                "memory": "4G", "dcu": 1, "time_limit": "00:05:00"},
        "actual_scheduler_environment": {
            name: os.environ.get(name) for name in (
                "SLURM_JOB_PARTITION", "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE",
                "SLURM_JOB_GPUS", "SLURM_STEP_GPUS", "HIP_VISIBLE_DEVICES",
                "CUDA_VISIBLE_DEVICES", "SLURM_JOB_NODELIST")},
        "packages": {}, "tensor": {},
        "new_software_installed": 0, "new_model_weights_downloaded": 0,
        "research_inputs_read": 0, "model_loading_training_inference": False,
    }
    for name in ("torch", "transformers", "tokenizers", "sentencepiece"):
        try:
            package = importlib.import_module(name)
            report["packages"][name] = {"importable": True,
                "version": getattr(package, "__version__", "unknown"),
                "file": getattr(package, "__file__", None)}
        except Exception as exc:
            report["packages"][name] = {"importable": False,
                "error_type": type(exc).__name__, "error": str(exc)[:1200]}
    if report["packages"]["torch"]["importable"]:
        import torch
        report["torch_backend"] = {"hip": getattr(torch.version, "hip", None),
                                   "cuda": getattr(torch.version, "cuda", None)}
        try:
            cpu = torch.tensor([[1., 2.], [3., 4.]])
            cpu_result = cpu @ cpu
            assert cpu_result.sum().item() == 54.0
            report["tensor"]["cpu"] = {"passed": True, "result_sum": 54.0}
            report["tensor"]["accelerator_available"] = bool(torch.cuda.is_available())
            report["tensor"]["accelerator_count"] = torch.cuda.device_count()
            if torch.cuda.is_available():
                device_tensor = cpu.to("cuda:0")
                result = device_tensor @ device_tensor
                torch.cuda.synchronize()
                assert torch.equal(result.cpu(), cpu_result)
                report["tensor"]["dcu"] = {"passed": True, "result_sum": result.sum().item(),
                    "device": str(result.device), "name": torch.cuda.get_device_name(0)}
        except Exception as exc:
            report["tensor"]["error"] = {"type": type(exc).__name__,
                "message": str(exc)[:1800], "traceback": traceback.format_exc()[-2500:]}
    report["runtime_qualified"] = (all(report["packages"][x]["importable"]
        for x in ("torch", "transformers", "tokenizers"))
        and report["tensor"].get("dcu", {}).get("passed", False))
    with open(sys.argv[1], "x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
