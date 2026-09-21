# 方法开发交接

- [RESEARCH_HANDOFF.md](RESEARCH_HANDOFF.md)：转向始末、历史结论、当前边界与接手顺序。
- [NEXT_EXECUTION_PROMPT.md](NEXT_EXECUTION_PROMPT.md)：已准备、未部署的下一轮 prompt，明确模型与 effort 分工。
- [METHOD_V1.md](METHOD_V1.md)：定义、文献依据、方程、失败条件及数据缺口。
- [synthetic_checks.py](synthetic_checks.py)：无经验输入的合成检查。
- [SYNTHETIC_RESULTS.json](SYNTHETIC_RESULTS.json)：实际运行结果，11/11 fixtures；非经验 power 或研究 PASS。
- [inference_stress.py](inference_stress.py) 与 [INFERENCE_STRESS_RESULTS.json](INFERENCE_STRESS_RESULTS.json)：500 次合成零假设检查，不是实际样本 power。
- [DECISION_AND_GAPS.md](DECISION_AND_GAPS.md)：已解决事项、未解决的证据条件与唯一下一步。

运行：`python3 p1/concentration_information/20260921_price_discovery_method/synthetic_checks.py`（仓库根目录）。

状态：方法原型完成，经验可行性和区别性贡献未通过。PIT 保持“未完成”。方法开发期间未访问 SCC、未采购。随后用户另行要求将本轮与前几轮成果 commit/push 到既有 P1 分支；Git 提交历史记录发布状态，不表示新研究执行获批。
