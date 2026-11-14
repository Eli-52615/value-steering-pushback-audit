"""提取一个新价值的向量(复用赛前 ValueTuner 的 3.2–3.4 和 3.5(a) 区分度),不做选层标定。
主实验里所有方向都在第 12 层、按仁慈的刻度注入,所以不需要新价值自己的 α_max。
用法:python run_extract.py --value values/xxx.yaml --purpose "..." """
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
import torch
from vt.config import load_cfg
from vt.judge import Judge
from vt.model import LM
from vt import pipeline as P
from vt.values import load_value
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--value", required=True)
ap.add_argument("--purpose", required=True)
a = ap.parse_args()
cfg = load_cfg(a.config)
value = load_value(a.value)
d = P.vdir(cfg, value["id"])
run = Run(a.purpose, str(d / "extract_summary.json"))
t0 = time.time()
log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)
lm, judge = LM(cfg), Judge(cfg.path("cache", "judge.sqlite"))
data = P.stage_data(cfg, judge, value, log)
rows = P.stage_responses(cfg, lm, judge, value, data, log)
v = P.stage_vectors(cfg, lm, value, rows, log)
ev = P.stage_eval(cfg, lm, judge, value, data, v, log)
L = 12
u = lambda x: (x / x.norm()).float()
cos = {}
for o in sorted(Path(cfg.work_dir, "values").iterdir()):
    if (o / "vectors.pt").exists() and o.name != value["id"]:
        cos[o.name] = round(float(u(v[L].float()) @ u(torch.load(o / "vectors.pt")[L].float())), 4)
kept = [r for r in rows if r["keep"]]
summ = {"id": value["id"], "layer": L, "auroc_L12": round(ev["auroc"][L], 4), "auroc_by_layer": [round(x, 3) for x in ev["auroc"]],
        "n_pos": sum(r["pole"] == "pos" for r in kept), "n_neg": sum(r["pole"] == "neg" for r in kept), "n_eval": ev["n"],
        "cos_L12": cos, "judge_calls": judge.n_calls, "run": run.id}
(d / "extract_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1))
log(json.dumps(summ, ensure_ascii=False))
run.done()
print("DONE", flush=True)
