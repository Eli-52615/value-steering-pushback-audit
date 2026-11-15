"""把一个价值的体检结果(checkup.json + layer_select.json)摘成可读的 Markdown,和另一个价值并排。
用法(服务器上):python show_checkup.py benevolence_ni benevolence > out.md"""
import json, sys
from pathlib import Path

W = Path("/root/autodl-tmp/vt_work/dev9b/values")


def load(v):
    return json.loads((W / v / "checkup.json").read_text()), json.loads((W / v / "layer_select.json").read_text())


def snip(s):
    return (s["left"][-14:] + "【" + s["center"] + "】" + s["right"][:14]).replace("\n", " ").replace("|", "／")


a, b = sys.argv[1], sys.argv[2]
(ca, la), (cb, lb) = load(a), load(b)
print(f"## 选层标定（{a} 对照 {b}）\n\n| 层 | {a} α_max | {a} 调节效果 | {a} 中档连贯性 | {b} α_max | {b} 调节效果 |\n|---|---|---|---|---|---|")
for ra, rb in zip(la["layers"], lb["layers"]):
    print(f"| {ra['layer']} | +{ra['alpha_max']['pos']:.2f}/−{ra['alpha_max']['neg']:.2f} | {ra['effect']:.1f} | {ra['coherence_mid']:.1f} "
          f"| +{rb['alpha_max']['pos']:.2f}/−{rb['alpha_max']['neg']:.2f} | {rb['effect']:.1f} |")
print(f"\n{a} 按规则选的层：第 {la['chosen']} 层（{b}：第 {lb['chosen']} 层）。主实验固定用第 12 层。")
L12 = [r for r in la["layers"] if r["layer"] == 12][0]
print(f"\n{a} 第 12 层扫描（价值分 / 连贯性，打分接口，生活情境题 10 道）：基线 {L12['baseline_trait']:.1f} / {L12['baseline_coherence']:.1f}")
for key in ("pos", "neg"):
    print(f"- {'+' if key == 'pos' else '−'}：" + "；".join(f"α={s['alpha']:.2f}: {s['trait']:.1f}/{s['coherence']:.1f}" for s in L12["calibration"]["sweep"][key]))
for v, c in ((a, ca), (b, cb)):
    print(f"\n## {v}：中性语料上激活最强 / 最弱的片段（第 12 层，前 10 条）\n")
    print("最强：\n" + "\n".join(f"{i + 1}. {snip(s)}（{s['value']:.1f}）" for i, s in enumerate(c["contexts"]["top"][:10])))
    print("\n最弱：\n" + "\n".join(f"{i + 1}. {snip(s)}（{s['value']:.1f}）" for i, s in enumerate(c["contexts"]["bottom"][:10])))
    print(f"\nlogit lens 推高的词：{'、'.join(t['token'].strip() for t in c['logit_lens']['up'][:20])}")
    print(f"logit lens 压低的词：{'、'.join(t['token'].strip() for t in c['logit_lens']['down'][:20])}")
    print("\nSAE 特征（和正极方向余弦最高的 8 个；解释是打分接口自动标的）：")
    for f in c["sae"]["cos_pos"][:8]:
        print(f"- #{f['feature']}（{f['stat']:.3f}，置信度{f['confidence']}）{f['explanation']}")
    print("\nSAE 特征（和负极方向余弦最高的 5 个）：")
    for f in c["sae"]["cos_neg"][:5]:
        print(f"- #{f['feature']}（{f['stat']:.3f}，置信度{f['confidence']}）{f['explanation']}")
    print(f"\n前 30 个 SAE 方向能解释的向量范数比例：{c['sae']['top30_dirs_explained_norm_frac']:.2f}")
    print("\n混杂：" + "；".join(f"{x['name']} {x['cos']:+.3f}{' ⚠️' if x['warn'] else ''}" for x in c["confound"]["items"]))
