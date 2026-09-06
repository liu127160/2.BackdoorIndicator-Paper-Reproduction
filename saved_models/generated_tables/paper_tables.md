# Paper tables: Vanilla / semantic / 400

本表为指定日志的实验结果，不是论文原始数值。单位均为百分比，表格保留一位小数。

评价轮固定为 659（攻击轮为 410–659）；400 表示实验初始 checkpoint 轮次。

## Table 2 — TPR/FPR (BA)

| Train alg. | Backdoor type | Injection round | Indicator | No defense |
| --- | --- | --- | --- | --- |
| Vanilla | semantic | 400 | 86.4/8.1 (0.0) | 0.0/0.0 (49.3) |

BA 为 poisoned acc（后门准确率）。No defense 不拒绝客户端，TPR/FPR 按 0.0/0.0 表示，并非日志检测计数。

## Table 7 — Indicator/No defense

| Train alg. | Backdoor type | 400 |
| --- | --- | --- |
| Vanilla | semantic | 88.4/89.8 |

Table 7 使用 benign acc（主任务准确率）。

## 核对与统计口径

TPR = 216/250 × 100 = 86.400000%；FPR = 191/2350 × 100 = 8.127660%。

使用第 659 轮训练后的累计检测计数：TP=216, FN=34, TN=2159, FP=191。FPR 分母包含 400–409 轮攻击开始前的良性客户端（共 2350），不是仅攻击期间的 2250。

按下列日志顺序合并；同一轮、同一准确率指标以最后一次全局模型记录为准。忽略本地模型及水印内部训练准确率；累计检测快照不相加，659 轮之后的数据不参与表格。

### No defense

- `saved_models/Sep.02_12.11.55/log.txt`

- `saved_models/Sep.02_21.59.50/log.txt`

合并后全局准确率覆盖 400–759 轮；覆盖重复指标记录 44 次。

- 第 659 轮 benign acc = 89.750000%；来源 `saved_models/Sep.02_21.59.50/log.txt:5220`。

- 第 659 轮 poisoned acc = 49.320000%；来源 `saved_models/Sep.02_21.59.50/log.txt:5221`。

### Indicator

- `saved_models/Sep.03_17.17.39/log.txt`

- `saved_models/Sep.05_17.26.11/log.txt`

合并后全局准确率覆盖 400–759 轮；覆盖重复指标记录 2330 次。

- 第 659 轮 benign acc = 88.400000%；来源 `saved_models/Sep.03_17.17.39/log.txt:23010`。

- 第 659 轮 poisoned acc = 0.000000%；来源 `saved_models/Sep.03_17.17.39/log.txt:23011`。
