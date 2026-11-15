"""任务 1(去情绪分量)的分析,探索性。读数:不调节的读者。只用标准库。
新仁慈去掉"情绪积极"分量(余弦 0.553)后,按变短后的长度(原注入范数的 83.3%)注入,+3、+6。
报告:相对 0 档位的让步率/纠正率变化(合并、平淡、情感),和新仁慈同档位、情绪积极 +6 的配对差,Δc/Δd′,截断和读数不一致。
用法:python orth_1116.py ../结果/main/main.jsonl"""
import json, random, sys
from collections import defaultdict
from statistics import median
from analyze import outcome, sdt

KEY, B = "choice2_reader", 4000
O = "orth:benevolence_ni|ctrl_sentiment"
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
cell, meta, correct = defaultdict(dict), defaultdict(list), {}
for r in rows:
    if r["pushback"] in ("plain", "emotional"):
        k = (r["dir"], r["notch"], r["pushback"])
        cell[k][r["id"]] = int(outcome(r, KEY) == "to_target")
        meta[k].append(r)
        correct[r["id"]] = r["correct1"]
C = sorted(i for i in cell[("none", 0, "plain")] if correct[i])
W = sorted(i for i in cell[("none", 0, "plain")] if not correct[i])
rate = lambda d, n, pbs, s: sum(cell[(d, n, pb)][i] for pb in pbs for i in s) / (len(s) * len(pbs))
rng = random.Random(20261116)
SC, SW = [[rng.choice(C) for _ in C] for _ in range(B)], [[rng.choice(W) for _ in W] for _ in range(B)]


def ci(f, side):
    S = SC if side == "c" else SW
    v = sorted(f(s) for s in S)
    return v[int(0.025 * B)], v[int(0.975 * B) - 1]


fmt = lambda f, side, ids: f"{100 * f(ids):+.1f} [{100 * ci(f, side)[0]:+.1f}, {100 * ci(f, side)[1]:+.1f}]"
PBS = {"合并": ("plain", "emotional"), "平淡": ("plain",), "情感": ("emotional",)}
print("## 去情绪分量:相对 0 档位\n")
print("| 条件 | 注入范数 | 让步 合并 | 让步 平淡 | 让步 情感 | 纠正 合并 | 回复中位数 平淡/情感 | 截断% | 两种读数不一致% |\n|---|---|---|---|---|---|---|---|---|")
for d, n in ((O, 3), (O, 6), ("benevolence_ni", 3), ("benevolence_ni", 6), ("ctrl_sentiment", 6)):
    if (d, n, "plain") not in cell:
        continue
    cols = [fmt(lambda s, p=p: rate(d, n, p, s) - rate("none", 0, p, s), "c", C) for p in PBS.values()]
    corr = fmt(lambda s: rate(d, n, PBS["合并"], s) - rate("none", 0, PBS["合并"], s), "w", W)
    ms = meta[(d, n, "plain")] + meta[(d, n, "emotional")]
    print(f"| {'去情绪新仁慈' if d == O else d} {n:+d} | {ms[0]['inject_norm']} | {' | '.join(cols)} | {corr} "
          f"| {median(r['a2_tokens'] for r in meta[(d, n, 'plain')]):.0f}/{median(r['a2_tokens'] for r in meta[(d, n, 'emotional')]):.0f} "
          f"| {100 * sum(r['a2_truncated'] for r in ms) / len(ms):.1f} | {100 * sum(r['choice2'] != r['choice2_reader'] for r in ms) / len(ms):.1f} |")
print("\n## 配对差(让步率,同题)\n")
for a, na, b, nb in ((O, 6, "benevolence_ni", 6), (O, 3, "benevolence_ni", 3), (O, 6, "ctrl_sentiment", 6)):
    if (a, na, "plain") not in cell or (b, nb, "plain") not in cell:
        continue
    print(f"- 去情绪 {na:+d} − {b} {nb:+d}:" + ";".join(f"{k} " + fmt(lambda s, p=p: rate(a, na, p, s) - rate(b, nb, p, s), "c", C) for k, p in PBS.items()))


def sd(d, n, c, w):
    P2 = ("plain", "emotional")
    return sdt(sum(cell[(d, n, pb)][i] for pb in P2 for i in w), 2 * len(w), sum(cell[(d, n, pb)][i] for pb in P2 for i in c), 2 * len(c))


print("\n## 信号检测(合并)\n")
for d, n in ((O, 3), (O, 6), ("benevolence_ni", 6)):
    if (d, n, "plain") in cell:
        dd = lambda c, w: sd(d, n, c, w)[0] - sd("none", 0, c, w)[0]
        dc = lambda c, w: sd(d, n, c, w)[1] - sd("none", 0, c, w)[1]
        bs = [(SC[k], SW[k]) for k in range(1000)]
        vc = sorted(dc(c, w) for c, w in bs); vd = sorted(dd(c, w) for c, w in bs)
        print(f"- {'去情绪新仁慈' if d == O else d} {n:+d}:Δc {dc(C, W):+.2f} [{vc[25]:+.2f}, {vc[974]:+.2f}];Δd′ {dd(C, W):+.2f} [{vd[25]:+.2f}, {vd[974]:+.2f}]")
