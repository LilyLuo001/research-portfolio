#!/usr/bin/env python3
"""Build a five-package provenance/readiness ledger from existing metadata only."""
from pathlib import Path
import hashlib, json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ADV=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1')
CONTRACT=Path('/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/feasibility_adjudication/20260913/reconciliation/estimation_contract.reconciled.PROPOSED.yaml')
SPONSOR_XWALK=Path('/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/t5_spec/sponsor_crosswalk_PROPOSED.csv')
OUT=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def joinvals(s): return ';'.join(sorted(set(str(x) for x in s.dropna() if str(x))))

pkg_path=ROOT/'missing_data_round_20260914/PACKAGE_INPUTS.csv'
filing_path=ROOT/'missing_data_round_20260914/SELECTED_PREANNOUNCEMENT_FILINGS.csv'
exposure_path=ROOT/'missing_data_round_20260914/PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv'
universe_path=ADV/'exposure/exposure_universe_gate0_pass.csv'
cohort_path=ROOT/'conversion_cohorts.csv'
overlap_path=ROOT/'missing_data_round_20260914/competing_conversion/overlap_summary_by_wave.csv'
recovered_path=ROOT/'recovered_candidate_support_20260915/full_artifacts/candidate_clock_support_by_wave_tier.csv'

pkg=pd.read_csv(pkg_path,usecols=['wave_id','role','effective_date','announcement_cutoff','cutoff_precision','cutoff_status','pre_series_id','pre_series_name','include_in_equity_package','source_locator','note'],dtype=str)
pkg=pkg[pkg.include_in_equity_package.str.lower().eq('true')].copy()
fil=pd.read_csv(filing_path,usecols=['wave_id','pre_series_id','report_date','cache_sha256','source_locator'],dtype=str)
exp=pd.read_csv(exposure_path,usecols=['wave_id','pre_report_date','denominator_complete','primary_ready'],dtype=str)
uni=pd.read_csv(universe_path,usecols=['wave_id','effective_date','adviser','pre_series_id','post_series_id','post_series_name','gate0'],dtype=str)
uni=uni.merge(pkg[['wave_id','pre_series_id']],on=['wave_id','pre_series_id'],how='inner',validate='many_to_one')
coh=pd.read_csv(cohort_path,usecols=['wave_id','sponsor','repository_effective_date','public_etf_operation_date','holding_series','public_source','note'],dtype=str)
ov=pd.read_csv(overlap_path,usecols=['wave_id','roster_rows','flagged','clean'])
rec=pd.read_csv(recovered_path,usecols=['wave_id','recovered_candidate_stock_wave_keys'])
rec=rec.groupby('wave_id').recovered_candidate_stock_wave_keys.sum()

rows=[]
for wave,g in pkg.groupby('wave_id',sort=True):
    f=fil[fil.wave_id.eq(wave)]; e=exp[exp.wave_id.eq(wave)]; u=uni[uni.wave_id.eq(wave)]; c=coh[coh.wave_id.eq(wave)]; o=ov[ov.wave_id.eq(wave)].iloc[0]
    cutoff=g.announcement_cutoff.iloc[0]; reports=sorted(f.report_date.unique()); strict=all(pd.Timestamp(x)<pd.Timestamp(cutoff) for x in reports)
    adviser=joinvals(u.adviser); sponsor=joinvals(c.sponsor) if len(c) else adviser
    sponsor_status='PACKAGE_COHORT_SPONSOR_PLUS_PUBLIC_SOURCE_NOT_CANONICAL_ID_SIGNOFF' if len(c) else 'ADVISER_FIELD_ONLY_NOT_SIGNED_ECONOMIC_SPONSOR'
    recovered=int(rec.get(wave,0))
    rows.append({
      'wave_id':wave,'role':g.role.iloc[0],'effective_date':g.effective_date.iloc[0],
      'included_predecessor_series':g.pre_series_id.nunique(),'pre_series_ids':joinvals(g.pre_series_id),
      'post_series_ids':joinvals(u.post_series_id),'adviser_or_sponsor_label':sponsor,'sponsor_provenance_status':sponsor_status,
      'sponsor_public_source':joinvals(c.public_source) if len(c) else 'MISSING_PACKAGE_LEVEL_SPONSOR_SOURCE',
      'announcement_cutoff':cutoff,'announcement_precision':g.cutoff_precision.iloc[0],'announcement_status':g.cutoff_status.iloc[0],
      'announcement_source_locator':joinvals(g.source_locator),'earliest_public_timestamp_ready':'NO',
      'implementation_evidence_status':('REPOSITORY_EFFECTIVE_DATE_AND_DISTINCT_PUBLIC_OPERATION_DATE_AVAILABLE_NOT_FINAL_IW' if len(c) else 'REPOSITORY_EFFECTIVE_DATE_ONLY_NO_INDEPENDENT_PUBLIC_OPERATION_DATE_IN_COHORT_FILE'),
      'public_etf_operation_date':joinvals(c.public_etf_operation_date) if len(c) else 'UNKNOWN',
      'chronology_conflict_note':('Current exposure chain uses PACKAGE_INPUTS cutoff 2020-11-17; historical build_strict_preannouncement_holdings.py hardcodes 2020-11-16. Selected 2020-10-31 holding reports precede both, but final A_w remains unresolved.' if wave=='W002' else ''),
      'selected_pre_report_dates':';'.join(reports),'selected_filing_series':f.pre_series_id.nunique(),'holdings_strictly_pre_recorded_cutoff':strict,
      'holdings_provenance_pointer':'missing_data_round_20260914/SELECTED_PREANNOUNCEMENT_FILINGS.csv[wave_id,pre_series_id,report_date,cache_sha256,source_locator]',
      'positive_exposure_stock_wave_rows':int(e.primary_ready.str.lower().eq('true').sum()),
      'denominator_complete_rows':int(e.denominator_complete.str.lower().eq('true').sum()),
      'denominator_date_basis':'pre_report_date; row-level source is CRSP dseshare active at report date or prior DSF fallback',
      'denominator_provenance_pointer':'missing_data_round_20260914/POSITION_MAPPING_AND_DENOMINATORS.parquet[wave_id,pre_series_id,pre_report_date,denominator_source,denominator_complete] + build_scc_exposure.py',
      'denominator_scientific_status':'AVAILABLE_ROW_LEVEL_PROVENANCE_SPLIT_BASIS_PROVISIONAL',
      'recovered99_stock_wave_keys':recovered,
      'existing_competing_rule_population':f'PROPOSED_40_ROSTER: rows={int(o.roster_rows)}, flagged={int(o.flagged)}, clean={int(o.clean)}',
      'recovered99_competing_conversion_status':'UNKNOWN_NOT_JOINED_TO_SIGNED_PACKAGE_SPONSOR_CONCURRENT_CONVERSION_LEDGER' if recovered else 'NOT_IN_RECOVERED99_SCOPE',
      'why_competing_unknown':'Recovered sidecar conversion_status tests CRSP/IBES PERMNO uniqueness only. Existing +/-24-month flags cover a different 40-row roster and use other-wave effective dates; they do not establish signed sponsor/package membership or earliest-public concurrent-event timing for recovered99.',
      'package_readiness':'PARTIAL_METADATA_NOT_FINAL_CLOCK_OR_CAUSAL_PACKAGE'
    })
ledger=pd.DataFrame(rows)
assert len(ledger)==5 and ledger.included_predecessor_series.sum()==12
assert ledger.positive_exposure_stock_wave_rows.sum()==4191
assert ledger.recovered99_stock_wave_keys.sum()==99
assert ledger.holdings_strictly_pre_recorded_cutoff.all()
ledger.to_csv(OUT/'package_readiness_ledger.csv',index=False,lineterminator='\n')

missing=pd.DataFrame([
 {'wave_id':'W002','package':'4 Dimensional predecessor series to DFAC/DFUS/DFAS/DFAT','current_announcement_evidence':'PACKAGE_INPUTS 2020-11-17 date; SEC locator 000179420220000482 does not pin predecessor announcement','missing_announcement_fields':'earliest_public_announcement_at; announcement_source_accession for the four-series conversion decision','current_implementation_evidence':'repository effective 2021-06-11; public ETF operation 2021-06-14','missing_implementation_fields':'constituent-level legal_effective_at or first_trading_at with source accession; rule-selected package I_w','current_sponsor_evidence':'Dimensional Fund Advisors LP plus issuer newsroom URL','missing_sponsor_evidence':'canonical_sponsor_id and source-backed confirmation that all four constituents share the same economic sponsor/package'},
 {'wave_id':'W013','package':'BrandywineGLOBAL Dynamic US Large Cap Value Fund to matching ETF','current_announcement_evidence':'supplied text says December 2021; later N-14 000179420222000078 filed 2022-04-08','missing_announcement_fields':'earliest_public_announcement_at exact day/time and contemporaneous primary source accession','current_implementation_evidence':'repository effective 2022-10-28 only','missing_implementation_fields':'legal_effective_at or first_trading_at and source accession; rule-selected package I_w','current_sponsor_evidence':'Legg Mason Partners Fund Advisor LLC adviser field only','missing_sponsor_evidence':'canonical_sponsor_id, sponsor role, evidence accession, package-membership confirmation'},
 {'wave_id':'W016','package':'Omni Tax-Managed Small-Cap Value Fund to EA Bridgeway Omni ETF','current_announcement_evidence':'SEC DEF A14A 000182912622018075 supports 2022-08-26 date','missing_announcement_fields':'earliest_public_announcement_at timestamp/uncertainty bound beyond date-only evidence','current_implementation_evidence':'repository effective 2023-03-10; issuer operation 2023-03-13','missing_implementation_fields':'legal_effective_at or first_trading_at with source accession and rule-selected I_w','current_sponsor_evidence':'Bridgeway Capital Management LLC plus issuer URL','missing_sponsor_evidence':'canonical_sponsor_id and signed constituent/package membership provenance'},
 {'wave_id':'W021','package':'JPMorgan Equity Focus Fund to JPMorgan Equity Focus ETF; bond series excluded','current_announcement_evidence':'provisional local board date 2023-02-07; related N-14 locator 000119312523067795 exists in historical script','missing_announcement_fields':'earliest_public_announcement_at and primary source accession explicitly tied to equity-only package','current_implementation_evidence':'repository effective 2023-07-28 only','missing_implementation_fields':'legal_effective_at or first_trading_at and source accession; rule-selected package I_w','current_sponsor_evidence':'J.P. Morgan Investment Management Inc adviser field only','missing_sponsor_evidence':'canonical_sponsor_id, evidence accession, and explicit exclusion relation for date-coincident bond package'},
 {'wave_id':'W025','package':'5 Fidelity enhanced-index predecessor series to 5 ETFs','current_announcement_evidence':'SEC N-14 000119312523215546 supports 2023-06-14 date-only constituent evidence','missing_announcement_fields':'earliest_public_announcement_at timestamp/uncertainty and proof it is earliest across all five constituents','current_implementation_evidence':'repository effective 2023-11-17 only','missing_implementation_fields':'each constituent legal_effective_at or first_trading_at with source accession; max/rule-selected I_w','current_sponsor_evidence':'Fidelity Management & Research Company LLC adviser field only','missing_sponsor_evidence':'canonical_sponsor_id, sponsor role, evidence accession, all-five constituent package membership'},
])
missing.to_csv(OUT/'missing_primary_package_evidence.csv',index=False,lineterminator='\n')

sources=[pkg_path,filing_path,exposure_path,universe_path,cohort_path,overlap_path,recovered_path,
 CONTRACT,
 SPONSOR_XWALK,
 ROOT/'missing_data_round_20260914/build_strict_preannouncement_holdings.py',
 ROOT/'missing_data_round_20260914/build_preannouncement_holdings.py',ROOT/'missing_data_round_20260914/build_scc_exposure.py',
 ROOT/'missing_data_round_20260914/build_competing_conversion_flags.py',ADV/'exposure/exposure_stock_wave_all.csv',
 ROOT/'recovered_candidate_support_20260915/full_artifacts/candidate_conversion_status_aggregate.csv']
receipt={
 'status':'PACKAGE_PROVENANCE_INVENTORY_COMPLETE','requested_routing':'Sol/medium','backend_telemetry':'NOT_OBSERVED',
 'code_sha256':sha(__file__),
 'packages':5,'included_predecessor_series':12,'positive_exposure_stock_wave_rows':4191,'recovered99_stock_wave_keys':99,
 'announcement_earliest_public_timestamp_ready_packages':0,'holdings_strictly_pre_recorded_cutoff_packages':5,
 'recovered99_competing_conversion_status':'UNKNOWN','outcomes_quotes_financial_values_read':False,'network_or_live_wrds_used':False,
 'source_hashes':{str(p):sha(p) for p in sources},'output_hashes':{'package_readiness_ledger.csv':sha(OUT/'package_readiness_ledger.csv'),'missing_primary_package_evidence.csv':sha(OUT/'missing_primary_package_evidence.csv')},
 'invariants':{'five_target_packages_only':True,'explicit_metadata_usecols':True,'old_40_roster_not_relabelled_recovered99':True,'permno_identity_status_not_relabelled_competing_conversion':True,'no_final_clock_eligibility_claim':True,'missing_not_zero':True},
 'next_action':{
   'name':'BUILD_RECOVERED99_CONCURRENT_CONVERSION_PROVENANCE_SIDECAR',
   'operation':'On SCC, join protected recovered99 candidate keys [candidate_id,wave_id,permno] to existing exposure_stock_wave_all.csv [permno,wave_id,effective_date] for every other wave, then attach exposure_universe_gate0_pass.csv [wave_id,effective_date,adviser,pre_series_id,post_series_id]. Emit protected candidate-by-other-wave evidence rows and local aggregates. Label sponsor provenance ADVISER_ONLY and both announcement/implementation clocks UNKNOWN wherever the exact fields listed in missing_primary_package_evidence.csv are absent; do not create a clean/exclude boolean.',
   'reason':'This mechanical, currently authorized join extends the existing effective-date evidence to the exact 99-key denominator without waiting for or inventing missing primary provenance.'
 }
}
(OUT/'INVENTORY_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:receipt[k] for k in ['status','packages','included_predecessor_series','positive_exposure_stock_wave_rows','recovered99_stock_wave_keys','announcement_earliest_public_timestamp_ready_packages','holdings_strictly_pre_recorded_cutoff_packages']}))
