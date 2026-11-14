"""确认性分析 C1–C4(见《研究设计与统计分析计划》第 6 节)。只用标准库,本机可跑。
用法:python stats.py trials.jsonl [--reader] [--notch 6] [--boot 10000] [--rand rand1,rand2,rand3]
统计单位是题:bootstrap 按题重抽样(答对的题和答错的题分别重抽),同一题在各条件下的结果一起被抽到。"""
import json, random, sys
from collections import defaultdict
from math import comb
from analyze import outcome, sdt


def load(path, key):
    """-> cell[(dir, notch, pushback)][题号] = 1/0(是否改到用户说的选项);correct[题号] = 第一轮对错"""
    cell, correct = defaultdict(dict), {}
    for l in open(path, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            cell[(r["dir"], r["notch"], r["pushback"])][r["id"]] = int(outcome(r, key) == "to_target")
            correct[r["id"]] = r["correct1"]
    return cell, correct


def mcnemar_exact(a, b):
    """配对二分类的精确 McNemar(双侧)。a、b 是同一批题在两个条件下的 0/1。返回 (只在 b 为 1 的题数, 只在 a 为 1 的题数, p)。"""
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n, k = n10 + n01, min(n10, n01)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return n01, n10, p


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def boot_ci(stat, ids_c, ids_w, B, seed=20261114):
    rng = random.Random(seed)
    vals = sorted(stat([rng.choice(ids_c) for _ in ids_c], [rng.choice(ids_w) for _ in ids_w]) for _ in range(B))
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def boot_p(stat, ids_c, ids_w, B, seed=20261114):
    """bootstrap 双侧 p:重抽样分布里落在 0 另一侧的比例 × 2(用于没有现成精确检验的量)。"""
    rng = random.Random(seed)
    vals = [stat([rng.choice(ids_c) for _ in ids_c], [rng.choice(ids_w) for _ in ids_w]) for _ in range(B)]
    lo = sum(v <= 0 for v in vals) / B
    return min(1.0, 2 * min(lo, 1 - lo) + 1 / B)


if __name__ == "__main__":
    a = sys.argv
    key = "choice2_reader" if "--reader" in a else "choice2"
    N = int(a[a.index("--notch") + 1]) if "--notch" in a else 6
    B = int(a[a.index("--boot") + 1]) if "--boot" in a else 10000
    rands = a[a.index("--rand") + 1].split(",") if "--rand" in a else ["rand1", "rand2", "rand3"]
    V = a[a.index("--dir") + 1] if "--dir" in a else "benevolence_ni"   # 偏离 1:确认性检验用"仁慈(不含对话者)"
    cell, correct = load(a[1], key)
    rands = [d for d in rands if (d, N, "plain") in cell]
    need = [(d, n, pb) for pb in ("plain", "emotional") for d, n in [("none", 0), (V, N)] + [(r, N) for r in rands]]
    ids = sorted(set.intersection(*[set(cell[k]) for k in need]))
    C, W = [i for i in ids if correct[i]], [i for i in ids if not correct[i]]
    PB = ["plain", "emotional"]
    rate = lambda d, n, pbs, s: sum(cell[(d, n, pb)][i] for pb in pbs for i in s) / (len(s) * len(pbs))
    base = lambda pbs, s: rate("none", 0, pbs, s)
    print(f"方向:{V}")
    print(f"读数:{'不调节的读者' if key != 'choice2' else '被调节的模型自己确认'};对比档位 {N:+d} vs 0;答对 {len(C)} 题,答错 {len(W)} 题;bootstrap {B} 次\n")

    # C1:仁慈 +N vs 0,错误让步率,两种反驳合并(每题两条试验,按试验配对)
    x0 = [cell[("none", 0, pb)][i] for pb in PB for i in C]
    x1 = [cell[(V, N, pb)][i] for pb in PB for i in C]
    up, down, p1 = mcnemar_exact(x0, x1)
    d1 = lambda c, w: rate(V, N, PB, c) - base(PB, c)
    print(f"C1 错误让步率:0 档位 {100 * base(PB, C):.1f}% → {V}{N:+d} {100 * rate(V, N, PB, C):.1f}%;"
          f"差 {100 * d1(C, W):+.1f} 个百分点,95% 区间 [{100 * boot_ci(d1, C, W, B)[0]:+.1f}, {100 * boot_ci(d1, C, W, B)[1]:+.1f}];"
          f"只在{N:+d}让步 {up} 条,只在 0 让步 {down} 条,McNemar p = {p1:.4f}")
    dh = lambda c, w: rate(V, N, PB, w) - base(PB, w)
    print(f"   (自我纠正率:{100 * base(PB, W):.1f}% → {100 * rate(V, N, PB, W):.1f}%;差 {100 * dh(C, W):+.1f},"
          f"95% 区间 [{100 * boot_ci(dh, C, W, B)[0]:+.1f}, {100 * boot_ci(dh, C, W, B)[1]:+.1f}])")
    ps = [p1]

    # C2:仁慈的效应减去随机方向的平均效应
    if rands:
        d2 = lambda c, w: d1(c, w) - sum(rate(r, N, PB, c) - base(PB, c) for r in rands) / len(rands)
        lo, hi = boot_ci(d2, C, W, B)
        ps.append(boot_p(d2, C, W, B))
        print(f"C2 仁慈减随机方向({','.join(rands)}):{100 * d2(C, W):+.1f} 个百分点,95% 区间 [{100 * lo:+.1f}, {100 * hi:+.1f}],bootstrap p = {ps[-1]:.4f}")
    else:
        print("C2 没有随机方向的数据")

    # C3:Δc 和 Δd′
    def sd(d, n, c, w):
        return sdt(sum(cell[(d, n, pb)][i] for pb in PB for i in w), 2 * len(w), sum(cell[(d, n, pb)][i] for pb in PB for i in c), 2 * len(c))
    dc = lambda c, w: sd(V, N, c, w)[1] - sd("none", 0, c, w)[1]
    dd = lambda c, w: sd(V, N, c, w)[0] - sd("none", 0, c, w)[0]
    ps.append(boot_p(dc, C, W, B))
    print(f"C3 Δc = {dc(C, W):+.2f},95% 区间 [{boot_ci(dc, C, W, B)[0]:+.2f}, {boot_ci(dc, C, W, B)[1]:+.2f}],bootstrap p = {ps[-1]:.4f};"
          f"Δd′ = {dd(C, W):+.2f},95% 区间 [{boot_ci(dd, C, W, B)[0]:+.2f}, {boot_ci(dd, C, W, B)[1]:+.2f}]")

    # C4:反驳方式 × 档位 的交互
    d4 = lambda c, w: (rate(V, N, ["emotional"], c) - base(["emotional"], c)) - (rate(V, N, ["plain"], c) - base(["plain"], c))
    ps.append(boot_p(d4, C, W, B))
    print(f"C4 交互(情感施压下的效应 减 平淡否定下的效应):{100 * d4(C, W):+.1f} 个百分点,95% 区间 [{100 * boot_ci(d4, C, W, B)[0]:+.1f}, {100 * boot_ci(d4, C, W, B)[1]:+.1f}],bootstrap p = {ps[-1]:.4f}")
    print("\nHolm 校正后的 p:", [round(p, 4) for p in holm(ps)])
