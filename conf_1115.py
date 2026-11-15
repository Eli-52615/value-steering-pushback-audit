"""C1 的置信度分层敏感性分析(计划第 7 节,探索性)。第一轮对所选字母的概率按中位数分成高/低两层,各算一次 C1。读数:不调节的读者。"""
import json, sys
from statistics import median
from analyze import outcome
r1 = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()}
conf = {i: r["r1"]["p"]["ABCD".index(r["choice1"])] for i, r in r1.items() if r["choice1"]}
cell = {}
for l in open(sys.argv[1], encoding="utf-8"):
    r = json.loads(l)
    if r["correct1"] and r["pushback"] in ("plain", "emotional"):
        cell[(r["dir"], r["notch"], r["pushback"], r["id"])] = outcome(r, "choice2_reader") == "to_target"
C = sorted({k[3] for k in cell if k[0] == "none"})
m = median(conf[i] for i in C)
print(f"答对题第一轮把握的中位数 {m:.4f}")
for lab, ids in (("高把握", [i for i in C if conf[i] >= m]), ("低把握", [i for i in C if conf[i] < m])):
    f = lambda d, n: sum(cell[(d, n, pb, i)] for pb in ("plain", "emotional") for i in ids) / (2 * len(ids))
    print(f"{lab} {len(ids)} 题:0 档位 {100*f('none',0):.1f}% → 新仁慈+6 {100*f('benevolence_ni',6):.1f}%,差 {100*(f('benevolence_ni',6)-f('none',0)):+.1f};"
          f"随机均值+6 差 {100*(sum(f(r,6) for r in ('rand1','rand2','rand3'))/3-f('none',0)):+.1f}")
