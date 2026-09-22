# ES MBP-1 成交方向裁定

日期：2026-09-22。

Databento 的[通用字段说明](https://databento.com/docs/standards-and-conventions/common-fields-enums-types)明确：当 `action=T` 时，`side=B` 是买方主动成交，`side=A` 是卖方主动成交，`side=N` 表示未指定方向；`T` 是主动订单成交且不改变订单簿。其 [MBP-1 schema](https://databento.com/docs/schemas-and-data-formats/mbp-1) 同样将 `side` 定义为触发事件的一侧。

对已下载的 `GLBX.MDP3` 2024-09-18 ES窗口作原始记录核查：467,752条MBP-1记录中，66,082条为 `action=T`；34,016条 `side=B`、32,065条 `side=A`、1条 `side=N`，已知方向比例为99.9985%。因此本轮可以将ES成交方向纳入所有模型共同的基础信息块，同时把未知方向单列。

构造沿用股票的三个过去区间，但ES数值是期货价格乘合约数的缩放notional proxy，没有乘合约乘数，不称为真实美元成交额。`no_trade` 是观察到没有成交；`side=N` 的成交进入 unknown volume，不能写成零有符号流。最终结果仍需复核全部32个ES文件的action/side分布。
