#!/usr/bin/env python3
"""Prepare/fold a fixed Stage5 frame into the frozen scorer; never call models.

Aggregate JSONL metadata is scanned without decoding payload/full_document values.
Blocked rows are never JSON-decoded or dereferenced as packets/reviews. The scan
must read framing bytes; it does not expose or materialize protected text values.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import field_score as scorer

HERE = Path(__file__).resolve().parent
IDENTITY = ('record_id', 'context_sha256')
META_KEYS = set(IDENTITY) | {'case', 'roster_sha256', 'leg', 'status', 'blocked', 'protected',
                           'task', 'source_task', 'qualification_task', 'blocked_reason'}


def require(test, code):
    if not test:
        raise ValueError(code)


def parse(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def number(value):
        result = float(value)
        require(math.isfinite(result), 'nonfinite_json_number')
        return result
    def bad(_):
        raise ValueError('nonfinite_json_number')
    return json.loads(text, object_pairs_hook=pairs, parse_float=number, parse_constant=bad)


def read(path):
    return parse(Path(path).read_bytes())


def write_new(path, value, *, jsonl=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (''.join(scorer.stable(row) + '\n' for row in value) if jsonl
            else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    # Repeated preparation may verify an identical frozen artifact; never replace.
    if path.exists():
        require(path.read_bytes() == data, 'immutable_adapter_output_conflict')
    else:
        with path.open('xb') as output:
            os.chmod(path, 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    return scorer.file_sha(path)


class MetadataScanner:
    """Skip JSON values as bytes; decode only allowed metadata scalar values."""
    def __init__(self, raw):
        self.raw, self.i = raw, 0

    def ws(self):
        while self.i < len(self.raw) and self.raw[self.i] in b' \r\n\t':
            self.i += 1

    def char(self, expected):
        self.ws()
        require(self.i < len(self.raw) and self.raw[self.i] == ord(expected), 'malformed_jsonl_metadata')
        self.i += 1

    def string_end(self):
        self.char('"')
        while self.i < len(self.raw):
            value = self.raw[self.i]
            self.i += 1
            if value == 92:
                self.i += 1
            elif value == 34:
                return
        raise ValueError('unterminated_jsonl_string')

    def skip(self):
        self.ws()
        require(self.i < len(self.raw), 'empty_json_value')
        value = self.raw[self.i]
        if value == 34:
            self.string_end()
        elif value in (123, 91):
            closing = '}' if value == 123 else ']'
            self.i += 1
            self.ws()
            if self.i < len(self.raw) and self.raw[self.i] == ord(closing):
                self.i += 1
                return
            while True:
                if value == 123:
                    self.string_end()
                    self.char(':')
                self.skip()
                self.ws()
                require(self.i < len(self.raw), 'unterminated_json_container')
                if self.raw[self.i] == ord(closing):
                    self.i += 1
                    return
                self.char(',')
        else:
            start = self.i
            while self.i < len(self.raw) and self.raw[self.i] not in b',}] \r\n\t':
                self.i += 1
            require(self.i > start, 'invalid_json_value')

    def object(self):
        self.char('{')
        result, seen = {}, set()
        self.ws()
        if self.i < len(self.raw) and self.raw[self.i] == 125:
            self.i += 1
            return result
        while True:
            self.ws()
            start = self.i
            self.string_end()
            key = parse(self.raw[start:self.i])
            require(key not in seen, 'duplicate_json_key')
            seen.add(key)
            self.char(':')
            self.ws()
            if key == 'row':
                result['row'] = self.object()
            else:
                start = self.i
                self.skip()
                if key in META_KEYS:
                    result[key] = parse(self.raw[start:self.i])
            self.ws()
            require(self.i < len(self.raw), 'unterminated_json_metadata')
            if self.raw[self.i] == 125:
                self.i += 1
                return result
            self.char(',')


def metadata(raw):
    scan = MetadataScanner(raw)
    result = scan.object()
    scan.ws()
    require(scan.i == len(raw), 'trailing_jsonl_content')
    return result


def identity(row):
    row = row.get('row', row)
    return tuple(row[key] for key in IDENTITY)


def read_metadata(path):
    result = {}
    with Path(path).open('rb') as source:
        for raw in source:
            if raw.strip():
                row = metadata(raw)
                key = identity(row)
                require(key not in result, 'duplicate_source_identity')
                result[key] = row
    return result


def read_selected(path, allowed):
    """Blocked values are skipped before full JSON decode, regardless of key order."""
    result = {}
    with Path(path).open('rb') as source:
        for raw in source:
            if raw.strip():
                key = identity(metadata(raw))
                if key in allowed:
                    require(key not in result, 'duplicate_source_identity')
                    result[key] = parse(raw)
    return result


def roster_sha(rows):
    # Matches stage5_common.roster_sha256 exactly (key insertion order matters).
    roster = sorted(({key: row[key] for key in IDENTITY} for row in rows),
                    key=lambda row: tuple(row[k] for k in IDENTITY))
    return hashlib.sha256(json.dumps(roster, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def verify_bundle():
    bundle = read(HERE / 'PROTOCOL_FREEZE.json')
    for name, digest in bundle['files'].items():
        require(scorer.file_sha(HERE / name) == digest, 'frozen_protocol_bundle_modified')
    return scorer.file_sha(HERE / 'PROTOCOL_FREEZE.json')


def load_frame(frame_path, freeze_path):
    freeze = read(freeze_path)
    require(freeze['frame_sha256'] == scorer.file_sha(frame_path), 'frozen_frame_sha_mismatch')
    require(freeze['protocol_bundle_sha256'] == verify_bundle(), 'protocol_bundle_sha_mismatch')
    require(freeze.get('frozen_before_first_request') is True, 'frame_not_frozen_before_request')
    frame = [parse(line) for line in Path(frame_path).read_bytes().splitlines() if line.strip()]
    expected_count = freeze.get('frame_count', freeze.get('context_count'))
    require(isinstance(expected_count, int) and len(frame) == expected_count,
            'frozen_frame_count_changed')
    require(len({identity(row) for row in frame}) == len(frame), 'duplicate_frame_identity')
    return frame, freeze


def freeze_frame(args):
    require(args.no_requests_yet, 'explicit_pre_request_assertion_required')
    require(scorer.file_sha(args.source_frame) == args.expected_source_frame_sha, 'source_frame_sha_mismatch')
    source = read(args.source_frame)
    require(isinstance(source, list) and len(source) == args.expected_count, 'unexpected_fresh_frame_count')
    require(0 < len(source) <= 150, 'fresh_frame_cap')
    require(len({row['record_id'] for row in source}) == len(source)
            and len({row['context_sha256'] for row in source}) == len(source), 'duplicate_frame_identity')
    frame = []
    for row in source:
        require(row.get('protected') is False and row.get('fresh_never_exposed') is True, 'ineligible_frame_slot')
        require(row['partition'] in ('confirmation', 'challenge'), 'invalid_partition')
        require(re.fullmatch('[a-f0-9]{64}', row['source_units_sha256']) is not None, 'source_units_not_frozen')
        frame.append({key: row[key] for key in ('case', 'record_id', 'context_sha256', 'partition',
                                               'protected', 'fresh_never_exposed', 'source_units_sha256')})
    directory = Path(args.output_directory)
    frame_path = directory / 'FRAME_PRIVATE.jsonl'
    frame_sha = write_new(frame_path, frame, jsonl=True)
    receipt = {'frame_sha256': frame_sha, 'protocol_bundle_sha256': verify_bundle(),
               'frozen_before_first_request': True, 'frame_count': len(frame),
               'source_frame_sha256': args.expected_source_frame_sha, 'roster_sha256': roster_sha(frame),
               'adapter_sha256': scorer.file_sha(__file__), 'at_utc': datetime.now(timezone.utc).isoformat()}
    prior_receipt = directory / 'FRAME_FREEZE_PUBLIC.json'
    if prior_receipt.exists():
        prior = read(prior_receipt)
        require(all(prior.get(k) == v for k, v in receipt.items() if k != 'at_utc'),
                'existing_frame_freeze_conflict')
        receipt = prior
    write_new(directory / 'FRAME_FREEZE_PUBLIC.json', receipt)
    public = {'status': 'frame_frozen_no_requests', 'frame_count': len(frame),
              'canonical_window_rows': 150, 'excluded_prior_contexts_no_replacement': 150 - len(frame),
              'frame_sha256': frame_sha, 'protocol_bundle_sha256': receipt['protocol_bundle_sha256'],
              'roster_sha256': receipt['roster_sha256'], 'model_calls': 0}
    write_new(directory / 'FRAME_CONVERSION_PUBLIC.json', public)
    return public


def excluded(key, rows, exclusions):
    record_id, context = key
    if record_id in exclusions.get('record_ids', []) or context in exclusions.get('context_sha256', []):
        return True
    for row in rows:
        if row.get('blocked') is True or row.get('protected') is True:
            return True
        status = row.get('status', '')
        if status == 'blocked_protected_metadata_only' or status.startswith('quarantined'):
            return True
        if any(row.get(k) in exclusions.get('tasks', []) for k in ('task', 'source_task', 'qualification_task')):
            return True
    return False


def exclusions_union(paths):
    result = {}
    for path in paths:
        for key, value in read(path).items():
            if isinstance(value, list):
                result.setdefault(key, set()).update(value)
    return result


def validate_carrier_metadata(rows, expected, leg, shared_roster):
    require(set(rows) == set(expected), 'model_output_roster_mismatch')
    for key, row in rows.items():
        require(row.get('leg') == leg and row.get('roster_sha256') == shared_roster
                and str(row.get('case')) == str(expected[key]['case']), 'model_output_frame_binding_mismatch')


def join_outputs(args):
    frame, freeze = load_frame(args.frame, args.frame_freeze)
    expected = {identity(row): row for row in frame}
    shared_roster = roster_sha(frame)
    luna_final, kimi_final = read(args.luna_final), read(args.kimi_final)
    require(luna_final['output_sha256'] == scorer.file_sha(args.luna_outputs), 'luna_output_sha_mismatch')
    validation = read(args.kimi_validation_receipt)
    require(validation['validated_output_sha256'] == scorer.file_sha(args.kimi_outputs), 'kimi_validated_output_sha_mismatch')
    for final, leg in ((luna_final, 'Luna'), (kimi_final, 'Kimi')):
        require(final.get('leg') == leg and final.get('roster_sha256') == shared_roster
                and final.get('output_roster_sha256') == shared_roster
                and final.get('outputs_accounted') == len(frame), 'terminal_output_frame_mismatch')
    exclusion_shas = {scorer.file_sha(path) for path in args.exclusions}
    require(all(final.get('exclusions_sha256') in exclusion_shas for final in (luna_final, kimi_final)),
            'missing_pinned_leg_quarantine_export')
    # Read metadata for BOTH legs before decoding ANY packet or review payload.
    input_meta = read_metadata(args.inputs)
    luna_meta = read_metadata(args.luna_outputs)
    kimi_meta = read_metadata(args.kimi_outputs)
    require(set(input_meta) == set(expected), 'source_input_roster_mismatch')
    validate_carrier_metadata(luna_meta, expected, 'Luna', shared_roster)
    validate_carrier_metadata(kimi_meta, expected, 'Kimi', shared_roster)
    exclusions = exclusions_union(args.exclusions)
    blocked = {key for key in expected if excluded(key, (input_meta[key], luna_meta[key], kimi_meta[key]), exclusions)}
    allowed = set(expected) - blocked
    inputs = read_selected(args.inputs, allowed)
    luna = read_selected(args.luna_outputs, allowed)
    kimi = read_selected(args.kimi_outputs, allowed)
    cases, counts = [], {'frame_count': len(frame), 'blocked_metadata_only': len(blocked),
                         'candidate_payloads': 0, 'reference_payloads': 0}
    for key, row in expected.items():
        case = {name: row[name] for name in IDENTITY}
        if key in blocked:
            case['protection_blocked'] = True
        else:
            item = inputs[key]
            require(str(item['case']) == str(row['case']), 'source_case_id_mismatch')
            packet = {name: item['row'][name] for name in (*IDENTITY, 'full_document')}
            require(hashlib.sha256(packet['full_document'].encode()).hexdigest() == key[1], 'packet_context_mismatch')
            require(scorer.digest_json(scorer.source_units(packet['full_document'])) == row['source_units_sha256'],
                    'packet_units_mismatch')
            packet['assignment'] = item['row'].get('assignment') or {
                'packet_id': str(item['case']), 'reviewer_role': 'primary',
                'provenance': 'bounded_stage5_fresh_confirmation_20261118'}
            case['packet'] = packet
            for label, carrier in (('candidate', luna[key]), ('reference', kimi[key])):
                payload = carrier.get('payload')
                require(payload is None or carrier['status'] == 'field_local_validation_complete',
                        'unexpected_unvalidated_payload')
                case[label] = payload
                case[label + '_processing_status'] = carrier['status']
                counts[label + '_payloads'] += payload is not None
        cases.append(case)
    directory = Path(args.output_directory)
    cases_sha = write_new(directory / 'JOINED_CASES_PRIVATE.jsonl', cases, jsonl=True)
    public = {'status': 'joined_for_frozen_scorer_not_scored', **counts, 'cases_sha256': cases_sha,
              'frame_sha256': freeze['frame_sha256'], 'model_calls': 0,
              'original_model_outputs_modified': False, 'all_frozen_slots_retained': True}
    write_new(directory / 'JOIN_PUBLIC.json', public)
    command = [sys.executable, str(HERE / 'field_score.py'), '--frame', str(Path(args.frame).resolve()),
               '--frame-freeze', str(Path(args.frame_freeze).resolve()), '--cases',
               str((directory / 'JOINED_CASES_PRIVATE.jsonl').resolve()), '--repo', str(Path(args.repo).resolve()),
               '--out', str((directory / 'SCORES_PRIVATE.json').resolve())]
    write_new(directory / 'SCORING_COMMAND_PUBLIC.json', {'argv': command, 'executed': False})
    return public


def report_and_queue(args):
    frame, freeze = load_frame(args.frame, args.frame_freeze)
    result = read(args.scores)
    require(result['protocol_version'] == read(HERE / 'CONFIRMATION_PROTOCOL.json')['version'],
            'score_protocol_version_mismatch')
    require(result['freeze_binding']['frame_sha256'] == freeze['frame_sha256']
            and result['freeze_binding']['protocol_bundle_sha256'] == freeze['protocol_bundle_sha256'],
            'score_freeze_binding_mismatch')
    require(result['accounting']['frame_cases'] == len(frame), 'score_frame_count_mismatch')
    queue = result['bounded_astra_diagnostic_queue']
    require(len(queue) <= 6 and len({identity(row) for row in queue}) == len(queue), 'astra_queue_cap_or_duplicate')
    expected = {identity(row): row for row in frame}
    require(all(identity(row) in expected for row in queue), 'astra_outside_confirmation_frame')
    require(queue == sorted(queue, key=lambda row: (row['rank_sha256'], row['record_id'])), 'astra_queue_order_changed')
    for row in queue:
        require(row['rank_sha256'] == scorer.digest_json([result['protocol_version'], *identity(row)]),
                'astra_rank_changed')
    input_meta = read_metadata(args.inputs)
    require(set(input_meta) == set(expected), 'source_input_roster_mismatch')
    exclusions = exclusions_union(args.exclusions)
    blocked = {identity(row) for row in queue if excluded(identity(row), (input_meta[identity(row)],), exclusions)}
    selected = {identity(row) for row in queue} - blocked
    sources = read_selected(args.inputs, selected)
    requests = []
    for row in queue:
        key = identity(row)
        if key in blocked:
            continue  # No replacement selection after results.
        source = sources[key]
        packet = {name: source['row'][name] for name in (*IDENTITY, 'full_document')}
        require(hashlib.sha256(packet['full_document'].encode()).hexdigest() == key[1], 'astra_source_mismatch')
        # Source only: no Kimi/Luna labels, scores, measure IDs or audit reasons.
        requests.append({'case': source['case'], 'row': packet, 'protected': False,
                         'fresh_never_exposed': True, 'partition': 'confirmation'})
    directory = Path(args.output_directory)
    write_new(directory / 'ASTRA_SELECTION_PRIVATE.json', queue)
    write_new(directory / 'ASTRA_INPUTS_PRIVATE.jsonl', requests, jsonl=True)
    public = {key: result[key] for key in ('protocol_version', 'accounting', 'measure_results',
              'eligible_measure_dependencies', 'modules_retained', 'not_qualified_by_this_test',
              'machine_reference_agreement_is_not_gold_accuracy', 'population_generalization_certified',
              'production_admission')}
    public.update(status='frozen_primary_scored_astra_prepared_not_called',
                  astra_diagnostic_selected=len(queue), astra_source_only_requests=len(requests),
                  astra_late_blocked_no_replacement=len(blocked), model_calls_by_adapter=0,
                  primary_reference_overwritten=False, primary_gate_unchanged=True,
                  scores_sha256=scorer.file_sha(args.scores), frame_sha256=freeze['frame_sha256'])
    write_new(directory / 'SCORING_PUBLIC.json', public)
    # No case IDs or queue identifiers in stdout/public summary.
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze')
    freeze.add_argument('--source-frame', required=True)
    freeze.add_argument('--expected-source-frame-sha', required=True)
    freeze.add_argument('--expected-count', type=int, default=135)
    freeze.add_argument('--no-requests-yet', action='store_true')
    freeze.add_argument('--output-directory', required=True)
    freeze.set_defaults(run=freeze_frame)
    join = sub.add_parser('join')
    for name in ('frame', 'frame-freeze', 'inputs', 'luna-outputs', 'kimi-outputs', 'luna-final',
                 'kimi-final', 'kimi-validation-receipt', 'repo', 'output-directory'):
        join.add_argument('--' + name, required=True)
    join.add_argument('--exclusions', nargs='+', required=True)
    join.set_defaults(run=join_outputs)
    report = sub.add_parser('report')
    for name in ('frame', 'frame-freeze', 'scores', 'inputs', 'output-directory'):
        report.add_argument('--' + name, required=True)
    report.add_argument('--exclusions', nargs='+', required=True)
    report.set_defaults(run=report_and_queue)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(args.run(args), ensure_ascii=False, allow_nan=False))
    except Exception as error:
        # Never include source content, model text, or arbitrary exception messages.
        print(json.dumps({'status': 'adapter_failed_closed', 'error_type': type(error).__name__}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
