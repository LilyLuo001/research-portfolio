"""Compare frozen parser with independent model readings; never calls it human gold."""
import hashlib
import json
import math
from pathlib import Path

B = Path(__file__).resolve().parent
FIELDS = ['education_present', 'prior_experience_present', 'explicit_no_experience']
CLAUSES = ['education_clauses', 'experience_clauses', 'software_qualification_clauses']


def wilson(success, n):
    if not n:
        return None
    z = 1.95996398454
    phat = success / n
    denom = 1 + z*z/n
    center = (phat + z*z/(2*n))/denom
    half = z*math.sqrt(phat*(1-phat)/n + z*z/(4*n*n))/denom
    return [max(0, center-half), min(1, center+half)]


def validate_review(path, ads, input_sha):
    review = json.loads(path.read_text())
    assert review['ads_sha256'] == input_sha, path
    labels = review['labels']
    assert len(labels) == len(ads)
    out = {r['BLIND_ID']: r for r in labels}
    assert len(out) == len(labels) and set(out) == set(ads)
    for bid, row in out.items():
        for field in FIELDS:
            assert row[field] in ('yes', 'no', 'unclear'), (path, bid, field)
        for group in CLAUSES:
            assert isinstance(row[group], list)
            for clause in row[group]:
                quote = clause['quote']
                assert isinstance(quote, str) and quote and quote in ads[bid], (path, bid, group, quote)
    return out


def decisions(result):
    es = result['evidence']
    def qualifies(e):
        return bool(e.get('is_applicant_requirement') or e.get('is_applicant_qualification_candidate')) and not e.get('negated_or_optional') and not e.get('ambiguous_abbreviation')
    edu = any(e['module']=='education' and qualifies(e) for e in es)
    exp = any(e['module']=='experience' and qualifies(e) and not e.get('no_experience_explicit') for e in es)
    none = any(e['module']=='experience' and e.get('no_experience_explicit') and e['context'] not in ('company','benefits','duties','equal_opportunity','application_policy') for e in es)
    return dict(zip(FIELDS, ['yes' if x else 'no' for x in (edu, exp, none)]))


def main():
    ads_path = B/'blind_pack/ads.json'
    ads = {r['BLIND_ID']:r['DESCRIPTION'] for r in json.loads(ads_path.read_text())}
    sha = hashlib.sha256(ads_path.read_bytes()).hexdigest()
    a = validate_review(B/'reviewer_a.json', ads, sha)
    b = validate_review(B/'reviewer_b.json', ads, sha)
    pred = {r['BLIND_ID']:r['prediction'] for r in json.loads((B/'predictions/v4_blind24.json').read_text())}
    assert set(pred)==set(ads)
    cases = []; metrics = {}
    for field in FIELDS:
        counts = dict(TP=0, FP=0, FN=0, TN=0, agreed_binary=0, disagreement_or_unclear=0)
        for bid in sorted(ads):
            av,bv,pv = a[bid][field],b[bid][field],decisions(pred[bid])[field]
            ref = av if av==bv and av!='unclear' else None
            if ref is None:
                category='disagreement_or_unclear'
                counts[category]+=1
            else:
                counts['agreed_binary']+=1
                category = ('T' if pv==ref else 'F')+('P' if pv=='yes' else 'N')
                counts[category]+=1
            cases.append({'BLIND_ID':bid,'field':field,'reviewer_a':av,'reviewer_b':bv,'parser':pv,'agreed_reference':ref,'category':category})
        tp,fp,fn,tn = (counts[k] for k in ['TP','FP','FN','TN'])
        metrics[field]=dict(counts, precision=tp/(tp+fp) if tp+fp else None,
            recall=tp/(tp+fn) if tp+fn else None,
            precision_wilson95=wilson(tp,tp+fp), recall_wilson95=wilson(tp,tp+fn))
    report={'status':'complete','review_kind':'independent model reading diagnostic, NOT human gold',
        'ads_sha256':sha,'n':len(ads),'metrics_vs_agreed_model_labels':metrics,
        'cases':cases,'population_accuracy_estimated':False,'full_semantic_release':False,
        'scope':'24 selected templates from a fixed regional pilot; known development cases/templates/employers excluded; no population weights inferred',
        'uncertainty':'Wilson intervals are simple binomial diagnostic intervals for observed consensus labels. They do not account for shared model errors, sampling design or employer dependence and do not justify population inference.',
        'required_next':'Review disagreement/mismatch evidence before deciding module scope; do not tune V4 using this pack and then call it independent validation.'}
    out=B/'comparison'
    out.mkdir(exist_ok=True)
    (out/'comparison_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
