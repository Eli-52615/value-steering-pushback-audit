#!/bin/bash
# 只用打分接口,不占 GPU。等新仁慈的 ±6、±3 跑完后,在本实验回复上打价值得分(G1-04)。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code3; R=../runs
until grep -q "^DONE" $R/p1.log 2>/dev/null; do sleep 120; done
python score_trait.py --trials $R/main.jsonl --value benevolence_ni --n 100 --out $R/trait_scores.jsonl --purpose "G1-04:在本实验第二轮回复上打仁慈(不含对话者)得分,每档 100 条" > $R/score_ni.log 2>&1
python score_trait.py --trials $R/main.jsonl --value benevolence --n 100 --out $R/trait_scores.jsonl --purpose "G1-04:同上,原定义仁慈(探索性)" > $R/score_orig.log 2>&1
