# corrected_v2 元数据普查结果

状态：`COMPLETE`。原 Terra 输出保持原样并在上级 `README.md` 标为 `INVALID_REQUIRED_SEMANTICS`；本文件只报告 corrected_v2 的唯一一次全量运行。

## 闸门与谱系

- 12 个合成边界 fixture 全部通过；故意篡改必需不变量时 gate 退出码为 1 且不产出 gate。
- 最终哈希 20-candidate SCC pilot 完成；另对 20 条实际映射观察逐条回读允许的 metadata/link 字段，CSV 行号、候选键、link 行/日期、CUSIP8 与全源歧义重算 7/7 通过。
- 全量运行在打开来源前验证同一 code/config/manifest gate；来源哈希与 manifest 相符。无购买、无财务/预测/报价/响应值读取，行级输出仅留 SCC。

## 全量计数

- H/L 候选分母 2,794：2,592 个在当前 metadata view 有唯一来源映射；202 个仍无当前 view 路径，状态为 `UNKNOWN`，不是“无财报”。202 分布：W002 H59/L73、W016 H24/L29、W025 H6/L11。
- 有效闭区间来源—候选路径 66,939；wave-specific candidate public-release keys 66,923。后者不是经独立核验的唯一经济事件。
- PRE/POST exact metadata keys：旧 capped 29,729 → uncapped 61,486，增加 31,757（PRE +8,160；POST +23,597）。这说明旧截断损失了元数据支持，不代表效应样本或可识别性。
- 路径状态：66,939 条 `UNIQUE_VALID_PERMNO` 有效路径；另有 541 条唯一映射但在候选闭区间外、4,076 条 `NO_VALID_PERMNO` 且在闭区间外；未观察到候选级 ambiguous 有效路径。

## nominal source-clock 诊断

在不施加 cached min2 时，72 个 stock-wave candidate keys 在同 wave/tier 内各至少有一个 nominal PRE 和 POST（不保证是 72 个不同 PERMNO）；施加 cached exact-key min2 后为 20。按旧 overlap 状态分层的“同一层内 PRE+POST”计数为：known-clean 16→3、known-not-clean 43→16、旧 view 外 UNKNOWN 13→1。known-clean 的 wave×tier 明细（before→cached-min2）为 W002 H 1→0/L 14→2、W013 H/L 0→0、W016 H 0→0/L 1→1、W021 H/L 0→0、W025 H/L 0→0；因此四个主 wave 中仅 W002 在 min2 前两 tier 都有 known-clean PRE+POST 支持。所有 09:30–15:00 仅为来源显示时钟，未认证时区或 RTH；这些是支持诊断，不是有效推断样本。

## 尚缺输入

202 个候选需要另有、且经版本固定的身份/公告元数据路径才能解除 UNKNOWN；新增 uncapped keys 缺逐 key analyst coverage，旧 view 外缺 overlap/clean 判定；来源时钟缺时区与交易日历认证。SUE、收益率、价格、行业控制与 POST response 本次均未读取，因此不能据此估计效应、ESS 或宣称模型可估。下一步仅应对已观察到的 nominal/known-clean 支持 key 做版本化 analyst-coverage 补全，不做泛化元数据采购或新 outcome 查询。
