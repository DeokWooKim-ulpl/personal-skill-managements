# -*- coding: utf-8 -*-
"""dash 1.3.0: 지난 게시 이후 바뀐 파일 목록 (LLM 없이). 프로젝트A 논문 학습 대시보드의 _작업/publish_diff.py를 일반화한 것.

    python -X utf8 -I publish_diff.py <dash_config.py>           바뀐 파일을 _changed.json에 쓰고 "changed N (index …)" / "unchanged" 출력
    python -X utf8 -I publish_diff.py <dash_config.py> --mark    게시를 마친 뒤 현재 상태를 기록
    선택: --state <파일> --changed <파일>  (기본: OUT/_published_state.json, OUT/_changed.json)

대상은 OUT의 index.html + _publish_files.json의 파일. index.html은 생성 시각("built")을 빼고 비교함.
게시: index.html이 바뀌었으면 file_path=OUT/index.html, 바뀐 파일은 _changed.json 목록을 files로 (root=OUT, 255개씩).
논문 서재(LIBRARY) 모드는 build.py <설정> --published 를 씀.
"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import load_config  # noqa: E402


def arg(name, default):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg = load_config(sys.argv[1])
    if getattr(cfg, "LIBRARY", False):
        sys.exit("논문 서재(LIBRARY) 모드는 build.py <설정> --published 로 게시 기록을 남김")
    out = os.path.join(cfg.ROOT_ABS, cfg.OUT)
    state = arg("--state", os.path.join(out, "_published_state.json"))
    changed = arg("--changed", os.path.join(out, "_changed.json"))

    def digest(rel):
        b = open(os.path.join(out, rel), "rb").read()
        if rel == "index.html":
            b = re.sub(rb'"built":\s*"[^"]*"', b'"built":""', b)
        return hashlib.sha1(b).hexdigest()

    files = ["index.html"] + json.load(open(os.path.join(out, "_publish_files.json"), encoding="utf-8"))
    cur = {f: digest(f) for f in files if os.path.isfile(os.path.join(out, f))}
    if "--mark" in sys.argv:
        json.dump(cur, open(state, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"marked {len(cur)}")
        return
    old = json.load(open(state, encoding="utf-8")) if os.path.exists(state) else {}
    ch = [f for f, h in cur.items() if old.get(f) != h and f != "index.html"]
    idx = old.get("index.html") != cur.get("index.html")
    json.dump(ch, open(changed, "w", encoding="utf-8"), ensure_ascii=False)
    print(("changed %d (index %s)" % (len(ch), "changed" if idx else "same")) if (ch or idx) else "unchanged")


if __name__ == "__main__":
    main()
