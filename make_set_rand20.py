"""从主实验的 300 道"先答对"的题里按学科分层抽 150 道,给 20 个新随机方向用(楠 2026-11-16 改进意见 1)。
用法:python make_set_rand20.py round1.jsonl main_set.json rand20_set.json [150] [种子]
抽法:每个学科内按种子打乱,然后各学科轮流出一题,直到抽满。只看第一轮对错和学科,不看任何第二轮结局。"""
import json, random, sys
from collections import defaultdict

r1p, setp, outp = sys.argv[1:4]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 150
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 20261116
r1 = {}
for l in open(r1p, encoding="utf-8"):
    if l.strip():
        r = json.loads(l); r1[r["id"]] = r
ids = [i for i in json.load(open(setp)) if r1[i]["correct1"]]
by = defaultdict(list)
for i in sorted(ids):
    by[r1[i]["subject"]].append(i)
rng = random.Random(seed)
for s in by:
    rng.shuffle(by[s])
out, k = [], 0
subs = sorted(by)
while len(out) < n:
    for s in subs:
        if k < len(by[s]) and len(out) < n:
            out.append(by[s][k])
    k += 1
json.dump(sorted(out), open(outp, "w"), ensure_ascii=False)
print(f"先答对 {len(ids)} 题,{len(subs)} 个学科;抽 {len(out)} 题,覆盖 {len({r1[i]['subject'] for i in out})} 个学科")
