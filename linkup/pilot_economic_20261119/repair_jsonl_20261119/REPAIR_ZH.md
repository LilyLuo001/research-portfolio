# 2026-11-19：JSONL 解析与原断点恢复

## 查到的事实

后台于 2026-11-18 20:10:57 UTC（北京时间 11 月 19 日 04:10）停止，原因是控制器对 JSONL 使用 `str.splitlines()`，错误地把合法 JSON 字符串内的 U+2028 分隔符当作记录边界。第二批实际上有 792 行，不是该方法分出的 793 段；模型结果没有损坏。输入同样有 7 个 U+2028。

第二批 791 个正文已有结果并完成本地字段校验；1 个原请求超过原始 63,000-byte 请求上限，状态为 `request_bound_exceeded_no_call`，没有领取、付费调用或结果。它保留未处理/未知，既不伪装成功，也不改大请求上限重跑。

## 修复边界

- 新增 controller v2 和 projection v3；原代码、schema、规则、PRIMARY、失败输出及原投影保留。
- JSONL 按物理 LF 读取，完整保留 Unicode 字符，不改文本、证据偏移或哈希。
- 对无调用的超限条目，用原 payload 构造器重现大小限制，并验证无既有 claim、无标签，才能让其他条目继续；不是放宽科学验收。
- 18 项合成工程测试通过，另在 Azure 上验证现有真实输出的完整 SHA、身份与字段落表。
- 恢复阶段没有模型调用；890 个历史本轮调用账目、费用预留与 897 个保护文件的 SHA 全部不变。
- 前 1,000 个物理行已守恒回填：884 个新提取结果、115 个保留旧状态、1 个未处理超限条目。旧状态不等于重新验收通过。
- 续跑沿用唯一预算/独占领取账本、原始起始时间和 48 小时总时限、最多 10,000 物理行及 $150 上限。不建立 timer，不重置计费或回退隔离。

## 云端回执

`/home/linkup/migration/pilot_economic_20261119/run01/control/jsonl_recovery_20261119/RECOVERY_PUBLIC.json`

物理回填：`/home/linkup/migration/pilot_economic_20261119/run01/projection/batch0002/PHYSICAL_INCREMENT_PRIVATE.jsonl`

原始状态、SQLite 快照和保护文件 SHA 清单保留在同一云端 recovery 目录的私有文件内；不上传 Git。运行与恢复是工程事实，不是总体语义准确率或五亿条完成证明。
