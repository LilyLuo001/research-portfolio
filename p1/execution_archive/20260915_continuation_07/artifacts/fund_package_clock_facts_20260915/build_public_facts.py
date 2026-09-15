#!/usr/bin/env python3
from pathlib import Path
import hashlib, json
import pandas as pd

BASE=Path('/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot')
SRC=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1')
OUT=BASE/'fund_package_clock_facts_20260915'
GATE=SRC/'exposure/exposure_universe_gate0_pass.csv'
MASTER=SRC/'universe_v2/output/event_master_final_reconciled.csv'
PACKAGE=BASE/'missing_data_round_20260914/PACKAGE_INPUTS.csv'
SELECTED=BASE/'missing_data_round_20260914/SELECTED_PREANNOUNCEMENT_FILINGS.csv'

PACKAGES={
 'S000000972':('W002_DFA_US_TAX_MANAGED_4','FOCAL_MAIN','SYNCHRONIZED_4_CONSTITUENTS_PRIMARY_MEMBERSHIP','2021-03-03','SEC_N14_FILING_DATE','0001794202-21-000086','KNOWN_EARLIER_2020_11_16_17_SIGNAL_NOT_PREDECESSOR_LINKED'),
 'S000000976':('W002_DFA_US_TAX_MANAGED_4','FOCAL_MAIN','SYNCHRONIZED_4_CONSTITUENTS_PRIMARY_MEMBERSHIP','2021-03-03','SEC_N14_FILING_DATE','0001794202-21-000086','KNOWN_EARLIER_2020_11_16_17_SIGNAL_NOT_PREDECESSOR_LINKED'),
 'S000000977':('W002_DFA_US_TAX_MANAGED_4','FOCAL_MAIN','SYNCHRONIZED_4_CONSTITUENTS_PRIMARY_MEMBERSHIP','2021-03-03','SEC_N14_FILING_DATE','0001794202-21-000086','KNOWN_EARLIER_2020_11_16_17_SIGNAL_NOT_PREDECESSOR_LINKED'),
 'S000016732':('W002_DFA_US_TAX_MANAGED_4','FOCAL_MAIN','SYNCHRONIZED_4_CONSTITUENTS_PRIMARY_MEMBERSHIP','2021-03-03','SEC_N14_FILING_DATE','0001794202-21-000086','KNOWN_EARLIER_2020_11_16_17_SIGNAL_NOT_PREDECESSOR_LINKED'),
 'S000047047':('W013_BRANDYWINE_DYNAMIC_US_LCV_1','FOCAL_MAIN','SINGLE_CONSTITUENT','2021-12-14','SEC_497K_PUBLIC_FILING_DATE','0001193125-21-356806','BOARD_2021_11_02_03_DISCLOSED_LATER;SUPPLIED_DECEMBER_SIGNAL'),
 'S000030751':('W016_BRIDGEWAY_OMNI_1','FOCAL_STRESS','SINGLE_CONSTITUENT','2022-08-26','PRIMARY_ADVISER_FAQ_DATE','0001829126-22-018075','NONE_EARLIER_LOCATED_IN_BOUNDED_EXISTING_EVIDENCE'),
 'S000032550':('W021_JPM_EQUITY_FOCUS_1','FOCAL_MAIN','EQUITY_CONSTITUENT_SEPARATE_FROM_SAME_DATE_BOND','2023-02-13','SEC_425_PUBLIC_FILING_DATE','0001193125-23-034520','KNOWN_2022_12_15_PRIOR_SUPPLEMENT_REFERENCED_NOT_DIRECTLY_PINNED'),
 'S000003492':('W021_JPM_LIMITED_DURATION_BOND_1','EXCLUDED_BOND','SEPARATE_PACKAGE_SAME_DATE_BUCKET','2023-02-13','SEC_425_PUBLIC_FILING_DATE','0001193125-23-034520','KNOWN_2022_12_15_PRIOR_SUPPLEMENT_REFERENCED_NOT_DIRECTLY_PINNED'),
 'S000015909':('W025_FIDELITY_ENHANCED_US_EQUITY_5','FOCAL_MAIN','SYNCHRONIZED_5_US_EQUITY_CONSTITUENTS','2023-08-18','SEC_N14_PUBLIC_FILING_DATE','0001193125-23-215546','KNOWN_JUNE_2023_ISSUER_PLAN_AND_2023_06_14_BOARD_DATE'),
 'S000015910':('W025_FIDELITY_ENHANCED_US_EQUITY_5','FOCAL_MAIN','SYNCHRONIZED_5_US_EQUITY_CONSTITUENTS','2023-08-18','SEC_N14_PUBLIC_FILING_DATE','0001193125-23-215546','KNOWN_JUNE_2023_ISSUER_PLAN_AND_2023_06_14_BOARD_DATE'),
 'S000015911':('W025_FIDELITY_ENHANCED_US_EQUITY_5','FOCAL_MAIN','SYNCHRONIZED_5_US_EQUITY_CONSTITUENTS','2023-08-18','SEC_N14_PUBLIC_FILING_DATE','0001193125-23-215546','KNOWN_JUNE_2023_ISSUER_PLAN_AND_2023_06_14_BOARD_DATE'),
 'S000019927':('W025_FIDELITY_ENHANCED_US_EQUITY_5','FOCAL_MAIN','SYNCHRONIZED_5_US_EQUITY_CONSTITUENTS','2023-08-18','SEC_N14_PUBLIC_FILING_DATE','0001193125-23-215546','KNOWN_JUNE_2023_ISSUER_PLAN_AND_2023_06_14_BOARD_DATE'),
 'S000019928':('W025_FIDELITY_ENHANCED_US_EQUITY_5','FOCAL_MAIN','SYNCHRONIZED_5_US_EQUITY_CONSTITUENTS','2023-08-18','SEC_N14_PUBLIC_FILING_DATE','0001193125-23-215546','KNOWN_JUNE_2023_ISSUER_PLAN_AND_2023_06_14_BOARD_DATE'),
 'S000001015':('W006_DFA_MARKETWIDE_VALUE_1','OTHER_WAVE_CONSTITUENT','INDEPENDENT_DFA_PACKAGE_NOT_JPM','2022-02-18','SEC_N14_PUBLIC_FILING_DATE','0001794202-22-000042','NONE_EARLIER_LOCATED_IN_BOUNDED_EXISTING_EVIDENCE'),
 'S000003858':('W006_JPM_MARKET_EXPANSION_1','OTHER_WAVE_CONSTITUENT','INDEPENDENT_JPM_PACKAGE_NOT_DFA','2022-01-19','SEC_PUBLIC_FILING_DATE','0001193125-22-012596','NONE_EARLIER_LOCATED_IN_BOUNDED_EXISTING_EVIDENCE'),
 'S000008429':('W032_MORGAN_STANLEY_PATHWAY_2','OTHER_WAVE_CONSTITUENT','SYNCHRONIZED_2_CONSTITUENTS_PRIMARY_MEMBERSHIP','2024-08-20','SEC_N14_PUBLIC_FILING_DATE','0001193125-24-203605','NONE_EARLIER_LOCATED_IN_BOUNDED_EXISTING_EVIDENCE'),
 'S000008433':('W032_MORGAN_STANLEY_PATHWAY_2','OTHER_WAVE_CONSTITUENT','SYNCHRONIZED_2_CONSTITUENTS_PRIMARY_MEMBERSHIP','2024-08-20','SEC_N14_PUBLIC_FILING_DATE','0001193125-24-203605','NONE_EARLIER_LOCATED_IN_BOUNDED_EXISTING_EVIDENCE'),
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

gate=pd.read_csv(GATE,usecols=['event_id','wave_id','effective_date','adviser','pre_series_id','pre_series_name','pre_cik','post_series_id','post_series_name','post_cik','pre_report_date','pre_accession','gate0'],dtype=str)
gate=gate[gate.pre_series_id.isin(PACKAGES)].copy()
master=pd.read_csv(MASTER,usecols=['pre_series_id','n14_first_filed','supporting_accessions','a_close_date','a_accession','final_effective_date','final_precision','final_source_accession','verified_effective_date','verified_date_source_accession','verified_date_source_form'],dtype=str)
package=pd.read_csv(PACKAGE,usecols=['wave_id','role','pre_series_id','include_in_equity_package'],dtype=str)
package['include_in_equity_package']=package.include_in_equity_package.str.lower().eq('true')
facts=gate.merge(master,on='pre_series_id',how='left',validate='one_to_one')
facts=facts.rename(columns={'pre_report_date':'legacy_gate0_pre_report_date'})
selected=pd.read_csv(SELECTED,usecols=['wave_id','pre_series_id','report_date','cache_sha256','source_locator'],dtype=str).rename(columns={'report_date':'selected_preannouncement_report_date','cache_sha256':'selected_holding_cache_sha256','source_locator':'selected_holding_source_locator'})
facts=facts.merge(selected,on=['wave_id','pre_series_id'],how='left',validate='one_to_one')
vals=facts.pre_series_id.map(PACKAGES)
facts[['package_id','package_role','package_membership_status','announcement_interval_start_date','announcement_fact_type','announcement_source_accession','known_earlier_signal']]=pd.DataFrame(vals.tolist(),index=facts.index)
# A later filing is evidence observed by that date, not proof that A_w starts then.
facts=facts.rename(columns={'announcement_interval_start_date':'known_public_fact_date'})
# Two earlier focal-package sources were pinned by the bounded primary repair.
facts.loc[facts.wave_id.eq('W021'),'known_public_fact_date']='2022-12-15'
facts.loc[facts.wave_id.eq('W021'),'announcement_fact_type']='SEC_497K_PUBLIC_SUPPLEMENT_DATE'
facts.loc[facts.wave_id.eq('W021'),'announcement_source_accession']='0001193125-22-305394'
facts.loc[facts.wave_id.eq('W025'),'known_public_fact_date']='2023-06-28'
facts.loc[facts.wave_id.eq('W025'),'announcement_fact_type']='SEC_PUBLIC_SUPPLEMENT_DATE'
facts.loc[facts.wave_id.eq('W025'),'announcement_source_accession']='0001364923-23-000040'
facts['announcement_lower_bound_date']=pd.NA
facts['announcement_upper_bound_date']=facts.known_public_fact_date
facts['announcement_lower_bound_date']=facts.known_public_fact_date
facts.loc[facts.wave_id.eq('W002'),'announcement_lower_bound_date']='2020-11-16'
facts.loc[facts.wave_id.eq('W021'),'announcement_upper_bound_date']='2022-12-15'
facts.loc[facts.wave_id.eq('W025'),'announcement_lower_bound_date']='2023-06-01'
facts.loc[facts.wave_id.eq('W025'),'announcement_upper_bound_date']='2023-06-28'
facts['announcement_bound_status']='DATE_ONLY_EARLIEST_DIRECTLY_VERIFIED_SOURCE_LOCATED_IN_BOUNDED_EVIDENCE;NO_GLOBAL_COMPLETENESS_CLAIM'
facts.loc[facts.wave_id.eq('W002'),'announcement_bound_status']='PLAUSIBLE_INTERVAL_FROM_UNRESOLVED_2020_11_16_17_SIGNAL_TO_DIRECT_PREDECESSOR_LINKED_SEC_N14_2021_03_03'
facts.loc[facts.wave_id.eq('W021'),'announcement_bound_status']='DATE_ONLY_EXACT_SEC_497K_SOURCE_PINNED;NO_EARLIER_SPECIFIC_SIGNAL_IN_BOUNDED_EVIDENCE'
facts.loc[facts.wave_id.eq('W025'),'announcement_bound_status']='CONSERVATIVE_JUNE_2023_ISSUER_PLAN_INTERVAL_TO_EXACT_SEC_SUPPLEMENT_2023_06_28;BOARD_DATE_NOT_ANNOUNCEMENT'
facts['known_earlier_signal_start_date']=pd.NA
facts['known_earlier_signal_end_date']=pd.NA
facts.loc[facts.wave_id.eq('W021'),['known_earlier_signal_start_date','known_earlier_signal_end_date']]=['2022-12-15','2022-12-15']
facts.loc[facts.wave_id.eq('W025'),['known_earlier_signal_start_date','known_earlier_signal_end_date']]=['2023-06-28','2023-06-28']
facts['announcement_time_precision']='DATE_OR_MONTH_ONLY;INTRADAY_AND_TIMEZONE_UNKNOWN'
facts['announcement_timezone']='UNKNOWN'
facts['selected_holdings_before_known_public_fact_date']=pd.to_datetime(facts.selected_preannouncement_report_date)<pd.to_datetime(facts.known_public_fact_date)
facts['selected_holdings_definitely_strictly_before_Aw']=(pd.to_datetime(facts.selected_preannouncement_report_date)<pd.to_datetime(facts.announcement_lower_bound_date)).astype(object)
facts.loc[facts.selected_preannouncement_report_date.isna(),'selected_holdings_definitely_strictly_before_Aw']=pd.NA
facts['implementation_verified_date']=facts.verified_effective_date.fillna(facts.final_effective_date)
facts['implementation_source_accession']=facts.verified_date_source_accession.fillna(facts.final_source_accession)
facts['implementation_precision']=facts.final_precision
facts['implementation_lower_bound_date']=facts.implementation_verified_date
facts['implementation_upper_bound_date']=facts.implementation_verified_date
facts['implementation_bound_status']='VERIFIED_DATE_ONLY;INTRADAY_AND_TIMEZONE_UNKNOWN'
facts.loc[facts.wave_id.eq('W002'),['implementation_lower_bound_date','implementation_upper_bound_date']]=['2021-06-11','2021-06-14']
facts.loc[facts.wave_id.eq('W002'),'implementation_bound_status']='LEGAL_COMPLETION_2021_06_11_TO_FIRST_LISTING_2021_06_14;CONTRACT_IW_SELECTION_NOT_REVALIDATED_HERE'
facts.loc[facts.wave_id.eq('W016'),['implementation_lower_bound_date','implementation_upper_bound_date']]=['2023-03-10','2023-03-13']
facts.loc[facts.wave_id.eq('W016'),'implementation_bound_status']='REPOSITORY_EFFECTIVE_2023_03_10_TO_PUBLIC_OPERATION_2023_03_13;CONTRACT_IW_SELECTION_NOT_REVALIDATED_HERE'
facts.loc[facts.wave_id.eq('W032'),['implementation_lower_bound_date','implementation_upper_bound_date']]=['2024-12-06','2024-12-09']
facts.loc[facts.wave_id.eq('W032'),'implementation_bound_status']='ASSET_ACQUISITION_COB_2024_12_06_TO_VERIFIED_REORGANIZATION_2024_12_09;EXPECTED_NOVEMBER_DATES_NOT_COMPLETION'
facts['first_trading_date_fact']='UNKNOWN'
facts.loc[facts.wave_id=='W002','first_trading_date_fact']='2021-06-14_ISSUER_LISTING'
facts.loc[facts.wave_id=='W016','first_trading_date_fact']='2023-03-13_REPOSITORY_PUBLIC_OPERATION_DATE_NOT_REVALIDATED_HERE'
facts.loc[facts.wave_id=='W032','first_trading_date_fact']='2024-11-18_EXPECTED_IN_ORIGINAL_N14_NOT_ACTUAL'
facts['typed_date_conflict']='NONE_OBSERVED'
facts.loc[facts.wave_id=='W032','typed_date_conflict']='EXPECTED_REORG_2024_11_15;EXPECTED_TRADING_2024_11_18;ASSET_ACQUISITION_COB_2024_12_06_SNIPPET;VERIFIED_COMPLETION_2024_12_09'
facts.loc[facts.pre_series_id=='S000003858','typed_date_conflict']='IMPLEMENTATION_SOURCE_ACCESSION_LOCAL_MASTER_0001193125_22_143769_VS_PRIMARY_CHECK_0001193125_22_143758;BOTH_SUPPORT_2022_05_06_COB'
facts['sponsor_fact_status']='ADVISER_AND_CONSTITUENT_SOURCE_OBSERVED_NOT_CANONICAL_SPONSOR_ID'
facts['split_and_pro_rata_status']='PROVISIONAL_NOT_CERTIFIED'
facts['clock_eligibility_fact_status']='SUPPORTED_DATE_INTERVAL_ONLY;BOUNDARY_CROSSERS_UNKNOWN;INTRADAY_AND_TIMEZONE_NOT_CERTIFIED'
facts['final_clean_or_exclude_status']='NOT_ASSIGNED_BY_PUBLIC_FACT_TABLE'
facts=facts.sort_values(['wave_id','package_id','pre_series_id'])
assert len(facts)==17 and set(facts.pre_series_id)==set(PACKAGES)
assert facts.loc[facts.wave_id.eq('W021'),'selected_holdings_before_known_public_fact_date'].eq(False).all()
assert facts.loc[facts.wave_id.isin(['W002','W013','W016','W025']),'selected_holdings_definitely_strictly_before_Aw'].eq(True).all()
assert facts[facts.wave_id=='W006'].package_id.nunique()==2
assert facts[facts.wave_id=='W032'].package_id.nunique()==1
# The pinned package input is used only to validate the 13 focal source series and
# the explicit W021 bond exclusion; it does not define the two other-wave packages.
expected_focal=set(facts[facts.package_role.isin(['FOCAL_MAIN','FOCAL_STRESS','EXCLUDED_BOND'])].pre_series_id)
package_focal=package[package.wave_id.isin(['W002','W013','W016','W021','W025'])]
assert set(package_focal.pre_series_id)==expected_focal
assert package_focal.loc[package_focal.pre_series_id.eq('S000003492'),'include_in_equity_package'].eq(False).all()
assert package_focal.loc[~package_focal.pre_series_id.eq('S000003492'),'include_in_equity_package'].eq(True).all()
facts.to_csv(OUT/'fund_package_clock_facts.csv',index=False)

holdings=[]
for _,r in facts.iterrows():
    holdings.append({'wave_id':r.wave_id,'pre_series_id':r.pre_series_id,'holdings_version':'LEGACY_GATE0_PRE_EFFECTIVE','report_date':r.legacy_gate0_pre_report_date,'source_locator':str(GATE),'strict_pre_Aw_status':'NOT_ASSESSED_AS_PREANNOUNCEMENT_SOURCE'})
    if pd.notna(r.selected_preannouncement_report_date):
        holdings.append({'wave_id':r.wave_id,'pre_series_id':r.pre_series_id,'holdings_version':'SELECTED_PREANNOUNCEMENT_FILINGS_20260914','report_date':r.selected_preannouncement_report_date,'source_locator':r.selected_holding_source_locator,'strict_pre_Aw_status':'SUPPORTED_STRICTLY_PRE_AW_INTERVAL' if bool(r.selected_holdings_definitely_strictly_before_Aw) else 'FAILS_STRICTLY_PRE_AW_INTERVAL'})
holdings=pd.DataFrame(holdings).sort_values(['wave_id','pre_series_id','holdings_version'])
holdings.to_csv(OUT/'holdings_date_version_facts.csv',index=False)

pkg=facts.groupby(['wave_id','package_id','package_role','package_membership_status'],as_index=False).agg(constituents=('pre_series_id','nunique'),known_public_fact_date=('known_public_fact_date','min'),announcement_lower_bound_date=('announcement_lower_bound_date','min'),announcement_upper_bound_date=('announcement_upper_bound_date','min'),announcement_bound_status=('announcement_bound_status','first'),implementation_lower_bound_date=('implementation_lower_bound_date','max'),implementation_upper_bound_date=('implementation_upper_bound_date','max'),implementation_bound_status=('implementation_bound_status','first'),selected_holdings_before_known_public_fact=('selected_holdings_before_known_public_fact_date','all'),selected_holdings_definitely_strictly_before_Aw=('selected_holdings_definitely_strictly_before_Aw','all'),split_and_pro_rata_status=('split_and_pro_rata_status','first'))
hc=facts.groupby(['wave_id','package_id'],as_index=False).agg(selected_holding_rows=('selected_preannouncement_report_date','count'))
pkg=pkg.merge(hc,on=['wave_id','package_id'],validate='one_to_one')
pkg['selected_holdings_Aw_status']='SUPPORTED_ALL_CONSTITUENTS_STRICTLY_PRE_AW_INTERVAL'
pkg.loc[pkg.selected_holding_rows.lt(pkg.constituents),'selected_holdings_Aw_status']='NOT_AVAILABLE_FOR_ALL_CONSTITUENTS'
pkg.loc[pkg.selected_holding_rows.eq(pkg.constituents)&~pkg.selected_holdings_definitely_strictly_before_Aw,'selected_holdings_Aw_status']='FAILS_STRICTLY_PRE_AW_INTERVAL'
pkg.to_csv(OUT/'package_fact_summary.csv',index=False)
receipt={'status':'PUBLIC_FUND_PACKAGE_CLOCK_FACTS_COMPLETE','counts':{'fund_series_rows':len(facts),'package_rows':len(pkg),'holdings_version_rows':len(holdings),'focal_included_series':int(facts.package_role.isin(['FOCAL_MAIN','FOCAL_STRESS']).sum()),'excluded_bond_series':int((facts.package_role=='EXCLUDED_BOND').sum()),'other_wave_series':int((facts.package_role=='OTHER_WAVE_CONSTITUENT').sum())},'invariants':{'17_expected_series':bool(len(facts)==17),'w021_selected_holding_is_after_known_public_fact_date':bool(facts.loc[facts.wave_id.eq('W021'),'selected_holdings_before_known_public_fact_date'].eq(False).all()),'other_four_focal_selected_holdings_strictly_pre_Aw_interval':bool(facts.loc[facts.wave_id.isin(['W002','W013','W016','W025']),'selected_holdings_definitely_strictly_before_Aw'].eq(True).all()),'legacy_gate0_holdings_not_promoted_to_preannouncement':bool(holdings.loc[holdings.holdings_version.eq('LEGACY_GATE0_PRE_EFFECTIVE'),'strict_pre_Aw_status'].eq('NOT_ASSESSED_AS_PREANNOUNCEMENT_SOURCE').all()),'package_A_uses_min_constituent_bounds':bool(pkg.announcement_lower_bound_date.notna().all() and pkg.announcement_upper_bound_date.notna().all()),'w006_two_independent_packages':bool(facts[facts.wave_id=='W006'].package_id.nunique()==2),'w032_one_two_constituent_package':bool(facts[facts.wave_id=='W032'].package_id.nunique()==1 and len(facts[facts.wave_id=='W032'])==2),'pinned_focal_package_series_exact':bool(set(package_focal.pre_series_id)==expected_focal),'w021_bond_exclusion_matches_pinned_input':bool(package_focal.loc[package_focal.pre_series_id.eq('S000003492'),'include_in_equity_package'].eq(False).all()),'no_clean_exclude_assigned':bool(facts.final_clean_or_exclude_status.eq('NOT_ASSIGNED_BY_PUBLIC_FACT_TABLE').all())},'input_sha256':{str(p):sha(p) for p in [GATE,MASTER,PACKAGE,SELECTED]},'output_sha256':{str(OUT/'fund_package_clock_facts.csv'):sha(OUT/'fund_package_clock_facts.csv'),str(OUT/'package_fact_summary.csv'):sha(OUT/'package_fact_summary.csv'),str(OUT/'holdings_date_version_facts.csv'):sha(OUT/'holdings_date_version_facts.csv')},'public_primary_locators':['SEC accessions in announcement_source_accession and implementation_source_accession','primary_package_checks_20260915/FINDINGS.md','primary_announcement_repair_20260915/FINDINGS.md'],'backend_telemetry':'NOT_OBSERVED'}
(OUT/'PUBLIC_FACTS_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
