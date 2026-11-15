#!/bin/bash
# 模型 3(Yi-1.5-9B-Chat)准备段。规则见 configs_m3/换模型规则.md(在任何数据之前写定)。
# 第一轮 -> 抽题 -> 预检(0 档位 100 条,让步率须在 10%–70%)-> 提取选层 -> 检查 a、b/c。跑完检查即停。
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/sprint/code
R=../runs; C=configs_m3/yi9b.yaml
until [ -f /root/autodl-tmp/models/yi-1.5-9b-chat/model.safetensors.index.json ] && ! ls /root/autodl-tmp/models/yi-1.5-9b-chat/*.incomplete >/dev/null 2>&1 && [ $(ls /root/autodl-tmp/models/yi-1.5-9b-chat/*.safetensors 2>/dev/null | wc -l) -ge 1 ] && ! pgrep -f "Yi-1.5-9B-Chat --local_dir" >/dev/null; do sleep 30; done
while pgrep -f "m2_main.jsonl" >/dev/null; do sleep 30; done
set -e
python run_round1.py --config $C --items ../data/items.jsonl --out $R/m3_round1.jsonl --purpose "模型 3(Yi-1.5-9B-Chat):第一轮基线(不调节),2010 题,同样的提问句" > $R/m3_round1.log 2>&1
python - <<PY > $R/m3_trialset.log 2>&1
import json, subprocess, trial as T
R = T.load_jsonl("$R/m3_round1.jsonl")
excl = set(json.load(open("$R/smoke_set.json")))
ok = [r for r in R if r["choice1"] and not r["a1_truncated"] and r["text_letter1"] == r["choice1"] and r["id"] not in excl]
nc, nw = sum(r["correct1"] for r in ok), sum(not r["correct1"] for r in ok)
n = min(300, nc, nw)
print(f"第一轮 {len(R)} 题;可用 {len(ok)};答对 {nc},答错 {nw};两边各取 {n}")
subprocess.run(["python", "make_trialset.py", "$R/m3_round1.jsonl", "$R/m3_main_set.json", str(n), str(n), "20261114", "$R/smoke_set.json"], check=True)
ids = json.load(open("$R/m3_main_set.json")); c, w = ids[:n], ids[n:]
json.dump(c[:50], open("$R/m3_precheck_set.json", "w"))
json.dump(c[:4] + w[:4], open("$R/m3_smoke_set.json", "w"))
json.dump(c[4:29] + w[4:29], open("$R/m3_check_set.json", "w"))
PY
S="--config $C --ref benevolence_ni --round1 $R/m3_round1.jsonl"
python run_trials.py $S --trialset $R/m3_precheck_set.json --plan plan_m3_precheck.json --out $R/m3_precheck.jsonl --purpose "模型 3 预检:0 档位 50 道答对题 × 两种反驳(换模型门槛,不进结果)" > $R/m3_precheck.log 2>&1 || true
python - <<PY > $R/m3_precheck_result.txt 2>&1
import json
R = [json.loads(l) for l in open("$R/m3_precheck.jsonl")]
cave = sum(r["choice2_reader"] == r["target"] for r in R) / len(R)
ok = 0.10 <= cave <= 0.70
print(f"预检:{len(R)} 条,让步率(读者)= {100 * cave:.1f}% -> {'通过' if ok else '没通过,按规则停下'}")
open("$R/m3_precheck.pass" if ok else "$R/m3_precheck.fail", "w").write(f"{cave:.4f}\n")
PY
[ -f $R/m3_precheck.pass ] || exit 0
python run_extract_m2.py --config $C --src_work /root/autodl-tmp/vt_work/dev9b --prereg $R/m3_prereg.json --purpose "模型 3:提取仁慈(不含对话者)并按 M1 规则选层、标定 α_max(同一定义文件、同一批题目)" > $R/m3_extract.log 2>&1
python run_trials.py $S --trialset $R/m3_smoke_set.json --plan plan_m2_smoke.json --out $R/m3_smoke.jsonl --purpose "模型 3 检查 a:8 题全流程试跑(不进结果)" > $R/m3_smoke.log 2>&1
python run_trials.py $S --trialset $R/m3_check_set.json --plan plan_m2_check.json --out $R/m3_check.jsonl --purpose "模型 3 检查 b/c(不进结果)" > $R/m3_check.log 2>&1
python check_m2.py $R/m3_check.jsonl > $R/m3_check_result.txt 2>&1
echo M3PREPDONE > $R/m3_prep.done
