# Apart Sprint 新代码（2026-11-14 起）

AI x Epistemics Research Sprint（Apart Research，2026-11-13 至 11-15）期间写的代码。

## 哪些是赛前工作（preexisting）

本目录**之外**的 `../../ValueTuner/` 是赛前工作（2026-11-12 至 11-13，里程碑 M0–M2）：模型封装、激活调节、价值向量提取流程、调音台界面，以及用它提取出来的"仁慈"向量和四个对照方向（话多、情绪、正式、顺从）。本目录通过 `sys.path` 引用它的 `vt` 包，没有改动它。

## 本目录是新工作

| 文件 | 作用 |
|---|---|
| `prep_items.py` | 从 CMMLU 测试集按学科分层抽题 |
| `trial.py` | 提示词、生成、选项概率读数、方向加载、档位换算 |
| `run_round1.py` | 第一轮基线（不调节） |
| `make_trialset.py` | 按第一轮结果挑试验用题 |
| `run_trials.py` | 主流程：方向 × 档位 × 反驳方式，断点续跑 |
| `analyze.py` | 汇总表（让步率、纠正率、d′、c） |
| `export_readable.py` | 把原始对话导出成可读的 Markdown |

## 复现

```
python prep_items.py <cmmlu/test> items.jsonl 30
python run_round1.py --items items.jsonl --out round1.jsonl
python make_trialset.py round1.jsonl set.json 300 300
python run_trials.py --round1 round1.jsonl --trialset set.json --plan plan.json --out trials.jsonl
python analyze.py trials.jsonl
```
