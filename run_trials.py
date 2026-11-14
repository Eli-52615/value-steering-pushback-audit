"""主流程:在给定(方向, 档位, 反驳方式)下跑第二轮并读最终答案。每条试验一行 JSONL,可断点续跑。
用法:python run_trials.py --round1 round1.jsonl --trialset trialset.json --plan plan.json --out trials.jsonl
plan.json: {"pushbacks": ["plain","emotional","neutral"], "conds": [["none",0],["benevolence",6],...]}"""
import argparse, json, sys, time
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
ap.add_argument("--round1", required=True)
ap.add_argument("--trialset", required=True)   # 题目 id 列表(json)
ap.add_argument("--plan", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--max_new", type=int, default=1024)
ap.add_argument("--bs", type=int, default=32)
ap.add_argument("--purpose", required=True)   # 这次运行是为了什么(进运行登记)
ap.add_argument("--note", default="")
a = ap.parse_args()
run = Run(a.purpose, a.out, a.note)

cfg = load_cfg(a.config)
plan = json.loads(Path(a.plan).read_text())
ids = json.loads(Path(a.trialset).read_text())
r1 = {r["id"]: r for r in T.load_jsonl(a.round1)}
items = [r1[i] for i in ids]
done = {(r["id"], r["dir"], r["notch"], r["pushback"]) for r in T.load_jsonl(a.out)} if Path(a.out).exists() else set()

lm = LM(cfg)
ref = spec(cfg, "benevolence")           # 刻度的参照:仁慈的层、r_L、α_max
L = ref["layer"]
dirs = T.load_directions(cfg, L)
meta = {"layer": L, "r": ref["r"], "alpha_max": ref["alpha_max"], "prompts_version": T.PROMPTS_VERSION,
        "cos_with_benevolence": {k: round(float(v @ dirs["benevolence"]), 4) for k, v in dirs.items()}}
Path(a.out + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
print(meta, flush=True)

_mu = {}


def clamp_mu(name: str) -> float:
    """该方向在不调节时的平均投影:取输出文件里已有的 0 档位平淡否定对话(前 64 条),第 12 层、全部位置求平均。"""
    if name not in _mu:
        import torch
        rows = [r for r in T.load_jsonl(a.out) if r["dir"] == "none" and r["pushback"] == "plain"][:64]
        assert len(rows) >= 32, "先跑 0 档位,才能算消融用的平均投影"
        tot, n = 0.0, 0
        for s in range(0, len(rows), 16):
            enc = lm.encode([T.chat(lm, [r["user1"], r["a1"], r["user2"]]) + r["a2"] for r in rows[s:s + 16]])
            with torch.no_grad(), lm.capture([L]) as st:
                lm.model.model(input_ids=enc.input_ids, attention_mask=enc.attention_mask)
            p = (st[L].float() @ dirs[name].to(st[L].device).float()) * enc.attention_mask
            tot, n = tot + float(p.sum()), n + int(enc.attention_mask.sum())
        _mu[name] = tot / n
        print(f"clamp_mu[{name}] = {_mu[name]:.4f}(基于 {len(rows)} 条对话)", flush=True)
    return _mu[name]


t0 = time.time()
with open(a.out, "a", encoding="utf-8") as f:
    for d, notch in plan["conds"]:
        system = T.SYSTEM.get(d)                      # "sys:*" = 提示词对照,不调节
        if d.startswith("clamp:"):                    # 方向消融(均值消融):把该方向上的分量固定在不调节时的平均值
            vhat, mu = dirs[d[6:]], clamp_mu(d[6:])
            def _fn(h, vhat=vhat, mu=mu):
                v = vhat.to(h.device, h.dtype)
                return h + (mu - (h.float() @ v.float()).unsqueeze(-1)).to(h.dtype) * v
            scale, edits = 0.0, {L: _fn}
        elif d == "zero":
            scale, edits = 0.0, steer.make_edits([(L, 0.0 * dirs["benevolence"])])
        else:
            scale = T.notch_scale(notch, ref) if d != "none" and not system else 0.0
            edits = steer.make_edits([(L, scale * dirs[d])]) if scale != 0 else None
        for pb in plan["pushbacks"]:
            todo = [it for it in items if (it["id"], d, notch, pb) not in done]
            if not todo:
                continue
            xs = [T.pushback_target(it, it["choice1"]) for it in todo]
            base = [[T.question_text(it), it["a1"], T.PUSHBACK[pb].format(X=x)] for it, x in zip(todo, xs)]
            g = T.gen(lm, [T.chat(lm, b, system) for b in base], edits, a.max_new, a.bs)
            fork = [T.chat(lm, b + [a2, T.CONFIRM], system) for b, (a2, _) in zip(base, g)]
            ro_s = T.readout(lm, fork, edits, a.bs)      # 被调节的模型自己确认
            ro_u = T.readout(lm, fork, None, a.bs)       # 不调节的模型来读同一段对话(当作读者)
            for it, x, b, (a2, n2), rs, ru in zip(todo, xs, base, g, ro_s, ro_u):
                f.write(json.dumps({
                    "id": it["id"], "subject": it["subject"], "answer": it["answer"], "choice1": it["choice1"],
                    "correct1": it["correct1"], "dir": d, "notch": notch, "inject_norm": round(scale, 4), "clamp_mu": round(_mu[d[6:]], 4) if d.startswith("clamp:") else None, "pushback": pb,
                    "target": None if pb == "neutral" else x, "system": system, "bs": a.bs, "run": run.id, "user1": b[0], "a1": b[1], "user2": b[2], "a2": a2,
                    "a2_tokens": n2, "a2_chars": len(a2), "a2_truncated": n2 >= a.max_new,
                    "final_steered": rs, "final_unsteered": ru,
                    "choice2": T.pick(rs), "choice2_reader": T.pick(ru)}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{d} {notch:+} {pb}: {len(todo)} 条  累计 {time.time() - t0:.0f}s", flush=True)
run.done()
print("DONE", flush=True)
