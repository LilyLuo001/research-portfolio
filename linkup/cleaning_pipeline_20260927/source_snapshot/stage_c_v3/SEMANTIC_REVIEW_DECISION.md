# V3 语义复核决定

V3 的技术回归通过，但本轮不放行为正式研究变量，也不开始全量语义运行。

另一个模型先完整阅读 12 条广告并冻结标签，之后主任务才生成 V3 对照。其结论不是人工金标准；样本少且来自既有区域开发试样，不能估总体准确率。它仍揭示了值得优先修复的共性问题：

- `Candidates should have a PhD and at least 3 years ...` 中的学位和年限已被发现，但语境停留为 unknown，没有进入要求计数。
- 银行广告的资格段仍继承 company 语境，真实学历—经验替代及一年经验要求因此被排除。
- `High School graduate`、部分本科学位常见表达没有进入学位词典。
- `What You Will Bring` 等资格标题覆盖不足，使明确经验条件缺少强度；preferred 标题与局部 must/required 冲突则需要单独标记。
- `Bachelor degree and three years ... or a master degree and one year ...` 不能把两个学位分别编码为无条件要求。当前局部候选不是完整路径解析。
- `Qualifications:\nExperience:\nOne to three years in banking.` 仍未绑定经验标题与紧随其后的年限。

同时保留正确行为：未提及经验不当作明确无需；福利中的 GED 不当作必备学历；并列经历年限不相加；同等学历与经验替代分开。

下一版仅修复段落作用域、局部资格措辞、常见词形及不明确资格路径的保守标记。不得按 JOB_HASH 写特例。用过的 12 条从此成为开发案例，后续冻结验证必须另外选取并按模板排除。V3 与其两区运行产物保留不覆盖，以便比较。
