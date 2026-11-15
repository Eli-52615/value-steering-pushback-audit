"""新价值的完整体检(和赛前 M1 对仁慈做的一样):选层标定(各候选层的 α_max、调节效果)+ 3.6 体检五项
(区分度、激活最强/最弱片段、logit lens、SAE 特征、与对照方向的混杂)。
已有的 data/responses/vectors/eval 直接复用(文件在就跳过),不重新提取,所以向量和主实验用的是同一个。
楠 11-15 下午裁定要做。用法:python run_checkup.py --value values/benevolence_ni.yaml --purpose "..." """
import argparse, json, sys, time

sys.path.insert(0, "/root/autodl-tmp/vt")
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
for f in ("data.json", "responses.json", "vectors.pt", "eval.json"):  # 必须复用主实验那一份向量
    assert (d / f).exists(), f"缺 {f}:体检必须用主实验用的那个向量,不能重提"
run = Run(a.purpose, str(d / "checkup.json"))
t0 = time.time()
log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)
lm, judge = LM(cfg), Judge(cfg.path("cache", "judge.sqlite"))
out = P.run_value(cfg, lm, judge, value, log)
sel = json.loads((d / "layer_select.json").read_text(encoding="utf-8"))
log(json.dumps({"chosen_layer": sel["chosen"], "per_layer": [{"L": r["layer"], "alpha_max": r["alpha_max"], "effect": round(r["effect"], 1),
               "coh_mid": round(r["coherence_mid"], 1)} for r in sel["layers"]], "judge_calls": judge.n_calls}, ensure_ascii=False))
run.done()
print("DONE", flush=True)
