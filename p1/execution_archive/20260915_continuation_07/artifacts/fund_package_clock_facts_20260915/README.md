# Fund/package/clock factual sidecar

状态：`FACTUAL_SIDECAR_COMPLETE; FINAL_SAMPLE_NOT_ASSIGNED`。本阶段把五个 focal package 和实际出现的 W006/W032 other-wave constituent 事实版本化，并在 SCC 上连接 exact recovered-99 denominator。没有读取收益、价格、forecast/EPS value，也没有估计效应、功效或最终 rank。

## 已实施事实

- 17 个 predecessor series 组成 9 个明确 package rows：五个 focal package（12 个纳入 equity series）、1 个 W021 同日但排除的 bond package，以及 W006 的独立 DFA/JPM packages、W032 的双 constituent package。W006 不是共享 sponsor/date-bucket package；原 12 个 W006 candidate-pairs 分解为 DFA membership 12、JPM membership 1，即 11 DFA-only、1 both。
- `A_w` 保存为当前有界证据下的最早独立核实公告区间，不要求全世界“无更早消息”证明：W002 为 unresolved 2020-11-16 signal 至 predecessor-linked N-14 2021-03-03；W021 为 SEC 497K 2022-12-15；W025 为 June plan 2023-06-01 至 SEC supplement 2023-06-28；其余为 date-only 已核实来源。时区/日内瞬间未认证。
- W032 保留不同类型日期：N-14 预期 2024-11-15 重组/11-18 trading；factsheet snippet 的 12-06 COB asset acquisition；后来 SEC 文件核实 12-09 completion。诊断使用实现区间 12-06..12-09，不把预期 November 日期改写为完成日。
- holdings 来源版本未混用：legacy gate0 的 pre-effective dates 只用于候选归属；`SELECTED_PREANNOUNCEMENT_FILINGS_20260914` 中 W002/W013/W016/W025 的 11 个 series 严格早于支持的 `A_w` 区间。W021 保存的 2022-12-31 holding 晚于 2022-12-15 公告，不能作为 pre-announcement holding。已定位另一个 W021 2022-09-30 NPORT-P 主文件，但 exposure/denominator 修复属于下一独立版本。

## recovered-99 结果

99 个候选保留为 120 个 candidate×other-wave keys：45 个真实链接、75 个 `NO_OTHER_WAVE_MATCH_IN_THIS_VERSIONED_EXPOSURE_SOURCE`。连接到 64 个 exact candidate-pair-series membership rows；加 75 个 sentinel 后，受保护侧车共 139 行，留在 SCC。

按合同原文“another conversion **before or inside** `[A_w-24m,A_w+24m)`”和整日不确定区间计算，25 个 candidate×other-wave keys 稳健满足排除条件，覆盖 17 个不同候选：W002 H6/L1，W016 H3/L5，W025 H1/L1。其余 82 个候选仅是“未在当前不完整 calendar 中观察到排除”，不是 clean；75 个 no-match keys 保持 UNKNOWN。正向排除事实不会被同一候选的另一 UNKNOWN constituent 擦除。

这一步没有重新运行 earnings/session 支持，因此不宣称最终 H/L 比较可估计。当前最具体的可执行修复是用已取得的 W021 NPORT-P（report 2022-09-30，series `S000032550`）重建该 wave 的严格 pre-announcement holdings/denominator，并保留旧 2022-12-31 版本；随后才可将修复后的 exposure membership 与当前侧车连接。另需保留 complete-conversion-calendar 的 17-wave/9-row identity gaps、split/pro-rata 和 source-clock 语义限制。

## Gate 与保护

6 个日期/边界/package fixtures 通过；20-candidate SCC pilot 含 34 个真实 pair 和 44 个 exact series membership rows。full entry 在读取完整受保护输入前核对 contract、code、facts、mapping、manifest 与 pilot hashes；直接绕过 gate 和 stale-pilot 两个负测试均正确拒绝。受保护明细仅在：

`/projectnb/econdept/qluo/P1_Refraction_WRDS/fund_package_clock_facts_20260915/full_v4/protected_candidate_package_membership.csv`

