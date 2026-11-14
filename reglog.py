"""运行登记:任何一次在模型上的运行,开始时记一条,结束时再记一条(成功/失败都记)。
登记文件是追加写的 JSONL,不改不删。只有开始、没有结束的记录 = 被杀掉或断电。
规划方案 4.8 第 1 条:没有登记的运行,结果不进论文。"""
import atexit, hashlib, json, os, socket, sys, time, traceback
from pathlib import Path

REG = Path(os.environ.get("SPRINT_REGISTRY", "/root/autodl-tmp/sprint/runs/registry.jsonl"))
HERE = Path(__file__).resolve().parent


def _commit():
    f = HERE / ".commit"          # 由 sync.sh 在同步前写入:提交号 + 工作区是否干净
    return f.read_text().strip() if f.exists() else "未知(没有经 sync.sh 同步)"


def _append(rec):
    REG.parent.mkdir(parents=True, exist_ok=True)
    with REG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


class Run:
    def __init__(self, purpose: str, out: str | None = None, note: str = ""):
        self.id = time.strftime("%m%d-%H%M%S") + "-" + Path(sys.argv[0]).stem
        self.out, self.ok, self.t0 = out, False, time.time()
        self.rows0 = self._rows()
        _append({"event": "start", "run": self.id, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "purpose": purpose,
                 "note": note, "argv": sys.argv, "commit": _commit(), "host": socket.gethostname(),
                 "out": out, "rows_before": self.rows0})
        atexit.register(self._end)
        self._hook = sys.excepthook
        sys.excepthook = self._exc
        self.err = None

    def _rows(self):
        return sum(1 for _ in open(self.out, encoding="utf-8")) if self.out and Path(self.out).exists() else 0

    def _exc(self, tp, val, tb):
        self.err = "".join(traceback.format_exception_only(tp, val)).strip()[:300]
        self._hook(tp, val, tb)

    def done(self):
        self.ok = True

    def _end(self):
        _append({"event": "end", "run": self.id, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "status": "完成" if self.ok else ("出错" if self.err else "中断"), "error": self.err,
                 "seconds": round(time.time() - self.t0), "rows_after": self._rows(),
                 "out_sha256_16": _sha(self.out) if self.out and Path(self.out).exists() else None})
