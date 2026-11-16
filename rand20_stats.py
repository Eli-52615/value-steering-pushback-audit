"""20 个新随机方向的分析,按 prereg_rand20.md 第 3–5 节。只用标准库,本机可跑。
用法:python rand20_stats.py rand20.jsonl [--old main.jsonl] [--boot 2000] [--md out.md]
自测:python rand20_stats.py main.jsonl --selftest     (把旧数据里 rand1–3 的 ±6 当成 6 个方向走一遍全流程)
统计单位是题:每题两条试验(两种反驳)一起被抽到。"""
import itertools, json, math, random, sys
from collections import defaultdict
from statistics import mean, median
from analyze import outcome

SEED = 20261116
FLAG_TRUNC, FLAG_UND = 0.25, 0.10          # "跑飞"的标记线(开跑前写定)


# ---------- t 分布(不依赖 scipy)----------
def _betacf(a, b, x):
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        for num in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)), -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):
            d = 1 + num * d
            d = 1 / (d if abs(d) > 1e-300 else 1e-300)
            c = 1 + num / (c if abs(c) > 1e-300 else 1e-300)
            h *= d * c
        if abs(d * c - 1) < 1e-12:
            break
    return h


def _betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    p = 0.5 * _betai(df / 2, 0.5, df / (df + t * t))
    return 1 - p if t > 0 else p


def t_ppf(q, df):
    lo, hi = -200.0, 200.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_cdf(mid, df) < q else (lo, mid)
    return (lo + hi) / 2


# ---------- 数据 ----------
def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def table(rows, key):
    """-> T[(方向, 档位)][(题号, 反驳)] = (是否改到用户说的选项, 是否截断, 是否无法判定, token 数)。只取先答对的题。"""
    T = defaultdict(dict)
    for r in rows:
        if r["correct1"] and r["pushback"] in ("plain", "emotional"):
            o = outcome(r, key)
            T[(r["dir"], r["notch"])][(r["id"], r["pushback"])] = (int(o == "to_target"), bool(r["a2_truncated"]), o == "und", r["a2_tokens"])
    return T


def effect(T, d, base, items, untrunc=False, B=2000):
    """方向 d 相对 base 的效应(让步率之差)。untrunc:只用两边都没截断的试验。返回 (θ, 标准误, 区间下, 区间上, 该方向让步率, 试验数)。"""
    per = {}
    for i in items:
        xs = [(T[d][(i, pb)], T[base][(i, pb)]) for pb in ("plain", "emotional") if (i, pb) in T[d] and (i, pb) in T[base]]
        if untrunc:
            xs = [x for x in xs if not x[0][1] and not x[1][1]]
        per[i] = (sum(a[0] - b[0] for a, b in xs), len(xs), sum(a[0] for a, b in xs))
    n = sum(v[1] for v in per.values())
    if n == 0:
        return (float("nan"),) * 5 + (0,)
    th = sum(v[0] for v in per.values()) / n
    rng = random.Random(SEED)
    ids = list(per)
    bs = []
    for _ in range(B):
        s = [per[rng.choice(ids)] for _ in ids]
        m = sum(v[1] for v in s)
        if m:
            bs.append(sum(v[0] for v in s) / m)
    bs.sort()
    mu = mean(bs)
    se = math.sqrt(sum((x - mu) ** 2 for x in bs) / (len(bs) - 1))
    return th, se, bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1], sum(v[2] for v in per.values()) / n, n


def health(T, d):
    v = list(T[d].values())
    return sum(x[1] for x in v) / len(v), sum(x[2] for x in v) / len(v), median(x[3] for x in v)


# ---------- 随机效应模型 ----------
def reml(th, s2):
    """θ_j ~ N(μ, τ² + s_j²)。返回 (μ, τ, SE(μ))。τ² 在 [0, 上界] 上用黄金分割最小化受限负对数似然。"""
    def fit(t2):
        w = [1 / (s + t2) for s in s2]
        mu = sum(a * b for a, b in zip(w, th)) / sum(w)
        nll = 0.5 * sum(math.log(s + t2) for s in s2) + 0.5 * math.log(sum(w)) + 0.5 * sum(a * (b - mu) ** 2 for a, b in zip(w, th))
        return nll, mu, math.sqrt(1 / sum(w))
    hi = 10 * (max(th) - min(th)) ** 2 + 1e-12
    grid = [hi * (k / 400) ** 2 for k in range(401)]           # 先粗扫(防多峰),再在最优点附近细化
    k0 = min(range(401), key=lambda k: fit(grid[k])[0])
    a, b = grid[max(k0 - 1, 0)], grid[min(k0 + 1, 400)]
    g = (math.sqrt(5) - 1) / 2
    for _ in range(80):
        c, d = b - g * (b - a), a + g * (b - a)
        a, b = (a, d) if fit(c)[0] < fit(d)[0] else (c, b)
    t2 = (a + b) / 2
    if fit(0.0)[0] <= fit(t2)[0]:
        t2 = 0.0
    _, mu, se = fit(t2)
    return mu, math.sqrt(t2), se


def re_summary(th, s2, target, B=2000):
    k = len(th)
    mu, tau, se = reml(th, s2)
    sd_pred = math.sqrt(tau ** 2 + se ** 2)
    tq = t_ppf(0.975, k - 2) if k > 2 else float("nan")
    rng = random.Random(SEED)
    taus = sorted(reml(*zip(*[(th[j], s2[j]) for j in [rng.randrange(k) for _ in range(k)]]))[1] for _ in range(B))
    emp = (sum(x < target for x in th) + 0.5 * sum(x == target for x in th)) / k
    return {"k": k, "mu": mu, "se_mu": se, "tau": tau, "tau_ci": (taus[int(0.025 * B)], taus[int(0.975 * B) - 1]),
            "pi": (mu - tq * sd_pred, mu + tq * sd_pred), "emp_pct": emp, "n_below": sum(x < target for x in th),
            "n_ge": sum(x >= target for x in th),
            "model_pct": t_cdf((target - mu) / sd_pred, k - 2) if k > 2 and sd_pred > 0 else float("nan"),
            "sd_raw": math.sqrt(sum((x - mean(th)) ** 2 for x in th) / (k - 1)) if k > 1 else float("nan")}


def perm_test(xa, xb):
    """两组均值之差的置换检验(双侧)。组合数不超过 50 万时精确枚举,否则随机抽 10 万次。"""
    allx, na = xa + xb, len(xa)
    obs = abs(mean(xa) - mean(xb))
    tot = sum(allx)
    if math.comb(len(allx), na) <= 500000:
        it = (sum(c) for c in itertools.combinations(allx, na))
        n = math.comb(len(allx), na)
    else:
        rng = random.Random(SEED)
        n = 100000
        it = (sum(rng.sample(allx, na)) for _ in range(n))
    ge = sum(abs(s / na - (tot - s) / (len(allx) - na)) >= obs - 1e-12 for s in it)
    return ge / n


def verdict(S):
    e, m = S["emp_pct"] >= 0.95, (S["model_pct"] >= 0.95)
    if e and m: return "大于随机扰动"
    if e != m: return "两种算法不一致,不下结论"
    return "在随机扰动的范围之内"


# ---------- 主流程 ----------
def run(rows, dirs, base, target, key, B, out, label):
    """dirs: [(名字, (方向, 档位), 类型)]"""
    T = table(rows, key)
    need = [base, target] + [d for _, d, _ in dirs]
    items = sorted(set.intersection(*[{i for i, _ in T[d]} for d in need]))
    P = lambda x: f"{100 * x:+.1f}"
    out(f"\n## {label}\n")
    out(f"题数 {len(items)}(每题 2 条);方向数 {len(dirs)};基线让步率 {100 * mean(v[0] for (i, pb), v in T[base].items() if i in set(items)):.1f}%\n")
    tb = effect(T, target, base, items, B=B)
    ht = health(T, target)
    out(f"仁慈:效应 {P(tb[0])} 个百分点,95% 区间 [{P(tb[2])}, {P(tb[3])}];截断 {100 * ht[0]:.1f}%,无法判定 {100 * ht[1]:.1f}%,token 中位数 {ht[2]:.0f}\n")
    out("| 方向 | 类型 | 让步率% | 效应(百分点) | 95% 区间 | 截断% | 无法判定% | token 中位数 | 跑飞 | 只算没截断的效应 |\n|---|---|---|---|---|---|---|---|---|---|")
    E = []
    for name, d, typ in dirs:
        e, h, eu = effect(T, d, base, items, B=B), health(T, d), effect(T, d, base, items, untrunc=True, B=B)
        flag = h[0] >= FLAG_TRUNC or h[1] >= FLAG_UND
        E.append({"name": name, "type": typ, "th": e[0], "se": e[1], "flag": flag, "th_u": eu[0], "se_u": eu[1]})
        out(f"| {name} | {typ} | {100 * e[4]:.1f} | {P(e[0])} | [{P(e[2])}, {P(e[3])}] | {100 * h[0]:.1f} | {100 * h[1]:.1f} | {h[2]:.0f} | {'是' if flag else ''} | {P(eu[0])}(n={eu[5]}) |")
    tbu = effect(T, target, base, items, untrunc=True, B=B)

    def block(title, es, tgt, fu=False):
        th = [e["th_u" if fu else "th"] for e in es]
        s2 = [e["se_u" if fu else "se"] ** 2 for e in es]
        if len(th) < 3:
            out(f"- {title}:方向不足 3 个,不算"); return None
        S = re_summary(th, s2, tgt, B)
        out(f"- {title}(k={S['k']}):μ = {P(S['mu'])},τ = {100 * S['tau']:.1f}(按方向重抽的区间 [{100 * S['tau_ci'][0]:.1f}, {100 * S['tau_ci'][1]:.1f}];效应的原始标准差 {100 * S['sd_raw']:.1f}),"
            f"新方向的 95% 预测区间 [{P(S['pi'][0])}, {P(S['pi'][1])}];仁慈({P(tgt)})严格大于 {S['n_below']}/{S['k']} 个方向,"
            f"经验百分位 {100 * S['emp_pct']:.1f}%,模型百分位 {100 * S['model_pct']:.1f}%")
        return S

    out("\n**随机效应模型与仁慈的百分位**\n")
    S = block("全部方向(主判据)", E, tb[0])
    if S:
        rank_p = (S["n_ge"] + 1) / (S["k"] + 1)
        out(f"\n**按事先写定的规则判读:{verdict(S)}**(排序检验 p = {S['n_ge'] + 1}/{S['k'] + 1} = {rank_p:.3f})\n")
    for typ in sorted({e["type"] for e in E}):
        block(f"只看「{typ}」", [e for e in E if e["type"] == typ], tb[0])
    types = sorted({e["type"] for e in E})
    if len(types) == 2:
        xa, xb = [[e["th"] for e in E if e["type"] == t] for t in types]
        out(f"- 两类均值之差:{types[0]} {P(mean(xa))} vs {types[1]} {P(mean(xb))},置换检验 p = {perm_test(xa, xb):.4f}")
    out("\n**敏感性分析**\n")
    Sa = block(f"(a) 去掉跑飞的方向({', '.join(e['name'] for e in E if e['flag']) or '无'})", [e for e in E if not e["flag"]], tb[0])
    Sb = block("(b) 只用没截断的回复", [e for e in E if e["th_u"] == e["th_u"]], tbu[0], fu=True)
    if S and Sa and verdict(S) != verdict(Sa):
        out("- **注意:去掉跑飞的方向后判读变了,结论依赖于是否计入跑飞的方向。**")
    return {"E": E, "S": S, "target": tb, "items": items}


if __name__ == "__main__":
    a = sys.argv
    B = int(a[a.index("--boot") + 1]) if "--boot" in a else 2000
    lines = []
    def out(s=""):
        print(s); lines.append(s)
    rows = load(a[1])
    if "--selftest" in a:
        dirs = [(f"rand{k}{n:+d}", (f"rand{k}", n), "正档" if n > 0 else "负档") for k in (1, 2, 3) for n in (6, -6)]
        run(rows, dirs, ("none", 0), ("benevolence_ni", 6), "choice2_reader", B, out, "自测:旧数据 rand1–3 的 ±6 当作 6 个方向(300 题)")
        sys.exit()
    names = sorted({r["dir"] for r in rows if r["dir"][:2] in ("rg", "rc")}, key=lambda s: (s[2:], s[:2]))
    full = [n for n in names if sum(1 for r in rows if r["dir"] == n) == max(sum(1 for r in rows if r["dir"] == m) for m in names)]
    dirs = [(n, (n, 6), "高斯" if n.startswith("rg") else "协方差") for n in full]
    out(f"# 20 个新随机方向:结果(规则见 code/prereg_rand20.md)\n\n已跑完的方向:{len(dirs)} 个" + (f"(未跑完、不计入:{sorted(set(names) - set(full))})" if set(names) - set(full) else ""))
    R = run(rows, dirs, ("none", 0), ("benevolence_ni", 6), "choice2_reader", B, out, "主分析:不调节的读者")
    R2 = run(rows, dirs, ("none", 0), ("benevolence_ni", 6), "choice2", B, out, "敏感性 (d):被调节的模型自己确认")
    if "--old" in a:
        old = [r for r in load(a[a.index("--old") + 1]) if r["id"] in set(R["items"])]
        To, Tn = table(old, "choice2_reader"), table(rows, "choice2_reader")
        out("\n## 和旧数据核对(同 150 题)\n")
        rate = lambda T, d: mean(v[0] for v in T[d].values())
        for d, nm in ((("none", 0), "不调节"), (("benevolence_ni", 6), "新仁慈 +6")):
            flips = sum(Tn[d][k][0] != To[d][k][0] for k in Tn[d])
            out(f"- {nm}:旧 {100 * rate(To, d):.1f}% → 同批重跑 {100 * rate(Tn, d):.1f}%;{len(Tn[d])} 条里标签不同的 {flips} 条({100 * flips / len(Tn[d]):.1f}%)")
        eo = effect(To, ("benevolence_ni", 6), ("none", 0), R["items"], B=B)
        en = R["target"]
        out(f"- 仁慈 +6 的效应:旧 {100 * eo[0]:+.1f},同批重跑 {100 * en[0]:+.1f},相差 {100 * abs(eo[0] - en[0]):.1f} 个百分点"
            + ("。**超过 5 个百分点,按规则先查原因。**" if abs(eo[0] - en[0]) > 0.05 else "(不超过 5,通过)"))
        out("\n**敏感性 (c):加上旧的 rand1–3(旧数据,相对旧基线)**\n")
        E3 = []
        for k in (1, 2, 3):
            e = effect(To, (f"rand{k}", 6), ("none", 0), R["items"], B=B)
            E3.append((e[0], e[1] ** 2))
            out(f"- rand{k} +6(同 150 题):{100 * e[0]:+.1f}")
        th = [e["th"] for e in R["E"]] + [x[0] for x in E3]
        s2 = [e["se"] ** 2 for e in R["E"]] + [x[1] for x in E3]
        S = re_summary(th, s2, en[0], B)
        out(f"- 合计 k={S['k']}:μ = {100 * S['mu']:+.1f},τ = {100 * S['tau']:.1f},预测区间 [{100 * S['pi'][0]:+.1f}, {100 * S['pi'][1]:+.1f}];"
            f"仁慈严格大于 {S['n_below']}/{S['k']},经验百分位 {100 * S['emp_pct']:.1f}%,模型百分位 {100 * S['model_pct']:.1f}% → {verdict(S)}")
        out("\n**只作描述:其他有名字的方向在同 150 题上的旧数据(相对旧基线)**\n")
        for d in sorted({k for k in To if k != ("none", 0) and not k[0].startswith(("rand", "sys:", "zero", "clamp"))}):
            e = effect(To, d, ("none", 0), R["items"], B=200)
            emp = mean(x["th"] < e[0] for x in R["E"])
            out(f"- {d[0]} {d[1]:+d}:{100 * e[0]:+.1f}(大于 {100 * emp:.0f}% 的新随机方向)")
    if "--md" in a:
        open(a[a.index("--md") + 1], "w", encoding="utf-8").write("\n".join(lines) + "\n")
