#!/bin/bash
# 早上(或任何时候)把服务器上的最新结果拉回来,更新登记,导出给楠读的材料,出汇总表、确认性检验和图。
# 用法:./morning.sh [方向,默认 benevolence_ni]
cd "$(dirname "$0")"; V=${1:-benevolence_ni}; M=../结果/main; mkdir -p $M
rsync -az vt:/root/autodl-tmp/sprint/runs/main.jsonl vt:/root/autodl-tmp/sprint/runs/main.jsonl.meta.json vt:/root/autodl-tmp/sprint/runs/main_set.json $M/
for f in main_noise_bs24.jsonl capability.jsonl cave_extract.jsonl trait_scores.jsonl; do rsync -az vt:/root/autodl-tmp/sprint/runs/$f $M/ 2>/dev/null; done
rsync -az vt:/root/autodl-tmp/sprint/runs/registry.jsonl ../结果/
python3 render_registry.py ../结果/运行登记-事后补记.jsonl ../结果/registry.jsonl ../运行登记.md
python3 jsonl_to_sqlite.py $M/主实验全部试验.sqlite $M/main.jsonl
H="$M/含结局-写完预测再打开"; mkdir -p "$H/图"
python3 analyze.py $M/main.jsonl --reader --md "$H/汇总-不调节的读者.md" > /dev/null
python3 analyze.py $M/main.jsonl --md "$H/汇总-模型自己确认.md" > /dev/null
python3 stats.py $M/main.jsonl --dir $V --reader > "$H/确认性检验-$V-读者.txt" 2>&1
python3 stats.py $M/main.jsonl --dir $V > "$H/确认性检验-$V-自己确认.txt" 2>&1
python3 export_readable.py $M/main.jsonl "$H/对话-$V-分层抽30条-含机器判定.md" --dir $V --sample 30
python3 export_readable.py $M/main.jsonl "$H/对话-$V+6与0档位结局不同-对照集.md" --dir $V --notch 6 --pairs --reader --max 30
python3 export_readable.py $M/main.jsonl "$M/对话-$V-0档位与+6档位-同题对照15对-不含机器判定.md" --dir $V --notch 6 --compare 15 --noverdict
[ -f ../结果/人工标注-待标.md ] || python3 export_readable.py $M/main.jsonl ../结果/人工标注-待标.md --dir $V --sample 60 --blind --seed 7
ssh vt "export PATH=/root/miniconda3/bin:\$PATH; cd /root/autodl-tmp/sprint/code3 && python plots.py ../runs/main.jsonl ../runs/figs_$V --dir $V > ../runs/plots_$V.log 2>&1; tail -n 1 ../runs/plots_$V.log"
rsync -az vt:/root/autodl-tmp/sprint/runs/figs_$V/ "$H/图/$V/"
echo "完成:$(grep -c '' $M/main.jsonl) 条"
