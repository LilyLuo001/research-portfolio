#!/usr/bin/env python3
"""Build pre-existing computerization measures on Census 2010 and 2018 support.

This is measurement-only code.  It never reads person-level CPS records or
post-ChatGPT outcomes.  The supported routes are fixed in RESEARCH_PLAN_v4:

* Webb ``pct_software`` and Autor-Dorn RTI use the direct Census-2010 to
  ``occ1990dd`` bridge.
* O*NET 24.3 element ``4.A.3.b.1`` (official label: *Interacting With
  Computers*) and Frey-Osborne probabilities begin on SOC 2010, are repaired
  to SOC 2018 with the official BLS crosswalk, collapsed to Census 2018 using
  OEWS employment weights, and then bridged to Census 2010 without
  renormalizing around missing components.

The module is stdlib-only.  Source Stata files are converted to CSV outside
the repository; their original hashes are still pinned in the receipt.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import subprocess
import zipfile
from collections import defaultdict
from xml.etree import ElementTree as ET


ONET_ELEMENT = "4.A.3.b.1"
ONET_OFFICIAL_LABEL = "Interacting With Computers"
MEASURES = (
    "webb_pct_software",
    "onet_computers_importance",
    "onet_computers_level",
    "rti_autor_dorn",
    "frey_osborne_probability",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def number(value):
    text = "" if value is None else str(value).strip()
    return None if not text else float(text)


def read_csv(path: pathlib.Path, required=()):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    fields = set(rows[0]) if rows else set()
    missing = set(required) - fields
    if missing:
        raise ValueError(f"{path.name} missing fields {sorted(missing)}")
    return rows


def _xlsx_shared_strings(archive: zipfile.ZipFile):
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    return ["".join(node.text or "" for node in item.iter(ns + "t"))
            for item in root.findall(ns + "si")]


def xlsx_rows(path: pathlib.Path, sheet_name: str):
    """Read values from one XLSX sheet without openpyxl."""
    main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    pkgns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rid = None
        for sheet in workbook.find(main + "sheets"):
            if sheet.attrib.get("name") == sheet_name:
                rid = sheet.attrib[relns + "id"]
                break
        if rid is None:
            raise ValueError(f"sheet {sheet_name!r} absent from {path.name}")
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = None
        for rel in rels.findall(pkgns + "Relationship"):
            if rel.attrib.get("Id") == rid:
                target = rel.attrib["Target"]
                break
        if target is None:
            raise ValueError(f"relationship for sheet {sheet_name!r} absent")
        member = target.lstrip("/")
        if not member.startswith("xl/"):
            member = "xl/" + member
        shared = _xlsx_shared_strings(archive)
        root = ET.fromstring(archive.read(member))
        result = []
        for row in root.iter(main + "row"):
            cells = {}
            for cell in row.findall(main + "c"):
                ref = cell.attrib.get("r", "A1")
                letters = re.match(r"[A-Z]+", ref).group(0)
                column = 0
                for char in letters:
                    column = column * 26 + ord(char) - 64
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    value = "".join(n.text or "" for n in cell.iter(main + "t"))
                else:
                    node = cell.find(main + "v")
                    value = "" if node is None else node.text or ""
                    if kind == "s" and value:
                        value = shared[int(value)]
                cells[column - 1] = value
            if cells:
                width = max(cells) + 1
                result.append([cells.get(i, "") for i in range(width)])
        return result


def read_bls_soc_crosswalk(path: pathlib.Path):
    rows = xlsx_rows(path, "Sorted by 2010")
    header = ["2010 SOC Code", "2010 SOC Title", "2018 SOC Code", "2018 SOC Title"]
    start = None
    for i, row in enumerate(rows):
        if [str(v).strip() for v in row[:4]] == header:
            start = i + 1
            break
    if start is None:
        raise ValueError("BLS SOC crosswalk header not found")
    result = []
    for row in rows[start:]:
        values = [str(v).strip() for v in (row + ["", "", "", ""])[:4]]
        if values[0] and values[2]:
            result.append({"soc_2010": values[0], "soc_2018": values[2],
                           "soc_2018_title": values[3]})
    if not result:
        raise ValueError("BLS SOC crosswalk has no data rows")
    return result


def read_census_conversion(path: pathlib.Path):
    """Read the official Census 2010-to-2018 occupation conversion table.

    Continuation rows leave the 2010 code and title blank, so those values must
    be carried forward.  The conversion rate is P(2018 code | 2010 code); it is
    used to identify routes, not inverted into an unsupported target weight.
    """
    rows = xlsx_rows(path, "E1 Total")
    start = None
    for i, row in enumerate(rows):
        if [str(v).strip() for v in (row + [""] * 5)[:5]] == [
                "2010 Code", "2010 Occupation title", "2018 Code",
                "2018 Occupation title", "Conversion Rate"]:
            start = i + 1
            break
    if start is None:
        raise ValueError("Census occupation conversion header not found")
    result = []
    old_code = old_title = ""
    for raw in rows[start:]:
        values = [str(v).strip() for v in (raw + [""] * 5)[:5]]
        if values[0]:
            old_code, old_title = values[0].zfill(4), values[1]
        if old_code and values[2]:
            result.append({
                "census_2010": old_code,
                "census_2010_title": old_title,
                "census_2018": values[2].zfill(4),
                "census_2018_title": values[3],
                "conversion_rate": float(values[4]),
            })
    if not result:
        raise ValueError("Census occupation conversion has no routes")
    return result


def read_census_code_titles(path, sheet_name):
    """Read a complete official Census occupation code list."""
    result = {}
    for row in xlsx_rows(path, sheet_name):
        values = [str(v).strip() for v in (row + ["", "", "", ""])[:4]]
        title, code = values[1], values[2]
        if re.fullmatch(r"\d{4}", code) and title:
            result[code] = title
    if len(result) < 500:
        raise ValueError(f"{sheet_name!r} yielded only {len(result)} titles")
    return result


def parse_onet24(path: pathlib.Path):
    with zipfile.ZipFile(path) as archive:
        member = "db_24_3_text/Work Activities.txt"
        with archive.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"),
                                    delimiter="\t")
            rows = [row for row in reader if row["Element ID"] == ONET_ELEMENT]
    labels = {row["Element Name"] for row in rows}
    if labels != {ONET_OFFICIAL_LABEL}:
        raise ValueError(f"unexpected O*NET label(s) for {ONET_ELEMENT}: {labels}")
    by_soc = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["Scale ID"] in {"IM", "LV"}:
            by_soc[row["O*NET-SOC Code"][:7]][row["Scale ID"]].append(row)
    result = {}
    rules = defaultdict(int)
    for soc, scales in by_soc.items():
        out = {}
        for scale, name in (("IM", "onet_computers_importance"),
                            ("LV", "onet_computers_level")):
            candidates = scales.get(scale, [])
            base = [row for row in candidates if row["O*NET-SOC Code"].endswith(".00")]
            chosen = base if base else candidates
            rule = "published_base_00" if base else "equal_mean_detail_children"
            rules[f"{scale}:{rule}"] += 1
            out[name] = (sum(float(row["Data Value"]) for row in chosen) / len(chosen)
                         if chosen else None)
        result[soc] = out
    return result, dict(sorted(rules.items())), len(rows)


FREY_LINE = re.compile(
    r"^\s*(\d+)\.\s+([01](?:\.\d+)?)\s+(?:(0|1)\s+)?"
    r"(\d{2}-\d{4})\s+(.+?)\s*$"
)


def parse_frey_text(text: str):
    rows = []
    for line in text.splitlines():
        match = FREY_LINE.match(line)
        if match and 1 <= int(match.group(1)) <= 702:
            rank, probability, label, soc, title = match.groups()
            rows.append({"rank": int(rank), "soc_2010": soc,
                         "frey_osborne_probability": float(probability),
                         "training_label": label or "", "occupation": title})
    if len(rows) != 702 or len({row["rank"] for row in rows}) != 702:
        raise ValueError(f"expected 702 Frey-Osborne appendix rows, got {len(rows)}")
    if len({row["soc_2010"] for row in rows}) != 702:
        raise ValueError("duplicate Frey-Osborne SOC code")
    return rows


def parse_frey_pdf(path: pathlib.Path):
    run = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         check=True, capture_output=True, text=True)
    return parse_frey_text(run.stdout)


def harmonize_soc2010(source, crosswalk, fields):
    targets = defaultdict(list)
    old_targets = defaultdict(set)
    titles = {}
    for route in crosswalk:
        old, new = route["soc_2010"], route["soc_2018"]
        old_targets[old].add(new)
        titles.setdefault(new, route["soc_2018_title"])
        if old in source:
            targets[new].append(old)
    result = {}
    statuses = defaultdict(int)
    for new, old_codes_raw in sorted(targets.items()):
        old_codes = sorted(set(old_codes_raw))
        row = {"soc_2018": new, "soc_2018_title": titles.get(new, ""),
               "source_soc_2010_codes": "|".join(old_codes)}
        if len(old_codes) == 1:
            old = old_codes[0]
            status = ("direct_or_recoded_single_source" if len(old_targets[old]) == 1
                      else "split_inherited_from_2010_parent")
            for field in fields:
                row[field] = source[old].get(field)
        else:
            equal = True
            for field in fields:
                values = [source[old].get(field) for old in old_codes]
                if any(value is None for value in values) or any(
                        abs(values[0] - value) > 1e-12 for value in values[1:]):
                    equal = False
            status = "merge_equal_source_scores" if equal else "merge_ambiguous_fail_closed"
            for field in fields:
                row[field] = source[old_codes[0]].get(field) if equal else None
        row["harmonization_status"] = status
        statuses[status] += 1
        result[new] = row
    mapped = {old for values in targets.values() for old in values}
    diagnostic = {
        "n_source_codes": len(source), "n_source_codes_mapped": len(mapped),
        "unmapped_source_codes": sorted(set(source) - mapped),
        "n_soc2018_rows": len(result), "status_counts": dict(sorted(statuses.items())),
    }
    return result, diagnostic


def match_soc_pattern(pattern, available):
    if pattern in available:
        return [pattern]
    if "X" in pattern:
        expression = "^" + re.escape(pattern).replace("X", r"\d") + "$"
    elif re.fullmatch(r"\d{2}-0000", pattern):
        expression = "^" + re.escape(pattern[:3]) + r"\d{4}$"
    elif re.fullmatch(r"\d{2}-\d{2}00", pattern):
        expression = "^" + re.escape(pattern[:-2]) + r"\d{2}$"
    elif re.fullmatch(r"\d{2}-\d{3}0", pattern):
        expression = "^" + re.escape(pattern[:-1]) + r"\d$"
    else:
        return []
    return sorted(code for code in available if re.fullmatch(expression, code))


def read_oews2021(path: pathlib.Path):
    rows = read_csv(path, {"vintage", "occ_code", "occupation_group", "total_employment"})
    result = {}
    for row in rows:
        if row["vintage"] == "2021" and row["occupation_group"] == "detailed":
            value = number(row["total_employment"])
            if value and value > 0:
                result[row["occ_code"].strip()] = value
    return result


def collapse_soc2018_to_census(soc_rows, bridge_rows, oews, fields):
    patterns = {}
    for row in bridge_rows:
        code, pattern = row["census_2018"].zfill(4), row["soc_2018_pattern"].strip()
        prior = patterns.setdefault(code, pattern)
        if prior != pattern:
            raise ValueError(f"conflicting SOC patterns for Census 2018 {code}")
    available = set(soc_rows)
    result = {}
    for code, pattern in sorted(patterns.items()):
        hits = match_soc_pattern(pattern, available)
        if hits and all(soc in oews for soc in hits):
            total = sum(oews[soc] for soc in hits)
            weights = {soc: oews[soc] / total for soc in hits}
            basis = "oews_2021_employment"
        elif hits:
            weights = {soc: 1.0 / len(hits) for soc in hits}
            basis = "equal_missing_oews_employment"
        else:
            weights, basis = {}, "no_matching_soc2018"
        out = {"census_2018": code, "soc_2018_pattern": pattern,
               "soc_component_count": len(hits), "soc_weight_basis": basis}
        for field in fields:
            covered = sum(weight for soc, weight in weights.items()
                          if soc_rows[soc].get(field) is not None)
            partial = sum(weight * soc_rows[soc][field] for soc, weight in weights.items()
                          if soc_rows[soc].get(field) is not None)
            out[field] = partial if abs(covered - 1.0) <= 1e-9 else None
            out[field + "_covered_weight"] = covered
            out[field + "_partial_sum"] = partial if covered > 0 else None
        result[code] = out
    return result


def bridge_census2010(bridge_rows, census_rows, fields):
    routes = defaultdict(list)
    for row in bridge_rows:
        routes[row["census_2010"].zfill(4)].append(row)
    result = {}
    for old, old_routes in sorted(routes.items()):
        major_groups = sorted({row["soc_2018_pattern"].strip()[:2]
                               for row in old_routes
                               if re.match(r"^\d{2}-", row["soc_2018_pattern"].strip())})
        out = {"cps_occ2010": old,
               "soc_major_group": major_groups[0] if len(major_groups) == 1 else "mixed"}
        for field in fields:
            covered = 0.0
            partial = 0.0
            for route in old_routes:
                weight = float(route["bridge_weight"])
                target = census_rows.get(route["census_2018"].zfill(4), {})
                target_covered = target.get(field + "_covered_weight", 0.0)
                target_partial = target.get(field + "_partial_sum")
                covered += weight * target_covered
                if target_partial is not None:
                    partial += weight * target_partial
            out[field] = partial if abs(covered - 1.0) <= 1e-9 else None
            out[field + "_covered_route_mass"] = covered
            out[field + "_partial_sum"] = partial if covered > 0 else None
        result[old] = out
    return result


def direct_dorn_rows(crosswalk_rows, webb_rows, task_rows):
    webb = {int(row["occ1990dd"]): row for row in webb_rows}
    task = {int(row["occ1990dd"]): row for row in task_rows}
    result = {}
    for route in crosswalk_rows:
        cps, occ = str(int(float(route["occ"]))).zfill(4), int(float(route["occ1990dd"]))
        if cps in result:
            raise ValueError(f"duplicate direct Dorn route for CPS {cps}")
        w, t = webb.get(occ), task.get(occ)
        routine = number(t.get("task_routine")) if t else None
        manual = number(t.get("task_manual")) if t else None
        abstract = number(t.get("task_abstract")) if t else None
        rti = (math.log(routine) - math.log(manual) - math.log(abstract)
               if routine and manual and abstract else None)
        result[cps] = {
            "cps_occ2010": cps, "occ1990dd": str(occ),
            "occupation": (w or {}).get("occ1990dd_title", ""),
            "webb_pct_software": number((w or {}).get("pct_software")),
            "rti_autor_dorn": rti,
        }
    return result


def direct_to_census2018(direct, bridge_rows, fields):
    """Carry Census-2010 Webb/RTI scores to Census 2018 without guess-filling.

    Splits inherit their single source score.  A target receiving multiple
    Census-2010 sources is scored only when every source is observed and the
    source scores agree.  The published conversion rates run in the opposite
    conditional direction and therefore cannot identify target weights.
    """
    routes = defaultdict(set)
    patterns = {}
    for route in bridge_rows:
        old = route["census_2010"].zfill(4)
        new = route["census_2018"].zfill(4)
        routes[new].add(old)
        patterns.setdefault(new, route["soc_2018_pattern"].strip())
    result = {}
    for new, sources_raw in sorted(routes.items()):
        sources = sorted(sources_raw)
        out = {
            "census2018": new,
            "soc_major_group": patterns.get(new, "")[:2],
            "source_census2010_codes": "|".join(sources),
        }
        for field in fields:
            values = [direct.get(old, {}).get(field) for old in sources]
            complete = values and all(value is not None for value in values)
            equal = complete and all(abs(values[0] - value) <= 1e-12
                                     for value in values[1:])
            out[field] = values[0] if equal else None
            if not complete:
                status = "missing_source_fail_closed"
            elif len(sources) == 1:
                status = "single_source_inherited"
            elif equal:
                status = "merge_equal_source_scores"
            else:
                status = "merge_ambiguous_fail_closed"
            out[field + "_harmonization"] = status
        result[new] = out
    return result


def build(args):
    bridge = read_csv(args.cps_bridge, {"census_2010", "census_2018",
                                       "soc_2018_pattern", "bridge_weight"})
    bls = read_bls_soc_crosswalk(args.bls_soc_crosswalk)
    census_conversion = read_census_conversion(args.census_conversion)
    title2010 = read_census_code_titles(
        args.census2010_code_list, "2010OccCodeList")
    title2018 = read_census_code_titles(
        args.census2018_code_list, "2018 Census Occ Code List")
    onet10, onet_rules, onet_rows = parse_onet24(args.onet24)
    frey_source_rows = parse_frey_pdf(args.frey_pdf)
    frey10 = {row["soc_2010"]: row for row in frey_source_rows}
    onet18, onet_diag = harmonize_soc2010(
        onet10, bls, ("onet_computers_importance", "onet_computers_level"))
    frey18, frey_diag = harmonize_soc2010(
        frey10, bls, ("frey_osborne_probability",))
    combined18 = {}
    for code in sorted(set(onet18) | set(frey18)):
        combined18[code] = {**onet18.get(code, {}), **frey18.get(code, {})}
    indirect_fields = ("onet_computers_importance", "onet_computers_level",
                       "frey_osborne_probability")
    census18 = collapse_soc2018_to_census(
        combined18, bridge, read_oews2021(args.oews), indirect_fields)
    indirect = bridge_census2010(bridge, census18, indirect_fields)
    direct = direct_dorn_rows(
        read_csv(args.dorn_crosswalk_csv, {"occ", "occ1990dd"}),
        read_csv(args.webb, {"occ1990dd", "occ1990dd_title", "pct_software"}),
        read_csv(args.dorn_task_csv,
                 {"occ1990dd", "task_abstract", "task_routine", "task_manual"}),
    )
    for code, row in direct.items():
        row["occupation"] = title2010.get(code, row.get("occupation", ""))
        row["occupation_title_vintage"] = "Census 2010 official"
    direct18 = direct_to_census2018(
        direct, bridge, ("webb_pct_software", "rti_autor_dorn"))
    output_rows = []
    for code in sorted(set(direct) | set(indirect)):
        row = {"cps_occ2010": code, "soc_major_group": "",
               "occ1990dd": "", "occupation": title2010.get(code, ""),
               "occupation_title_vintage": "Census 2010 official"}
        row.update(indirect.get(code, {}))
        row.update(direct.get(code, {}))
        row["occupation"] = title2010.get(code, row.get("occupation", ""))
        output_rows.append(row)

    fields = ["cps_occ2010", "soc_major_group", "occ1990dd", "occupation",
              "occupation_title_vintage", *MEASURES]
    for field in indirect_fields:
        fields.extend([field + "_covered_route_mass", field + "_partial_sum"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in output_rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key, "")
                             for key in fields})

    target_rows = []
    for code in sorted(set(census18) | set(direct18)):
        row = {
            "census2018": code,
            "soc_major_group": "",
            "occupation": title2018.get(code, ""),
            "occupation_title_vintage": "Census 2018 official",
        }
        row.update(census18.get(code, {}))
        row.update(direct18.get(code, {}))
        row["occupation"] = title2018.get(code, row.get("occupation", ""))
        target_rows.append(row)
    target_fields = [
        "census2018", "soc_major_group", "occupation",
        "occupation_title_vintage", "source_census2010_codes", *MEASURES,
        "webb_pct_software_harmonization", "rti_autor_dorn_harmonization",
    ]
    for field in indirect_fields:
        target_fields.extend([field + "_covered_weight", field + "_partial_sum"])
    args.census2018_output.parent.mkdir(parents=True, exist_ok=True)
    with args.census2018_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=target_fields, lineterminator="\n")
        writer.writeheader()
        for row in target_rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key, "")
                             for key in target_fields})

    source_paths = {
        "webb": args.webb, "dorn_crosswalk_dta": args.dorn_crosswalk_source,
        "dorn_task_dta": args.dorn_task_source, "onet24": args.onet24,
        "bls_soc_crosswalk": args.bls_soc_crosswalk,
        "frey_osborne_pdf": args.frey_pdf, "oews": args.oews,
        "cps_bridge": args.cps_bridge,
        "census_conversion": args.census_conversion,
        "census2010_code_list": args.census2010_code_list,
        "census2010_code_list_source": args.census2010_code_list_source,
        "census2018_code_list": args.census2018_code_list,
    }
    receipt = {
        "record_version": "yax-computerization-measures-v1",
        "status": "PASS",
        "scope": "measurement only; no CPS person records or outcomes read",
        "post_event_outcomes_opened": False,
        "inputs": {name: {"path": str(path), "sha256": sha256(path)}
                   for name, path in source_paths.items()},
        "source_locators": {
            "webb_author_page": "https://www.michaelwebb.co/",
            "webb_distribution": "https://eepurl.com/gxo4zr",
            "dorn_data_page": "https://www.ddorn.net/data.htm",
            "dorn_crosswalk": "https://www.ddorn.net/data/occ2010_occ1990dd.zip",
            "dorn_task": "https://www.ddorn.net/data/occ1990dd_task_alm.zip",
            "onet_archive": "https://www.onetcenter.org/db_releases.html",
            "onet24_text": "https://www.onetcenter.org/dl_files/database/db_24_3_text.zip",
            "bls_soc_crosswalk": "https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx",
            "frey_osborne": "https://www.oxfordmartin.ox.ac.uk/downloads/academic/The_Future_of_Employment.pdf",
            "census2010_code_list": "https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2010-occ-codes-with-crosswalk-from-2002-2011.xls",
            "census2018_code_list": "https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx",
        },
        "webb": {"measure": "pct_software", "native_taxonomy": "occ1990dd"},
        "onet": {
            "release": "24.3", "release_date": "May 2020",
            "element_id": ONET_ELEMENT, "official_element_name": ONET_OFFICIAL_LABEL,
            "naming_note": "official 24.3 label verified from Work Activities.txt",
            "primary_scale": "IM", "robustness_scale": "LV",
            "source_rows_for_element": onet_rows, "soc2010_aggregation_rules": onet_rules,
            "harmonization": onet_diag,
        },
        "rti": {
            "formula": "ln(task_routine)-ln(task_manual)-ln(task_abstract)",
            "source": "Autor-Dorn occ1990dd_task_alm",
        },
        "frey_osborne": {"role": "secondary", "appendix_rows": len(frey_source_rows),
                          "harmonization": frey_diag},
        "output": {"path": str(args.output), "sha256": sha256(args.output),
                   "rows": len(output_rows),
                   "complete_codes": {field: sum(row.get(field) is not None
                                                  for row in output_rows)
                                      for field in MEASURES}},
        "census2018_output": {
            "path": str(args.census2018_output),
            "sha256": sha256(args.census2018_output),
            "rows": len(target_rows),
            "complete_codes": {field: sum(row.get(field) is not None
                                             for row in target_rows)
                               for field in MEASURES},
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--webb", type=pathlib.Path, required=True)
    ap.add_argument("--dorn-crosswalk-csv", type=pathlib.Path, required=True)
    ap.add_argument("--dorn-crosswalk-source", type=pathlib.Path, required=True)
    ap.add_argument("--dorn-task-csv", type=pathlib.Path, required=True)
    ap.add_argument("--dorn-task-source", type=pathlib.Path, required=True)
    ap.add_argument("--onet24", type=pathlib.Path, required=True)
    ap.add_argument("--bls-soc-crosswalk", type=pathlib.Path, required=True)
    ap.add_argument("--frey-pdf", type=pathlib.Path, required=True)
    ap.add_argument("--oews", type=pathlib.Path, required=True)
    ap.add_argument("--cps-bridge", type=pathlib.Path, required=True)
    ap.add_argument("--census-conversion", type=pathlib.Path, required=True)
    ap.add_argument("--census2010-code-list", type=pathlib.Path, required=True)
    ap.add_argument("--census2010-code-list-source", type=pathlib.Path, required=True)
    ap.add_argument("--census2018-code-list", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--census2018-output", type=pathlib.Path, required=True)
    ap.add_argument("--receipt", type=pathlib.Path, required=True)
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    for path in (args.webb, args.dorn_crosswalk_csv, args.dorn_crosswalk_source,
                 args.dorn_task_csv, args.dorn_task_source, args.onet24,
                 args.bls_soc_crosswalk, args.frey_pdf, args.oews, args.cps_bridge,
                 args.census_conversion, args.census2010_code_list,
                 args.census2010_code_list_source, args.census2018_code_list):
        if not path.is_file():
            print(f"NEED_HUMAN: missing input {path}")
            return 2
    receipt = build(args)
    print(json.dumps(receipt["output"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
