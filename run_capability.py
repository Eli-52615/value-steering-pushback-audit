"""单轮正确率检查:在每个(方向, 档位)下只做第一轮,看调节有没有把模型的答题能力搞坏。
题目是没进任何试验集的题。回答在调节下生成,最终字母由不调节的读者读出。
用法:python run_capability.py --items items.jsonl --exclude a.json b.json --n 200 --plan plan.json --out cap.jsonl --purpose "..." """
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
from vt.config import load_cfg
from vt.model import LM
from vt import steer
from vt.dose import spec
import trial as T
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--items", required=True)
ap.add_argument("--exclude", nargs="*", default=[])
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--plan", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--purpose", required=True)
a = ap.parse_args()
run = Run(a.purpose, a.out)
cfg = load_cfg(a.config)
excl = set()
for p in a.exclude:
    excl |= set(json.load(open(p)))
items = [it for it in T.load_jsonl(a.items) if it["id"] not in excl]
random.Random(20261115).shuffle(items)
items = items[:a.n]
done = {(r["id"], r["dir"], r["notch"]) for r in T.load_jsonl(a.out)} if Path(a.out).exists() else set()
lm = LM(cfg)
ref = spec(cfg, "benevolence")
L = ref["layer"]
dirs = T.load_directions(cfg, L)
qs = [T.question_text(it) for it in items]
with open(a.out, "a", encoding="utf-8") as f:
    for d, notch in json.loads(Path(a.plan).read_text())["conds"]:
        if all((it["id"], d, notch) in done for it in items):
            continue
        scale = T.notch_scale(notch, ref) if d != "none" else 0.0
        edits = steer.make_edits([(L, scale * dirs[d])]) if scale != 0 else None
        g = T.gen(lm, [T.chat(lm, [q]) for q in qs], edits, 160, 48)
        ro = T.readout(lm, [T.chat(lm, [q, x[0], T.CONFIRM]) for q, x in zip(qs, g)], None, 48)
        for it, (a1, n1), r in zip(items, g, ro):
            c = T.pick(r)
            f.write(json.dumps({"id": it["id"], "answer": it["answer"], "dir": d, "notch": notch, "a1": a1, "a1_tokens": n1,
                                "reader": r, "choice": c, "correct": c == it["answer"], "run": run.id}, ensure_ascii=False) + "\n")
        f.flush()
        print(f"{d} {notch:+}: 正确率 {sum(T.pick(r) == it['answer'] for it, r in zip(items, ro)) / len(items):.3f}", flush=True)
run.done()
print("DONE", flush=True)
