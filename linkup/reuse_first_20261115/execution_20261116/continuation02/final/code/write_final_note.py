"""Write an execution report from verified public receipts, not a manuscript."""
import json
from pathlib import Path
W=Path(__file__).parent
load=lambda n:json.loads((W/n).read_text())
c=load('COST_PUBLIC.json');q=load('QUALIFICATION_DECISION_PUBLIC.json');p=load('CHECKPOINT_PUBLIC.json');m=load('QUALIFICATION_COMPARISON_PUBLIC.json')
assert p['full_blob_readback_SHA_verified'] and not q['machine_reference_qualified_fields']
rows=[]
labels={'technology':'技术名称及角色','experience.general_work':'一般工作经验','experience.occupation_task':'职业/任务经验','experience.industry_domain':'行业经验','experience.tool_specific':'工具经验','entry.explicit_no_experience':'明确无经验要求','entry.explicit_new_graduate':'明确应届毕业生','entry.current_student_internship':'在校生/实习','entry.explicit_junior_or_entry_label':'明确初级标签','responsibility.independent_judgment':'独立判断','responsibility.client_ownership':'客户责任','responsibility.people_supervision':'人员监督','responsibility.training_mentoring':'培训指导'}
for f,x in m['fields'].items():
 pct=lambda n:'NA' if n is None else f'{n*100:.1f}%'
 rows.append(f"| {labels[f]} | {x['known_reference_cases']}/300 | {pct(x['positive_outcome']['precision'])} | {pct(x['positive_outcome']['recall'])} | {pct(x['outcome_macro_f1'])} | 未通过 |")
text=f'''# LinkUp 本轮续跑结果与真实断点

## 一句话结论
中断的固定模型资格测试已经运行到最终结论并完成云端归档；**Luna 候选量产路线未通过，不能开启 1 万条试产**。这不是“五亿条已洗完”，也不是已有清洗成果失效。论文仍暂停，没有恢复计时器或创建新资源。

## 已实际完成
- Luna：500 个固定输入全部有结果，290 条通过冻结工程校验，209 条校验失败、1 条 JSON 失败。失败输出保留，没有回炉调参或换样本。
- Kimi：复用 150 条已有独立对照，新增 350 条全部在 Azure 落盘并校验；新增中 307 条工程通过，28 条冻结校验失败、4 条消息数量异常、6 条可见输出边界失败、5 条提供商过滤保护。
- GPT/Astra：对原定 30 条哈希排序留出样本和 20 条分歧样本分别盲审；50 条均获得通过冻结工程校验的输出。两组单独报告，不合并成总体准确率；未要求真人审核。
- 完成 300 条留出集、13 个字段的冻结资格判断；200 条开发集没有进入资格门。**通过字段为 0，新增正式生产记录为 0，试产费用为 0。**
- 原始账本、旧值库和历史验收状态 SHA 未变。另存本轮新增 5 个提供商保护上下文，所有后续队列必须继承这层排除；不混入原账本的 56 个隔离数。

## 为什么没有继续试产
预设门槛为主要字段及完整关系 Precision≥90%、Recall≥80%、Macro-F1≥85%，另有参考覆盖与正负例支持条件。Luna 在本次端到端流程下，字段正例召回约 28.6%–57.9%，宏平均 F1 约 54.3%–71.9%；不是仅少量格式瑕疵就可以宣称合格。

这些是**对独立模型参考的协议一致性**，不是人工真值准确率。完整关系使用严格的规范化元组匹配，自由文本释义差异也会降低一致率；不把低一致率等同于真实语义全部错误。工程校验失败会按预先规则计入缺失/弃答，没有临时放宽标准来抬高分数。GPT 的工程通过率也不等于 100% 事实正确率。

| 字段 | 已知参考 | 正例 P | 正例 R | outcome Macro-F1 | 完整资格门 |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

完整关系、正负支持和失败理由见 `QUALIFICATION_COMPARISON_PUBLIC.json`；GPT 的两组独立结果见 `INDEPENDENT_AUDIT_PUBLIC.json`。

## 旧成果已接上，仍不能重复计数
- 204,774,035 条美国广告基础清洗、5,804,936 条新版字段增量继续复用，两者重叠，不能相加。
- 当前细语义总账 55,882 个上下文：39,298 个旧验收上下文已接上值、10 个旧验收缺载体；6,500 个待核验上下文已接上值、6 个缺载体；10,012 个状态待对账；56 个历史隔离。
- 已将 62,414 个现有广告身份接上 CREATED，其中 45,592 个有旧验收值；保留所有原字段口径、未知状态和 67 个多 PRIMARY 版本。这是细语义账本范围，不是全库覆盖。
- 缺少的 10 条旧验收结果已定位到两个当年因 `credential_content_review` 暂缓迁移的文件；现有 VM 身份访问预期 Blob 返回 `BlobNotFound`。没有绕过保护、改验收状态或重新推理填数。
- 全交付的“唯一广告/唯一缺字段模型输入”分母仍未知；Records 行数、Descriptions 行数、美国广告数、上下文数不能直接相减。当前元数据已能解释缺口，但不能伪造一个全量生产报价。

## 费用与预算
| 模型段 | 已返回用量的估价 | 保守请求预留（不是账单） |
|---|---:|---:|
| Luna | ${c['qualification_model_legs']['Luna']['priced_usage_estimate_usd']:.4f} | ${c['qualification_model_legs']['Luna']['conservative_reserved_usd']:.4f} |
| Kimi | ${c['qualification_model_legs']['Kimi']['priced_usage_estimate_usd']:.4f} | ${c['qualification_model_legs']['Kimi']['conservative_reserved_usd']:.4f} |
| GPT/Astra | ${c['qualification_model_legs']['Astra']['priced_usage_estimate_usd']:.4f} | ${c['qualification_model_legs']['Astra']['conservative_reserved_usd']:.4f} |
| 合计 | ${c['total_priced_usage_estimate_usd']:.4f} | ${c['total_conservative_model_reservations_usd']:.4f} |

资格测试上限仍 $250；没有把保守预留当成实付。部分请求无 usage，Azure 正式账单及既有 VM/Blob 的任务级费用尚未核对，所以不能宣称项目总花费恰好等于上述估价。对账/复用各 $25 上限不变；$150 试产额度未使用；论文暂停、全量补缺资金未预支。

## 本轮修复与失败留痕
1. Kimi 开始前，ARM 回执读取超时导致租约失效。先确认旧进程退出、零模型提交、云端零结果，保存过期租约后才恢复，没有重复模型调用。
2. 统计代码漏处理原 validator 已明文允许的“替代组共用条件（分支为 null）”。另存兼容修复版本并在本地/云端通过 19 个合成测试；原 schema、结果、样本和阈值不动，共用条件不压成无条件或选中分支。
3. 首次 GPT 50 个请求因 Responses API 要求 JSON 字样出现在 input 中而全部在推理前返回 HTTP400，未生成模型答案。保留全部拒绝回执；仅给同一 50 条各补发一次格式修复请求。原自设 60 次 HTTP 子上限显式改为 100（含原 50 次），每输入总计最多 2 次，$100 审核预算仍计入两轮全部预留；没有重复任何已生成模型答案。修复后遇第一个系统性 HTTP 错误即停，不再遍历错误配置。
4. 归档控制载荷过大时在本地拒绝执行，再分块运输同一载荷；重组 SHA 验证后执行。不是重新分析或重复模型调用。

## 云端交付与后续边界
- 当前总控：`azure_workspace:execution_20261116/run001/AZURE_RESEARCH_STATE.json`。
- 已有值库：`azure_workspace:execution_20261116/run001/continuation01/joined_revision003/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite`。
- 最终决定及两组模型对照：`azure_workspace:execution_20261116/run001/continuation02/`。
- 新归档在 `migration-receipts` 容器：`{p['archive_blob_key']}`，{p['archive_bytes']:,} 字节，已完整回读验证 SHA256：`{p['archive_sha256']}`。
- 本轮模型工作进程已结束。不能把这轮测完解释为全量任务完成：身份/回执缺口仍未全部消除；Luna 量产资格失败；1 万条条件试产与全量补缺均未放行。下一步只能继续不重复的旧结果对账，或明确另一个符合预算的生产测量方案；不得自动复活失败路线、削弱门槛或打开全库推理。
'''
# Render numeric placeholders without interpolating any private row data.
(W/'CONTINUATION_FINAL_ZH.md').write_text(text)
print(json.dumps({'report_written':True,'source':'verified_public_receipts','manuscript_modified':False}))
