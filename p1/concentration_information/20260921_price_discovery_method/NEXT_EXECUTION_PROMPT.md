# P1：新闻—ETF—真实篮子联合覆盖与方法实现

状态：`PREPARED_NOT_EXECUTED`。将本 prompt 提交为执行指令后才开始；它不批准经验响应值分析或购买。

## 目标和先读材料

在 LilyLuo001/research-portfolio 的既有 P1 工作分支，推进候选问题：“ETF 的总量价格发现优势，是否掩盖公司信息覆盖的不均衡？”

依次读取 `p1/concentration_information/20260921_price_discovery_method/RESEARCH_HANDOFF.md`、相邻 literature 目录的 `CONTRIBUTION_ASSESSMENT.md`，以及本目录 `METHOD_V1.md`、`DECISION_AND_GAPS.md` 和两个合成结果 JSON。接受历史结论，不重启全项目审计。旧 H2 保持 INCONCLUSIVE_STOP_SPENDING，PIT 保持未完成。

本轮要产出实际联合覆盖或逐项可定位缺口，以及经过独立复核的方法实现。不是写另一份泛化计划，也不是提前证明论文成立。

## 模型、effort 与委派

| 板块 | 请求模型 / effort | 责任 |
| --- | --- | --- |
| 协调与科学裁决 | gpt-5.6-sol / medium | 保留已有协调器；锁定范围、估计对象与最终决定，不代做机械库存 |
| 来源绑定/联合覆盖工程 | gpt-5.6-terra / medium | 现有 manifest、许可、时钟/身份/持仓元数据与覆盖计数；独占 sources/ 输出 |
| 方法代码工程 | gpt-5.6-terra / medium | 在合成数据实现成对响应、标准化、比值集合与分解；独占 method/ 输出 |
| 独立方法及数据复核 | gpt-5.6-sol / high | 实际代码和覆盖材料存在后启动；独立复算关键计数、反例及估计对象，不是第二个角色标题 |

最多同时运行协调器加两个工程代理；工程完成后再启 reviewer。无嵌套委派、额外文献团队、Max/Ultra 或自动 Astra 升级。若确有 Sol 无法关闭的具体理论问题，记录问题和最小证据包后提出单项升级请求，而非重开整篇研究。

先核对实际工具暴露的模型/effort 能力。分别记录 requested、accepted dispatch、observable telemetry；不可见填 NOT_OBSERVED，不能凭自述认证模型。不可用时报告该板块阻碍，继续能完成的非替代工作，不暗换模型。无新 agent 配置、认证改动或上下文全量复制。只传当前子任务和相关文件路径。记录 token 使用仅限可观察统计。

## 权限与输出边界

先读现有本地文档、代码、manifest 和已许可元数据汇总；只对有明确既有来源、字段、操作及环境许可的视图执行查询。SCC 登录成功不是新操作授权；不连接 WRDS，不恢复广泛 PIT 原表核查。精确权限不足则准备白名单查询和一次具体操作请求，仍完成已获准部分。

不读取 EPS/forecast 数值、价格/报价数值/size、returns、CAR、响应结果或 outcome 排名；不 SELECT *，不先读全表再丢列。原始数据 footer 仅名称/类型/记录数等获准元数据，禁止读取财务/报价列 min/max 统计。受限源产生 coverage 布尔值必须有已批准的 custodian 过程，否则为 UNKNOWN。

许可行级元数据留 SCC；本地与 Git 只放可发布代码、文档、汇总和 receipts。无购数、认证修改、原始输入修改或 merge。用户的 Git 发布授权仅用于本轮经检查的轻量 P1 产物：先精确 stage、检查无密钥/行级许可记录再 commit/push 到既有分支；无 force push、不改 main。

## A. 源绑定与真实联合覆盖

1. 从已有留存 manifest 解析实际文件、版本、数据集/schema、时间范围及既有授权；不按文件名宣称数据可用、不全盘递归扫 SCC、不重哈希全部大文件。历史完整性回执可复用，记录未复核部分。
2. 绑定经济消息、发行人/证券、ETF、公告前实际持仓与可得时间、历史有效标识、公告时间区间/时区、交易日历、报价覆盖元数据。区分持仓与 PCF/指数代理；代理不能标成真实篮子。ticker 不替代历史映射。
3. 由获准元数据程序生成新闻—ETF—篮子连接；逐阶段报告源记录数、经济事件认证状态、ETF/发行人/日期覆盖、时间精度、共同 session、真实篮子可构造状态、各期限联合覆盖与缺失原因。区分“文件范围覆盖”“记录覆盖”“双边报价状态有效”，前者不能证明后者。未知不是零；模板不是观测。
4. 不默默继承旧 conversion、top8/490 或已购四个技术探针的研究人口。列出实际窗口能回答哪些有限问题、不能代表哪些总体。不得静默以近期或 RTH 替代所需历史/非 RTH。
5. 同一事件跨 ETF 的复用、发行人/日期依赖及 TOP/REST 共同支持只作元数据描述；不当成有效样本量或经验 power。新闻强度/流动性数值未读时，其共同支持注明 NOT_ASSESSED。

## B. 有限方法实现，不读经验结果

1. 将 V1 编成可测试的纯函数/小型实现，区分 ETF 和实际篮子、bid/ask/mid、经济消息依赖单位、时钟区间及有效但未更新的报价状态。
2. 明确估计量是标准化平均响应之比，不是公司平均速度。选择一项透明、可实现的固定共同支持标准化方案并标为 PROPOSED；不得为代码方便改 estimand，也不引入无必要的 ML/复杂架构。
3. 实现响应差/终端响应的联合协方差与比值置信集合，保留无界、分离与空集合；组间比值差须联合推断，不用两个区间相减。实际 issuer/date 多维推断未验证就不宣称可用。
4. 实现构成/组内响应分解及无支持时显式拒绝。保留终端等价、稳定性、反转、报价两侧不一致与时钟不确定的失败状态；不把不显著当等价。
5. 复用已完成 fixtures，只增补本次生产接口/数学修改所需测试。新增合成数据检验重复事件、弱分母、构成变化、异步缺报、共同支持失败和标准化 estimand。明确哪些只是逻辑测试、哪些校准了推断。无经验 power。
6. 5/60 分钟、TOP5、±10% 等 V1 草案参数保持 PROPOSED_NOT_FROZEN，提交简明冻结选项。不存在未获批准的默认确认性分析；改变公式/映射必须在变更表说明并测试。

## C. 独立复核与停止规则

reviewer 读取新 source bindings、代码和实际汇总，独立从获准元数据复算关键分母/重复连接；不能访问时写 NOT_REPRODUCED，不签数据 PASS。检查标准化、比值推断、篮子可比性及文献增量边界。只复核这次新增内容，不重复旧 H2 或完整文献审计。

最多两轮针对明确问题清单的修复—复核；最终 review 必须对应最终受影响文件 hash。仍有阻断项则 HOLD，不能留下未复核修复却声称 PASS。合成测试通过不是独立理论证明。

## 交付与唯一下一行动

在新的 `p1/concentration_information/20260921_news_basket_readiness/` 保存：

- `SOURCE_BINDINGS.json`：来源/版本、许可证据、字段映射、可用与未知；不含凭据。
- `JOINT_SUPPORT.md`：实际分阶段汇总、分母、来源、缺口；获准行级连接表仅 SCC，回执给出路径。
- `METHOD_V2.md`、`method/` 代码与合成测试结果：变更表、估计对象、待冻结参数及运行命令。
- `INDEPENDENT_REVIEW.md`：独立复算、问题闭环及最终 hash。
- `EXECUTION_RECEIPT.json`：实际命令/边界、模型路由证据、是否运行/未运行、输出与测试哈希。
- `DECISION.md`：至多一页，选择 READY_FOR_PI_FREEZE / HOLD_DATA / HOLD_METHOD / NO_DISTINCT_CONTRIBUTION；多个阻碍可并列，列一个优先下一行动。

READY_FOR_PI_FREEZE 不是 research GO，也不自动允许打开经验值。若缺输入，给一次精确的 source/columns/filter/environment/output 操作请求，不要求用户提供程序可以生成的名单，不要求重签整个研究合同。若已具备有限试验条件，交付一份小样本冻结及值访问提案，不自动执行。

本轮不声称集中度因果效应、ETF 独立信息生产、Alpha 消失或实证 power；最终仍为 HOLD_CONTRIBUTION_AND_EMPIRICAL_VALIDATION，直到后续具体科学门槛真正通过。

路由依据：官方文档支持明确指定 model 与 effort，但实际能力须运行时验证：https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning 。本文件只记录请求分工，不证明任何代理已经启动。
