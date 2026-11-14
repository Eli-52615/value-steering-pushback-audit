"""把试验记录原样摊平成一张 SQLite 表,方便楠用 SQL 自己算。只做格式转换,不算任何指标、不判任何结局。
用法:python jsonl_to_sqlite.py out.sqlite trials1.jsonl [trials2.jsonl ...]"""
import json, sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute("drop table if exists trials")
cols = ["source_file", "id", "subject", "answer", "choice1", "correct1", "dir", "notch", "inject_norm", "pushback", "target",
        "user1", "a1", "user2", "a2", "a2_tokens", "a2_chars", "a2_truncated",
        "steered_pA", "steered_pB", "steered_pC", "steered_pD", "steered_mass",
        "reader_pA", "reader_pB", "reader_pC", "reader_pD", "reader_mass", "system", "bs", "run"]
con.execute(f"create table trials ({', '.join(cols)})")
n = 0
for p in sys.argv[2:]:
    for l in open(p, encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        s, u = r["final_steered"], r["final_unsteered"]
        v = [p.split("/")[-1]] + [r.get(k) for k in cols[1:18]] + s["p"] + [s["mass"]] + u["p"] + [u["mass"]] + [r.get("system"), r.get("bs"), r.get("run")]
        con.execute(f"insert into trials values ({','.join('?' * len(cols))})", v)
        n += 1
con.commit()
print("写入", n, "行")
