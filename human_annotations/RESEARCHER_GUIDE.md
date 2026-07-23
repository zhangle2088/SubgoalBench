# 研究负责人操作指南

## 1. 正式标注前

建议使用三个互不接触的标注者编号，例如 `A01`、`A02`、`A03`。编号不应包含姓名、邮箱或学号。

先使用额外样本进行短暂培训：

1. 共同阅读 Φ 和 Δ 标准；
2. 完成少量练习并讨论分歧；
3. 冻结标注说明；
4. 清除练习进度后再开始正式标注。

正式数据开始后，不应根据 probe 分数、ASR 或已出现的标注结果修改 rubric。若确实必须修改，应提升 `PACKAGE_VERSION`、重新生成整个工作包并重新标注。

## 2. 盲法

标注者可以看到：

- 原始用户任务；
- 候选动作之前的工作流；
- Φ 所需的 payload 和 candidate action；
- Δ 所需的 prefix、payload 和对应 action；
- A–E 标准。

标注者不应看到：

- Kimi 或其他 probe 的分数、label probabilities 或 reasoning；
- prefix 的人工设计等级或预期顺序；
- 任意目标模型的 ASR、tool execution outcome 或 defense result；
- 其他标注者答案。

浏览器数据按 `package version + annotator ID + factor` 分开保存。同一个编号不要交给多人共用。

## 3. 样本设计

Φ 覆盖 10 个 fixed workflow state 中的全部 60 个 payload。

Δ 使用 20 个完整 payload 组：每个 workflow state 选择主坐标中最低 Φ 和最高 Φ 的 payload，并保留每组全部 8 个 prefix，共 160 项。这样可以覆盖不同执行阻力，同时不根据待验证的 Δ 分数选择样本。页面对全部样本进行基于标注者编号的确定性随机排序；组内顺序不会呈现给标注者。

具体选择记录在 `package_manifest.json`。

## 4. 收集文件

建议将 CSV 放在一个不随工作包分发的目录，例如：

```text
human_annotations/collected/
  A01_phi.csv
  A01_delta.csv
  A02_phi.csv
  ...
```

分析脚本允许中途导出的不完整 CSV，但正式统计前应确认：

- 每名标注者的 Φ 为 60/60；
- 每名标注者的 Δ 为 160/160；
- `package_version` 完全一致；
- 同一标注者、factor、item 只有一条非空答案。

如果同一个人多次导出，分析脚本会按 `updated_at` 保留最新记录并给出提示。

## 5. 论文建议报告的量

- 标注者人数、背景、培训与盲法；
- Φ/Δ 样本数和 Δ 的分层抽样单位；
- exact agreement 和 within-one-label agreement；
- ordinal Krippendorff's alpha；
- human mean 与 probe score 的 Spearman rho 和 MAE；
- human consensus 与 probe modal label 的 quadratic weighted kappa；三位标注者无多数标签时，consensus 使用序数中位数；
- Δ 每个 payload 组内的 Kendall tau-b；
- 按 workflow/action family 的主要分歧类型。

置信区间和最终论文表建议在冻结 CSV 后另行做 cluster bootstrap；Δ 应按 payload group 重采样，Φ 至少按 workflow 或 payload 重采样。

## 6. 隐私与伦理记录

若标注者不是论文作者，应记录招募方式、报酬、预计耗时、知情说明以及适用的机构伦理要求。论文中只报告汇总统计，不公开标注者编号与备注中的个人信息。
