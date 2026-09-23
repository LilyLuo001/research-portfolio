# 第一篇 Phase 1 最终独立有限复核

日期：2026-09-23。范围仅限上一轮必须修复项所影响的 Phase 1 文件及 SCC 新输出；未重审其他内容，未运行第二篇，未提交或推送。

## 最终结论

**`LIMITED_FINAL_PASS`**。

事件窗、完整时间网格、缺失处理、SCC 重跑、输入输出哈希、NYSE/NYSE American 处理边界，以及最后两项文字/字段标签均已修复。在本复核的严格有限范围内无剩余必须修复项。

## 已通过的修复

### 1. SCC 新结果独立复现：PASS

直接读取同一 SCC equity/futures feature parquet，以未调用被审脚本函数的独立实现重算全部 8 个日期×网格行。按 `(date, grid_shift_ms)` 比较新 `FOMC_DEMO_METRICS.csv`：

- 25 个数值字段的最大绝对差：`2.1316282072803006e-14`；
- `post_all_joint_valid` 布尔字段全部一致；
- 每行预样本 481 格、post 60 格、联合有效 60 格；
- 日期、事件/对照配对、0/500 ms 网格选择不变。

哈希核对：

- equity input：`d2b2b2b65207199c1e6fc0ab1e9198a0fde966d10386bfb92db13001e5e97203`
- futures input：`b504fc2d0679852a101a2fafdf315a1dc5396045e5ab216be0a67508db94d4c2`
- SCC/local metrics：`fd0990dfdf175cd371ebf0b11cb8b4348bcc8cae67d833ffb9c800c3e73854d4`
- SCC paths：`fe309e5087e1fa7cb70ea6a6d458c673db3ba76056f8b803964304a5b1312327`
- 被审脚本：`3c21815553ac86e9b69780cc616fa1714ad792066efa303776fd2a0985edfe36`

SCC receipt 记录上述输出哈希与 8/480 行；本地 receipt 与 SCC receipt 规范化后的 JSON 内容完全一致。压缩 paths 的哈希是本次实际 SCC 文件哈希。

### 2. 时钟、窗口和缺失：PASS

- 主 0 ms 网格使用 `rel=1..60`，严格覆盖 `(t0,t0+60s]`，不再包含事件前一秒。
- 500 ms 敏感性明确覆盖 `(t0+0.5s,t0+60.5s]`，metrics 中同时保存实际起止偏移 `500/60500 ms`，不再冒充相同绝对端点。
- 每行明确报告 `post_expected_bins=60`、`post_grid_rows=60`、`post_joint_valid_bins=60` 与 `post_all_joint_valid`。
- equity/ES 先 outer merge，再对完整 `second_index` 网格 reindex；lag 在完整网格上形成，不会把上一条有效记录冒充前一秒。
- 累计路径对缺失收益使用 NA 且 `cumsum(skipna=False)`，不再把缺失收益填为零；路径末端、早期峰值和相关型汇总受有效性约束。当前 8 行均为 60/60，因此新数值完整。
- 绝对 midpoint update 数改为相同 60 个桶，并用 `min_count=60` 防止缺列值被静默忽略。

### 3. SPY–ES 口径：PASS

`pre_beta_spy_on_es` 仍是预样本一秒收益上的无截距 contemporaneous OLS 斜率；`divergence_bp` 是 beta 缩放的累计收益残余代理。文稿继续明确它不是 carry-adjusted basis、NAV 折价、套利收益、纯信息误差、协整向量、永久信息份额或 FOMC 韧性恢复。

### 4. NYSE 2015 处理范围与来源：PASS

`EVENT_CANDIDATES.csv` 已新增 SEC enforcement order URL，并将受影响对象改为 NYSE 与 NYSE American/MKT、排除 NYSE Arca。`DESIGN_DECISION.md` 与 `method_review_draft.md` 已明确：主经验总体聚焦 NYSE-listed S&P 500 证券，而 American/MKT 是同时发生的伴随处理，不是未处理对照。

这与已核实的两项监管来源一致：

- SEC Data Highlight：<https://www.sec.gov/about/corporate-stock-trading-volume-spreads-depth-during-after-nyse-trading-suspension-july-8-2015>
- SEC Release No. 33-10463：<https://www.sec.gov/files/litigation/admin/2018/33-10463.pdf>

正式 11:32–15:10 区间、约 10:45 起恶化、10:51 起 self-help/停止路由及约 11:27 下令暂停的表述均仍受来源支持；文稿没有把分钟级监管边界冒充证券/网关秒级边界。

### 5. 替代和识别边界：PASS

未发现把剩余份额、共同移动或 FOMC 结果写成替代成功或因果识别。FOMC 仍是测量演示；`INFORMATION_SHARE`、`CHANNEL_SUBSTITUTION_CAUSAL_EFFECT` 和论文结果均保持未估计/开放状态。

## 最终标签核对：PASS

`PILOT_RESULTS.md` 已在开头和末行统一为 480 path rows，lead-balance 范围已更新为约 `0.02–0.10`。脚本和 CSV 已将三个容易误读的字段改为 support-neutral 名称：`max_abs_divergence_first10_bins_bp`、`abs_divergence_interval_end_bp`、`residual_divergence_ratio_end_to_peak10bins`。旧的 `0_10s`、`60s` 和 `60s_to_peak10` 字段名已不再出现。

本轮最终标签修改没有改变上一轮已独立通过的经济数值；依照任务要求未重复数值复算，只核对字段、文件和 SCC 最终哈希。

实际模型/推理遥测：`NOT_OBSERVED`。
