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

## 状态
- 一致行 + A 补全行足以支撑 E2-T2-dune 的市场清单起草 (registry.csv 的 oracle/
  redemption 列可先填这些行)。
- `--complete E2-T1-facts` 待 owner 复核本 memo 三处冲突后执行。
