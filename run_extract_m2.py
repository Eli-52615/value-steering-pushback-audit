"""模型 2:提取"仁慈(不含对话者)"并按 M1 的选层规则选层、标定 α_max。不做体检(楠 11-16 裁定不跑)。
和模型 1 完全相同的东西:价值定义文件(values/benevolence_ni.yaml)、提取用的问题和评分细则(拷贝模型 1 的 data.json,
不重新生成)、中性语料的提示(打分接口缓存里的同一批)、ValueTuner 3.3–3.5 的代码和阈值。
只有回答由 Gemma 自己生成,再由同一个打分接口打分筛选。
选层和刻度在看到任何结局之前定下:层 = M1 规则选中的层;+6 档位 = 该层正向 α_max 的 0.6 倍(trial.notch_scale)。
结果写进 <work_dir>/values/benevolence_ni/{layer_select.json, extract_summary.json} 和 runs/m2_prereg.json。
用法:python run_extract_m2.py --config <gemma yaml> --purpose "..." """
import argparse, json, shutil, sys, time
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
from vt.config import load_cfg
from vt.judge import Judge
from vt import pipeline as P
from vt.neutral import Neutral
from vt.values import load_value
from lm_compat import make_lm
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--value", default="values/benevolence_ni.yaml")
ap.add_argument("--src_work", default="/root/autodl-tmp/vt_work/dev9b")   # 模型 1 的工作目录(拷贝题目和缓存用)
ap.add_argument("--purpose", required=True)
ap.add_argument("--prereg", default="../runs/m2_prereg.json")
a = ap.parse_args()
cfg = load_cfg(a.config)
value = load_value(a.value)
d = P.vdir(cfg, value["id"])
src = Path(a.src_work)
# 同一批题目、同一份评分细则、同一个打分缓存(只拷贝,不覆盖已有文件)
for s, t in ((src / "values" / value["id"] / "data.json", d / "data.json"),
             (src / "values" / value["id"] / "value.json", d / "value.json"),
             (src / "cache" / "judge.sqlite", cfg.path("cache", "judge.sqlite"))):
    if not t.exists():
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, t)
run = Run(a.purpose, str(d / "layer_select.json"))
t0 = time.time()
log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)
lm, judge = make_lm(cfg), Judge(cfg.path("cache", "judge.sqlite"))
log(f"层数 {len(lm.layers)},候选层 {cfg.candidate_layers}")
neutral = Neutral(cfg)
neutral.build(lm, judge, log)
data = P.stage_data(cfg, judge, value, log)
rows = P.stage_responses(cfg, lm, judge, value, data, log)
v = P.stage_vectors(cfg, lm, value, rows, log)
ev = P.stage_eval(cfg, lm, judge, value, data, v, log)
sel = P.stage_select(cfg, lm, judge, value, data, v, ev, neutral, log)
L = sel["chosen"]
row = next(r for r in sel["layers"] if r["layer"] == L)
kept = [r for r in rows if r["keep"]]
summ = {"model": cfg.model_path, "value": value["id"], "chosen_layer": L, "rule_satisfied": sel["rule_satisfied"],
        "auroc_chosen": round(ev["auroc"][L], 4), "auroc_by_layer": [round(x, 3) for x in ev["auroc"]],
        "alpha_max": row["alpha_max"], "r": row["r"], "notch6_alpha": round(0.6 * row["alpha_max"]["pos"], 4),
        "notch6_inject_norm": round(0.6 * row["alpha_max"]["pos"] * row["r"], 4),
        "n_pos": sum(r["pole"] == "pos" for r in kept), "n_neg": sum(r["pole"] == "neg" for r in kept),
        "per_layer": [{"L": r["layer"], "auroc": round(r["auroc"], 3), "alpha_max": r["alpha_max"], "effect": round(r["effect"], 1),
                       "coherence_mid": round(r["coherence_mid"], 1)} for r in sel["layers"]],
        "judge_calls": judge.n_calls, "run": run.id, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule": "选层:M1 规则(连贯性≥70 的候选层中调节效果最大者);+6 = 0.6 × 该层正向 α_max;随机方向同注入范数"}
(d / "extract_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1))
Path(a.prereg).write_text(json.dumps(summ, ensure_ascii=False, indent=1))
log(json.dumps(summ, ensure_ascii=False))
run.done()
print("DONE", flush=True)
