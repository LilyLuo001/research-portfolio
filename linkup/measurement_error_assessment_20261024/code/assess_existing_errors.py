#!/usr/bin/env python3
"""Bounded error assessment from frozen aggregates and reference outcomes.

No original_text read, new labels, parser/model execution, or corpus production.
All new calculations must run as an authorized SCNet scheduler job.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import pandas as pd

MAJORS = ('11', '13', '15', '17')
A = 'genai_use_with_or_without_software'
B = 'traditional_software_use_no_ai'
EXP = ('general_work', 'occupation_task', 'industry_domain', 'tool_specific')
EPS = (0, .01, .02, .025, .05, .10)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def counts(df, field):
    values = df[field]
    p, n = int((values == 1).sum()), int((values == 0).sum())
    return dict(total=len(df), positive=p, negative=n, unknown=len(df)-p-n)


def classified_metrics(tn, fp, fn, tp):
    def div(a, b):
        return a/b if b else None
    n = tn+fp+fn+tp
    return dict(n=n, tn=tn, fp=fp, fn=fn, tp=tp,
                mismatch_fraction=div(fp+fn, n),
                positive_precision=div(tp, tp+fp), positive_recall=div(tp, tp+fn),
                false_positive_rate=div(fp, fp+tn), false_negative_rate=div(fn, fn+tp),
                reference_positive_share=div(tp+fn, n), predicted_positive_share=div(tp+fp, n),
                signed_prevalence_bias=div(fp-fn, n))


def bounds(c, eps=0, include_recorded_unknown=True):
    # eps bounds the fraction of currently known labels corrupted in EACH cell.
    # Continuous mass relaxation, conservative vs integral ad flips; not sharp.
    known = c['positive']+c['negative']
    denom = c['total'] if include_recorded_unknown else known
    if not denom:
        return None
    lo = max(0, c['positive']-eps*known)/denom
    hi = (min(known, c['positive']+eps*known) +
          (c['unknown'] if include_recorded_unknown else 0))/denom
    return lo, hi


def unknown_membership_bounds(ca, cb, cu):
    # Unknown-technology ads may be A, B, or neither. Known outcome positives
    # go to B for minimization and A for maximization; negatives vice versa.
    # Allocate unknown-outcome ads across A/B at their adverse outcome states.
    # These are conservative reference-assignment envelopes, NOT error CIs.
    lower, upper = [], []
    for x in range(cu['unknown']+1):
        a_den = ca['total']+cu['negative']+x
        b_den = cb['total']+cu['positive']+cu['unknown']-x
        if a_den and b_den:
            lower.append(ca['positive']/a_den -
                         (cb['positive']+cb['unknown']+cu['positive']+cu['unknown']-x)/b_den)
        a_den = ca['total']+cu['positive']+x
        b_den = cb['total']+cu['negative']+cu['unknown']-x
        if a_den and b_den:
            upper.append((ca['positive']+ca['unknown']+cu['positive']+x)/a_den -
                         cb['positive']/b_den)
    return (min(lower), max(upper)) if lower and upper else None


def main():
    ap = argparse.ArgumentParser()
    for name in ('joined', 'q1', 'baseline', 'old_diagnostic', 'output'):
        ap.add_argument('--'+name.replace('_', '-'), required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    if (out/'RUN_RECEIPT_PUBLIC.json').exists():
        raise SystemExit('guard: completed assessment exists')
    started = time.perf_counter()
    cols = ['occupation_major', 'technology_group', 'explicit_new_graduate',
            'explicit_no_experience', 'duty_any']
    cols += ['experience_'+x for x in EXP]
    cols += ['status_'+x for x in ('technology_category_and_role', 'experience_object',
             'experience_strength', 'experience_literal_years',
             'qualification_conditions_and_alternatives', 'entry_wording_and_scope',
             'current_responsibility_subject_and_relation')]
    df = pd.read_parquet(args.joined, columns=cols)
    if len(df) != 10000:
        raise RuntimeError('frozen complete fixed10k size changed')
    df['occupation_major'] = df['occupation_major'].astype(str)
    q1 = pd.read_csv(args.q1)
    cell_rows, sens, tipping, member = [], [], [], []
    for obj in EXP:
        field = 'experience_'+obj
        cells = {}
        for major in MAJORS:
            mm = df[df.occupation_major == major]
            for group in (A, B, 'uncertain_technology'):
                c = counts(mm[mm.technology_group == group], field)
                cells[(major, group)] = c
                cell_rows.append(dict(measure=field, major=major, group=group, **c))
            if not all(cells[(major,g)]['positive']+cells[(major,g)]['negative'] for g in (A,B)):
                raise RuntimeError('required known cell unavailable; no renormalization')
        def contrast(eps, recorded):
            parts = []
            for major in MAJORS:
                ba, bb = (bounds(cells[(major,g)], eps, recorded) for g in (A,B))
                parts.append((ba[0]-bb[1], ba[1]-bb[0]))
            return sum(x[0] for x in parts)/4, sum(x[1] for x in parts)/4
        point = sum(cells[(m,A)]['positive']/(cells[(m,A)]['positive']+cells[(m,A)]['negative'])-
                    cells[(m,B)]['positive']/(cells[(m,B)]['positive']+cells[(m,B)]['negative'])
                    for m in MAJORS)/4
        existing = q1[(q1.frame == 'complete_fixed10k') &
                      (q1.scope == 'equal_0.25_major_standardization') &
                      (q1.measure == field) & (q1.row_type == 'difference')]
        if len(existing) != 1 or abs(float(existing.iloc[0].point)-point) > 1e-12:
            raise RuntimeError('existing Q1 point not reproduced')
        base = contrast(0, True)
        if max(abs(base[0]-float(existing.iloc[0].lower)),
               abs(base[1]-float(existing.iloc[0].upper))) > 1e-12:
            raise RuntimeError('existing recorded-unknown bounds not reproduced')
        for recorded in (False, True):
            for eps in EPS:
                lo, hi = contrast(eps, recorded)
                sens.append(dict(measure=field, point=point,
                    includes_recorded_outcome_unknown=recorded,
                    hypothetical_known_label_error_cap_each_major_group=eps,
                    lower=lo, upper=hi, direction_preserved=(lo > 0),
                    membership='fixed accepted reference groups',
                    interpretation='sensitivity assumption, not estimated error or CI'))
            low, high = 0., 1.
            for _ in range(60):
                mid = (low+high)/2
                if contrast(mid, recorded)[0] > 0:
                    low = mid
                else:
                    high = mid
            tipping.append(dict(measure=field, point=point,
                includes_recorded_outcome_unknown=recorded,
                continuous_each_cell_known_label_error_cap_to_allow_zero=high,
                fixed_membership=True, estimated_error_rate=False))
        bp = [unknown_membership_bounds(cells[(m,A)],cells[(m,B)],cells[(m,'uncertain_technology')])
              for m in MAJORS]
        member.append(dict(measure=field, point=point,
            lower=sum(x[0] for x in bp)/4, upper=sum(x[1] for x in bp)/4,
            uncertain_technology_ads_in_four_major_scope=sum(cells[(m,'uncertain_technology')]['total'] for m in MAJORS),
            interpretation='recorded outcome unknown + recorded technology-member unknown; no latent label-error correction; conservative envelope, not CI'))
    for name, rows in (('Q1_CELL_COUNTS',cell_rows),('Q1_LATENT_ERROR_SENSITIVITY',sens),
                       ('Q1_SIGN_TIPPING_THRESHOLDS',tipping),('Q1_UNKNOWN_MEMBERSHIP_ENVELOPES',member)):
        pd.DataFrame(rows).to_csv(out/(name+'.csv'), index=False)
    # Include eligibility-unknown ads in a separate Q2 sensitivity; not 71/10k.
    q2 = []
    for entry in ('explicit_new_graduate','explicit_no_experience'):
        c = counts(df[df[entry] == 1], 'duty_any')
        u = counts(df[df[entry].isna()], 'duty_any')
        lo = c['positive']/(c['total']+u['negative']+u['unknown'])
        hi = (c['positive']+c['unknown']+u['positive']+u['unknown'])/(c['total']+u['positive']+u['unknown'])
        q2.append(dict(frame='complete_fixed10k',weight=1,entry=entry,
            denominator_scope='entry-positive ads; separate expansion by recorded eligibility unknowns',
            eligibility_positive=c['total'], known_duty=c['positive']+c['negative'],
            positive_duty=c['positive'], unknown_duty=c['unknown'],
            known_duty_rate=c['positive']/(c['positive']+c['negative']),
            recorded_duty_unknown_lower=c['positive']/c['total'],
            recorded_duty_unknown_upper=(c['positive']+c['unknown'])/c['total'],
            eligibility_unknown=u['total'], eligibility_unknown_duty_positive=u['positive'],
            eligibility_unknown_duty_negative=u['negative'], eligibility_unknown_duty_unknown=u['unknown'],
            combined_recorded_unknown_lower=lo, combined_recorded_unknown_upper=hi,
            latent_semantic_error_included=False))
    pd.DataFrame(q2).to_csv(out/'Q2_ELIGIBILITY_AND_DUTY_UNKNOWNS.csv',index=False)
    unknown_rows=[]
    for col in [c for c in cols if c.startswith('status_')]:
        known=int(df[col].isin(('known','not_applicable')).sum())
        unknown_rows.append(dict(kind='family_acceptance_mask',family=col[7:], total=10000, usable_reference_ads=known,
                                 unresolved_ads=10000-known, unresolved_share=(10000-known)/10000,
                                 interpretation='recorded unavailability, not misclassification rate'))
    for col in ['experience_'+x for x in EXP]+['explicit_new_graduate','explicit_no_experience','duty_any']:
        c=counts(df,col)
        unknown_rows.append(dict(kind='derived_outcome',family=col,total=10000,
            usable_reference_ads=c['positive']+c['negative'],unresolved_ads=c['unknown'],
            unresolved_share=c['unknown']/10000,
            interpretation='actual binary outcome unknown, may differ from family mask; not misclassification'))
    pd.DataFrame(unknown_rows).to_csv(out/'REFERENCE_AVAILABILITY.csv',index=False)
    base=pd.read_csv(args.baseline)
    selected=base[base.scope_type=='overall']
    br=[]
    for row in selected.to_dict('records'):
        br.append(dict(target=row['target'],decision=row['decision'],
                       **classified_metrics(*[int(row[k]) for k in ('tn','fp','fn','tp')]),
                       reference='Pro labels; final holdout, not wholly blind'))
    pd.DataFrame(br).to_csv(out/'TFIDF_REFERENCE_ERRORS.csv',index=False)
    old=pd.read_csv(args.old_diagnostic)
    oldrows=[]
    for r in old[old.sample_component=='core'].to_dict('records'):
        oldrows.append(dict(object=r['experience_type'],component='32 stratified core',
            excluded_uncertain=int(r['uncertain_excluded']),
            **classified_metrics(*[int(r[k]) for k in ('candidate_negative_review_negative',
               'candidate_positive_review_negative','candidate_negative_review_positive',
               'candidate_positive_review_positive')]),
            interpretation='unweighted diagnostic versus Pro; definition/coverage differences; not corpus error rate'))
    pd.DataFrame(oldrows).to_csv(out/'OLD_RULE_DIAGNOSTIC_ERRORS.csv',index=False)
    # Proposed tolerances, not a change to frozen historical adoption criteria.
    ppv=[]
    positives=int((df.explicit_new_graduate==1).sum())
    unlabelled=int(df.explicit_new_graduate.isna().sum())
    prevalence_scenarios={
        'recorded_unknown_all_negative_lower':positives/len(df),
        'known_reference_labels_only':positives/(len(df)-unlabelled),
        'recorded_unknown_all_positive_upper':(positives+unlabelled)/len(df)}
    for scenario,prevalence in prevalence_scenarios.items():
        for recall in (.8,.9):
            desired=.9
            max_fpr=recall*prevalence*(1-desired)/(desired*(1-prevalence))
            ppv.append(dict(frame='complete_fixed10k',scenario=scenario,
                reference_prevalence_scenario=prevalence,entry_positive_ads=positives,
                entry_unknown_ads=unlabelled,assumed_recall=recall,
                desired_positive_precision=desired,required_fpr_ceiling=max_fpr,
                actual_measured_fpr=False))
    pd.DataFrame(ppv).to_csv(out/'RARE_ENTRY_FPR_SCENARIOS.csv',index=False)
    receipt=dict(status='complete_bounded_error_assessment',new_reviews=0,new_model_runs=0,
        corpus_shards_processed=0,rows=10000,
        reference='frozen Batch069 accepted Pro; not human ground truth',
        old_full_corpus_error='not_estimated: no frozen old-rule-to-Batch069 probability-weighted validation assembled in this job; historical core32 only',
        unchanged_historical_adoption_rules=True,
        inputs={n:sha(getattr(args,n)) for n in ('joined','q1','baseline','old_diagnostic')},
        python=platform.python_version(), elapsed_seconds=time.perf_counter()-started,
        sensitivity_assumptions=['four majors each0.25 unchanged','known group memberships fixed except separately named membership envelope',
          'hypothetical corruption cap applies independently within each known major/group outcome cell',
          'conservative continuous-mass envelope; correlated context and semantic constraints may tighten it',
          'uncertainty bounds are not sampling confidence intervals or estimates of hidden error',
          'no certification outside fixed technology candidate frame'])
    receipt['outputs']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'RUN_RECEIPT_PUBLIC.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':receipt['status'],'elapsed_seconds':receipt['elapsed_seconds'],
                      'new_reviews':0,'new_models':0,'output_files':len(receipt['outputs'])}))


if __name__=='__main__':
    main()
