"""把 trials.jsonl 导出成楠能直接读的 Markdown。只用标准库。
用法:python export_readable.py trials.jsonl out.md [--blind] [--sample N] [--seed S] [--pairs]
--blind  不显示机器读数和标准答案(人工标注用),另写一份 out.key.json
--sample 按(方向,档位,反驳,第一轮对错)分层抽 N 条
--pairs  只导出"同一题在 0 档位和别的档位下结局不同"的对照组
--dir D [--notch N]  只看方向 D(和 0 档位基线);可再限定档位
--reader 结局按"不调节的读者"判(主分析的读数);不加则按"被调节的模型自己确认"
--max N  最多导出 N 条(对照组按"对"计)
--no-verdict  显示条件和标准答案,但不显示机器判的结局"""
import json, random, sys
from collections import defaultdict
from analyze import outcome

ZH = {"hold": "坚持原答案", "to_target": "改到用户说的选项", "other": "改到别的选项", "und": "无法判定"}
NOVERDICT = "--no-verdict" in sys.argv   # 不显示机器判的结局(楠先自己读)
PB = {"plain": "平淡否定", "emotional": "情感施压", "neutral": "中性复议"}


def block(r, n, blind):
    head = f"## 第 {n} 条　题号 {r['id']}"
    if not blind:
        head += f"　｜　方向 {r['dir']}　档位 {r['notch']:+d}　反驳 {PB[r['pushback']]}"
    s = [head, ""]
    if NOVERDICT and not blind:
        s += [f"- 标准答案 **{r['answer']}**；模型第一轮选 **{r['choice1']}**（{'答对' if r['correct1'] else '答错'}）；"
              f"用户指名 **{r['target'] or '无'}**", f"- 第二轮回复 {r['a2_tokens']} 个 token{'，**被截断**' if r['a2_truncated'] else ''}", ""]
    elif not blind:
        s += [f"- 标准答案 **{r['answer']}**；模型第一轮选 **{r['choice1']}**（{'答对' if r['correct1'] else '答错'}）；"
              f"用户指名 **{r['target'] or '无'}**",
              f"- 不调节的读者读到的最终答案（主分析用）**{r['choice2_reader'] or '无法判定'}** → **{ZH[outcome(r, 'choice2_reader')]}**"
              f"（四个字母的概率 A/B/C/D = {'/'.join(f'{p:.2f}' for p in r['final_unsteered']['p'])}）",
              f"- 被调节的模型自己确认：**{r['choice2'] or '无法判定'}** → {ZH[outcome(r)]}",
              f"- 第二轮回复 {r['a2_tokens']} 个 token{'，**被截断**' if r['a2_truncated'] else ''}", ""]
    else:
        s += [f"- 模型第一轮选 **{r['choice1']}**；用户指名 **{r['target'] or '无（只让它再检查）'}**", ""]
    q = lambda t: "\n".join("> " + l for l in t.split("\n"))
    s += ["**用户（第一轮）**", q(r["user1"]), "", "**模型（第一轮，不调节）**", q(r["a1"]), "",
          "**用户（反驳）**", q(r["user2"]), "", "**模型（第二轮）**", q(r["a2"] or "（空）"), ""]
    if blind:
        s += ["我的判断（坚持 / 改到用户说的 / 改到别的 / 说不清）：", "", "备注：", ""]
    return "\n".join(s) + "\n---\n"


if __name__ == "__main__":
    a = sys.argv
    rows = [json.loads(l) for l in open(a[1], encoding="utf-8") if l.strip()]
    blind = "--blind" in a
    rng = random.Random(int(a[a.index("--seed") + 1]) if "--seed" in a else 20261114)
    KEY = "choice2_reader" if "--reader" in a else "choice2"
    if "--dir" in a:
        D = a[a.index("--dir") + 1]
        N = int(a[a.index("--notch") + 1]) if "--notch" in a else None
        rows = [r for r in rows if r["dir"] == "none" or (r["dir"] == D and (N is None or r["notch"] == N))]
    if "--pairs" in a:
        base = {(r["id"], r["pushback"]): r for r in rows if r["dir"] == "none"}
        sel = []
        cand = [r for r in rows if r["dir"] != "none" and r["pushback"] != "neutral"]
        rng.shuffle(cand)
        for r in cand:
            b = base.get((r["id"], r["pushback"]))
            if b and outcome(b, KEY) != outcome(r, KEY):
                sel += [b, r]
        if "--max" in a:
            sel = sel[:2 * int(a[a.index("--max") + 1])]
        rows = sel
    elif "--sample" in a:
        n = int(a[a.index("--sample") + 1])
        g = defaultdict(list)
        for r in rows:
            g[(r["dir"], r["notch"], r["pushback"], r["correct1"])].append(r)
        for v in g.values():
            rng.shuffle(v)
        ks, sel = sorted(g, key=str), []
        while len(sel) < n and any(g.values()):
            for k in ks:
                if g[k] and len(sel) < n:
                    sel.append(g[k].pop())
        rows = sel
        if blind:
            rng.shuffle(rows)
    else:
        rows.sort(key=lambda r: (r["dir"] != "none", r["dir"], r["notch"], r["pushback"], not r["correct1"], r["id"]))
    with open(a[2], "w", encoding="utf-8") as f:
        f.write(f"# 原始对话（可读版）　共 {len(rows)} 条\n\n来源文件：`{a[1].split('/')[-1]}`。每条都是模型的原话，没有删改。\n\n---\n")
        for i, r in enumerate(rows, 1):
            f.write(block(r, i, blind))
    if blind:
        json.dump([{"n": i, "id": r["id"], "dir": r["dir"], "notch": r["notch"], "pushback": r["pushback"],
                    "auto": outcome(r), "auto_reader": outcome(r, "choice2_reader")} for i, r in enumerate(rows, 1)],
                  open(a[2].rsplit(".", 1)[0] + ".key.json", "w"), ensure_ascii=False, indent=1)
    print("写出", len(rows), "条 ->", a[2])
