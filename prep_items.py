"""从 CMMLU 测试集按学科分层抽题,生成 items.jsonl。新工作(赛期内)。
用法:python prep_items.py <cmmlu/test 目录> <输出 jsonl> [每学科题数=30] [seed=20261114]"""
import csv, json, random, sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
per = int(sys.argv[3]) if len(sys.argv) > 3 else 30
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 20261114
rng = random.Random(seed)
n = 0
with out.open("w", encoding="utf-8") as f:
    for p in sorted(src.glob("*.csv")):
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        rows = [r for r in rows if r["Answer"] in "ABCD" and all(r[k].strip() for k in "ABCD")]
        idx = sorted(rng.sample(range(len(rows)), min(per, len(rows))))
        for i in idx:
            r = rows[i]
            f.write(json.dumps({"id": f"{p.stem}:{i}", "subject": p.stem, "q": r["Question"].strip(),
                                "opts": {k: r[k].strip() for k in "ABCD"}, "answer": r["Answer"]}, ensure_ascii=False) + "\n")
            n += 1
print("items", n)
