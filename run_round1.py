"""第一轮基线:不调节,每题只做一次。输出 round1.jsonl(每题一行,含完整回答与读数)。
用法:python run_round1.py --config <yaml> --items items.jsonl --out round1.jsonl"""
import argparse, json, re, sys, time
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/vt")
from vt.config import load_cfg
from vt.model import LM
import trial as T

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--items", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--max_new", type=int, default=160)
ap.add_argument("--bs", type=int, default=48)
a = ap.parse_args()

items = T.load_jsonl(a.items)
done = {r["id"] for r in T.load_jsonl(a.out)} if Path(a.out).exists() else set()
items = [it for it in items if it["id"] not in done]
lm = LM(load_cfg(a.config))
t0 = time.time()
with open(a.out, "a", encoding="utf-8") as f:
    for s in range(0, len(items), 256):
        ch = items[s:s + 256]
        qs = [T.question_text(it) for it in ch]
        g = T.gen(lm, [T.chat(lm, [q]) for q in qs], None, a.max_new, a.bs)
        ro = T.readout(lm, [T.chat(lm, [q, x[0], T.CONFIRM]) for q, x in zip(qs, g)], None, a.bs)
        for it, (a1, n1), r in zip(ch, g, ro):
            m = re.match(r"\s*\**\s*(?:答案|选项|我选)?\s*[:：是为]?\s*\**\s*([ABCD])(?![A-Za-z])", a1)
            c = T.pick(r)
            f.write(json.dumps({**it, "a1": a1, "a1_tokens": n1, "a1_truncated": n1 >= a.max_new, "r1": r,
                                "choice1": c, "text_letter1": m.group(1) if m else None,
                                "correct1": (c == it["answer"]) if c else None,
                                "prompts_version": T.PROMPTS_VERSION}, ensure_ascii=False) + "\n")
        f.flush()
        print(f"{s + len(ch)}/{len(items)}  {time.time() - t0:.0f}s", flush=True)
print("DONE", flush=True)
