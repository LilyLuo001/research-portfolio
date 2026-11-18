"""Create the explicitly authorized, post-confirmation economic release mask.

Only existing PUBLIC aggregates are read here. This does not re-score, label,
mutate old outputs, or promote complete structured relations.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / 'confirmation_stage5_20261118'
SCORE_SHA = '58c659a42536855e09877972036e0f30376bd8c475d53dc7b9b86c6c41130529'


def main():
    source = OLD / 'SCORING_PUBLIC.json'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SCORE_SHA
    score = json.loads(source.read_text())
    protocol = json.loads((OLD / 'protocol/CONFIRMATION_PROTOCOL.json').read_text())
    specs = {x['id']: x for x in protocol['measures']}
    released = []
    for measure, row in score['measure_results']['confirmation'].items():
        if row['outcome_macro_f1'] < 0.80:
            continue
        released.append({
            'id': measure, 'spec': specs[measure],
            'release': 'provisional_economic_use_user_authorized',
            'released_component': 'binary_outcome_only',
            'outcome_macro_f1': row['outcome_macro_f1'],
            'known_reference_coverage': row['known_reference_coverage'],
            'known_reference_cases': row['known_reference_cases'],
            'support': row['support'],
            'relation_metrics_diagnostic_not_certification': row['source_unit_supported_relation'],
            'original_blocking_reasons_retained': row['blocking_reasons'],
            'structured_atoms_release': 'saved_unverified',
        })
    assert len(released) == 15
    value = {
        'protocol_version': 'economic-pilot-20261119-v1',
        'authorization': 'Human expressly authorized outcome Macro-F1 >= 0.80 after inspecting the fixed 135-case results, CPU rules and a <=10000-input pilot within $150.',
        'selection_after_observing_results': True,
        'not_a_new_independent_confirmation': True,
        'not_human_gold_accuracy': True,
        'population_error_rate_certified': False,
        'original_confirmation_gate_unchanged': True,
        'original_score_sha256': SCORE_SHA,
        'released_measure_ids': [x['id'] for x in released],
        'released_measures': released,
        'publication_rules': {
            'candidate': 'Luna; original Kimi is the independent machine reference, not truth.',
            'requires_local_engineering_validity': True,
            'unknown_never_zero': True,
            'partial_or_invalid_field_does_not_erase_other_valid_fields': True,
            'relation_named_outcome': 'For .relations/.conditionality/.family_role/.exact_named_relation, release only the original binary presence outcome. The name is not certification of individual relation atoms, conditions, names or roles.',
            'explicit_entry_low_support': 'Only seven positive reference cases; retain low-support flag.',
            'technology_relation_low_coverage': 'Known reference coverage approximately 51.1%; retain coverage flags and unknowns.',
            'numeric_education_keywords': 'CPU source-evidenced candidates are separate versioned outputs. No rule hit is not absence. A duration is not an unconditional minimum and local proximity does not prove its experience object.',
            'old_results': 'Never modify prior accepted, saved, reviewed-unknown, unreconciled or protected outputs.',
            'full_scope': '500 million is the requested approximate commercial physical-row target; current catalog and local cache ratios are not verification of that global denominator.',
            'CREATED': 'First observation time proxy; before/after changes do not automatically identify an AI causal effect.',
        },
        'phase_prior_reserved_nano': 215331565700,
        'prior_confirmation_reserved_nano': 37266419300,
        'phase_infrastructure_reserved_nano': 50000000000,
        'phase_cap_nano': 450000000000,
        'pilot_cap_nano': 150000000000,
        'pilot_legs_usd_caps': {'Luna': 110, 'Kimi': 25, 'Astra': 15},
        'pilot_limits': {'physical_rows': 10000, 'Luna_contexts': 10000, 'Kimi_audits': 100, 'Astra_diagnostics': 20},
        'aggregate_tpm_schedule': 800000,
        'model_tpm_schedule': {'Luna': 80000, 'Kimi': 720000, 'Astra': 800000},
        'Kimi_verified_deployment_tpm': 3000000,
        'Astra_transport_amendment': 'Prefix Responses input with Return JSON.; unchanged schema/instructions and old failed outputs retained.',
    }
    target = HERE / 'ECONOMIC_RELEASE_PUBLIC.json'
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    if target.exists():
        assert target.read_bytes() == data
    else:
        target.write_bytes(data)
    print(json.dumps({'path': str(target), 'sha256': hashlib.sha256(data).hexdigest(), 'binary_measures': len(released)}))


if __name__ == '__main__':
    main()
