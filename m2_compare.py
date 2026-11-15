"""两个模型并排:C1–C4 用到的格子 + 系统提示阳性对照。读数:不调节的读者(主分析)。只用标准库。
C1–C4 本身用 stats.py 原样算(只换数据文件);这里补:各条件逐个相对 0 档位的变化(合并/平淡/情感)、基线、
新仁慈减每个随机方向、回复长度、截断、无法判定、两种读数不一致。
用法:python m2_compare.py ../结果/main/main.jsonl ../结果/main_m2/m2_main.jsonl > 输出.md"""
import json, random, sys
from collections import defaultdict
from statistics import median
from analyze import outcome, sdt

B = 4000
CONDS = [("benevolence_ni", 6), ("rand1", 6), ("rand2", 6), ("rand3", 6), ("sys:defer", 0)]
NAME = {"benevolence_ni": "新仁慈 +6", "rand1": "随机 1 +6", "rand2": "随机 2 +6", "rand3": "随机 3 +6", "sys:defer": "系统提示①"}


def load(p):
    cell, meta, correct = defaultdict(dict), defaultdict(list), {}
    for l in open(p, encoding="utf-8"):
        r = json.loads(l)
        if r["pushback"] in ("plain", "emotional") and ((r["dir"], r["notch"]) in CONDS or r["dir"] == "none"):
            k = (r["dir"], r["notch"], r["pushback"])
            cell[k][r["id"]] = int(outcome(r, "choice2_reader") == "to_target")
            meta[k].append(r)
            correct[r["id"]] = r["correct1"]
    return cell, meta, correct


PBS = {"合并": ("plain", "emotional"), "平淡": ("plain",), "情感": ("emotional",)}
for label, path in (("模型 1:Qwen3.5-9B", sys.argv[1]), ("模型 2:Gemma-3-4b-it", sys.argv[2])):
    cell, meta, correct = load(path)
    C = sorted(i for i in cell[("none", 0, "plain")] if correct[i])
    W = sorted(i for i in cell[("none", 0, "plain")] if not correct[i])
    rate = lambda d, n, pbs, s: sum(cell[(d, n, pb)][i] for pb in pbs for i in s) / (len(s) * len(pbs))
    rng = random.Random(20261116)
    SC = [[rng.choice(C) for _ in C] for _ in range(B)]
    SW = [[rng.choice(W) for _ in W] for _ in range(B)]

    def fmt(f, S, ids):
        v = sorted(f(s) for s in S)
        return f"{100 * f(ids):+.1f} [{100 * v[int(.025 * B)]:+.1f}, {100 * v[int(.975 * B) - 1]:+.1f}]"
    print(f"\n## {label}\n")
    print(f"答对 {len(C)} 题、答错 {len(W)} 题。")
    for pb in ("plain", "emotional"):
        ms = meta[("none", 0, pb)]
        print(f"- 0 档位 {('平淡' if pb == 'plain' else '情感')}:让步率 {100 * rate('none', 0, (pb,), C):.1f}%,纠正率 {100 * rate('none', 0, (pb,), W):.1f}%,"
              f"回复中位数 {median(r['a2_tokens'] for r in ms):.0f} token,截断 {100 * sum(r['a2_truncated'] for r in ms) / len(ms):.1f}%")
    print("\n| 条件 | 让步 合并 | 让步 平淡 | 让步 情感 | 纠正 合并 | Δc / Δd′(合并) | 回复中位数 平淡/情感 | 截断 | 无法判定(读者) | 两种读数不一致 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for d, n in CONDS:
        if (d, n, "plain") not in cell:
            continue
        cols = [fmt(lambda s, p=p: rate(d, n, p, s) - rate("none", 0, p, s), SC, C) for p in PBS.values()]
        corr = fmt(lambda s: rate(d, n, PBS["合并"], s) - rate("none", 0, PBS["合并"], s), SW, W)
        P2 = ("plain", "emotional")
        sd = lambda dd, nn: sdt(sum(cell[(dd, nn, pb)][i] for pb in P2 for i in W), 2 * len(W), sum(cell[(dd, nn, pb)][i] for pb in P2 for i in C), 2 * len(C))
        (d1, c1), (d0, c0) = sd(d, n), sd("none", 0)
        ms = meta[(d, n, "plain")] + meta[(d, n, "emotional")]
        print(f"| {NAME[d]} | {' | '.join(cols)} | {corr} | {c1 - c0:+.2f} / {d1 - d0:+.2f} "
              f"| {median(r['a2_tokens'] for r in meta[(d, n, 'plain')]):.0f}/{median(r['a2_tokens'] for r in meta[(d, n, 'emotional')]):.0f} "
              f"| {100 * sum(r['a2_truncated'] for r in ms) / len(ms):.1f}% | {100 * sum(r['choice2_reader'] is None for r in ms) / len(ms):.1f}% "
              f"| {100 * sum(r['choice2'] != r['choice2_reader'] for r in ms) / len(ms):.1f}% |")
    print("\n新仁慈 +6 减每个随机方向 +6(让步率,同题):")
    for r in ("rand1", "rand2", "rand3"):
        print(f"- 减{NAME[r]}:" + ";".join(f"{k} " + fmt(lambda s, p=p: rate("benevolence_ni", 6, p, s) - rate(r, 6, p, s), SC, C) for k, p in PBS.items()))
