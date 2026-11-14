"""把运行登记(事后补记 + 自动登记)渲染成楠能读的表。用法:python render_registry.py 补记.jsonl registry.jsonl out.md"""
import json, sys
rows, ends = [], {}
for p in sys.argv[1:3]:
    try:
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r.get("event") == "end":
                    ends[r["run"]] = r
                else:
                    rows.append(r)
    except FileNotFoundError:
        pass
out = ["# 运行登记", "",
       "任何一次在模型上的运行都在这里，包括失败、中断、重跑。**没有登记的运行，结果不进论文。**",
       "标「事后补」的是 11-14 凌晨登记机制建立之前的运行，由 Code 按日志和文件时间补记；之后的由脚本自动登记（开始记一条、结束记一条，追加写，不改不删）。",
       "由 `code/render_registry.py` 生成，不要手改。原始登记：`结果/运行登记-事后补记.jsonl`、`结果/registry.jsonl`。", "",
       "| # | 运行编号 | 时间 | 为了什么 | 状态 | 输出文件（行数） | 代码版本 | 备注 |", "|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    e = ends.get(r["run"], {})
    if r.get("backfilled"):
        st, n = r["status"] + "（事后补）", r.get("rows_after")
        note = r.get("note", "") + (f"　错误：{r['error']}" if r.get("error") else "")
    else:
        st = e.get("status", "**没有结束记录（还在跑，或者被杀、断电）**")
        n = f"{r.get('rows_before')} → {e.get('rows_after')}" if e else r.get("rows_before")
        note = (r.get("note") or "") + (f"　错误：{e['error']}" if e.get("error") else "") + (f"　用时 {e['seconds']} 秒" if e else "")
    out.append(f"| {i} | {r['run']} | {r['time']} | {r['purpose']} | {st} | {(r.get('out') or '—').split('/')[-1]}（{n if n is not None else '—'}） | {r.get('commit', '')} | {note} |")
open(sys.argv[3], "w", encoding="utf-8").write("\n".join(out) + "\n")
print("登记", len(rows), "条")
