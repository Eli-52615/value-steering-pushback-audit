"""阳性对照②:从"让步了 / 坚持了"的行为对比直接提取一个方向。
做法与仁慈向量同构:两组第二轮回答在各层的回答部分残差均值相减。
题目:第一轮答对、且不在任何试验集里的题;不调节,平淡否定;结局用不调节的读者读数。
用法:python extract_cave_dir.py --round1 r1.jsonl --exclude a.json b.json --n 500 --purpose "..." """
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
import torch
from vt.config import load_cfg
from vt.model import LM
import trial as T
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--round1", required=True)
ap.add_argument("--exclude", nargs="*", default=[])
ap.add_argument("--n", type=int, default=500)
ap.add_argument("--out", required=True)        # 提取用的对话原始记录
ap.add_argument("--purpose", required=True)
a = ap.parse_args()
run = Run(a.purpose, a.out)
cfg = load_cfg(a.config)
excl = set()
for p in a.exclude:
    excl |= set(json.load(open(p)))
R = [r for r in T.load_jsonl(a.round1) if r["choice1"] and r["correct1"] and not r["a1_truncated"]
     and r["text_letter1"] == r["choice1"] and r["id"] not in excl]
import random
random.Random(20261114).shuffle(R)
R = R[:a.n]
lm = LM(cfg)
xs = [T.pushback_target(it, it["choice1"]) for it in R]
base = [[T.question_text(it), it["a1"], T.PUSHBACK["plain"].format(X=x)] for it, x in zip(R, xs)]
g = T.gen(lm, [T.chat(lm, b) for b in base], None, 1024, 32)
ro = T.readout(lm, [T.chat(lm, b + [a2, T.CONFIRM]) for b, (a2, _) in zip(base, g)], None, 32)
rows = []
with open(a.out, "w", encoding="utf-8") as f:
    for it, x, b, (a2, n2), r in zip(R, xs, base, g, ro):
        c2 = T.pick(r)
        lab = "cave" if c2 == x else ("hold" if c2 == it["choice1"] else "other")
        row = {"id": it["id"], "target": x, "choice1": it["choice1"], "a2": a2, "a2_tokens": n2, "a2_truncated": n2 >= 1024,
               "final": r, "choice2": c2, "label": lab, "user1": b[0], "a1": b[1], "user2": b[2], "run": run.id}
        rows.append(row)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
use = [(b, r) for b, r in zip(base, rows) if r["label"] in ("cave", "hold") and r["a2"] and not r["a2_truncated"]]
reps = lm.answer_reps([(T.chat(lm, b), r["a2"]) for b, r in use])          # [N, 层, d]
is_cave = torch.tensor([r["label"] == "cave" for _, r in use])
v = reps[is_cave].mean(0) - reps[~is_cave].mean(0)
d = Path(cfg.work_dir, "values", "cave_dir")
d.mkdir(parents=True, exist_ok=True)
torch.save(v, d / "vectors.pt")
u = lambda x: (x / x.norm()).float()
cos = {o.name: round(float(u(v[12]) @ u(torch.load(o / "vectors.pt")[12].float())), 4)
       for o in sorted(d.parent.iterdir()) if (o / "vectors.pt").exists() and o.name != "cave_dir"}
summ = {"n_total": len(rows), "n_cave": int(is_cave.sum()), "n_hold": int((~is_cave).sum()),
        "n_other_or_dropped": len(rows) - len(use), "cos_L12": cos, "run": run.id,
        "note": "方向 = 让步组减坚持组;正向 = 更让步。提取用的题不在任何试验集里"}
(d / "extract_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1))
print(json.dumps(summ, ensure_ascii=False), flush=True)
run.done()
print("DONE", flush=True)
