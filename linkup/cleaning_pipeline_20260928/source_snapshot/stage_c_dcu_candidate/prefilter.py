"""Conservative DCU prefilter for the frozen enrichment technology scans.

The accelerator returns only a superset mask.  Python ``re`` remains the
authority for matching, boundaries, offsets, ordering, and output values.
"""
from __future__ import annotations

import hashlib
import importlib.util
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Sequence

ENRICHMENT_SHA256 = "cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6"
V6_SHA256 = "d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744"
MAGIC = b"DCUMASK1"

# One or more necessary ASCII substrings for each frozen _TECH_PATTERNS entry.
# Matching is deliberately ASCII-case-insensitive and ignores word boundaries,
# so it can produce false positives but cannot reject a true ASCII match.
ANCHORS: Sequence[Sequence[bytes]] = (
    (b"large language model",),
    (b"llm",),
    (b"generative ai",),
    (b"chatgpt", b"gpt"),
    (b"machine learning",),
    (b"deep learning",),
    (b"neural network",),
    (b"predictive model",),
    (b"computer vision",),
    (b"natural language processing", b"nlp"),
    (b"artificial intelligence", b"ai"),
    (b"microsoft office", b"ms office"),
    (b"excel",),
    (b"power bi",),
    (b"tableau",),
    (b"salesforce",),
    (b"sap",),
    (b"python",),
    (b"sql",),
    (b"java",),
)
SOFTWARE_BIT = len(ANCHORS)
AI_BIT = SOFTWARE_BIT + 1
ALL_MASK = (1 << (AI_BIT + 1)) - 1

# Necessary literals for every frozen V5 software/AI pattern. The exceptional
# one-letter R and AI patterns use conservative ASCII boundary predicates.
SOFTWARE_ANCHORS = (
    b"office", b"excel", b"power", b"word", b"access", b"sheets",
    b"sql", b"tableau", b"sas", b"spss", b"stata", b"python", b"java",
    b"javascript", b"typescript", b"c++", b"c#", b".net", b"ruby", b"go",
    b"matlab", b"salesforce", b"sap", b"oracle", b"workday", b"servicenow",
    b"slack", b"teams", b"zoom", b"jira", b"confluence", b"asana", b"trello",
    b"github", b"gitlab",
)
AI_ANCHORS = (
    b"artificial", b"machine", b"generative", b"chatgpt", b"openai", b"gpt",
    b"claude", b"gemini", b"copilot", b"dall", b"midjourney",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_frozen_enrichment(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ENRICHMENT_SHA256:
        raise RuntimeError("frozen enrichment SHA-256 mismatch: %s" % digest)
    module = load_module(path, "frozen_enrichment_dcu_candidate")
    if len(module._TECH_PATTERNS) != len(ANCHORS):
        raise RuntimeError("anchor table does not match frozen technology patterns")
    return module


def load_frozen_v6(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != V6_SHA256:
        raise RuntimeError("frozen V6 SHA-256 mismatch: %s" % digest)
    return load_module(path, "frozen_v6_dcu_candidate")


def _ascii_word(byte: int) -> bool:
    return 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122 or byte == 95


def _standalone_upper(raw: bytes, token: bytes) -> bool:
    start = 0
    while True:
        found = raw.find(token, start)
        if found < 0:
            return False
        end = found + len(token)
        if (found == 0 or not _ascii_word(raw[found - 1])) and (end == len(raw) or not _ascii_word(raw[end])):
            return True
        start = found + 1


def cpu_mask(text: str) -> int:
    """Exact oracle for the HIP prefilter, not for the authoritative regexes."""
    raw = text.encode("utf-8")
    if any(byte >= 128 for byte in raw):
        return ALL_MASK
    folded = raw.lower()
    mask = 0
    for index, alternatives in enumerate(ANCHORS):
        if any(anchor in folded for anchor in alternatives):
            mask |= 1 << index
    if any(anchor in folded for anchor in SOFTWARE_ANCHORS) or _standalone_upper(raw, b"R"):
        mask |= 1 << SOFTWARE_BIT
    if any(anchor in folded for anchor in AI_ANCHORS) or _standalone_upper(raw, b"AI"):
        mask |= 1 << AI_BIT
    return mask


def cpu_masks(texts: Iterable[str]) -> List[int]:
    return [cpu_mask(text) for text in texts]


def _write_input(path: Path, texts: Sequence[str]) -> None:
    encoded = [text.encode("utf-8") for text in texts]
    offsets = [0]
    for value in encoded:
        offsets.append(offsets[-1] + len(value))
    with path.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(struct.pack("<I", len(texts)))
        handle.write(struct.pack("<%dQ" % len(offsets), *offsets))
        for value in encoded:
            handle.write(value)


def _read_output(path: Path, expected: int) -> List[int]:
    raw = path.read_bytes()
    header = len(MAGIC) + 4
    if len(raw) < header or raw[:len(MAGIC)] != MAGIC:
        raise RuntimeError("invalid DCU mask output")
    count = struct.unpack_from("<I", raw, len(MAGIC))[0]
    if count != expected or len(raw) != header + 4 * count:
        raise RuntimeError("DCU mask output count/size mismatch")
    return list(struct.unpack_from("<%dI" % count, raw, header))


def gpu_masks(texts: Sequence[str], executable: Path) -> List[int]:
    """Run one batched HIP invocation; the executable performs no regex logic."""
    with tempfile.TemporaryDirectory(prefix="linkup-dcu-mask.") as temp:
        input_path = Path(temp) / "input.bin"
        output_path = Path(temp) / "output.bin"
        _write_input(input_path, texts)
        subprocess.run([str(executable), str(input_path), str(output_path)], check=True)
        masks = _read_output(output_path, len(texts))
    invalid = [value for value in masks if value & ~ALL_MASK]
    if invalid:
        raise RuntimeError("DCU returned unknown mask bits")
    return masks


def enrich_with_mask(enrichment, payload: dict, mask: int) -> dict:
    """Call unchanged frozen regexes after removing provably irrelevant families.

    This temporarily narrows a module global and is intended for one call at a
    time inside an existing process worker.  It is not thread safe.
    """
    original = enrichment._TECH_PATTERNS
    enrichment._TECH_PATTERNS = tuple(
        entry for index, entry in enumerate(original) if mask & (1 << index)
    )
    try:
        return enrichment.enrich(payload)
    finally:
        enrichment._TECH_PATTERNS = original
