# -*- coding: utf-8 -*-
"""dash 엔진을 고친 뒤 이 엔진을 쓰는 대시보드를 한꺼번에 다시 만듦 (게시는 Claude가 URL마다 함).

    python -X utf8 -I rebuild_all.py            PROJECTS.md에서 설정이 dash_config.py인 행을 모두 다시 생성
    python -X utf8 -I rebuild_all.py <글자>     프로젝트 이름에 그 글자가 든 행만

출력: 행마다 이름, URL, 게시할 page(file_path)와 root, 게시 파일 수.
엔진(page.html·JS)만 바뀌었으면 index.html 하나만 같은 URL에 게시하면 됨 (capabilities는 넘기지 않음).
문서·그림도 바뀌었으면 OUT/_publish_files.json 목록을 files로 함께 넘김 (255개씩).
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(HERE, "..", "..", "PROJECTS.md")


def rows():
    out = []
    for ln in open(PROJECTS, encoding="utf-8"):
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        m = re.search(r"`([^`]*dash_config\.py)`", cells[1])
        if not m or not os.path.isfile(m.group(1)):
            continue
        url = re.search(r"https://claude\.ai/artifact/\w+", cells[2])
        out.append((re.sub(r"\*", "", cells[0]), m.group(1), url.group(0) if url else ""))
    return out


def main(flt=""):
    for name, cfg, url in rows():
        if flt and flt not in name:
            continue
        print(f"=== {name}\n    설정 {cfg}\n    URL  {url or '(아직 게시 안 함)'}")
        r = subprocess.run([sys.executable, "-X", "utf8", "-I", os.path.join(HERE, "build.py"), cfg],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = (r.stdout.strip().splitlines() or [""])[-1]
        if r.returncode:
            print("    생성 실패:", (r.stderr.strip().splitlines() or ["?"])[-1])
            continue
        print("    " + last)
        m = re.search(r"→ (.+)$", last)
        if m:
            out = m.group(1).strip()
            pub = os.path.join(out, "_publish_files.json")
            n = len(json.load(open(pub, encoding="utf-8"))) if os.path.isfile(pub) else 0
            print(f"    게시: file_path={os.path.join(out, 'index.html')}  root={out}  (문서·그림 {n}개)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
