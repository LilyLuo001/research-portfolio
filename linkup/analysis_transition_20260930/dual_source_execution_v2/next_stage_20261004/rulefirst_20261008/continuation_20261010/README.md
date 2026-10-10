# D59 云端滚动续作（待运行回执）

本目录记录 2026-10-10 用户批准的滚动续作：在已验收五个实际语料 shard 之后，继续对冻结 manifest 中尚未验收的 shard 应用冻结规则。BU 直接从昆山/乌镇拉取源文件，用户提供的身份保存在代码和 Git 之外；Mac 不承载原文。只有在控制器启动、实际调度作业和完整回执出现后，才报告 direct-pull 已发生。

本轮不调用 API、不运行模型推理、不改变语义规则。滚动生产最多四个并发任务，每任务 4 CPU/8 GiB，并受 200 GB 总任务、10 GB 原始 staging、35 GB metadata staging 等上限约束；超出配额或重复失败时停止准入。metadata 采用一次有界缓存和分组定向查找，保留全部键以及 no-match、missing code、unofficial occupation、unmapped geography 等状态，不把旧 6,010,975 行候选框架当作分母。

当前状态：ROOT_CONTINUATION_DECISION.json 和公共编排脚本已准备。调度器观测到 preparation job 8004843 为 qw、production array 8004875 的 1–8 任务为 hqw/dependency-pending；它们已提交但尚未开始或完成。metadata 计划使用 26.606 GB PyArrow4 有界流式缓存与 grouped-wave joins，不使用 DuckDB。已发布运行快照：metadata key-prep job 8004986 exit 0（34 秒，424226 keys，1.107 GB）；controller QA 8005004 仍为 hqw、仅等待 QA 依赖；四个 staging jobs 8005067–8005070 正在运行，production 8004875 和 metadata QA 8004985 仍待处理。首批5个历史结果仍为 424226 postings、2162637 evidence；新的生产输出与 metadata join 尚未完成，不能宣称 D59 全量完成。公共 Git 只收录脱敏代码、方法、执行路径、聚合状态和回执；私有 manifest、凭据、原文及逐行输出不入库。此前五 shard 的 424225 processed、1 invalid_text retained、2162637 evidence rows 仍是历史已验收结果，与本轮新增结果分开。


## D60 scope correction

用户已明确：当前 8 个 shard 的 staging→production→QA 可以完成；这次 approximately 2.18 GB BU 使用是最后一次。后续所有 bulk extraction 和 metadata joins 改在中国 SCNet 原地运行，不把 26.6 GB metadata cache 转移到 BU。BU controller 8005004 与 metadata discovery 8005585 正在取消流程中；在收到实际 cancellation receipt 前不宣称已取消。D60 只限制未来权限，保留 D59 已有 BU 输出和 SCNet 原始数据，不改写历史运行事实。


D60 handoff closure：已尝试将现有约 15 MB key artifact 从 BU 传至昆山目标目录；传输目标已写入，但 30 秒 checksum readback 超时，因此状态为 unverified，未发布 KEY_TRANSPORT_RECEIPT_PUBLIC.json。BU 原件保留。当前没有国内 preflight、join 或 production job 已提交；本记录不声称中国 SCNet 已开始运行。


BU wave closeout：BU8 已完成 672,976 postings、3,440,595 evidence rows、366,822,166 bytes，QA job 8004985 通过。该数字与已验收的前五 shard 不能直接相加为 unique 总量；跨集合 key audit 仍待中国侧完成。当前中国侧 agents 正在处理 Kunshan metadata 与 Wuzhen 四生产任务，实际 job 尚未由公共回执确认。


D61 当前状态：WZ production job 46208844 的四个任务完成，QA 46209816 通过，342546 postings、1753539 evidence rows、186863325 bytes；wrapper 初次失败 job 46208826（exit 1、无数据）保留为历史事实，随后修复 load order。昆山 metadata join/initial inventory job 124116745 仍运行中，未完成。BU 13-shard 回传约 598 MB 仍进行且未验证，cross-13 QA 尚未通过。


BU13 传输与 QA 已解决：作业 124118871 完成（exit 0，37 秒，54 files，597,922,077 bytes，hash 全通过）；13 shards 合计 1,097,202 postings、5,603,232 evidence，global JOB_HASH/locator unique。失败 124117556、重复取消 124117634、以及 124118220/124118472 的启动问题均保留为历史故障记录，修复为 module-only bootstrap，不归因于平台。metadata job 124116745 仍运行，正在 extracting records_01，未宣称完成。


BU13 cleanup 已核验完成：删除 26 个已回传私有 Parquet（597,842,064 bytes）、16 个临时 staging 文件（2,180,308,411 bytes）及 3 个专用凭据文件；公共 receipts/code/logs、SCNet 原始数据和无关 job 均保留。metadata job 124116745 仍运行，不能宣称完整 metadata/full wave 完成。


D62 runtime optimization is prepared while the replacement wave runs: `ROOT_D62_METADATA_PREFILTER_PUBLIC.json` and the independent acceptance checklist define the Arrow exact-hash prefilter and fixed semantic gates. Qualification job 124122881 passed the synthetic O*NET/Records checks, but its cache and synthetic Records predicate caveats do not establish real Records accuracy or performance. Replacement chain 124124467→124124470[1–4]→124124478 is queued/dependency-pending; the full wave remains pending final PASS. The prior 124116745 chain stopped; its partial R1 receipt is preserved but unaccepted and not merged.
