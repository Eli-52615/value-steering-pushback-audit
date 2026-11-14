#!/bin/bash
# 主实验第一段。每一步都是一次独立的登记运行;任何一步出错,后面的照常继续(各步互不依赖)。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code
R=../runs; S="--round1 $R/round1.jsonl --trialset $R/main_set.json"
python make_trialset.py $R/round1.jsonl $R/main_set.json 300 300 20261114 $R/smoke_set.json > $R/main_set.log 2>&1
python run_trials.py $S --plan plan_m1_none.json     --out $R/main.jsonl --purpose "主实验:0 档位基线,三种反驳(措辞 v1)" > $R/m1.log 2>&1
python run_trials.py $S --plan plan_m2_benev.json    --out $R/main.jsonl --purpose "主实验:仁慈 ±6、±3,三种反驳(C1/C3/C4 用)" > $R/m2.log 2>&1
python run_trials.py $S --plan plan_m3_sysdefer.json --out $R/main.jsonl --purpose "阳性对照①:系统提示'以用户的意见为准',不调节(楠的预期已写)" > $R/m3.log 2>&1
python run_trials.py $S --plan plan_m4_rand.json     --out $R/main.jsonl --purpose "主实验:三个随机方向 ±6(C2 用)" > $R/m4.log 2>&1
python run_trials.py $S --plan plan_m5_zero.json     --out $R/main.jsonl --purpose "阴性检验(主实验题):调节通路开着加零向量" > $R/m5.log 2>&1
python run_trials.py $S --plan plan_m6_noise.json --bs 24 --out $R/main_noise_bs24.jsonl --purpose "批次噪声底(主实验题):0 档位换批量 24 重跑" > $R/m6.log 2>&1
echo PHASE1DONE > $R/phase1.done
