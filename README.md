# Value steering under user pushback: a signal-detection audit

Code for the report *Steering Moves the Threshold, Not the Judgment: A Pre-registered Signal-Detection Audit of Value Steering under User Pushback* (AI x Epistemics Research Sprint, Apart Research, November 2026).

Model: Qwen3.5-9B. Items: CMMLU test set. The model wrapper, steering hooks and value-extraction pipeline come from a pre-competition project (`vt` package, imported via `sys.path`, not included here); see Appendix D of the report.

| File | Purpose |
|---|---|
| `trial.py`, `run_trials.py` | Prompts, generation, option-probability readout; runs direction × strength × pushback cells with resume |
| `analyze.py`, `stats.py` | Per-cell rates, d′ and c; pre-registered confirmatory tests (item bootstrap, Holm) |
| `prereg_rand20.md`, `make_rand20.py`, `make_set_rand20.py`, `rand20_stats.py` | Twenty random directions: rules (committed before the run), direction generation, item sample, random-effects analysis |
| `ruler_sample.py`, `ruler_correct.py`, `ruler_influence.py` | Human validation of the readout: stratified blind sample, correction and outcomes, per-label influence |
| `reglog.py`, `render_registry.py` | Append-only run registry |
| `plots_v1.py` | Figures 1 and 2 |

Commit history is part of the record: analysis rules were committed before the data they govern (e.g. `e99d17c` before the random-direction run, `a9b1f23` before its results were pulled). Comments in the code are in Chinese.

---

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
