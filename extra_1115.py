"""11-15 补报用的补充计算(全部是探索性的,确认性检验以 stats.py 为准)。只用标准库。
用法:python extra_1115.py ../结果/main/main.jsonl ../结果/main/capability.jsonl > out.json
算的东西:
  A 每个(方向, 档位)相对 0 档位的让步率/纠正率变化,两种反驳合并和分开,按题 bootstrap 区间
  B 剂量趋势:让步 ~ 档位 的逻辑回归斜率(两种反驳合并),按题 bootstrap 区间
  C C1 的敏感性:剔除被截断的试验(两边任一被截断的配对都剔)
  D 新仁慈 +6 减"情绪积极 +6"、减每个随机方向
  E 单轮正确率(调节没把模型搞坏)
读数一律用"不调节的读者"(G1-05 裁定的主分析读数)。"""
import json, math, random, sys
from collections import defaultdict
from analyze import outcome

KEY, B, SEED = "choice2_reader", 2000, 20261115
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
cell, trunc, correct = defaultdict(dict), defaultdict(dict), {}
for r in rows:
    k = (r["dir"], r["notch"], r["pushback"])
    cell[k][r["id"]] = int(outcome(r, KEY) == "to_target")
    trunc[k][r["id"]] = r["a2_truncated"]
    correct[r["id"]] = r["correct1"]
C = sorted(i for i in cell[("none", 0, "plain")] if correct[i])
W = sorted(i for i in cell[("none", 0, "plain")] if not correct[i])
PB = ("plain", "emotional")


def rate(d, n, pbs, ids):
    return sum(cell[(d, n, pb)][i] for pb in pbs for i in ids) / (len(ids) * len(pbs))


def boot(stat, ids, seed=SEED):
    rng = random.Random(seed)
    v = sorted(stat([rng.choice(ids) for _ in ids]) for _ in range(B))
    return v[int(0.025 * B)], v[int(0.975 * B) - 1]


out = {"A": [], "B": {}, "C": {}, "D": [], "E": []}
conds = sorted({(d, n) for d, n, pb in cell if pb == "plain" and (d, n) != ("none", 0) and (d, n, "emotional") in cell})
for d, n in conds:
    row = {"dir": d, "notch": n}
    for name, ids in (("cave", C), ("corr", W)):
        for lab, pbs in (("pooled", PB), ("plain", ("plain",)), ("emotional", ("emotional",))):
            f = lambda s, pbs=pbs: 100 * (rate(d, n, pbs, s) - rate("none", 0, pbs, s))
            lo, hi = boot(f, ids)
            row[f"{name}_{lab}"] = [round(f(ids), 1), round(lo, 1), round(hi, 1)]
    out["A"].append(row)


def logit_slope(xs, ys):
    """一元逻辑回归 y ~ a + b x 的牛顿法。返回 b(每升一档,让步的对数几率变多少)。"""
    a = b = 0.0
    for _ in range(25):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            p = 1 / (1 + math.exp(-(a + b * x)))
            w = p * (1 - p)
            ga += y - p; gb += (y - p) * x
            haa += w; hab += w * x; hbb += w * x * x
        det = haa * hbb - hab * hab
        a += (hbb * ga - hab * gb) / det
        b += (haa * gb - hab * ga) / det
    return b


for d in ("benevolence_ni", "benevolence"):
    notches = [-6, -3, 0, 3, 6]

    def pts(ids, d=d):
        xs, ys = [], []
        for n in notches:
            dd = "none" if n == 0 else d
            for pb in PB:
                for i in ids:
                    xs.append(n); ys.append(cell[(dd, n, pb)][i])
        return xs, ys
    f = lambda s: logit_slope(*pts(s))
    est = f(C)
    rng = random.Random(SEED); bs = sorted(f([rng.choice(C) for _ in C]) for _ in range(500))
    out["B"][d] = {"slope_per_notch": round(est, 4), "ci95": [round(bs[12], 4), round(bs[487], 4)], "boot": 500,
                   "odds_ratio_0_to_6": round(math.exp(6 * est), 2)}

# C:剔除截断
pairs = [(i, pb) for pb in PB for i in C if not trunc[("none", 0, pb)][i] and not trunc[("benevolence_ni", 6, pb)][i]]
r0 = sum(cell[("none", 0, pb)][i] for i, pb in pairs) / len(pairs)
r1 = sum(cell[("benevolence_ni", 6, pb)][i] for i, pb in pairs) / len(pairs)
out["C"] = {"n_trials_kept": len(pairs), "n_trials_total": 2 * len(C), "base": round(100 * r0, 1), "bni6": round(100 * r1, 1),
            "diff": round(100 * (r1 - r0), 1)}
for pb in PB:
    t = [i for i in C if trunc[("benevolence_ni", 6, pb)][i]]
    nt = [i for i in C if not trunc[("benevolence_ni", 6, pb)][i]]
    out["C"][f"bni6_{pb}_cave_if_truncated"] = [sum(cell[("benevolence_ni", 6, pb)][i] for i in t), len(t)]
    out["C"][f"bni6_{pb}_cave_if_not_truncated"] = [sum(cell[("benevolence_ni", 6, pb)][i] for i in nt), len(nt)]

# D:新仁慈 +6 减其他方向 +6(两种反驳合并 + 分开)
for o in ("ctrl_sentiment", "rand1", "rand2", "rand3", "cave_dir", "benevolence"):
    rr = {"vs": o}
    for lab, pbs in (("pooled", PB), ("plain", ("plain",)), ("emotional", ("emotional",))):
        f = lambda s, pbs=pbs: 100 * (rate("benevolence_ni", 6, pbs, s) - rate(o, 6, pbs, s))
        lo, hi = boot(f, C)
        rr[lab] = [round(f(C), 1), round(lo, 1), round(hi, 1)]
    out["D"].append(rr)

# E:单轮正确率
cap = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
g = defaultdict(list)
for r in cap:
    g[(r["dir"], r["notch"])].append(r["correct"])
base = g[("none", 0)]
for k in sorted(g, key=lambda k: (k[0] != "none", k)):
    v = g[k]
    out["E"].append({"dir": k[0], "notch": k[1], "n": len(v), "acc": round(100 * sum(v) / len(v), 1),
                     "diff_vs_none": round(100 * (sum(v) / len(v) - sum(base) / len(base)), 1)})
print(json.dumps(out, ensure_ascii=False, indent=1))
