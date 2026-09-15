# corrected-v2 最终哈希 20-candidate SCC pilot

状态：`METADATA_PILOT_PASS`，仅为 implementation gate，不是 research-pilot 结论。12 个合成边界 fixture 全部通过；最终 20-candidate pilot 保留全部分母（10 个旧 v1 已表示、10 个先前未表示 UNKNOWN），其中 10 个有唯一来源映射，10 个无当前 view source-row path。

266 条有效 link paths、266 个 distinct `(source_row_id,candidate_id)`、266 个 period keys、266 个 wave-specific candidate public-release keys。另对 20 条实际映射观察在 SCC 回读允许字段，7 项谱系断言全部通过。故意篡改必需不变量时 gate 拒绝且不产出 gate。

锁定哈希：code `28897abb6196b36d5b6fbb2b8b3dc4417c6bd861f0f2833335dd9ab15605e41e`；config `19aba25f327923de4c7048b241933e2d3edbf5413243285ab14df52b8efd9c79`；manifest `54e4b8b943c5a8a8af173cf2dfaaa66590ad56d1e381f8157854cf11b6f4d9c9`；gate `7b85859d42897dc7e2c70f07d9a72015832c41afec9d43471e2097082750f706`。全量已在该 gate 下完成，结果见 `RUN_RESULTS.md`。

