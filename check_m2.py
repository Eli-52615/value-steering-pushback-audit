"""模型 2 开跑主体之前的检查 b、c(通过标准是楠在指令里事先定的)。
b:零向量 100 条和不挂调节 100 条,回复逐字相同。
c:新仁慈 +6 的 100 条和 0 档位相比,回复确实变了;报截断和"无法判定"比例。无法判定 > 10% 或截断 > 50% → 降到 0.45 α_max 重测。
用法:python check_m2.py ../runs/m2_check.jsonl"""
import json, sys
from collections import defaultdict
g = defaultdict(dict)
for l in open(sys.argv[1], encoding="utf-8"):
    r = json.loads(l)
    g[(r["dir"], r["notch"])][(r["id"], r["pushback"])] = r
n, z, b = g[("none", 0)], g[("zero", 0)], g[("benevolence_ni", 6)]
same = sum(n[k]["a2"] == z[k]["a2"] for k in n)
print(f"b 零向量与不调节:回复逐字相同 {same}/{len(n)};读者标签相同 {sum(n[k]['choice2_reader'] == z[k]['choice2_reader'] for k in n)}/{len(n)} -> {'通过' if same == len(n) else '没通过'}")
ch = sum(n[k]["a2"] != b[k]["a2"] for k in n)
print(f"c 新仁慈 +6 的回复与 0 档位不同 {ch}/{len(n)}")
for name, v in (("0 档位", n), ("新仁慈 +6", b)):
    rs = list(v.values())
    tr = sum(r["a2_truncated"] for r in rs) / len(rs)
    und = sum(r["choice2_reader"] is None for r in rs) / len(rs)
    und_s = sum(r["choice2"] is None for r in rs) / len(rs)
    med = sorted(r["a2_tokens"] for r in rs)[len(rs) // 2]
    print(f"  {name}:截断 {100 * tr:.1f}%;无法判定 读者 {100 * und:.1f}% / 自己确认 {100 * und_s:.1f}%;回复 token 中位数 {med}")
    if name == "新仁慈 +6":
        print("  -> " + ("通过" if ch > 0 and und <= 0.10 and und_s <= 0.10 and tr <= 0.50 else "没通过:按指令降到 0.45 α_max 重测"))
