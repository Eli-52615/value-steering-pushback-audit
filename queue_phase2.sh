#!/bin/bash
# 主实验第二段:等第一段跑完后自动接续。各步互不依赖,一步出错不影响后面。
# 两个阳性对照的调节条件有闸:楠写下预期后,Code 才放 ok_*.flag,否则跳过(规划方案 4.8 第 3 条)。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code2
R=../runs; S="--round1 $R/round1.jsonl --trialset $R/main_set.json"
until [ -f $R/phase1.done ]; do sleep 30; done
python run_extract.py --value values/benevolence_ni.yaml --purpose "提取新价值:仁慈(不含对话者),楠 G1 签字时提出" > $R/p1x.log 2>&1
python run_trials.py $S --plan plan_p1_bni.json --out $R/main.jsonl --purpose "主实验:仁慈(不含对话者) ±6、±3" > $R/p1.log 2>&1
python run_trials.py $S --plan plan_p3_clamp.json --out $R/main.jsonl --purpose "方向消融(G1-07):仁慈与随机方向的分量固定在平时均值,第 12 层" > $R/p3.log 2>&1
python run_trials.py $S --plan plan_p2_style.json --out $R/main.jsonl --purpose "主实验:话多、情绪积极 ±6(风格对照)" > $R/p2.log 2>&1
python run_capability.py --items ../data/items.jsonl --exclude $R/main_set.json $R/smoke_set.json --n 200 --plan plan_p4_cap.json --out $R/capability.jsonl --purpose "单轮正确率检查:各方向各档位下 200 道未用过的题" > $R/p4.log 2>&1
python extract_cave_dir.py --round1 $R/round1.jsonl --exclude $R/main_set.json $R/smoke_set.json --n 500 --out $R/cave_extract.jsonl --purpose "阳性对照②:提取让步方向(只提取,不调节)" > $R/p5x.log 2>&1
if [ -f $R/ok_cave.flag ]; then python run_trials.py $S --plan plan_p5_cave.json --out $R/main.jsonl --purpose "阳性对照②:让步方向 ±6" > $R/p5.log 2>&1; else echo "跳过:楠还没写②的预期" > $R/p5.log; fi
python run_extract.py --value values/autonomy.yaml --purpose "提取价值:自主(阳性对照③ / 第二个价值)" > $R/p6x.log 2>&1
if [ -f $R/ok_autonomy.flag ]; then python run_trials.py $S --plan plan_p6_auto.json --out $R/main.jsonl --purpose "阳性对照③:自主 ±6、±3" > $R/p6.log 2>&1; else echo "跳过:楠的③预期待确认" > $R/p6.log; fi
echo PHASE2DONE > $R/phase2.done
