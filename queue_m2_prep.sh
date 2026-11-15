#!/bin/bash
# 模型 2(Gemma-3-4b-it)准备段:等任务 1(去情绪分量)跑完后自动接续。每一步都走运行登记;输出全部写到 runs/m2_*,不碰模型 1 的文件。
# 跑到"检查 b/c"为止就停,Code 看过检查结果再开跑主体 7200 条。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code
R=../runs; C=configs_m2/gemma4b.yaml
while pgrep -f "plan_p7_orth.json" >/dev/null; do sleep 30; done
set -e
python run_round1.py --config $C --items ../data/items.jsonl --out $R/m2_round1.jsonl --purpose "模型 2:第一轮基线(不调节),2010 题,同样的提问句" > $R/m2_round1.log 2>&1
# 抽题:同样的入选条件和按学科轮流的规则;两边取相同的最大数,上限 300
python - <<PY > $R/m2_trialset.log 2>&1
import json, subprocess, trial as T
R = T.load_jsonl("$R/m2_round1.jsonl")
excl = set(json.load(open("$R/smoke_set.json")))
ok = [r for r in R if r["choice1"] and not r["a1_truncated"] and r["text_letter1"] == r["choice1"] and r["id"] not in excl]
nc, nw = sum(r["correct1"] for r in ok), sum(not r["correct1"] for r in ok)
n = min(300, nc, nw)
print(f"第一轮 {len(R)} 题;可用 {len(ok)};答对 {nc},答错 {nw};两边各取 {n}")
subprocess.run(["python", "make_trialset.py", "$R/m2_round1.jsonl", "$R/m2_main_set.json", str(n), str(n), "20261114", "$R/smoke_set.json"], check=True)
ids = json.load(open("$R/m2_main_set.json")); c = [i for i in ids[:n]]; w = [i for i in ids[n:]]
json.dump(c[:4] + w[:4], open("$R/m2_smoke_set.json", "w"))
json.dump(c[4:29] + w[4:29], open("$R/m2_check_set.json", "w"))
PY
python run_extract_m2.py --config $C --purpose "模型 2:提取仁慈(不含对话者)并按 M1 规则选层、标定 α_max(同一定义文件、同一批题目)" > $R/m2_extract.log 2>&1
S="--config $C --ref benevolence_ni --round1 $R/m2_round1.jsonl"
python run_trials.py $S --trialset $R/m2_smoke_set.json --plan plan_m2_smoke.json --out $R/m2_smoke.jsonl --purpose "模型 2 检查 a:8 题全流程试跑(不进结果)" > $R/m2_smoke.log 2>&1
python run_trials.py $S --trialset $R/m2_check_set.json --plan plan_m2_check.json --out $R/m2_check.jsonl --purpose "模型 2 检查 b/c:零向量与不调节各 100 条、新仁慈 +6 100 条(不进结果)" > $R/m2_check.log 2>&1
echo M2PREPDONE > $R/m2_prep.done
