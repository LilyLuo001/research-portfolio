# `JOB_HASH` 连接是否真正 1:1：证据说明

**结论：在已审计的 269 个 Job Records 文件与昆山 1,358 个完整 Description 文件范围内，所有成功匹配的 `JOB_HASH` 都是严格的 1:1 键连接，没有重复扩张。** 但“描述左连接的全部输出”还包括 14,978 个没有 Records 对应行的孤立描述键；同时，当前描述子集只覆盖 Records 键的约 46.17%，不能说所有 Records 都有描述。

## 两侧唯一性

Records 侧的 Phase A 全量审计覆盖 269 个文件、356,449,214 行。`JOB_HASH` 非空行 356,449,214、空值 0、distinct 356,449,214、重复键组 0、重复超额行 0。审计按首个十六进制字符分成 16 个互斥桶，每个桶内的行数都等于 distinct 数；各桶前缀互斥，因此组合后仍是全局唯一。后续 Arrow 索引的 footer 也守恒为 356,449,214 行，并带固定输入清单签名。

Description 侧的键投影覆盖昆山 1,358 个完整文件、164,581,116 行。`JOB_HASH` 空值 0、格式错误 0。独立分组验证得到 164,581,116 个 distinct 键、重复键组 0、重复超额 occurrence 0，验证状态为 `PASS`。因此在此批 Description 中，每一行也是一个唯一 `JOB_HASH`。

## 连接守恒

最终键连接以 164,581,116 个 Description 键为左表，得到：

- 成功匹配 164,566,138；
- Records 中无对应键的 Description 孤立键 14,978；
- `matched + orphan = 164,581,116`，与左表键数完全一致；
- `matched_occurrences = matched_keys = 164,566,138`；
- `orphan_occurrences = orphan_keys = 14,978`；
- Description 公司 ID 与匹配 Records 公司 ID 的冲突键为 0。

由于 Records 键唯一、Description 键也唯一，成功匹配部分不可能形成 1:N、N:1 或 N:N fanout，所以成功匹配是严格 1:1。Description 左连接整体仍是一行一个 Description 键，但其中 14,978 行为未匹配行，不能称作“成功的 1:1”。

成功匹配占 Description 键的约 **99.9909%**。反过来，只有 164,566,138 / 356,449,214，即约 **46.17%** 的 Records 键出现在当前 Description 子集中；尚有 191,883,076 个 Records 键未被这些 Description 覆盖。这是覆盖率问题，不是连接 fanout。

## 尚未证明的范围

该结论精确适用于当前 269-file Records 快照与昆山 1,358-file Description 子集。若华中还有不属于这 1,358 文件的额外 Description 文件，必须在跨区域合并后再做一次全局键分组，才能证明合并语料仍无重复键。`JOB_HASH` 是供应商基于 URL 的 posting/location 键；键的 1:1 不等于唯一经济 vacancy，也不能证明描述正文版本历史。
