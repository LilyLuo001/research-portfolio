# E2-T1 union check — channel A (claude_l2) ∪ channel B (gemini_free)
_per v1.1 appendix A. A: `ops/l1/out/E2-T1-facts.json` (2026-07-09). B:
`ops/l1/out/E2-T1-facts-B.json` (2026-07-09). Decision rule: 一致 → 入 registry;
冲突 → 双列, owner 仲裁; 单通道 UNKNOWN → 采另一通道并标注单源._

## 一致 (可直接入 registry)
| id/对象 | 结论 | 备注 |
|---|---|---|
| oracles/mF-ONE | eOracle (Fasanara NAV → Midas → eOracle) | A、B 同 |
| oracles/mTBILL | OpenEden 官方 on-chain price oracle (NAV/token) | A、B 同 |
| redemption/syrupUSDC | FIFO 队列, 常态当日, 上限 30 天 (软 gate) | A、B 同 |
| redemption/mTBILL | 即时或 T+1 (周末 T+2), 最低 1 USDC | A、B 同 |
| coinbase-vault (结论部分) | Steakhouse curator, Base; High-Yield 层含 USDtb → RWA 敞口 | A、B 同; 下游影响提示一致 |

## A 补全 B 的 UNKNOWN (单源, 标注后入 registry)
- **oracles/sACRED = RedStone NAV 喂价** (B: UNKNOWN)。来源为 RedStone 官方博客
  (oracle 提供方自述) + Morpho 市场页。
- **redemption/sACRED = ACRED interval fund 季度 tender ≥5% (SEC N-23C3A)**
  (B: UNKNOWN)。SEC 文件为最高等级一手来源。⚠️ 同时更正早期 kimi 通道的
  "T+0 无门槛" — 该说法与 SEC 文件矛盾, 弃用。**季度 gate + Morpho 上的循环杠杆
  = E2 脆弱性叙事的核心案例, 此行价值最高。**

## 冲突 (owner 仲裁后才入 registry)
1. **oracles/syrupUSDC**: A = Chainlink Exchange-Rate feed (Base, data.chain.link);
   B = API3 OEV。可能 per-chain/per-market 不同 — 仲裁动作: 链上读 Ethereum 主市场
   (0x729bad…cf44) 与 Base 市场的 oracle 地址各自归属。
2. **redemption/AA_FalconXUSDC**: A = 月度赎回, min 250k, 无赎回费;
   B = 1–4 周 cycle + 31 天通知 + 72h 提前退出。按 decisions.md FalconX 决议,
   B 通道此资产行本就在加严审查名单 — 仲裁动作: 以 Pareto/FalconX 法律文件为准。
3. **coinbase-vault 地址**: B 给出 0xbeeF010f…8183 / 0xbeeff249…8845, A 未能从
   explorer 独立取得 → 按 C0 纪律 (地址不得凭记忆/二手) 须 explorer 核对后采信。

## 双通道皆 UNKNOWN (registry 记 UNKNOWN)
- oracles/AA_FalconXUSDC 的链上实现 (两通道均只到 "推断: Pareto NAV 喂价")。
- navlink/Horizon 逐 feed 更新频率 (B 的 "每工作日" 为标注推断, 不入 registry;
  A 提供可查证路径: data.chain.link 各 feed 的 heartbeat 参数)。
- redemption/cUSDO 底层 USDO 条款。

## 附带发现 (直接给 E2 正文素材)
- **2025-05-25 Morpho cUSDO/USDC 市场 oracle 操纵事件** (Aerodrome sAMM LP oracle),
  官方 post-mortem: https://forum.morpho.org/t/post-mortem-aerodrome-cusdo-usdc-amm-lp-oracle-manipulation-on-morpho-lending-market/1794
  — RWA 抵押 × 可操纵 oracle 的实锤案例, §脆弱性 直接引用。

## Explorer verification (2026-07-09, on-chain reads via public RPC eth_call; 仲裁仍归 owner)
_方法: 直接 `eth_call` Morpho Blue (`0xBBBB…FFCb`) `idToMarketParams` + oracle/feed
getter 探针 (BASE_FEED_*, BASE_VAULT, description, api3ServerV1, aggregator),
Ethereum via ethereum-rpc.publicnode.com, Base via base-rpc.publicnode.com;
市场清单交叉引用 blue-api.morpho.org。链上读数即一手来源。_

### 冲突 1 (oracles/syrupUSDC) — 链上证据
- **Ethereum 主市场** `0x729bad…cf44` (syrupUSDC/USDC, lltv 0.915, listed):
  oracle = `0x80032f4cb6E3573b9ed61E888AF658E48Fb790cC`。该合约四个外部 feed
  getter (BASE_FEED_1/2, QUOTE_FEED_1/2) 全为零, 仅 `BASE_VAULT() =`
  syrupUSDC token (`0x80ac24aA…f5Cc0b`), `price()` 正常 → **纯 vault 汇率
  oracle (convertToAssets), 无任何外部数据 feed** — 既非 Chainlink 数据 feed,
  亦非 API3。同一 oracle 合约还服务 ETH 上 syrupUSDC/USDT 与 /AUSD 市场。
- **Base listed 市场** `0x52f04b…48a5` (syrupUSDC/USDC, lltv 0.915): oracle =
  `0x8e5581119B7a6737dD829Dc2FC364F498c0da50C`, 其 `BASE_FEED_1 =
  0x311d3a3fAA1D5939C681e33C2CDAC041FF388eb2`, `description() =
  "syrupUSDC-USDC Exchange Rate"`, `latestRoundData()` 可读, 且为 proxy →
  `aggregator() = 0xc6c99357…7d42` (Chainlink EACAggregatorProxy 结构) →
  **与 A 通道 "Chainlink Exchange-Rate feed (Base)" 一致**。
- **API3**: 两条链上与 syrupUSDC 相关的全部 oracle (含 3 个 ETH unlisted
  市场的 oracle) 均无 `api3ServerV1()` 接口 → **B 通道 "API3 OEV" 在链上
  未获得任何支持**。
- 残余不确定性: Base feed 的 Chainlink 归属基于接口结构 (proxy+aggregator+
  description); data.chain.link 页面比对可作最终背书。ETH 另有 3 个 unlisted
  syrupUSDC/USDC 市场使用不同 oracle (`0x4F570B…`, `0x426e27…`, `0xDddd77…`),
  说明 per-market 差异真实存在 — B 的答案可能来自其中之一, 但均非 API3。

### 冲突 3 (coinbase-vault 地址) — 链上证据
- `0xbeeF010f9cb27031ad51e3333f9aF9C6B1228183`: **Base 有码, Ethereum 无码**。
  链上读数: name = "Steakhouse USDC", symbol = steakUSDC, asset = Base USDC
  (`0x833589…2913`), curator = `0x827e8607…ecdb`; Morpho API: listed=true
  (Vault V1)。
- `0xbeeff2490FEffa212faC2f6553682C219E6a8845`: **Base 有码, Ethereum 无码**。
  链上读数: name = "Steakhouse High Yield USDC Edition", symbol = sirloinUSDC,
  asset = Base USDC, curator 同上; Morpho API 以 **Vault V2** 端点
  (`vaultV2ByAddress`) 返回同名 → 是 V2 vault, 不在 V1 清单里。
- 结论性质: 两地址均通过链上确认 (C0 的 explorer 门槛满足), 名称/curator/
  asset 与 "Steakhouse curator, Base, High-Yield 层" 的双通道一致行吻合。
  ⚠️ 注意第二个 vault 是 Morpho Vault V2 — registry 若记录 vault 类型,
  此处须标 V2。

### 冲突 2 (redemption/AA_FalconXUSDC)
非链上可核事项 (Pareto/FalconX 法律文件) — 不在本节范围, 仍待 owner 仲裁。

## 状态
- 一致行 + A 补全行足以支撑 E2-T2-dune 的市场清单起草 (registry.csv 的 oracle/
  redemption 列可先填这些行)。
- `--complete E2-T1-facts` 待 owner 复核本 memo 三处冲突后执行。

## 仲裁 (2026-07-10, owner 在会话中授权执行; 终审签字仍归 owner)

### 冲突 1 — oracles/syrupUSDC: 裁定 = 按链上证据分链录入
- **Ethereum 主市场** (`0x729bad…cf44`): oracle `0x80032f…90cC` = **纯 vault
  汇率 oracle (convertToAssets), 无外部 feed** — 非 Chainlink 数据feed, 非 API3。
- **Base listed 市场** (`0x52f04b…48a5`): **Chainlink 结构 Exchange-Rate feed**
  (proxy→aggregator, description "syrupUSDC-USDC Exchange Rate")。
- **B 通道 "API3 OEV" 弃用** — 两链所有相关 oracle 均无 api3ServerV1 接口。
- registry 录入时必须保留 per-chain/per-market 维度 (ETH 另有 3 个 unlisted
  市场用不同 oracle)。残余事项 (非阻塞): data.chain.link 页面比对作最终背书。
- 证据等级: 链上 eth_call 一手读数 → 高置信, 即刻入 registry。

### 冲突 3 — coinbase-vault 地址: 裁定 = 采信 B 的两地址, 带限定词
- `0xbeeF010f…8183` = Steakhouse USDC (steakUSDC, **Vault V1**, Base);
  `0xbeeff249…8845` = Steakhouse High Yield USDC (sirloinUSDC, **Vault V2**, Base)。
- 两地址均 **仅 Base 有码** (Ethereum 无码), curator/name/asset 与双通道一致行
  吻合 → C0 explorer 门槛满足, 入 registry, **必须带 "Base-only" 与 V1/V2 限定**。
- 备注: B 通道在此行提供了正确地址 — 加严审查是逐行核对, 不是整通道否决;
  本行通过核对, FalconX 行 (下) 未通过。

### 冲突 2 — redemption/AA_FalconXUSDC: 裁定 = 不入 registry, 记 UNKNOWN-pending
- 三个互不一致的版本并存, 无一来自本会话可直接检索的一手页面:
  A = 月度赎回, min 250k, 无赎回费 (来源 falconx.io newsroom — 本环境 403);
  B = 1–4 周 cycle + 31 天通知 + 72h 提前退出 (来源为不可溯源的 grounding
  redirect; 且本资产 B 行在加严审查名单 — decisions.md FalconX 决议);
  检索摘要另给出 "月度 cycle + 14 天通知" 第三版本 (摘要非一手, 仅作线索)。
- 本会话验证尝试全部被环境代理 403: falconx.io, pareto.credit,
  docs.pareto.credit, pharos.watch, ethereum-rpc.publicnode.com (eth_call)。
- **按 C0: 无一手来源 → UNKNOWN。** registry 该行记 UNKNOWN-pending, 双列
  两通道原文, 禁止任何版本先行入表。
- **owner 浏览器核验路径 (~10 分钟, 二选一即可)**:
  1. docs.pareto.credit → Credit Vault epoch/withdrawal 机制页 + FalconX
     vault 专页 (cycle 长度、notice、instant-withdraw 条款、费率);
  2. Etherscan 已验证合约 **`0x433d5b175148da32ffe1e1a37a939e1b7e79be4d`
     (Pareto: Credit Vault FalconX USDC)** → Read Contract, 读 epoch/
     withdraw 参数 (链上读数 = 一手, 与冲突1同证据等级)。
- 推断 (显式标注, 待核): B 的 "72h + 下一 cycle 利率低 ≥1% 触发提前退出"
  形似 Pareto instant-withdraw 机制的参数化描述 — 若属实, A/B 可能各描述了
  同一机制的不同侧面 (常规 epoch 赎回 vs instant withdraw)。以文档/链上为准。

### 结论
- 冲突 1、3 已裁定并可入 registry; 冲突 2 记 UNKNOWN-pending (不阻塞
  E2-T2-dune 市场清单)。`complete E2-T1-facts` 据此执行 — 完成的是"提取+
  union 任务", registry 的 FalconX redemption 行仍为 UNKNOWN 直至 owner 核验。

### 冲突 2 补遗 (2026-07-10) — owner 核验回传, UNKNOWN-pending 解除
- owner 走了核验路径 1 (docs.pareto.credit), 回传引文 (本环境仍 403, 无法
  复取, 引文按 owner 提交记录):
  - 赎回周期 = 月度: "Cycle length | One month"
    (docs.pareto.credit/product/credit-vaults/live-vaults.md)
  - 通知期 = 1 个月: "Redemptions | Monthly, 1-month notice" (同页)
  - instant/early withdraw 存在: 下一 cycle 利率 "lower than the previous
    one by 1% or more" 时启用, "within 72 hours" 内 claim
    (docs.pareto.credit/product/users/lenders/guides/redeem.md)
  - 最低赎回额 = UNKNOWN (未见); 赎回费 = UNKNOWN ("Performance fee | 10%"
    为业绩费, 非赎回费)
  - 地址页列 Ethereum 合约 0x433D5B175148dA32Ffe1e1A37a939E1b7e79be4d
    (docs.pareto.credit/developers/addresses/product/credit-vaults.md)
- **本节 §推断 的预登记假设被证实**: A/B 各描述了同一机制的两个侧面
  (A = 常规月度 epoch 赎回; B = 参数化 instant-withdraw 路径)。A 的
  "min 250k, 无赎回费" 未再现, 维持 UNKNOWN。
- registry 行动: e2/registry.csv 建表时按上述口径录入 AA_FalconXUSDC
  redemption 行; 裁定记录另见 ops/decisions.md 2026-07-10 条目。
