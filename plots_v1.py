"""论文 v1 的两张图(评审意见 4.1 第 5 条、不足 2)。在服务器上跑(需要 matplotlib);只读结果文件,不跑模型。
用法:python plots_v1.py main.jsonl 输出目录 [rand20.jsonl]
图 A:让步率–纠正率平面。每个 ±6 条件一个点,过基线画"分辨力不变"的曲线。沿曲线滑动 = 只动门槛。
图 B:20 个新随机方向的效应分布(按类型),标出仁慈。"""
import json, sys
from collections import defaultdict
from statistics import NormalDist

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze import outcome

Z, PHI = NormalDist().inv_cdf, NormalDist().cdf
EN = {"benevolence_ni": "benevolence", "benevolence": "benevolence (orig.)", "cave_dir": "capitulation dir.", "ctrl_sentiment": "sentiment",
      "ctrl_verbosity": "verbosity", "autonomy": "autonomy", "rand1": "rand 1", "rand2": "rand 2", "rand3": "rand 3",
      "orth:benevolence_ni|ctrl_sentiment": "benev. minus sentiment"}
OFF = {("cave_dir", 6): (-58, 7), ("autonomy", -6): (-12, 15), ("orth:benevolence_ni|ctrl_sentiment", 6): (6, -11), ("benevolence_ni", 6): (-52, -4), ("rand2", 6): (5, 4),
       ("ctrl_sentiment", 6): (-50, -3), ("ctrl_verbosity", -6): (5, 4), ("rand1", 6): (-38, -10), ("rand2", -6): (-40, -9),
       ("rand1", -6): (5, -10), ("ctrl_verbosity", 6): (6, -9)}     # 挤在一起的标签手动挪开
main, outd = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(main, encoding="utf-8") if l.strip()]
g = defaultdict(list)
for r in rows:
    if r["pushback"] in ("plain", "emotional"):
        g[(r["dir"], r["notch"])].append(r)


def fh(rs):
    C = [r for r in rs if r["correct1"]]; W = [r for r in rs if not r["correct1"]]
    f = sum(outcome(r, "choice2_reader") == "to_target" for r in C) / len(C)
    h = sum(outcome(r, "choice2_reader") == "to_target" for r in W) / len(W)
    return f, h, sum(r["a2_truncated"] for r in rs) / len(rs)


# ---------- 图 A ----------
fig, ax = plt.subplots(figsize=(6.2, 4.6), dpi=200)
f0, h0, _ = fh(g[("none", 0)])
d0 = Z(h0) - Z(f0)
xs = [i / 400 for i in range(4, 397)]
ax.plot([100 * x for x in xs], [100 * PHI(d0 + Z(x)) for x in xs], "-", color="0.55", lw=1, zorder=1, label=f"equal sensitivity (d′ = {d0:.2f})")
ax.scatter([100 * f0], [100 * h0], s=90, marker="*", color="k", zorder=5, label="no steering")
for (d, n), rs in sorted(g.items()):
    if abs(n) != 6 or d not in EN:
        continue
    f, h, tr = fh(rs)
    col = "#c0392b" if d == "benevolence_ni" else ("0.45" if d.startswith("rand") else "#2c6fbb")
    ax.scatter([100 * f], [100 * h], s=42, marker="o" if n > 0 else "v", facecolors="none" if tr >= 0.25 else col, edgecolors=col, linewidths=1.2, zorder=4)
    ax.annotate(f"{EN[d]} {n:+d}", (100 * f, 100 * h), xytext=OFF.get((d, n), (4, 3)), textcoords="offset points", fontsize=6.2, color=col)
ax.scatter([], [], s=42, marker="o", color="#c0392b", label="benevolence")
ax.scatter([], [], s=42, marker="o", color="0.45", label="random directions")
ax.scatter([], [], s=42, marker="o", color="#2c6fbb", label="other named directions")
ax.scatter([], [], s=42, marker="o", facecolors="none", edgecolors="k", label="≥25% of replies truncated")
ax.set_xlabel("Regressive capitulation rate (%)  — switching away from a correct answer")
ax.set_ylabel("Self-correction rate (%)")
ax.set_xlim(0, 60); ax.set_ylim(40, 100)
ax.legend(fontsize=6.5, loc="lower right", frameon=False)
ax.set_title("Each steering condition (±6) against the equal-sensitivity curve", fontsize=9)
ax.grid(alpha=0.2)
fig.tight_layout(); fig.savefig(f"{outd}/figA_roc_plane.png"); fig.savefig(f"{outd}/figA_roc_plane.pdf")
print("图 A 写出;基线 F,H,d′ =", round(f0, 4), round(h0, 4), round(d0, 3))

# ---------- 图 B ----------
if len(sys.argv) > 3:
    new = [json.loads(l) for l in open(sys.argv[3], encoding="utf-8") if l.strip()]
    t = defaultdict(dict)
    for r in new:
        if r["correct1"]:
            t[r["dir"]][(r["id"], r["pushback"])] = (int(outcome(r, "choice2_reader") == "to_target"), r["a2_truncated"])
    base = t["none"]
    eff = lambda d: 100 * sum(t[d][k][0] - base[k][0] for k in t[d]) / len(t[d])
    trn = lambda d: sum(v[1] for v in t[d].values()) / len(t[d])
    fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=200)
    names = sorted(d for d in t if d[:2] in ("rg", "rc") and len(t[d]) == len(base))
    for y, (pre, lab, col) in enumerate((("rg", "Gaussian", "0.45"), ("rc", "covariance-matched", "#2c6fbb"))):
        ds = [d for d in names if d.startswith(pre)]
        for i, d in enumerate(sorted(ds, key=eff)):
            ax.scatter([eff(d)], [y + (i - len(ds) / 2) * 0.05], s=36, facecolors="none" if trn(d) >= 0.25 else col, edgecolors=col, linewidths=1.2)
        ax.text(-0.01, y, f"{lab}\n(n = {len(ds)})", transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=7.5)
    b = eff("benevolence_ni")
    ax.axvline(b, color="#c0392b", lw=1.5); ax.text(b, 1.52, f" benevolence {b:+.1f}", color="#c0392b", fontsize=7.5, va="top")
    ax.axvline(0, color="k", lw=0.6)
    ax.set_yticks([]); ax.set_ylim(-0.5, 1.55)
    ax.set_xlabel("Change in regressive capitulation vs. no steering (percentage points)")
    ax.set_title("Twenty random directions at the same injection norm (hollow: ≥25% truncated)", fontsize=8.5)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout(); fig.savefig(f"{outd}/figB_random_directions.png"); fig.savefig(f"{outd}/figB_random_directions.pdf")
    print("图 B 写出;方向数", len(names), "仁慈", round(b, 1))
