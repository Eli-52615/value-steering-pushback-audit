"""11-15 补报的主图(读数:不调节的读者)。输入 extra_1115.py 的输出。
图 A:剂量—效应,2×2(让步/纠正 × 平淡/情感),新仁慈与原定义仁慈的档位曲线,±6 处逐个画出随机方向、情绪积极、让步方向。
图 B:所有方向在 ±6 的效应(两种反驳合并),随机方向单独标灰。
用法:python plots_1115.py 补充计算-1115.json outdir"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open(sys.argv[1], encoding="utf-8"))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
A = {(r["dir"], r["notch"]): r for r in d["A"]}
NAME = {"benevolence_ni": "Benevolence (excl. interlocutor)", "benevolence": "Benevolence (original def.)",
        "rand1": "Random 1", "rand2": "Random 2", "rand3": "Random 3", "ctrl_sentiment": "Positive sentiment",
        "ctrl_verbosity": "Verbosity", "cave_dir": "Capitulation direction", "autonomy": "Autonomy",
        "sys:defer": "System prompt: defer to user", "clamp:benevolence": "Mean-ablate benevolence (orig.)",
        "clamp:rand1": "Mean-ablate random 1"}
RED, BLUE, GREY = "#c0392b", "#2471a3", "#7f7f7f"

# ---------- 图 A ----------
fig, axes = plt.subplots(2, 2, figsize=(9, 7), sharex=True)
for i, (m, lab) in enumerate((("cave", "Δ regressive capitulation (pp)"), ("corr", "Δ self-correction (pp)"))):
    for j, pb in enumerate(("plain", "emotional")):
        ax = axes[i, j]
        ax.axhline(0, color="black", lw=0.8)
        for v, ls, col in (("benevolence_ni", "-", RED if m == "cave" else BLUE), ("benevolence", "--", "#555555")):
            xs = [-6, -3, 0, 3, 6]
            ys = [0 if n == 0 else A[(v, n)][f"{m}_{pb}"][0] for n in xs]
            lo = [0 if n == 0 else A[(v, n)][f"{m}_{pb}"][1] for n in xs]
            hi = [0 if n == 0 else A[(v, n)][f"{m}_{pb}"][2] for n in xs]
            ax.errorbar(xs, ys, yerr=[[y - l for y, l in zip(ys, lo)], [h - y for y, h in zip(ys, hi)]], fmt="o" + ls, color=col,
                        capsize=3, label=NAME[v], lw=1.8 if v == "benevolence_ni" else 1.2)
        for k, (o, mk) in enumerate((("rand1", "s"), ("rand2", "s"), ("rand3", "s"), ("ctrl_sentiment", "D"), ("cave_dir", "*"))):
            for n in (-6, 6):
                if (o, n) in A:
                    y, l, h = A[(o, n)][f"{m}_{pb}"]
                    x = n + (0.25 + 0.17 * k) * (1 if n > 0 else -1)
                    ax.errorbar([x], [y], yerr=[[y - l], [h - y]], fmt=mk, color=GREY if o.startswith("rand") else ("#8e44ad" if o == "ctrl_sentiment" else "#d35400"),
                                ms=7 if mk == "*" else 5, capsize=2,
                                label=NAME[o] if (i, j, n) == (0, 0, 6) and o not in ("rand2", "rand3") else None)
        ax.set_title(f"{'Plain' if pb == 'plain' else 'Emotional'} pushback", fontsize=10)
        if j == 0:
            ax.set_ylabel(lab)
        if i == 1:
            ax.set_xlabel("Steering notch")
        ax.set_xticks([-6, -3, 0, 3, 6])
h, l = axes[0, 0].get_legend_handles_labels()
l = ["Random directions (each)" if x == "Random 1" else x for x in l]
fig.legend(h, l, loc="lower center", ncol=3, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, 0.07, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(out / f"figA_dose_by_pushback.{ext}", dpi=200)

# ---------- 图 B ----------
rows = [(k, A[k]) for k in A if k[1] in (6, -6) or k[0].startswith(("sys", "clamp"))]
rows.sort(key=lambda kr: kr[1]["cave_pooled"][0])
fig, ax = plt.subplots(figsize=(7.5, 0.33 * len(rows) + 1.2))
for y, ((dd, n), r) in enumerate(rows):
    lab = NAME.get(dd, dd) + (f" ({n:+d})" if n else "")
    col = GREY if dd.startswith("rand") else (RED if dd == "benevolence_ni" else "black")
    for m, off, c in (("cave", 0.12, RED), ("corr", -0.12, BLUE)):
        v, lo, hi = r[f"{m}_pooled"]
        ax.errorbar([v], [y + off], xerr=[[v - lo], [hi - v]], fmt="o", color=c, ms=4, capsize=2, alpha=0.45 if dd.startswith("rand") else 1)
    ax.text(-0.01, y, lab, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8, color=col,
            fontweight="bold" if dd == "benevolence_ni" else "normal")
ax.axvline(0, color="black", lw=0.8)
ax.set_yticks([])
ax.set_xlabel("Change vs. unsteered baseline, plain + emotional (pp, 95% CI by item)")
ax.plot([], [], "o", color=RED, label="Δ regressive capitulation"); ax.plot([], [], "o", color=BLUE, label="Δ self-correction")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.subplots_adjust(left=0.36)
for ext in ("png", "pdf"):
    fig.savefig(out / f"figB_all_directions.{ext}", dpi=200)
print("ok")
