"""生成 20 个新的随机方向(楠 2026-11-16 的改进意见 1):10 个普通高斯,10 个按第 12 层激活的协方差抽。
用法:python make_rand20.py --out ../runs/rand20_dirs.pt [--n 10] [--seed 20261116]

协方差方向的抽法:取中性语料(ValueTuner 赛前缓存,501 篇、约 11 万个正文 token)在调节层的残差 X,
减去均值后 v = (X − μ)ᵀ z,z ~ N(0, I_n)。这样 v ~ N(0, n·Σ̂),正是"按激活协方差抽",不需要做特征分解。
所有方向都归一成单位向量,注入时和仁慈用同一个范数(run_trials 的档位换算不变)。
方向在看到任何结局之前由种子定死;本脚本只读缓存的激活和已有的价值向量,不跑模型、不碰任何试验结果。"""
import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, "/root/autodl-tmp/vt")
from vt.config import load_cfg
from vt.dose import spec
from reglog import Run

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="/root/autodl-tmp/vt/configs/dev9b.yaml")
ap.add_argument("--ref", default="benevolence")
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=10)        # 每种各 n 个
ap.add_argument("--seed", type=int, default=20261116)
a = ap.parse_args()
run = Run("生成 20 个新随机方向(10 高斯 + 10 按激活协方差),不跑模型", a.out)

cfg = load_cfg(a.config)
L = spec(cfg, a.ref)["layer"]
N = Path(cfg.work_dir) / "neutral"
content = np.load(N / "tokens.npz")["content"]
X = torch.from_numpy(np.ascontiguousarray(np.load(N / f"resid_L{L}.npy", mmap_mode="r")[content])).cuda().float()
mu = X.mean(0)
Xc = X - mu
g = torch.Generator().manual_seed(a.seed)
unit = lambda v: v / v.norm(dim=-1, keepdim=True)
G = unit(torch.randn(a.n, cfg.d_model, generator=g))                    # 普通高斯
Z = torch.randn(a.n, Xc.shape[0], generator=g)                         # 协方差方向用的系数
C = unit((Z.cuda() @ Xc).cpu())
dirs = {f"rg{k + 1:02d}": G[k].clone() for k in range(a.n)} | {f"rc{k + 1:02d}": C[k].clone() for k in range(a.n)}
torch.save(dirs, a.out)

# ---- 诊断(只描述方向本身,和结局无关)----
S = (Xc.T @ Xc / Xc.shape[0]).double()
ev = torch.linalg.eigvalsh(S).flip(0).clamp(min=0)
mean_ev = float(ev.sum() / cfg.d_model)
var_ratio = lambda v: float(v.double().cuda() @ S @ v.double().cuda()) / mean_ev     # 沿该方向的激活方差 ÷ 各方向平均方差
named = {}
for d in sorted((Path(cfg.work_dir) / "values").iterdir()):
    if (d / "vectors.pt").exists():
        v = torch.load(d / "vectors.pt")[L].float()
        named[d.name] = v / v.norm()
M = torch.stack(list(dirs.values()))
cosm = (M @ M.T).fill_diagonal_(0).abs()
diag = {"layer": L, "seed": a.seed, "n_tokens": int(Xc.shape[0]), "sha256_16": hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:16],
        "participation_ratio": float(ev.sum() ** 2 / (ev ** 2).sum()),
        "top_pc_share": {str(k): round(float(ev[:k].sum() / ev.sum()), 4) for k in (1, 10, 100)},
        "max_abs_cos_between_new_dirs": round(float(cosm.max()), 4),
        "var_ratio_named": {k: round(var_ratio(v), 2) for k, v in named.items()},
        "dirs": {k: {"type": "gauss" if k.startswith("rg") else "cov", "var_ratio": round(var_ratio(v), 2),
                     "cos": {n: round(float(v @ w), 4) for n, w in named.items()}} for k, v in dirs.items()}}
Path(a.out + ".json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in diag.items() if k != "dirs"}, ensure_ascii=False))
for k, v in diag["dirs"].items():
    print(k, v["type"], "方差比", v["var_ratio"], "与新仁慈余弦", v["cos"].get("benevolence_ni"))
run.done()
print("DONE")
