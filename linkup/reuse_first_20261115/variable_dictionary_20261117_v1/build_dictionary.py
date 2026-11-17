"""Build a versioned metadata dictionary; never reads advertisements or calls models."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json

VERSION = '1.0.0'
P = 'linkup/reuse_first_20261115/'
SOURCES = {
    'scope': P+'execution_20261116/continuation02/final/GAP_REGISTER_PUBLIC.json',
    'field_counts': P+'integration_20261116/FIELD_STATUS_COUNTS_PUBLIC.json',
    'base_schema': 'linkup/corpus_release_20261012/results/SCHEMA_PUBLIC.json',
    'old_reuse_map': 'linkup/analysis_transition_20260930/reuse_analysis_20261010/FIELD_REUSE_MAP_PUBLIC.json',
    'delta_inventory': 'linkup/analysis_transition_20260930/reuse_expansion_20261010/D67_COMPLETED_INVENTORY_PUBLIC.json',
    'delta_code': 'linkup/analysis_transition_20260930/reuse_expansion_20261010/code/project_one_shard.py',
    'formal_schema': 'linkup/formal800_20261012/FORMAL800_REVIEW_SCHEMA.json',
    'formal_instructions': 'linkup/formal800_20261012/REVIEW_INSTRUCTIONS.md',
    'attachment_code': P+'execution_20261116/code/cloud_stage2_values.py',
    'base_capabilities': P+'reuse_audit_20261116/EXISTING_BASE_CAPABILITIES_PUBLIC.json',
    'semantic_assets': P+'reuse_audit_20261116/HISTORICAL_SEMANTIC_ASSETS_PUBLIC.json',
    'research_agenda': P+'research_agenda_recovery_20261116/RESEARCH_AGENDA_AND_MEASUREMENT_ZH.md',
    'five_module_contract': P+'measurement_protocol_20261117/FIVE_MODULE_CONTRACT_PUBLIC.json',
    'shadow': P+'measurement_protocol_20261117/SHADOW_DIAGNOSTIC_PUBLIC.json',
}
MODULES = {'A':'机会重新分配','B':'经历重新组合','C':'工作职责演变','D':'人员进入路径','E':'早期计算机化对比','X':'共用身份与来源'}
STATUS = {
    'structural_reuse':'已有结构数据，可按原口径复用',
    'partial_semantic_reuse':'已有部分语义，按原验收范围复用',
    'proxy_only':'已有规则候选，不等于新语义变量',
    'derive_pending':'已有部分输入，派生与连接待完成',
    'new_definition':'新结构或分类，旧结果不能直接填满',
    'external_pending':'待外部数据交付及字段核验',
    'scope_pending':'全交付范围与覆盖待核清',
}
GLOBAL_REUSE_GUARD = [
    '先按保护集合排除；隔离项不得读取、推理或自动重跑',
    '原四键身份映射保留；不能只用JOB_HASH或JOB_HASH+CREATED消除多对多',
    '语义复用同时核验完整规范上下文指纹、原schema/指令版本和原字段验收掩码',
    '同名列不是同义列；规则输出保持legacy_proxy版本，不晋升新语义真值',
    '保留多个PRIMARY和冲突，不采用latest-wins；已审未知不变成否定或自动待重跑',
    '字段缺失数按同一交付范围、去重单位和版本计算；不同资产覆盖不能相加',
]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    def readrel(p):return json.loads((a.repo/p).read_text())
    source_records={k:{'repository_relative_path':v,'sha256':hashlib.sha256((a.repo/v).read_bytes()).hexdigest()} for k,v in SOURCES.items()}
    scope=readrel(SOURCES['scope']);counts=readrel(SOURCES['field_counts']);variables=[];mapping=[]
    def add(key,label,module,unit,dtype,definition,values,status,need,deps=(),sources=(),note=''):
        variables.append({'variable_key':key,'definition_version':VERSION,'label_zh':label,'modules':list(module),'unit':unit,'type':dtype,'definition_zh':definition,'allowed_values_or_units':values,'availability_code':status,'availability_zh':STATUS[status],'remaining_work_zh':need,'dependencies':list(deps),'source_refs':list(sources),'missingness_rule':'未处理无测量值；未提及只用于已完整审阅文本；歧义/冲突为unknown；工程失败单列；数值缺失不是0。','interpretation_limit_zh':note,'full_delivery_missing_inputs':None})
    def mapto(key,asset,selector,mode,coverage,need,refs,transform='原值原版本保留，不重判'):
        mapping.append({'variable_key':key,'asset_key':asset,'source_selector':selector,'reuse_mode':mode,'coverage_basis_zh':coverage,'transform_zh':transform,'remaining_or_blocking_zh':need,'source_refs':refs,'new_semantic_acceptance_granted':False})
    def structural(key,label,unit,dtype,definition,values,selector,coverage,need='仅补真实缺键；全量非空率尚未核清',module='X',asset='BASE_RECORDS',refs=('base_schema','scope')):
        add(key,label,module,unit,dtype,definition,values,'structural_reuse',need,sources=refs)
        mapto(key,asset,selector,'exact_copy_or_keyed_metadata_join',coverage,need,list(refs))
    def semantic(key,label,module,unit,dtype,definition,values,selector,need='保留兼容旧值；全交付覆盖与新增路线资格未完成',deps=(),note=''):
        if '[*]' in selector:deps=tuple(dict.fromkeys([*deps,'lk.claim.item_anchor']))
        add(key,label,module,unit,dtype,definition,values,'partial_semantic_reuse',need,deps,('formal_schema','field_counts','attachment_code'),note)
        mapto(key,'FORMAL800_PRO_ACCEPTED',selector,'same_definition_original_mask_only','历史字段投影Pro31,690上下文，不是当前全部载体的最新字段普查；Formal800等重叠不可相加',need,['formal_schema','field_counts','attachment_code'])
    structural('lk.identity.ad_key','广告来源四键','广告源记录','tuple','保留JOB_HASH、SOURCE_FILE、SOURCE_ROW、RECORD_SOURCE_ROW四元组及其上下文映射','四键；跨来源多重对应单列','ad.k / JOB_HASH+SOURCE_FILE+SOURCE_ROW+RECORD_SOURCE_ROW','当前细语义映射62,414个四键；US基础204,774,035广告，口径不同',need='完整交付去重广告数仍未知，不能按五亿减US底库',refs=('scope','attachment_code'))
    structural('lk.identity.context','规范正文指纹','规范完整上下文','string','按固定正文标准化版本计算的全文指纹；不是广告身份','fingerprint + normalizer_version','document.h / context_sha256','细语义总账55,882上下文',need='复用时同时核对版本；不以同广告推定同正文',refs=('scope','attachment_code'))
    structural('lk.provenance.source','原成果来源与版本','字段载体','struct','保留资产、原文件SHA、原行号、schema/指令/代码版本和掩码','asset/source_sha/source_ordinal/version/mask','document.*; field_mask; accepted_original_values.*','39,298原验收上下文有载体；10个缺载体',need='保留67组多PRIMARY；找不到载体不重跑',refs=('scope','attachment_code'))
    structural('lk.time.created','首次观察日期代理','广告源记录','datetime','数据库CREATED作为岗位首次观察时间代理，绝不宣称正文生成时间','保留原精度和日期质量','metadata_resolution.created / CREATED','62,414现有四键已完成连接；45,592四键有原验收值',module='ABCDE',refs=('scope','base_capabilities'),need='其余全量元数据连接和覆盖待核；不重连现有62,414键')
    for key,label,selector,definition,dtype in [
        ('lk.time.delete','删除/退出观察日期','DELETE_DATE','供应商记录的删除日期；不是已招到人时间','datetime'),
        ('lk.time.last_checked','最后检查日期','LAST_CHECKED','最后一次来源检查时间，不能当作新增岗位时间','datetime'),
        ('lk.time.last_updated','最后更新日期','LAST_UPDATED','来源更新记录时间，不自动表示重新招聘','datetime'),
        ('lk.company.vendor_id','供应商公司标识','COMPANY_ID','保留原供应商公司标识；不等于跨库统一雇主','string'),
        ('lk.job.title','原岗位名称','TITLE / metadata_title','保留原岗位名称，不直接据此认定经验或初级','string'),
        ('lk.geo','国家与地区','COUNTRY / STATE / CENSUS_REGION','保留供应商地理字段及映射版本、未知状态','struct'),
        ('lk.occupation','职业映射','OCCUPATION_MAJOR + mapping_version','职业代码及版本，未映射不硬补','struct')]:
        structural(key,label,'广告源记录',dtype,definition,'原字段及其缺失/映射状态',selector,'候选6,010,975有保留metadata连接；D67 5,804,936与其及底库可重叠','按资产核字段存在与非空；全库宽表并非已留存',module='ABCDE',refs=('base_capabilities','base_schema'))
    # Source fields and coverage differ across existing metadata assets.
    for m in mapping:
        if m['variable_key']=='lk.job.title':
            m.update(asset_key='FIXED10K_METADATA',source_selector='TITLE / metadata_title (source-specific)',coverage_basis_zh='固定10,000广告已有标题；Records窄索引不含TITLE',remaining_or_blocking_zh='全范围标题可用性待源schema核验；不能从窄索引猜出TITLE')
        elif m['variable_key'] in ['lk.time.delete','lk.time.last_checked','lk.time.last_updated','lk.company.vendor_id','lk.geo']:
            m.update(asset_key='RECORDS_INDEX_AND_SCOPED_METADATA',coverage_basis_zh='Records窄索引269原文件/356,449,214原始行中列存在；字段非空覆盖不等于行数；fixed10k另有已有值',remaining_or_blocking_zh='按来源列绑定；fixed10k DELETE_DATE9,702、LAST_UPDATED2,081；不宣称全库非空')
            if m['variable_key']=='lk.geo':m['source_selector']='Records index: COUNTRY/STATE; retained candidate metadata: CENSUS_REGION'
        elif m['variable_key']=='lk.occupation':
            m.update(asset_key='CANDIDATE_METADATA_AND_D67',source_selector='candidate metadata: OCCUPATION_MAJOR; D67: ONET_OCCUPATION_CODE/official_occupation_status',coverage_basis_zh='候选6,010,975：ONET唯一匹配6,008,133，缺2,842；D67重叠不能相加')
    add('lk.industry','雇主行业及时间有效性','ABDE','雇主×时期','code','用版本化行业映射描述雇主所在行业，不用广告中要求的行业经验替代','行业代码/层级/有效期/unknown','derive_pending','先核现有行业供应商字段和企业桥表；本轮未确认全量逐行可用',('lk.company.vendor_id',),('research_agenda',))
    structural('lk.input.quality','原输入与工程可用性','广告源记录','struct','保留空正文、解析错、证据截断与enrichment不完整标记，不将工程usable解释为语义准确','usable/DESCRIPTION_EMPTY/PARSE_ERROR/INPUT_EVIDENCE_TRUNCATED/ENRICHMENT_INCOMPLETE','ad_schema quality fields','旧底座204,774,035；工程usable204,768,752',need='消费旧标记并保留原因；不能丢失不可用记录',refs=('base_schema','base_capabilities'))
    structural('lk.document.completeness','正文审阅完整性','上下文','enum','原review的全文、部分或未决状态决定是否允许未提及断言','reviewed_full/reviewed_partial/unresolved','document.document_json.document_status','Pro31,690中29,671全文、1,911部分、108未决',refs=('field_counts','formal_schema'))
    add('lk.state.axes','字段状态与资格四轴','X','上下文×变量×版本','struct','执行进度、测量状态、工程有效性、路线资格分别存储，隔离为独立保护','workflow/measurement/engineering/route_qualification + quarantine','derive_pending','旧账本映射到新四轴，保留原状态；不能把未处理转未知',sources=('five_module_contract','scope'))
    mapto('lk.state.axes','GLOBAL_LEDGER','final_status + field_mask + source-specific masks','status_crosswalk_no_promotion','55,882上下文；原验收39,308、待验6,506、待对账10,012、隔离56','原验收并不表示所有字段已知',['scope','field_counts'])
    add('lk.evidence.ref','稳定证据编号和位置','BCE','原子主张×证据','struct','由程序绑定完整规范正文的证据编号、起止位置、原文来源与重复位置歧义','span_id/start/end/context_fingerprint/status','derive_pending','复用原引文/证据位置；新增稳定编号，不让模型重抄引文',('lk.identity.context','lk.provenance.source'),('formal_schema','shadow'))
    mapto('lk.evidence.ref','FORMAL800_PRO_ACCEPTED','*.quotes + evidence_resolution','derive_from_existing_evidence_only','有原值载体的兼容上下文；逐字段引文覆盖未统一量化','引文定位通过不是语义支持；重复位置不随意择一',['formal_schema','attachment_code'])
    dims={'general_work':'一般工作经历','occupation_task':'职业/任务经历','industry_domain':'行业/领域经历','tool_specific':'工具特定经历'}
    for dim,label in dims.items():
        key='lk.exp.'+dim
        semantic(key,label+'要求或偏好','B','上下文×经历类别','enum','是否至少有一项申请者明确、非豁免的'+label+'要求或偏好；明确豁免不构成present','present/not_mentioned/unknown','experience_outcomes.'+dim,note='要求与偏好由条款强度区分；四类经历可共存，不能相加成年限')
        if dim!='occupation_task':
            old='specific_tool' if dim=='tool_specific' else dim
            mapto(key,'BASE_LEGACY_PROXY','exp_'+old+'_{main,required,preferred,broad,exact_or_unspecified}','legacy_proxy_only','US基础204,774,035覆盖旧输出，不是该字段非空数','不得把旧规则列直接命名为新语义提及',['base_schema','old_reuse_map'])
        else:mapto(key,'BASE_LEGACY_PROXY','occupation_task structural NA','not_reusable_as_measurement','旧底座未形成该语义维度','消费D67和已验语义，不用旧NA当无经历',['old_reuse_map'])
        mapto(key,'D67_RULE_DELTA','kind=experience; parse objects_json; tool -> tool_specific; outcome_status','legacy_proxy_only','5,804,936广告增量与基础重叠','按旧候选映射版本解析；描述性规则候选不得直接升级',['delta_inventory','delta_code'])
    add('lk.claim.item_anchor','原子主张的同条款锚点','BCE','原载体×条款/条目','struct','以原文件SHA、原记录位置、数组路径和索引绑定所有原子，禁止不同条款的对象/年限/强度误拼','source_sha + source_ordinal + array_path + item_index + context','derive_pending','从已有载体确定性生成；不是新的语义标签',('lk.provenance.source','lk.identity.context'),('attachment_code','formal_schema'))
    for key,label,dtype,definition,values,selector in [
        ('lk.exp.object','经历对象类别','enum','每条经历主张的对象类别，保留unresolved','general_work/occupation_task/industry_domain/tool_specific/unresolved','experience_clauses[*].object'),
        ('lk.exp.object_label','对象原描述','string','保留原模型/原文对象描述；只是显示与溯源，不以字符串全等裁定语义','free_text','experience_clauses[*].object_detail'),
        ('lk.exp.years_min','对象年限下界','number?','仅为同一经历条款、同一对象绑定的字面年限下界','年；null不是0','experience_clauses[*].years_min'),
        ('lk.exp.years_max','对象年限上界','number?','同一经历条款的字面年限上界，不把无上界填0','年；null可为未写上界或未知，结合关系状态','experience_clauses[*].years_max'),
        ('lk.exp.years_relation','年限数值关系','enum','区分至少、区间、恰好、至多、未写和未决','at_least/range/exact/at_most/not_stated/unresolved','experience_clauses[*].years_relation'),
        ('lk.exp.strength','经历要求强度','enum','要求/优先/明确豁免作用于具体经历对象，不能跨对象传播','required/preferred/explicitly_waived/unspecified/unresolved','experience_clauses[*].strength'),
        ('lk.exp.conditionality','经历适用条件状态','enum','经历条款是否依赖其他条件；条件必须另保留','unconditional/conditional/unspecified/unresolved','experience_clauses[*].conditionality'),
        ('lk.qual.group_link','条款到资格分支连接','struct','保留条款与资格组、分支连接；null分支可为共享条件','group/branch/null','experience_clauses[*].alternative_group + alternative_branch'),
        ('lk.qual.legacy_groups','原资格组和分支','array','保留旧组的AND/OR、分支条件文字和引文，不假装已解析任意嵌套逻辑','group/relation/branches(condition,quotes)','qualification_alternatives[*]')]:
        semantic(key,label,'B','同一源经历条款' if key.startswith('lk.exp.') else '同一源资格组及被引用条款',dtype,definition,values,selector,deps=('lk.claim.item_anchor','lk.evidence.ref'))
    for v in variables:
        if v['variable_key'] in ['lk.exp.years_min','lk.exp.years_max','lk.exp.years_relation']:
            v['required_companion_bindings']=['lk.exp.object','lk.exp.strength','lk.exp.conditionality','lk.qual.group_link','lk.qual.legacy_groups']
            v['interpretation_limit_zh']='原值复制必须保留同一锚点及上述伴随属性；全局最低门槛还需完整资格路径，不跨条款取min。'
    for key,col in [('lk.exp.years_min','MIN_YEARS'),('lk.exp.years_max','MAX_YEARS'),('lk.exp.years_relation','BOUND_TYPE'),('lk.exp.strength','REQUIREMENT_STRENGTH')]:
        mapto(key,'BASE_DURATION_CANDIDATES',col+' + EVIDENCE_ORDINAL + OBJECT_TYPE + DURATION_UNIT','legacy_literal_evidence_only','131,286,035条旧duration证据行，不是独立广告数','保留四键和单位；字面数字不是语义正确对象绑定',['base_schema','base_capabilities'])
    add('lk.exp.bound_inclusivity','年限边界是否含等号','B','同一源经历条款','enum','区分严格大于与至少；原schema未给完整独立开闭区间字段，不补猜','inclusive/exclusive/unspecified/unknown','new_definition','可保留D67 strict_lower候选；Formal年限不能自动补出开闭属性',('lk.claim.item_anchor','lk.exp.years_relation'),('formal_schema','delta_inventory'))
    mapto('lk.exp.bound_inclusivity','D67_RULE_DELTA','kind=experience; strict_lower + duration_kind/lower_years/upper_years','legacy_proxy_only','D67 5,804,936广告载体范围，非此属性已知数','保留同条款对象/强度/条件；新语义资格尚未确认',['delta_inventory','delta_code'])
    add('lk.qual.condition_atoms','学历/证照等资格条件原子','B','资格分支条件','struct','仅编码影响经验替代路径的学历、证照及其他明确条件；不把学历年数当工作年限','typed_condition + value + negation + evidence + unresolved','new_definition','旧branch.condition可复用文字，尚不能直接得到结构化学历/证照；只补研究所需条件',('lk.qual.legacy_groups','lk.claim.item_anchor'),('formal_schema','five_module_contract'))
    add('lk.exp.object_concept','规范对象概念编号','B','经历条款','code','在版本化对象词典中区分行业、职业任务、工具等概念；显示措辞与概念分开','concept_code + dictionary_version + unresolved','new_definition','旧object_detail不能仅靠换词序/相似度自动映射；需有限对象词典和歧义规则',('lk.exp.object','lk.exp.object_label'),('five_module_contract',))
    add('lk.qual.logic','可计算资格条件结构','B','相关资格组','logic_tree','完整保留相关AND/OR、否定、共享条件及嵌套作用范围；不确定分支保持unknown','atomic_nodes + typed_edges + completeness','new_definition','复用旧组/引用；结构化树及完整性尚未完成，不擅自把AND换OR',('lk.qual.group_link','lk.qual.legacy_groups','lk.qual.condition_atoms','lk.exp.strength'),('five_module_contract','formal_schema'))
    variables[-1]['conditional_dependencies']={'numeric_duration_condition':['lk.exp.years_min','lk.exp.years_max','lk.exp.years_relation','lk.exp.bound_inclusivity']}
    entry={'explicit_no_experience':'明确无经验要求','explicit_new_graduate':'明确欢迎应届','current_student_internship':'当前学生或实习','explicit_junior_or_entry_label':'明确初级/入门标签'}
    for dim,label in entry.items():semantic('lk.entry.'+dim,label,'ABC','上下文×entry维度','enum','按冻结定义记录'+label+'表述；不是统一的初级岗位真值','present/not_mentioned/unknown','entry_outcomes.'+dim,note='未写经验不是零经验；指导junior不是招聘junior')
    semantic('lk.entry.conditions','entry证据与条件','ABC','entry条款','array','保存每个entry目标对应的适用条件和证据','target/conditionality/quotes','entry_items[*]')
    duty={'independent_judgment':'独立判断','client_ownership':'客户责任','people_supervision':'人员监督','training_mentoring':'培训指导'}
    for dim,label in duty.items():semantic('lk.duty.'+dim,label+'广义责任信号','C','上下文×责任维度','enum','招聘岗位本人的明确'+label+'当前职责、要求能力或既往经验均可为present；不是纯当前职责','present/not_mentioned/unknown','responsibility_outcomes.'+dim,note='严格当前职责必须用同item主体和关系；旧四类不是完整任务包')
    for key,label,definition,values,sel in [
        ('lk.duty.subject','职责主体','区分招聘岗位本人、别人和公司整体','advertised_worker/other_employee/employer_general/unresolved','responsibility_items[*].subject'),
        ('lk.duty.relation','职责与时间关系','区分当前职责、要求能力、既往经历、他人和雇主描述','current_duty/required_capability/prior_experience/other_person/employer_description/unresolved','responsibility_items[*].relation'),
        ('lk.duty.conditions','职责条件与证据','职责条件必须附着到具体维度、主体及关系','dimension/conditionality/quotes','responsibility_items[*]')]:semantic(key,label,'C','职责条款','enum_or_struct',definition,values,sel)
    add('lk.duty.current','严格当前职责四维','C','上下文×职责维度','enum_vector','仅同一item满足subject=advertised_worker且relation=current_duty才构成当前职责阳性；判定未提及须完整相关库存，partial或关系未决不能据此判无','per_dimension present/not_mentioned/unknown','derive_pending','从兼容旧item确定性筛选并保留条件；不直接用responsibility_outcomes当当前职责',('lk.claim.item_anchor','lk.duty.subject','lk.duty.relation','lk.duty.conditions'),('formal_instructions','formal_schema'))
    mapto('lk.duty.current','FORMAL800_PRO_ACCEPTED','responsibility_items[*]: same item dimension + subject=advertised_worker + relation=current_duty','deterministic_derivation_not_new_annotation','原已验且条件/关系可用条目；整体not_mentioned还需完整相关审阅','保留原mask、partial和unknown；未投影为当前职责不等于无职责',['formal_schema','formal_instructions','attachment_code'])
    add('lk.task.activity','活动—对象任务原子','CE','任务条款','struct','记录当前岗位具体做什么及作用对象，覆盖执行、核验、协调等，不限原四职责','activity/object/subject/time/condition/evidence','new_definition','旧四职责只能提供局部信息，不能补出完整活动清单',('lk.duty.subject','lk.duty.relation','lk.evidence.ref'),('five_module_contract',))
    add('lk.task.code','版本化任务分类','CDE','任务条款','code','将任务原子映射到冻结任务分类及版本，为任务变化/跨职业距离提供共同口径','task_code/taxonomy_version/unmapped','new_definition','需任务分类和独立确认；现有旧四职责不自动等同完整任务维度',('lk.task.activity',),('five_module_contract','research_agenda'))
    for key,label,definition,values,sel in [
        ('lk.tech.inventory','技术提及库存状态','完整审阅下技术是否提及及是否未知','explicit_mentions_recorded/not_mentioned_after_full_review/unknown','technology_inventory_status'),
        ('lk.tech.entity','技术实体','保留明确技术实体名称，显示文字不直接作为同义判断标准','name + evidence','technology_items[*].technology'),
        ('lk.tech.family','技术类别','区分传统软件、预测AI、GenAI及未决','traditional_software_system/predictive_ml_ai/generative_ai/unresolved','technology_items[*].family'),
        ('lk.tech.role','技术与岗位角色关系','区分开发技术、实施部署、用工具工作和背景提及','develop_technology/implement_deploy_technology/use_tool_for_work/background_mention/unresolved','technology_items[*].role'),
        ('lk.tech.developed_object','实际开发对象','保留开发的对象，避免把用Tableau制作报表判为开发Tableau','free_text + context_note + evidence','technology_items[*].developed_object + context_note')]:semantic(key,label,'CE','技术条款或上下文','enum_or_text',definition,values,sel,note='提及不等于采用；未提及不等于未采用')
    for key,selector,asset in [('lk.tech.family','tech_*_detected; predictive_ai unavailable','BASE_LEGACY_PROXY'),('lk.tech.role','technology/role_cue/negated/tech_group','D67_RULE_DELTA'),('lk.entry.explicit_new_graduate','flags_json.graduate_language / kind=entry evidence','D67_RULE_DELTA'),('lk.duty.independent_judgment','flags_json.task_independent_responsibility','D67_RULE_DELTA')]:
        mapto(key,asset,selector,'legacy_proxy_only','对应旧底座或69片增量载体范围；非字段完整覆盖','旧predictive_ai全零为不可测；保留候选而非新语义真值',['old_reuse_map','delta_inventory','delta_code'])
    derived=[
      ('measure.new_ads','首次观察广告数量','A','职业/企业/地区×时期','按CREATED统计首次观察广告，先固定去重单位及来源覆盖',('lk.identity.ad_key','lk.time.created'),'MACRO_RECORDS','已有月度/年度汇总','已有253,210,047条US Records全历史，2016起199,644,730，非Description分母','structural_reuse','复用既有数量与职业构成；增量只补缺范围'),
      ('measure.active_ads','期末活跃广告存量','A','分组×时点','按实际生命周期及删失政策构造时点活跃，不将更新算新增',('lk.time.created','lk.time.delete','lk.time.last_checked'),'MACRO_RECORDS','已有月末活跃及缺删除敏感性','既有宏观范围；2026只到9月6日','structural_reuse','保留原missing-delete假设和同范围分母'),
      ('measure.exits','观察到的删除退出量','A','分组×时期','直接按合格删除日期计退出，删失与再出现单列',('lk.time.delete','lk.time.last_checked'),'MACRO_RECORDS','当前仅有存量恒等式退出诊断','直接DELETE_DATE退出维度表未交付','derive_pending','不能拿存量差代替直接退出量'),
      ('measure.entry_share','明确entry表述份额','A','分组×时期','四个entry维度分别报告，若合成指标必须固定条件规则；仅在实际已审范围计算并披露全体覆盖',tuple('lk.entry.'+d for d in entry),'PARTIAL_SEMANTIC_PLUS_RECORDS','entry_outcomes + four-key CREATED join','无全国同范围同时间语义标签的已确认交付','derive_pending','全国entry份额缺标签覆盖及拼接；不能用小样本替代全库'),
      ('measure.experience_bundle','经历要求组合','B','上下文或广告','保留一般/职业/行业/工具经历的对象、年限、强度和条件联合结构，不相加重叠年限',('lk.claim.item_anchor','lk.exp.object','lk.exp.years_min','lk.exp.years_max','lk.exp.years_relation','lk.exp.bound_inclusivity','lk.exp.strength','lk.exp.conditionality','lk.qual.logic'),'ACCEPTED_SEMANTIC','兼容原条款/分支','部分有原值；完整新条件结构未完成','derive_pending','按具体比较的依赖派生；不是对所有条款求一个min'),
      ('measure.cross_domain_openness','公开跨领域资格开放','BD','广告×来源经历类别','只有明确接受相关/替代经历的证据才判公开开放；未要求行业经验不是接受转行',('lk.exp.object_concept','lk.exp.strength','lk.qual.logic'),'PARTIAL_SEMANTIC','原对象、条件与证据可提供部分基础','没有可直接复用的全量跨行业接受指标','new_definition','定义具体来源目标领域及替代证据；不能猜录用概率'),
      ('measure.task_mix','职责与任务构成','CE','分组×时期','原四职责与扩展任务分类分版本统计；任何一项阳性与完整任务库存区分',('lk.duty.current',),'PARTIAL_SEMANTIC','旧四职责及有限Q2表','已有有限范围结果，不是全国完整任务包','derive_pending','旧四维统计无需等待扩展分类；扩展任务统计另依赖lk.task.code'),
    ]
    for key,label,mods,unit,definition,deps,asset,selector,coverage,status,need in derived:
        add(key,label,mods,unit,'count/rate/structured_measure',definition,'预先冻结分母、时间窗口、条件与缺失政策',status,need,deps,('base_capabilities','five_module_contract'))
        mapto(key,asset,selector,'reuse_existing_aggregate_or_dependency_derivation',coverage,need,['base_capabilities','five_module_contract'])
    # Preserve the actual fixed10k seven-family masks, not a fabricated thirteen-field crosswalk.
    for v in list(variables):
        key=v['variable_key'];families=[]
        if key.startswith('lk.exp.'):
            families=['experience_literal_years'] if 'year' in key or 'bound_' in key else ['experience_strength'] if key.endswith('strength') else ['experience_object']
            if key.endswith('conditionality'):families=['qualification_conditions_and_alternatives']
        elif key.startswith('lk.qual.'):families=['qualification_conditions_and_alternatives']
        elif key.startswith('lk.entry.'):families=['entry_wording_and_scope']
        elif key.startswith('lk.duty.'):families=['current_responsibility_subject_and_relation']
        elif key.startswith('lk.tech.'):families=['technology_category_and_role']
        if families:
            mapto(key,'FIXED10K_BATCH069', 'field_family='+','.join(families)+'; status + structured_value (original clause links retained)','original_family_masks_then_atom_binding','原10,000广告/7,617规范上下文；七族状态不等于十三维独立已知','新概念/新逻辑只复用底层文字和引用，不从family=known推每个新原子已知',['field_counts','attachment_code','semantic_assets'])
    # Existing Kimi and Astra outputs are retained candidates, not erased gaps.
    mapto('lk.provenance.source','KIMI_SAVED_UNVERIFIED','document where original_accepted=0; join field_value on d','saved_candidate_no_promotion','原1309批次1137工程候选/172例外；全局6500待验上下文已有载体，二者不是可相加口径','不重新生成相同广告；只有身份/原mask/新路线逐字段核验后才可改变使用层',['scope','semantic_assets','attachment_code'])
    mapto('lk.provenance.source','ASTRA_ORIGINAL','document asset/source provenance + preserved original acceptance','preserve_original_scope_only','原接受5上下文；含此前2；另1失败载体定位未解决','接受5不是新语义质量认证；失败载体缺失不等于未处理',['semantic_assets','scope'])
    # Personnel/history definitions remain semantic requirements, not claims
    # that a particular uninspected vendor column or new result already exists.
    rv=json.loads((out/'REVELIO_REQUIREMENTS_PUBLIC.json').read_text())
    rvlabels=['人员与职位身份','职位起止区间','历史可观察性与左截断','来源目标职业','来源目标行业','人员事件正交轴','跨职业进入','跨行业进入','事前总工作月数','目标领域既往月数','事前职业任务距离','相关经验月数','事前工具经历证据','事件前学历','经验阶段分层','可见人员事件数','入职者构成','目标进入风险集人数','首次目标进入人数','首次目标进入率','目标职业留存','跨库实体映射','两端时间对齐','跨库共同支持','历史技术暴露参照','技术扩散阶段','真正历史结果','技术比较口径']
    mods={'personnel_entry':'D','experience_combinations':'B','opportunities':'A','computerization_comparison':'E'}
    existing_refs={v['repository_relative_path']:k for k,v in source_records.items()}
    for raw,label in zip(rv['variables'],rvlabels,strict=True):
        refs=[]
        for path in raw['source_relative_paths']:
            if path not in existing_refs:
                k='person_history_source_'+str(len(existing_refs)+1);existing_refs[path]=k
                source_records[k]={'repository_relative_path':path,'sha256':hashlib.sha256((a.repo/path).read_bytes()).hexdigest()}
            refs.append(existing_refs[path])
        key=raw['stable_id'];status='derive_pending' if key=='hist.comparison_spec' else 'external_pending'
        numeric_count=key in ['pe.observed_event_count','pe.target_risk_count','pe.first_target_entry_count']
        months=key in ['pe.total_work_months','pe.target_experience_months','pe.related_experience_months']
        rate=key in ['pe.first_target_entry_rate','pe.entrant_composition','pe.target_retention']
        dtype='nonnegative_integer?' if numeric_count else 'nonnegative_number?' if months or key=='pe.task_distance' else 'rate_or_rate_vector?' if rate else 'versioned_struct_or_enum'
        allowed='人数；unknown不为0' if numeric_count else '月；并行区间不重复累计；缺历史保持unknown' if months else '[0,1]且有明确分母/窗口；分母0为not_applicable' if rate else '分类和结构为目标规范；具体供应商列仍待实查绑定'
        add(key,label,''.join(mods[x] for x in raw['research_modules']),raw['unit'],dtype,raw['definition'],allowed,status,raw['conditions'],raw['dependencies']['variable_ids'],refs,raw['unknown_vs_not_mentioned'])
        variables[-1]['missingness_rule']=raw['unknown_vs_not_mentioned']
        variables[-1]['external_dependencies']=raw['dependencies']['external_requirements']
        variables[-1]['data_contract_status']='semantic_requirement_not_verified_vendor_schema'
        mapto(key,'REVELIO_PENDING' if key.startswith('pe.') else 'CROSS_DATASET_PENDING' if key.startswith('bridge.') else 'HISTORICAL_REFERENCE_PENDING','no_verified_physical_column_binding','method_only_no_existing_value_claim','本轮未验证任何人员结果或真实历史指标交付','复用方法与LinkUp侧已完成的兼容输入；须核真实数据与映射',refs,raw['reuse_mapping']['old_asset_or_rule'])
    for v in variables:
        if not any(m['variable_key']==v['variable_key'] for m in mapping):
            mapto(v['variable_key'],'NO_DIRECT_OLD_FIELD','no_direct_column','dependency_or_definition_work', '旧字段不能直接覆盖该新变量',v['remaining_work_zh'],v['source_refs'])
    structural_assets={'lk.identity.ad_key':'BASE_AND_JOINED_IDENTITY','lk.identity.context':'GLOBAL_SEMANTIC_LEDGER','lk.provenance.source':'JOINED_SEMANTIC_VALUES','lk.time.created':'BASE_AND_JOINED_METADATA','lk.document.completeness':'PRO_ACCEPTED_REVIEW','lk.input.quality':'BASE_LEAN'}
    for row in mapping:
        if row['asset_key']=='BASE_RECORDS':row['asset_key']=structural_assets[row['variable_key']]
    sem=['Formal800_final_reference','fixed10k_Batch069_reference','Pro_continuous_and_merged']
    asset_bindings={
      'BASE_AND_JOINED_IDENTITY':['legacy_US_base_narrow','unified_known_asset_ledger'],
      'GLOBAL_SEMANTIC_LEDGER':['unified_known_asset_ledger'],
      'JOINED_SEMANTIC_VALUES':['unified_known_asset_ledger'],
      'BASE_AND_JOINED_METADATA':['legacy_US_base_narrow','unified_known_asset_ledger'],
      'PRO_ACCEPTED_REVIEW':['Pro_continuous_and_merged'],
      'BASE_LEAN':['legacy_US_base_narrow'],
      'FIXED10K_METADATA':['fixed10k_metadata_append'],
      'RECORDS_INDEX_AND_SCOPED_METADATA':['Records_structured_index','fixed10k_metadata_append'],
      'CANDIDATE_METADATA_AND_D67':['candidate_metadata_join_6010975','D67_rulefirst_delta69'],
      'GLOBAL_LEDGER':['unified_known_asset_ledger'],
      'FORMAL800_PRO_ACCEPTED':['Formal800_final_reference','Pro_continuous_and_merged'],
      'BASE_LEGACY_PROXY':['legacy_US_base_narrow'],
      'BASE_DURATION_CANDIDATES':['legacy_US_base_narrow'],
      'D67_RULE_DELTA':['D67_rulefirst_delta69'],
      'FIXED10K_BATCH069':['fixed10k_Batch069_reference'],
      'KIMI_SAVED_UNVERIFIED':['OpenCode_Kimi_parent_candidates'],
      'ASTRA_ORIGINAL':['Astra_original_parent'],
      'MACRO_RECORDS':['existing_macro_2016_2026'],
      'PARTIAL_SEMANTIC_PLUS_RECORDS':sem+['Records_structured_index'],
      'ACCEPTED_SEMANTIC':sem,
      'PARTIAL_SEMANTIC':sem,
      'NO_DIRECT_OLD_FIELD':[], 'REVELIO_PENDING':[], 'CROSS_DATASET_PENDING':[], 'HISTORICAL_REFERENCE_PENDING':[]}
    result={'dictionary_version':VERSION,'date':'2026-11-17','status':'definition_and_reuse_inventory_release_not_production_qualification','modules':MODULES,'target_scale_approximate':500000000,'future_increments_and_revelio_retained':True,'version_policy':'stable variable keys; breaking definition/denominator changes require major version; added nonbreaking variables minor; wording corrections patch; source measurement versions never overwritten','status_codes':STATUS,'reuse_guards':GLOBAL_REUSE_GUARD,'variables':variables}
    refs={'source_records':source_records,'scope_snapshot':scope['scope_units'],'fine_semantic_states':scope['fine_semantic_states'],'scope_warning':'Description原始行、Records原始行、去重广告、上下文及字段覆盖是不同单位，不相加减推全量缺口。','covered_source_counts_not_field_nonnull_counts':True}
    assert all(row['asset_key'] in asset_bindings for row in mapping)
    for name,data in [('VARIABLE_DICTIONARY_PUBLIC.json',result),('REUSE_MAPPING_PUBLIC.json',{'version':VERSION,'rows':mapping,'asset_catalog_bindings':asset_bindings,'all_global_guards_apply':GLOBAL_REUSE_GUARD}),('SOURCES_AND_SCOPE_PUBLIC.json',refs),('LEGACY_FIELD_COVERAGE_PUBLIC.json',counts)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    keys={v['variable_key'] for v in variables}
    assert len(keys)==len(variables)
    assert all(m['variable_key'] in keys for m in mapping)
    assert all(set(v['dependencies'])<=keys for v in variables)
    assert all(v['source_refs'] for v in variables)
    print(json.dumps({'root_variables':len(variables),'reuse_rows':len(mapping),'sources':len(source_records)}))

if __name__=='__main__':main()
