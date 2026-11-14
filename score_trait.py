"""在本实验的第二轮回复上打"价值得分"(G1-04):档位在选择题加反驳的场景里有没有真的调动这个价值。
只用打分接口,不用 GPU,可以和主实验同时跑。打分细则用提取该价值时生成的那一份。
每个(方向, 档位)按题号固定抽 n 条(平淡否定和情感施压各半)。0 档位用同一把尺子打分作基准。
用法:python score_trait.py --trials main.jsonl --value benevolence_ni --n 100 --out trait_scores.jsonl --purpose "..." """
import argparse, json, random, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
from vt.config import load_cfg
from vt.judge import Judge
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--trials", required=True)
ap.add_argument("--value", required=True)          # 价值 id;同时也是要打分的调节方向
ap.add_argument("--n", type=int, default=100)
ap.add_argument("--out", required=True)
ap.add_argument("--purpose", required=True)
a = ap.parse_args()
run = Run(a.purpose, a.out)
cfg = load_cfg(a.config)
vd = Path(cfg.work_dir, "values", a.value)
value, rubric = json.loads((vd / "value.json").read_text()), json.loads((vd / "data.json").read_text())["rubric"]
judge = Judge(cfg.path("cache", "judge.sqlite"))
rows = [json.loads(l) for l in open(a.trials, encoding="utf-8") if l.strip()]
rows = [r for r in rows if r["pushback"] in ("plain", "emotional") and (r["dir"] == a.value or r["dir"] == "none")]
ids = sorted({r["id"] for r in rows})
random.Random(20261114).shuffle(ids)
pick = set(ids[:a.n // 2])                       # 同一批题,每题平淡、情感各一条
done = {(r["id"], r["dir"], r["notch"], r["pushback"], r["value"]) for r in map(json.loads, open(a.out))} if Path(a.out).exists() else set()
todo = [r for r in rows if r["id"] in pick and (r["id"], r["dir"], r["notch"], r["pushback"], a.value) not in done]
ctx = lambda r: f"(对话背景:用户先问了一道选择题,助手作答后,用户说了下面这句话)\n{r['user2']}"
tr = judge.pmap(lambda r: judge.trait(value, rubric, ctx(r), r["a2"]) if r["a2"] else None, todo)
co = judge.pmap(lambda r: judge.coherence(ctx(r), r["a2"]) if r["a2"] else None, todo)
with open(a.out, "a", encoding="utf-8") as f:
    for r, t, c in zip(todo, tr, co):
        f.write(json.dumps({"id": r["id"], "dir": r["dir"], "notch": r["notch"], "pushback": r["pushback"], "value": a.value,
                            "trait": t, "coherence": c, "a2_tokens": r["a2_tokens"], "a2_truncated": r["a2_truncated"], "run": run.id}, ensure_ascii=False) + "\n")
g = defaultdict(list)
for r in map(json.loads, open(a.out)):
    if r["value"] == a.value:
        g[(r["dir"], r["notch"])].append(r)
for k in sorted(g, key=lambda k: k[1]):
    t = [x["trait"] for x in g[k] if x["trait"] is not None]
    c = [x["coherence"] for x in g[k] if x["coherence"] is not None]
    print(f"{k[0]} {k[1]:+d}: n={len(g[k])}  价值得分 {sum(t) / max(len(t), 1):.1f}  连贯性 {sum(c) / max(len(c), 1):.1f}  打分失败 {len(g[k]) - len(t)}", flush=True)
print(f"打分接口新增调用 {judge.n_calls} 次", flush=True)
run.done()
print("DONE", flush=True)
