#!/bin/bash
# 20 个新随机方向(楠 2026-11-16 改进意见 1)。判读规则见 prereg_rand20.md,在本队列启动之前提交。
# 顺序:生成方向 → 8 题试跑(不调节 + 高斯 1 个 + 协方差 1 个)→ 正式运行(同一批 150 题:不调节、新仁慈 +6、20 个方向 +6)。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code
R=../runs; D=$R/rand20_dirs.pt
[ -f $D ] || python make_rand20.py --out $D > $R/rand20_dirs.log 2>&1 || { echo "生成方向失败" >> $R/rand20_queue.log; exit 1; }
python -c "import json;ids=json.load(open('rand20_set.json'));json.dump(ids[:8],open('$R/rand20_smoke_set.json','w'))"
python run_trials.py --round1 $R/round1.jsonl --trialset $R/rand20_smoke_set.json --plan plan_r20_smoke.json --extra_dirs $D \
  --out $R/rand20_smoke.jsonl --purpose "20 个新随机方向:8 题试跑(不调节、高斯 1 个、协方差 1 个)" > $R/rand20_smoke.log 2>&1 || { echo "试跑失败" >> $R/rand20_queue.log; exit 1; }
python run_trials.py --round1 $R/round1.jsonl --trialset rand20_set.json --plan plan_r20.json --extra_dirs $D \
  --out $R/rand20.jsonl --purpose "20 个新随机方向 +6(10 高斯 + 10 协方差)× 150 道先答对的题 × 两种反驳;同批重跑不调节与新仁慈 +6" > $R/rand20.log 2>&1
echo RAND20DONE > $R/rand20.done
