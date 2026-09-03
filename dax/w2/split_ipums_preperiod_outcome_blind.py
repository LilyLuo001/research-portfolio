"""Create a pre-period IPUMS CSV without parsing rejected post outcomes.

The input is streamed as raw CSV records.  Only the prefix ending at MONTH is
decoded for every row.  A row is copied byte-for-byte only after YEAR/MONTH
establish that it is no later than 2022-11.  For later rows, fields after that
prefix are neither split, decoded, logged, nor written.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import pathlib
import tempfile
from collections import Counter
from datetime import datetime, timezone


PRE_END_CODE = 202211
PROTECTED_FIELDS = {
    "WTFINL", "EMPSTAT", "LABFORCE", "OCC", "OCC2010", "OCC1990",
    "CLASSWKR", "WKSTAT", "EARNWT", "HOURWAGE", "EARNWEEK",
    "TELWRKPAY", "TELWRKHR",
}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def open_input(path: pathlib.Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def parse_prefix(raw: bytes, field_count: int) -> list[bytes]:
    """Parse exactly ``field_count`` leading CSV fields and ignore the suffix."""
    if field_count < 1:
        raise ValueError("field_count must be positive")
    fields: list[bytes] = []
    value = bytearray()
    quoted = False
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte == 34:  # quote
            if quoted and index + 1 < len(raw) and raw[index + 1] == 34:
                value.append(34)
                index += 2
                continue
            quoted = not quoted
        elif byte == 44 and not quoted:  # comma
            fields.append(bytes(value))
            if len(fields) == field_count:
                return fields
            value.clear()
        elif byte in (10, 13) and not quoted:
            fields.append(bytes(value))
            if len(fields) >= field_count:
                return fields[:field_count]
            break
        else:
            value.append(byte)
        index += 1
    if quoted:
        raise ValueError("unterminated quote before MONTH prefix completed")
    if len(fields) < field_count:
        fields.append(bytes(value))
    if len(fields) < field_count:
        raise ValueError("record ended before MONTH prefix completed")
    return fields[:field_count]


def split_preperiod(
    source: pathlib.Path,
    output: pathlib.Path,
    receipt_path: pathlib.Path,
) -> dict[str, object]:
    if source.resolve() == output.resolve():
        raise ValueError("source and output must differ")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    source_sha = sha256_file(source)
    pre_counts: Counter[str] = Counter()
    rejected_counts: Counter[str] = Counter()
    pre_rows = rejected_rows = total_rows = 0
    temporary: pathlib.Path | None = None
    try:
        with open_input(source) as incoming:
            header = incoming.readline()
            if not header:
                raise ValueError("empty input")
            names = next(csv.reader([header.decode("utf-8-sig").rstrip("\r\n")]))
            if "YEAR" not in names or "MONTH" not in names:
                raise ValueError("header must contain YEAR and MONTH")
            year_index = names.index("YEAR")
            month_index = names.index("MONTH")
            prefix_count = max(year_index, month_index) + 1
            protected_indexes = [names.index(name) for name in PROTECTED_FIELDS if name in names]
            if protected_indexes and min(protected_indexes) < prefix_count:
                raise ValueError("protected outcome appears inside required date prefix")

            fd, temp_name = tempfile.mkstemp(
                prefix=output.name + ".", suffix=".tmp", dir=output.parent
            )
            os.close(fd)
            temporary = pathlib.Path(temp_name)
            # Compression follows the requested final output, not the .tmp suffix.
            outgoing = (
                gzip.GzipFile(filename=str(temporary), mode="wb", mtime=0)
                if output.suffix == ".gz"
                else temporary.open("wb")
            )
            with outgoing:
                outgoing.write(header)
                for line_number, raw in enumerate(incoming, start=2):
                    prefix = parse_prefix(raw, prefix_count)
                    try:
                        year = int(prefix[year_index])
                        month = int(prefix[month_index])
                    except ValueError as error:
                        raise ValueError(f"invalid date prefix at row {line_number}") from error
                    if month < 1 or month > 12:
                        raise ValueError(f"invalid MONTH at row {line_number}")
                    month_label = f"{year:04d}-{month:02d}"
                    total_rows += 1
                    if year * 100 + month <= PRE_END_CODE:
                        outgoing.write(raw)
                        pre_rows += 1
                        pre_counts[month_label] += 1
                    else:
                        # Deliberately do not decode, split, log, or write raw's suffix.
                        rejected_rows += 1
                        rejected_counts[month_label] += 1
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

    receipt = {
        "record_version": "ipums-outcome-blind-preperiod-split-v1",
        "status": "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_sha,
        "output_sha256": sha256_file(output),
        "cutoff_month": "2022-11",
        "rows_total": total_rows,
        "rows_written_preperiod": pre_rows,
        "rows_rejected_postperiod": rejected_rows,
        "preperiod_month_counts": dict(sorted(pre_counts.items())),
        "rejected_month_counts": dict(sorted(rejected_counts.items())),
        "date_fields_decoded_for_all_rows": ["YEAR", "MONTH"],
        "protected_fields_decoded_for_rejected_rows": False,
        "postperiod_rows_written": False,
        "postperiod_outcomes_printed": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = split_preperiod(args.source, args.output, args.receipt)
    print(json.dumps({
        "status": receipt["status"],
        "rows_written_preperiod": receipt["rows_written_preperiod"],
        "rows_rejected_postperiod": receipt["rows_rejected_postperiod"],
        "postperiod_outcomes_printed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
