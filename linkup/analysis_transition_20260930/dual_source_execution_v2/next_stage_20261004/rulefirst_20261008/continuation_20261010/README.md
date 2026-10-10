# D59 云端滚动续作（待运行回执）

本目录记录 2026-10-10 用户批准的滚动续作：在已验收五个实际语料 shard 之后，继续对冻结 manifest 中尚未验收的 shard 应用冻结规则。BU 直接从昆山/乌镇拉取源文件，用户提供的身份保存在代码和 Git 之外；Mac 不承载原文。只有在控制器启动、实际调度作业和完整回执出现后，才报告 direct-pull 已发生。

本轮不调用 API、不运行模型推理、不改变语义规则。滚动生产最多四个并发任务，每任务 4 CPU/8 GiB，并受 200 GB 总任务、10 GB 原始 staging、35 GB metadata staging 等上限约束；超出配额或重复失败时停止准入。metadata 采用一次有界缓存和分组定向查找，保留全部键以及 no-match、missing code、unofficial occupation、unmapped geography 等状态，不把旧 6,010,975 行候选框架当作分母。

当前状态：ROOT_CONTINUATION_DECISION.json 和公共编排脚本已准备。调度器观测到 preparation job 8004843 为 qw、production array 8004875 的 1–8 任务为 hqw/dependency-pending；它们已提交但尚未开始或完成。metadata 计划使用 26.606 GB PyArrow4 有界流式缓存与 grouped-wave joins，不使用 DuckDB。已发布运行快照：metadata key-prep job 8004986 exit 0（34 秒，424226 keys，1.107 GB）；controller QA 8005004 仍为 hqw、仅等待 QA 依赖；四个 staging jobs 8005067–8005070 正在运行，production 8004875 和 metadata QA 8004985 仍待处理。首批5个历史结果仍为 424226 postings、2162637 evidence；新的生产输出与 metadata join 尚未完成，不能宣称 D59 全量完成。公共 Git 只收录脱敏代码、方法、执行路径、聚合状态和回执；私有 manifest、凭据、原文及逐行输出不入库。此前五 shard 的 424225 processed、1 invalid_text retained、2162637 evidence rows 仍是历史已验收结果，与本轮新增结果分开。


## D60 scope correction

用户已明确：当前 8 个 shard 的 staging→production→QA 可以完成；这次 approximately 2.18 GB BU 使用是最后一次。后续所有 bulk extraction 和 metadata joins 改在中国 SCNet 原地运行，不把 26.6 GB metadata cache 转移到 BU。BU controller 8005004 与 metadata discovery 8005585 正在取消流程中；在收到实际 cancellation receipt 前不宣称已取消。D60 只限制未来权限，保留 D59 已有 BU 输出和 SCNet 原始数据，不改写历史运行事实。


最新状态：BU lane1 job 8005067 已完成（exit 0，2 shards，541,205,581 bytes，wall 2305 秒）；其余 lanes/生产波次仍在运行或等待，不能称为整个八 shard 批次完成。国内原地 preflight 已公开：昆山连通性/runtime 尚未验证，乌镇可达但需要 Intel shared libraries；尚无国内 production job。保留初始约 23 GB 可用空间与不超过 1 GB 新输出的 routing 约束。
