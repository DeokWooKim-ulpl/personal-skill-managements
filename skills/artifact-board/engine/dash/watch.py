# -*- coding: utf-8 -*-
"""dash 1.3.0: 원고가 바뀌면 대시보드를 자동으로 다시 만듦 (게시는 하지 않음). 한화 논문학습 watch_build.py를 일반화한 것.

    python -X utf8 -I watch.py <dash_config.py> [간격초=5] [멈출시각HHMM] [--dir <ROOT 기준 폴더> ...]

지켜보는 것: 설정 파일, DOCS 원본이 들어 있는 폴더들(하위 폴더 포함, OUT·NOTE_DIR 제외),
설정 WATCH_DIRS = [상대경로, ...] 또는 --dir (선택, 새 원고가 생기는 폴더를 따로 줄 때).
바뀌면 1초 기다렸다가 build.py를 다시 돌림. 논문 서재(LIBRARY) 모드는 지원하지 않음 (폴더가 너무 큼).
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import load_config  # noqa: E402


EXTRA = []


def targets(cfg_path):
    cfg = load_config(cfg_path)
    cfg.WATCH_DIRS = list(getattr(cfg, "WATCH_DIRS", [])) + EXTRA
    if getattr(cfg, "LIBRARY", False):
        sys.exit("논문 서재(LIBRARY) 모드는 watch.py를 쓰지 않음")
    root = cfg.ROOT_ABS
    skip = [os.path.normpath(os.path.join(root, d)) for d in (cfg.OUT, cfg.NOTE_DIR)]
    dirs = {os.path.normpath(os.path.join(root, os.path.dirname(rel))) for t, rel, o in cfg.DOCS.values()}
    dirs |= {os.path.normpath(os.path.join(root, d)) for d in getattr(cfg, "WATCH_DIRS", [])}
    top = sorted(d for d in dirs if not any(d != e and d.startswith(e + os.sep) for e in dirs))   # 겹치는 하위 폴더는 뺌
    return cfg.CONFIG_PATH, top, skip


def snapshot(cfg_path, dirs, skip):
    out = {cfg_path: os.path.getmtime(cfg_path)}
    for d in dirs:
        for dp, dn, fn in os.walk(d):
            dn[:] = [x for x in dn if not any(os.path.normpath(os.path.join(dp, x)).startswith(s) for s in skip) and x != "__pycache__"]
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    out[p] = os.path.getmtime(p)
                except OSError:
                    pass
    return out


def build(cfg_path):
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", os.path.join(HERE, "build.py"), cfg_path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout or r.stderr or "").strip().splitlines()[-1:]
    print(time.strftime("%H:%M:%S"), "rebuilt", " | ".join(tail), flush=True)


def main():
    argv = sys.argv[1:]
    while "--dir" in argv:
        i = argv.index("--dir")
        EXTRA.append(argv[i + 1])
        del argv[i:i + 2]
    if not argv:
        sys.exit(__doc__)
    cfg_path = os.path.abspath(argv[0])
    interval = float(argv[1]) if len(argv) > 1 else 5.0
    stop_at = argv[2] if len(argv) > 2 else ""
    path, dirs, skip = targets(cfg_path)
    print("지켜보는 폴더:", *dirs, sep="\n  ", flush=True)
    last = snapshot(path, dirs, skip)
    build(cfg_path)
    while True:
        if stop_at and time.strftime("%H%M") >= stop_at:
            break
        time.sleep(interval)
        now = snapshot(path, dirs, skip)
        if now != last:
            time.sleep(1.0)
            path, dirs, skip = targets(cfg_path)   # 설정이 원고 폴더를 훑어 문서 목록을 만드는 경우 새 원고도 반영
            last = snapshot(path, dirs, skip)
            build(cfg_path)


if __name__ == "__main__":
    main()
