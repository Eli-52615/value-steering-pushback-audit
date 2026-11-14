"""主图。在服务器上跑(本机没有 matplotlib)。图里的字用英文(论文用)。
用法:python plots.py trials.jsonl 输出目录 [--dir benevolence_ni] [--reader|--steered] [--boot 2000]
图 1:错误让步率与自我纠正率随档位的变化(平淡否定 + 情感施压合并,另各画一张),带按题 bootstrap 的 95% 区间;
      随机方向 ±6 画成灰色区间。
图 2:d′ 和 c 随档位的变化。
图 3:各方向在 +6 相对 0 档位的错误让步率变化(森林图)。
同时写出 fig_data.json:图上每个点的数值和区间,供数字核对表引用。"""
import json, random, sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze import outcome, sdt

a = sys.argv
V = a[a.index("--dir") + 1] if "--dir" in a else "benevolence_ni"
key = "choice2" if "--steered" in a else "choice2_reader"
B = int(a[a.index("--boot") + 1]) if "--boot" in a else 2000
out = Path(a[2]); out.mkdir(parents=True, exist_ok=True)
cell, correct = defaultdict(dict), {}
for l in open(a[1], encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        cell[(r["dir"], r["notch"], r["pushback"])][r["id"]] = int(outcome(r, key) == "to_target")
        correct[r["id"]] = r["correct1"]
LBL = {"benevolence_ni": "Benevolence (excl. interlocutor)", "benevolence": "Benevolence (original def.)", "autonomy": "Autonomy",
       "cave_dir": "Capitulation direction", "ctrl_verbosity": "Verbosity", "ctrl_sentiment": "Positive sentiment",
       "sys:defer": "System prompt: defer to user", "clamp:benevolence": "Mean-ablate benevolence (orig.)",
       "clamp:rand1": "Mean-ablate random", "rand": "Random directions (mean of 3)", "zero": "Zero vector (negative control)"}


def have(d, n, pbs):
    return all((d, n, pb) in cell for pb in pbs)


def ids_for(keys):
    s = set.intersection(*[set(cell[k]) for k in keys])
    return sorted(i for i in s if correct[i]), sorted(i for i in s if not correct[i])


def rate(d, n, pbs, s):
    if d == "rand":
        ds = [x for x in ("rand1", "rand2", "rand3") if have(x, n, pbs)]
        return sum(rate(x, n, pbs, s) for x in ds) / len(ds)
    return sum(cell[(d, n, pb)][i] for pb in pbs for i in s) / (len(s) * len(pbs))


def boot(stat, C, W, seed=20261114):
    rng = random.Random(seed)
    v = sorted(stat([rng.choice(C) for _ in C], [rng.choice(W) for _ in W]) for _ in range(B))
    return stat(C, W), v[int(0.025 * B)], v[int(0.975 * B) - 1]


def keys_of(d, n, pbs):
    if d == "rand":
        return [(x, n, pb) for x in ("rand1", "rand2", "rand3") for pb in pbs if (x, n, pb) in cell]
    return [(d, n, pb) for pb in pbs]


data = {"direction": V, "readout": key, "boot": B}
notches = sorted({n for (d, n, pb) in cell if d == V} | {0})
src = lambda n: ("none", 0) if n == 0 else (V, n)

# ---- 图 1
for tag, pbs in (("pooled", ["plain", "emotional"]), ("plain", ["plain"]), ("emotional", ["emotional"])):
    ns = [n for n in notches if have(*src(n), pbs)]
    if len(ns) < 2:
        continue
    C, W = ids_for([k for n in ns for k in keys_of(*src(n), pbs)])
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    rec = {"n_correct": len(C), "n_wrong": len(W), "points": []}
    for name, col, sel in (("Regressive capitulation (was right, switched to user's wrong option)", "#c0392b", "C"),
                           ("Self-correction (was wrong, switched to user's right option)", "#2471a3", "W")):
        pts = [boot(lambda c, w, n=n: rate(*src(n), pbs, c if sel == "C" else w), C, W) for n in ns]
        ax.errorbar(ns, [100 * p[0] for p in pts], yerr=[[100 * (p[0] - p[1]) for p in pts], [100 * (p[2] - p[0]) for p in pts]],
                    marker="o", color=col, capsize=3, label=name)
        rec["points"] += [{"metric": sel, "notch": n, "rate": p[0], "lo": p[1], "hi": p[2]} for n, p in zip(ns, pts)]
    for n in (6, -6):
        if keys_of("rand", n, pbs):
            Cr, Wr = ids_for(keys_of("rand", n, pbs) + keys_of("none", 0, pbs))
            for sel, col in (("C", "#c0392b"), ("W", "#2471a3")):
                p = boot(lambda c, w: rate("rand", n, pbs, c if sel == "C" else w), Cr, Wr)
                ax.errorbar([n + (0.35 if sel == "C" else 0.6)], [100 * p[0]], yerr=[[100 * (p[0] - p[1])], [100 * (p[2] - p[0])]],
                            marker="s", color="gray", mfc=col, capsize=3, alpha=0.8,
                            label="Random directions, same norm" if (n == 6 and sel == "C") else None)
                rec["points"].append({"metric": sel, "notch": n, "dir": "rand", "rate": p[0], "lo": p[1], "hi": p[2]})
    ax.set_xlabel(f"Steering notch: {LBL.get(V, V)}"); ax.set_ylabel("% of trials"); ax.set_xticks(ns); ax.set_ylim(0, 100)
    ax.set_title({"pooled": "Plain + emotional pushback", "plain": "Plain pushback", "emotional": "Emotional pushback"}[tag], fontsize=10)
    ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False)
    fig.savefig(out / f"fig1_{tag}.png", dpi=300, bbox_inches="tight"); fig.savefig(out / f"fig1_{tag}.pdf", bbox_inches="tight"); plt.close(fig)
    data[f"fig1_{tag}"] = rec

# ---- 图 2
pbs = ["plain", "emotional"]
ns = [n for n in notches if have(*src(n), pbs)]
if len(ns) >= 2:
    C, W = ids_for([k for n in ns for k in keys_of(*src(n), pbs)])
    def sd(n, c, w, j):
        d, nn = src(n)
        return sdt(sum(cell[(d, nn, pb)][i] for pb in pbs for i in w), 2 * len(w), sum(cell[(d, nn, pb)][i] for pb in pbs for i in c), 2 * len(c))[j]
    fig, axs = plt.subplots(1, 2, figsize=(7, 3))
    rec = []
    for j, (ax, nm) in enumerate(zip(axs, ("Sensitivity d′", "Criterion c  (higher = more reluctant to switch)"))):
        pts = [boot(lambda c, w, n=n: sd(n, c, w, j), C, W) for n in ns]
        ax.errorbar(ns, [p[0] for p in pts], yerr=[[p[0] - p[1] for p in pts], [p[2] - p[0] for p in pts]], marker="o", color="black", capsize=3)
        ax.set_xlabel("Steering notch"); ax.set_title(nm, fontsize=9); ax.set_xticks(ns)
        rec += [{"metric": "dprime" if j == 0 else "c", "notch": n, "value": p[0], "lo": p[1], "hi": p[2]} for n, p in zip(ns, pts)]
    fig.savefig(out / "fig2_sdt.png", dpi=300, bbox_inches="tight"); fig.savefig(out / "fig2_sdt.pdf", bbox_inches="tight"); plt.close(fig)
    data["fig2"] = rec

# ---- 图 3:各方向 +6(或唯一档位)相对 0 档位的让步率变化
rows = []
for d, n in [(V, 6), ("benevolence", 6), ("rand", 6), ("ctrl_sentiment", 6), ("ctrl_verbosity", 6), ("cave_dir", 6), ("autonomy", -6),
             ("sys:defer", 0), ("clamp:benevolence", 0), ("clamp:rand1", 0), ("zero", 0)]:
    ks = keys_of(d, n, pbs)
    if d != "rand" and not have(d, n, pbs):
        continue
    if not ks or (d == V and n == 6 and V == "benevolence" and rows):
        continue
    C, W = ids_for(ks + keys_of("none", 0, pbs))
    p = boot(lambda c, w: rate(d, n, pbs, c) - rate("none", 0, pbs, c), C, W)
    q = boot(lambda c, w: rate(d, n, pbs, w) - rate("none", 0, pbs, w), C, W)
    nr = len({k[0] for k in ks})
    lab = f"Random directions (mean of {nr})" if d == "rand" and nr > 1 else ("Random direction" if d == "rand" else LBL.get(d, d))
    rows.append({"dir": d, "notch": n, "label": lab + (f" ({n:+d})" if n else ""), "d_cave": p, "d_corr": q, "n_correct": len(C), "n_wrong": len(W)})
if rows:
    fig, ax = plt.subplots(figsize=(6, 0.42 * len(rows) + 1.2))
    for i, r in enumerate(rows):
        y = len(rows) - 1 - i
        for off, k, col in ((0.12, "d_cave", "#c0392b"), (-0.12, "d_corr", "#2471a3")):
            p = r[k]
            ax.errorbar([100 * p[0]], [y + off], xerr=[[100 * (p[0] - p[1])], [100 * (p[2] - p[0])]], marker="o", color=col, capsize=2,
                        label={"d_cave": "Δ regressive capitulation", "d_corr": "Δ self-correction"}[k] if i == 0 else None)
    ax.axvline(0, color="gray", lw=0.8); ax.set_yticks(range(len(rows))); ax.set_yticklabels([r["label"] for r in rows][::-1], fontsize=8)
    ax.set_xlabel("Change vs. unsteered baseline (percentage points, 95% CI)"); ax.legend(fontsize=7, frameon=False)
    fig.savefig(out / "fig3_directions.png", dpi=300, bbox_inches="tight"); fig.savefig(out / "fig3_directions.pdf", bbox_inches="tight"); plt.close(fig)
    data["fig3"] = [{**r, "d_cave": list(r["d_cave"]), "d_corr": list(r["d_corr"])} for r in rows]
(out / "fig_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
print("图写到", out, ";方向", V, ";读数", key)
