#!/usr/bin/env python3
"""Compare bounded Astra diagnostics; never replace Kimi or recompute a gate."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

import cloud_score_adapter as a
import field_score as s


def agreement(left, right, spec):
    if left['outcome'] == 'unknown' or right['outcome'] == 'unknown':
        return None
    return (left['outcome'] == right['outcome'] and
            (not spec['require_claim_agreement'] or s.lists_equal(left['atoms'], right['atoms'])))


def diagnose(args):
    frame, freeze = a.load_frame(args.frame, args.frame_freeze)
    scores = a.read(args.scores)
    protocol = a.read(Path(s.__file__).parent / 'CONFIRMATION_PROTOCOL.json')
    a.require(scores['protocol_version'] == protocol['version'], 'diagnostic_protocol_mismatch')
    a.require(scores['freeze_binding']['frame_sha256'] == freeze['frame_sha256'] and
              scores['freeze_binding']['protocol_bundle_sha256'] == freeze['protocol_bundle_sha256'],
              'diagnostic_score_binding_mismatch')
    a.require(a.read(args.join_receipt)['cases_sha256'] == s.file_sha(args.joined_cases),
              'original_joined_cases_changed')
    primary_sha = s.file_sha(args.scores)
    expected = {a.identity(row): row for row in frame}
    selected = {a.identity(row) for row in scores['bounded_astra_diagnostic_queue']}
    a.require(len(selected) <= 6 and selected <= set(expected), 'diagnostic_queue_out_of_bounds')
    requests = a.read_metadata(args.astra_inputs)
    outputs = a.read_metadata(args.astra_outputs)
    primary_meta = a.read_metadata(args.joined_cases)
    a.require(set(primary_meta) == set(expected), 'primary_case_roster_changed')
    a.require(0 < len(requests) <= 6 and set(requests) <= selected and set(outputs) == set(requests),
              'astra_request_output_subset_mismatch')
    final = a.read(args.astra_final)
    shared_roster = a.roster_sha(frame)
    request_roster = a.roster_sha([row['row'] for row in requests.values()])
    a.require(final.get('leg') == 'Astra' and final.get('terminal_no_active_requests') is True and
              final.get('roster_sha256') == shared_roster and final.get('output_roster_sha256') == request_roster and
              final.get('outputs_accounted') == len(requests) and
              final.get('physical_attempts', 7) <= 6 and final.get('logical_calls', 7) <= 6 and
              final.get('reserved_nano', 8_000_000_001) <= 8_000_000_000,
              'astra_terminal_cap_or_roster_mismatch')
    a.require(final['output_sha256'] == s.file_sha(args.astra_outputs), 'astra_output_sha_mismatch')
    a.require(final['exclusions_sha256'] in {s.file_sha(path) for path in args.exclusions},
              'missing_astra_quarantine_export')
    a.validate_carrier_metadata(outputs, {key: expected[key] for key in requests}, 'Astra', shared_roster)
    exclusions = a.exclusions_union(args.exclusions)
    blocked = {key for key in requests if a.excluded(key, (requests[key], outputs[key]), exclusions)}
    allowed = set(requests) - blocked
    # Quarantine metadata from the third reader is resolved before decoding any
    # corresponding primary review, source packet or Astra review.
    cases = a.read_selected(args.joined_cases, allowed)
    astra = a.read_selected(args.astra_outputs, allowed)
    validator = s.load_validator(args.repo, protocol)
    counts = {spec['id']: Counter() for spec in protocol['measures']}
    for key in requests:
        if key in blocked:
            for counter in counts.values():
                counter['blocked_metadata_only'] += 1
            continue
        case, third = cases[key], astra[key]
        packet = case.get('packet')
        if case.get('protection_blocked') or packet is None:
            for counter in counts.values():
                counter['primary_packet_unavailable'] += 1
            continue
        a.require(a.identity(packet) == key, 'diagnostic_packet_identity_mismatch')
        units = s.source_units(packet['full_document'])
        a.require(s.digest_json(units) == expected[key]['source_units_sha256'], 'diagnostic_source_units_mismatch')
        reviews = [case.get('candidate'), case.get('reference'), third.get('payload')]
        a.require(reviews[2] is None or third['status'] == 'field_local_validation_complete',
                  'astra_unvalidated_payload')
        statuses = [case.get('candidate_processing_status', 'unprocessed'),
                    case.get('reference_processing_status', 'unprocessed'), third['status']]
        validations = [validator.validate(packet, review, protected=False) if review is not None else {}
                       for review in reviews]
        for spec in protocol['measures']:
            luna, kimi, third_obs = [s.observe(review, valid, spec, packet, units, validator.frozen, state)
                                    for review, valid, state in zip(reviews, validations, statuses)]
            counter = counts[spec['id']]
            counter['audited_slots'] += 1
            with_luna, with_kimi = agreement(third_obs, luna, spec), agreement(third_obs, kimi, spec)
            for label, value in (('luna', with_luna), ('kimi', with_kimi)):
                counter['astra_' + label + '_comparable'] += value is not None
                counter['astra_' + label + '_agreement'] += value is True
            if with_luna is None or with_kimi is None:
                counter['not_comparable_all_three'] += 1
            elif with_luna and with_kimi:
                counter['astra_agrees_with_both'] += 1
            elif with_luna:
                counter['astra_agrees_with_luna_only'] += 1
            elif with_kimi:
                counter['astra_agrees_with_kimi_only'] += 1
            else:
                counter['astra_agrees_with_neither'] += 1
    a.require(s.file_sha(args.scores) == primary_sha, 'primary_score_artifact_changed')
    public = {'status': 'bounded_astra_diagnostics_only', 'frame_count': len(frame),
              'diagnostics_selected': len(selected), 'source_only_requests': len(requests),
              'late_blocked_metadata_only': len(blocked), 'physical_attempts': final['physical_attempts'],
              'reserved_usd': final['reserved_nano'] / 1e9,
              'measure_diagnostics': {key: dict(value) for key, value in counts.items()},
              'original_primary_scores_sha256': primary_sha, 'astra_outputs_sha256': final['output_sha256'],
              'reference_overwritten': False, 'primary_gates_recomputed': False,
              'production_admission': False, 'new_model_calls_by_diagnostic_tool': 0,
              'interpretation': 'Third-machine agreement diagnostics; no gold labels or new qualification.'}
    a.write_new(args.output, public)
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frame', 'frame-freeze', 'scores', 'joined-cases', 'join-receipt', 'astra-inputs',
                 'astra-outputs', 'astra-final', 'repo', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--exclusions', nargs='+', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(diagnose(args), ensure_ascii=False, allow_nan=False))
    except Exception as error:
        print(json.dumps({'status': 'diagnostic_failed_closed', 'error_type': type(error).__name__}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
