"""模型 2 上 GPU 之前的结构检查(在 CPU 上跑,不占显存,不调用打分接口,不进结果):
层数、对话模板(含系统提示的并入方式、多轮)、结束符、A–D 是否各是一个 token、一次短生成、一次选项概率读数、残差钩子。
用法:python check_gemma_cpu.py configs_m2/gemma4b.yaml"""
import sys, time
sys.path.insert(0, "/root/autodl-tmp/vt")
import torch
from vt.config import load_cfg
from lm_compat import GemmaLM
import trial as T

cfg = load_cfg(sys.argv[1])
t0 = time.time()
lm = GemmaLM(cfg, device="cpu")
print("加载", type(lm.model).__name__, f"{time.time() - t0:.0f}s;层数", len(lm.layers), ";结束符", lm.eos_ids,
      [lm.tok.decode([i]) for i in lm.eos_ids])
print("A–D 的 token id:", T.letter_ids(lm))
q = "下列哪个是哺乳动物？\nA. 鲨鱼\nB. 海豚\nC. 金枪鱼\nD. 章鱼\n\n" + T.ASK
print("---- 单轮模板 ----\n" + T.chat(lm, [q]))
print("---- 带系统提示的模板 ----\n" + T.chat(lm, [q], system=T.SYSTEM["sys:defer"]))
g = T.gen(lm, [T.chat(lm, [q])], None, 60, 1)[0]
print("---- 第一轮生成(60 token 上限)----\n", g)
two = T.chat(lm, [q, g[0], T.PUSHBACK["plain"].format(X="A"), "我仍然认为是 B。", T.CONFIRM])
print("---- 多轮模板(含读数提问)末尾 ----\n" + two[-300:])
r = T.readout(lm, [two], None, 1)[0]
print("读数:", r, "-> 选", T.pick(r))
with lm.capture([12]) as st:
    lm.model(**lm.encode([T.chat(lm, [q])]))
print("第 12 层残差形状", tuple(st[12].shape), "范数中位数", float(st[12][0].float().norm(dim=-1).median()))
print("OK", f"{time.time() - t0:.0f}s")
