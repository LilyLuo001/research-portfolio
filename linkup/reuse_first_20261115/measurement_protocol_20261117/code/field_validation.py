"""Field-local engineering adapter, proposal v1; no production admission.

Uses the unchanged Formal800 schema and mechanical checks on isolated field
projections. Projections are internal validation fixtures, NEVER replacement
reviews. Original values, free text, evidence and historical status are untouched.
No file writes, model calls, extraction, semantic truth or corpus qualification.
"""
from copy import deepcopy
import json
import math

import jsonschema

DIMS = {
    'experience': ('general_work', 'occupation_task', 'industry_domain', 'tool_specific'),
    'entry': ('explicit_no_experience', 'explicit_new_graduate',
              'current_student_internship', 'explicit_junior_or_entry_label'),
    'responsibility': ('independent_judgment', 'client_ownership',
                       'people_supervision', 'training_mentoring'),
}
FIELDS = ('technology',) + tuple(f'{family}.{dim}' for family, dims in DIMS.items() for dim in dims)
INVENTORIES = {
    'experience': ('experience_clauses', 'object'),
    'entry': ('entry_items', 'target'),
    'responsibility': ('responsibility_items', 'dimension'),
}


def parse_review(serialized):
    """Reject duplicate JSON keys instead of silently picking a value."""
    def unique(pairs):
        obj = {}
        for name, value in pairs:
            if name in obj:
                raise ValueError('duplicate_json_key')
            obj[name] = value
        return obj
    def bad_constant(_):
        raise ValueError('nonfinite_json_number')
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('nonfinite_json_number')
        return number
    obj = json.loads(serialized, object_pairs_hook=unique, parse_constant=bad_constant,
                     parse_float=finite_float)
    if not isinstance(obj, dict):
        raise ValueError('review_not_object')
    return obj


def _empty_projection(review):
    p = {k: deepcopy(review[k]) for k in ('record_id', 'context_sha256', 'document_status')}
    # Unrelated unknown placeholders are never emitted as observed outcomes.
    for family, dims in DIMS.items():
        p[family + '_outcomes'] = {dim: 'unknown' for dim in dims}
        p[INVENTORIES[family][0]] = []
    p.update(qualification_alternatives=[], technology_items=[],
             technology_inventory_status='unknown', unresolved_notes=[])
    return p


def _projection(review, field):
    p = _empty_projection(review)
    if field == 'technology':
        for name in ('technology_items', 'technology_inventory_status'):
            p[name] = deepcopy(review.get(name))
        return p, []
    family, dimension = field.split('.')
    inventory, selector = INVENTORIES[family]
    outcomes = review.get(family + '_outcomes')
    items = review.get(inventory)
    if not isinstance(outcomes, dict) or not isinstance(items, list):
        return p, ['family_container_missing_or_malformed']
    if set(outcomes) - set(DIMS[family]):
        return p, ['family_outcome_cannot_be_assigned']
    if any(not isinstance(item, dict) or item.get(selector) not in DIMS[family] for item in items):
        # An unassignable item may belong to any dimension in this family.
        # Retain it at source and block this family, never silently discard it.
        return p, ['family_item_cannot_be_assigned']
    p[family + '_outcomes'][dimension] = deepcopy(outcomes.get(dimension))
    p[inventory] = deepcopy([item for item in items if item[selector] == dimension])
    if family == 'experience':
        groups = review.get('qualification_alternatives')
        # This shared container is needed only by fields with linked clauses.
        wanted = [item.get('alternative_group') for item in p[inventory]
                  if item.get('alternative_group') is not None]
        if wanted:
            if not isinstance(groups, list) or any(
                not isinstance(group, dict) or not isinstance(group.get('group'), str)
                for group in groups
            ):
                return p, ['linked_qualification_container_malformed']
            # Preserve every branch of a referenced group and every duplicate;
            # the frozen checks detect ambiguous IDs/missing branches.
            p['qualification_alternatives'] = deepcopy([g for g in groups if g['group'] in wanted])
            # A complete qualification path also depends on other experience
            # dimensions in that group, including null-branch shared conditions.
            # Validate those clauses without emitting/inventing their outcomes.
            p[inventory] = deepcopy([item for item in items if
                item[selector] == dimension or item.get('alternative_group') in wanted])
    return p, []


class FieldValidator:
    def __init__(self, schema, frozen_validator):
        self.schema = deepcopy(schema)
        self.validator = jsonschema.Draft202012Validator(self.schema)
        self.frozen = frozen_validator

    def validate(self, packet, review, *, protected):
        """Trusted caller must supply protection membership before data access.

        Result has statuses/check locations only. The caller retains the source
        review and must independently verify schema/code hashes and coverage.
        An engineering-valid field is not automatically analysis-ready.
        """
        if not isinstance(protected, bool):
            raise ValueError('trusted_protection_flag_required')
        if protected:
            return {'status': 'quarantined', 'fields': {}, 'production_admission': False}
        shared = []
        try:
            self.frozen.validate_packet([packet])
        except (RuntimeError, KeyError, TypeError, ValueError):
            shared.append('trusted_packet_invalid')
        if not isinstance(review, dict):
            shared.append('review_not_object')
        else:
            for name in ('record_id', 'context_sha256', 'document_status'):
                prop = self.schema['properties'][name]
                if name not in review or list(jsonschema.Draft202012Validator(prop).iter_errors(review.get(name))):
                    shared.append('shared_schema:' + name)
            if isinstance(packet, dict):
                for name in ('record_id', 'context_sha256'):
                    if review.get(name) != packet.get(name):
                        shared.append('trusted_binding:' + name)
            if set(review) - set(self.schema['properties']):
                shared.append('unassigned_top_level_property')
        if shared:
            return {'status': 'shared_input_invalid', 'shared_errors': shared,
                    'fields': {field: {'status': 'blocked_shared_input'} for field in FIELDS},
                    'production_admission': False}

        results = {}
        for field in FIELDS:
            p, errors = _projection(review, field)
            checked_quotes = repeated_quotes = 0
            if not errors:
                try:
                    json.dumps(p, allow_nan=False)
                except (ValueError, TypeError):
                    errors.append('non_json_or_nonfinite_field_value')
            if not errors:
                structural = list(self.validator.iter_errors(p))
                # Error locations only: no original wording in diagnostics.
                errors.extend('schema:' + '/'.join(map(str, e.absolute_path)) for e in structural)
                if not structural:
                    # Counts/errors describe only this field's dependency projection.
                    errors.extend('consistency:' + str(i) for i, _ in enumerate(self.frozen.validate_cross_fields(p)))
                    for path, quotation in self.frozen.quote_arrays(p):
                        occurrences = self.frozen.find_all(packet['full_document'], quotation)
                        checked_quotes += 1
                        repeated_quotes += len(occurrences) > 1
                        if not occurrences:
                            errors.append('evidence_missing:' + '/'.join(map(str, path)))
            if field == 'technology':
                declared = review.get('technology_inventory_status')
                unknown = declared == 'unknown'
            else:
                family, dimension = field.split('.')
                group = review.get(family + '_outcomes')
                declared = group.get(dimension) if isinstance(group, dict) else None
                unknown = declared == 'unknown'
            status = 'invalid_local' if errors else ('reviewed_unknown' if unknown else 'engineering_valid')
            results[field] = {'status': status, 'errors': errors,
                              'checked_quote_instances': checked_quotes,
                              'repeated_quote_instances': repeated_quotes,
                              'inventory_scope': 'full' if review['document_status'] == 'reviewed_full' else 'partial',
                              'field_review_complete': review['document_status'] == 'reviewed_full',
                              'semantic_accuracy_certified': False}
        # Notes and unused groups remain source material, not invented values.
        return {'status': 'field_checks_completed', 'fields': results,
                'original_review_modified': False, 'production_admission': False}


def canonical_logic(node, allowed_atoms):
    """Canonicalize a pre-coded relation, not natural-language meaning.

    The caller must bind atoms to a frozen dictionary and source evidence.
    Display wording is outside this representation. Unknown phrases require a
    semantic review; similarity is never used to replace AND with OR.
    """
    if not isinstance(node, dict):
        raise ValueError('unresolved_logic')
    if set(node) == {'atom'}:
        if not isinstance(node['atom'], str) or node['atom'] not in allowed_atoms:
            raise ValueError('unresolved_atom')
        return ('atom', node['atom'])
    if set(node) != {'op', 'args'} or node['op'] not in ('and', 'or'):
        raise ValueError('unresolved_operator')
    args = node['args']
    if not isinstance(args, list) or len(args) < 2:
        raise ValueError('invalid_logic_arity')
    children = [canonical_logic(arg, allowed_atoms) for arg in args]
    # Only the same boolean operator is associative; preserve mixed grouping.
    flattened = []
    for child in children:
        flattened.extend(child[1]) if child[0] == node['op'] else flattened.append(child)
    return (node['op'], tuple(sorted(flattened)))
