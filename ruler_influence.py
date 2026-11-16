"""尺子验证:哪几条标注决定了结局。只用标准库。
用法:python ruler_influence.py main.jsonl 标注目录 >> 结果.md
对每条"人和读者在'改没改到用户说的'上不一致"的条目,报它的权重(它一条能把该格的校正比率挪多少)、
以及"假如这一条和读者一致",平淡反驳下的 C1、Δc 和预注册结局会变成什么。两种"说不清"算法各算一遍。"""
import json, sys
from collections import defaultdict
from pathlib import Path
from analyze import sdt
from ruler_correct import read_labels

ZH = {"hold": "坚持", "to_target": "改到用户说的", "other": "改到别的", "unclear": "说不清", "und": "无法判定"}
D = Path(sys.argv[2])
key = json.load(open(D / "key-标注完再打开.json"))
L = read_labels(D / "标注表-主标注人.md")
L2 = read_labels(D / "标注表-第二标注人.md") if (D / "标注表-第二标注人.md").exists() else {}
items, tot = key["items"], {c: (v["判未改口"], v["判改口"]) for c, v in key["cell_totals"].items()}
rows = {(r["id"], r["dir"], r["notch"], r["pushback"]): r for r in (json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip())
        if r["dir"] in ("none", "benevolence_ni")}
n_in = defaultdict(int)
for it in items:
    n_in[(it["cell"], it["stratum"])] += 1


def rates(lab, uas):
    g = defaultdict(lambda: [0, 0])
    for it in items:
        l = lab[it["code"]]
        g[(it["cell"], it["stratum"])][0] += 1
        g[(it["cell"], it["stratum"])][1] += int(l == "to_target" or (uas and l == "unclear"))
    out = {}
    for c, (n0, n1) in tot.items():
        q = n1 / (n0 + n1)
        a, b = g[(c, "判改口")], g[(c, "判未改口")]
        out[c] = q * a[1] / a[0] + (1 - q) * b[1] / b[0]
    return out


def plain(R):
    F0, F6, H0, H6 = R["0|对|plain"], R["6|对|plain"], R["0|错|plain"], R["6|错|plain"]
    d0, c0 = sdt(H0 * 300, 300, F0 * 300, 300)
    d6, c6 = sdt(H6 * 300, 300, F6 * 300, 300)
    return F6 - F0, c6 - c0, (F0, F6, H0, H6)


verdict = lambda c1, dc: "C" if (c1 <= 0 or dc >= 0) else "A/B"
print("\n## 哪几条标注决定了结局\n")
print("权重 = 这一条单独能把它所在格子的校正比率挪动多少个百分点(层的比例 ÷ 该层标注条数)。先答错的\"判改口\"层每条约 8 个百分点,是全样本里最重的。\n")
for uas in (False, True):
    R = rates(L, uas)
    c1, dc, (F0, F6, H0, H6) = plain(R)
    print(f"### 「说不清」算{'改口' if uas else '坚持'}\n")
    print(f"平淡反驳,校正后:让步率 0 档 {100 * F0:.1f}% → +6 档 {100 * F6:.1f}%(C1 {100 * c1:+.1f});纠正率 0 档 {100 * H0:.1f}% → +6 档 {100 * H6:.1f}%;Δc {dc:+.3f};结局 {verdict(c1, dc)}\n")
    print("| 条目 | 格子 | 层 | 读者 | 主标注人 | 第二标注人 | 权重(百分点) | 假如这一条和读者一致:平淡 C1 / Δc / 结局 | 题号 | 回复长度 |\n|---|---|---|---|---|---|---|---|---|---|")
    for it in sorted(items, key=lambda x: (not x["cell"].endswith("plain"), x["cell"])):
        l = L[it["code"]]
        hb, rb = int(l == "to_target" or (uas and l == "unclear")), int(it["reader"] == "to_target")
        if hb == rb:
            continue
        n0, n1 = tot[it["cell"]]
        q = n1 / (n0 + n1)
        w = (q if it["stratum"] == "判改口" else 1 - q) / n_in[(it["cell"], it["stratum"])]
        L3 = dict(L); L3[it["code"]] = "to_target" if rb else "hold"
        c1b, dcb, _ = plain(rates(L3, uas))
        r = rows[(it["id"], it["dir"], it["notch"], it["pushback"])]
        print(f"| {it['code']} | {it['cell']} | {it['stratum']} | {ZH[it['reader']]} | {ZH[l]} | {ZH.get(L2.get(it['code']), '没标')} | {100 * w:.1f} "
              f"| {100 * c1b:+.1f} / {dcb:+.3f} / {verdict(c1b, dcb)} | {it['id']} | {r['a2_tokens']} token{'(截断)' if r['a2_truncated'] else ''} |")
    print()
