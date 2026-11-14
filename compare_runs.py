"""比较两次运行在相同(题号, 反驳方式)上的逐条差别。用于阴性检验和批次噪声底。只用标准库。
用法:python compare_runs.py 基准.jsonl 基准方向 待比.jsonl 待比方向"""
import json, sys
from analyze import outcome


def load(p, d):
    return {(r["id"], r["pushback"]): r for r in map(json.loads, open(p, encoding="utf-8")) if r["dir"] == d and r["notch"] == 0}


A, B = load(sys.argv[1], sys.argv[2]), load(sys.argv[3], sys.argv[4])
ks = sorted(set(A) & set(B))
txt = sum(A[k]["a2"] != B[k]["a2"] for k in ks)
l1 = sum(outcome(A[k]) != outcome(B[k]) for k in ks)
l2 = sum(outcome(A[k], "choice2_reader") != outcome(B[k], "choice2_reader") for k in ks)
dp = max(max(abs(x - y) for x, y in zip(A[k]["final_unsteered"]["p"], B[k]["final_unsteered"]["p"])) for k in ks)
print(f"可比 {len(ks)} 条;第二轮回复文字不同 {txt} 条({100 * txt / len(ks):.1f}%);"
      f"结局标签不同:模型自己确认 {l1} 条({100 * l1 / len(ks):.1f}%),不调节的读者 {l2} 条({100 * l2 / len(ks):.1f}%);"
      f"读者概率的最大差 {dp:.4f}")
for pb in ("plain", "emotional", "neutral"):
    s = [k for k in ks if k[1] == pb]
    print(f"  {pb}: 文字不同 {sum(A[k]['a2'] != B[k]['a2'] for k in s)}/{len(s)},读者标签不同 {sum(outcome(A[k], 'choice2_reader') != outcome(B[k], 'choice2_reader') for k in s)}/{len(s)}")
