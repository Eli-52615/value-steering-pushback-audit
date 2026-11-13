"""从第一轮结果里挑试验用的题:答对、答错各 n 题,按学科轮流取,保证可复现。
入选条件:四个字母概率和 >= 0.5;回答没被截断;回答开头写的字母与读数一致。
用法:python make_trialset.py round1.jsonl out.json n_correct n_wrong [seed] [exclude.json ...]"""
import json, random, sys
from collections import defaultdict
import trial as T

r1, out, nc, nw = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 20261114
excl = set()
for p in sys.argv[6:]:
    excl |= set(json.load(open(p)))
R = T.load_jsonl(r1)
ok = [r for r in R if r["choice1"] and not r["a1_truncated"] and r["text_letter1"] == r["choice1"] and r["id"] not in excl]
print(f"第一轮 {len(R)} 题;可用 {len(ok)};答对 {sum(r['correct1'] for r in ok)},答错 {sum(not r['correct1'] for r in ok)}")
rng = random.Random(seed)


def take(pool, n):
    by = defaultdict(list)
    for r in pool:
        by[r["subject"]].append(r["id"])
    for v in by.values():
        rng.shuffle(v)
    subs, got = sorted(by), []
    while len(got) < n and any(by.values()):
        for s in subs:
            if by[s] and len(got) < n:
                got.append(by[s].pop())
    return got


ids = take([r for r in ok if r["correct1"]], nc) + take([r for r in ok if not r["correct1"]], nw)
json.dump(ids, open(out, "w"))
print("入选", len(ids))
