# 条件试产发布mask：离线工程准备

此目录没有运行入口、队列提取、正文读取、网络/模型调用或生产许可。没有使用真实评分或试产样本；只实现发布前的必要条件检查。Stage 5冻结文件及runtime未修改。

## 最小API

```python
from release_mask import load_gate, row_mask

gate = load_gate(
    original_frozen_protocol_directory,
    original_saved_scores_path,       # field_score.py输出的原SCORES_PRIVATE.json
    expected_score_sha256=trusted_score_receipt_sha,
    expected_frame_sha256=trusted_existing_frame_freeze_sha,
)

mask = row_mask(
    gate,
    declared_missing_measures=exact_missing_measure_ids,
    validation=unchanged_field_validator_result,
    observations=unchanged_observe_results_by_exact_measure_id,
    derived_dependencies=explicit_complete_dependency_declarations,
)
```

`load_gate`固定核验原协议、协议bundle及bundle四个成员的SHA；核对原评分的`freeze_binding`、协议版本、固定分母、完整measure清单和challenge隔离，并要求`eligible_measure_dependencies`精确等于confirmation内独立通过的measure清单。没有合格measure立即抛`MaskError`。它消费原评分，不重算或放宽科学门槛。缺少freeze_binding的公共摘要不能代替原评分。

`row_mask`只输出ID与固定原因码，既不生成也不改写研究值：

- 发布集合＝独立合格精确measure ∩ 明确声明真正缺失的measure ∩ 本条完整且工程有效字段 ∩ 本条已知measure。
- 工程状态采用原`FieldValidator.validate`结构：`fields[field].status == engineering_valid`、空errors、full inventory、完整review；共享输入失效、protected、invalid、unknown、partial均不会成为可用值。
- measure状态采用原`field_score.observe`结构：`status == known`且outcome为present或not_mentioned。字段整体有效不能抹掉某项measure的unresolved/unknown。不存在的观察也不能放行。
- 只接受协议中精确measure ID；family、通配符、未知ID、重复ID均拒绝。通过mention不会自动通过同family的years或strength。
- 未声明缺失的字段不发布；“未提到”不由helper推断，必须来自原完整review及原observe结果。

## 信任边界

评分SHA和frame SHA必须来自既有可信评分/冻结回执。不能自行hash一个任意输入后，把同一hash当成授权。SHA匹配证明字节一致；独立Kimi来源、冻结先后、真实缺失/新鲜性、保护并集、唯一领取、金额/速率及单条source/output/validation/observation的同源绑定仍由外部可信控制完成。本helper不声称验证这些条件，也不消费广告ID或正文。

调用方必须保留原验证和observe结果，且证明它们来自同一个SHA绑定的输出与完整输入；不能把别条有效字段状态移来使用。`declared_missing_measures`也必须来自真实现存字段缺口，不能把old unknown、未核账或保护状态声明成未处理。

冻结协议没有完整的派生量依赖映射。因此`derived_dependencies`只接受调用方显式、事先有依据的完整精确依赖清单，不从名字/正文/同family猜测。`derived_all_declared_dependencies_released`仅在全部声明依赖都在本条发布集合时为true；空依赖和未知依赖拒绝。这个布尔值只是必要条件，不认证依赖声明充分，也不给派生科学量资格。它不会把派生ID加入`eligible_measure_dependencies`。旧值复用的另行资格证明不在这个最小API内，不能绕过本检查。

所有返回始终包含`production_admission=false`、`derived_qualification_granted=false`和外部运行控制未由helper验证的标记。没有独立合格measure时不返回可执行gate；某条交集为空时只返回空mask。

## 合成验证

运行：

```sh
python3 -B -m unittest -v test_release_mask.py
```

测试只读取冻结协议/代码，以原`field_score.summarize`生成合成聚合；不读取真实评分、输出、context或正文。临时文件只含合成元数据。17项测试覆盖SHA与冻结绑定、原bundle修改、固定分母、eligible-list一致性、challenge不可晋级、字段/measure未知或失效、缺失交集、同family扩张、派生依赖闭包、无合格项拒绝、JSON重复键/非有限数及输入不变性。此次17项全部通过；这是工程验证，不是独立资格结果。
