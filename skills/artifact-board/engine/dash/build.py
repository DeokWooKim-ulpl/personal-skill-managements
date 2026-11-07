# -*- coding: utf-8 -*-
"""artifact-board 연구 대시보드(dash) 생성기 — 한화 과제 연구 대시보드(2026-11-06)를 일반화한 것.

    python -I build.py <프로젝트의 dash_config.py>

결과 (설정 OUT 폴더):
    index.html            게시할 페이지 (왼쪽 목차 + 읽기 칸 + 문단별 질문·메모)
    docs/<key>.html       문서마다 블록으로 나눈 HTML (페이지가 fetch로 불러옴)
    img/<hash>.webp       문서 그림 (줄여서 webp)
    _publish_files.json   이번에 게시할 파일 목록 (docs + 쓰인 그림)
    <MANIFEST>            노트 동기화용 문서 목록 (게시 안 함)

설정 파일(파이썬)에 둘 것 — SKILL.md "연구 대시보드" 항 참고
    TITLE, SUBTITLE, ROOT(설정 파일 기준 프로젝트 루트), OUT, NOTE_DIR, RULES, ASK_EXAMPLE
    DOCS  = {key: (제목, 원본 md 상대경로, {옵션})}   옵션: section, until_end, area, prefer, drop_rows, dates(표 날짜 D-day)
    VIEWS = [{"group": 이름, "items": [{"id", "title", "tabs": [[key, 탭 이름], ...], "card", "notice", "summary", "schedule", "files", "special"}]}]
    EXTRA_FILES = [(이름표, 상대경로), ...]          (선택) 파일 위치 화면에만 나오는 결과물
    summary(api) -> [{"label","value","sub","alert","date","href"}]  (선택) 첫 화면 숫자 칸. date가 있으면 D-day를 페이지가 계산
    SCHEDULE = {"start","end","tiles":[[이름,날짜]],"marks":[[이름,날짜]]}  (선택) "schedule": True 화면의 기간 막대
    EMBED_DOCS = True                                   (선택) 문서를 index.html 안에도 넣음 (기본 켬)
    NOTE_NAME(rel) -> 파일 이름                          (선택) 노트 사본 이름 (원고 이름이 겹칠 때)
    pre_build(api)                                     (선택) 생성 전에 원고를 갱신하는 일
원본 md는 읽기만 함. 원본이 없어진 문서는 탭에서 빠짐.
"""
import datetime, importlib.util, json, os, re, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blocks import ESC, Images, Renderer, blocks_with_ids, preprocess  # noqa: E402

DASH_VERSION = "1.3.0"   # 1.1.x: 논문 서재(library) 모드 (library.py), 요약·그림 탭, 검색. 1.3.0: 일정·D-day, 문서 내장, 그림 재시도, 전체 점검


def load_config(path):
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location("dash_config", path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    cfg.CONFIG_PATH = path
    cfg.ROOT_ABS = os.path.normpath(os.path.join(os.path.dirname(path), getattr(cfg, "ROOT", ".")))
    cfg.WIN_ROOT = getattr(cfg, "WIN_ROOT", None) or cfg.ROOT_ABS.replace("/", "\\")
    cfg.MANIFEST = getattr(cfg, "MANIFEST", None) or (cfg.OUT.rstrip("/") + "_manifest.json")
    for k, v in (("SUBTITLE", ""), ("RULES", ""), ("ASK_EXAMPLE", ""), ("EXTRA_FILES", []), ("ARTIFACT_URL", ""), ("DOCS", {}), ("VIEWS", [])):
        if not hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


def mtime(root, rel):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(root, rel))).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""


def note_name(cfg, rel):
    """노트 사본 파일 이름. 설정에 NOTE_NAME(rel)이 있으면 그것(이름이 겹치는 원고 폴더용)."""
    if hasattr(cfg, "NOTE_NAME"):
        return cfg.NOTE_NAME(rel)
    return os.path.splitext(os.path.basename(rel))[0] + "__노트.md"


def note_copy(cfg, rel):
    return f"{cfg.NOTE_DIR}/{note_name(cfg, rel)}"


def section_range(blocks, start, until_end=False):
    """start로 시작하는 h2 블록부터 다음 h2 전까지 (until_end면 끝까지)."""
    on, out = False, []
    for b in blocks:
        bid, kind, a, z, raw = b
        if kind == "h" and raw.lstrip().startswith("## "):
            if on and not until_end:
                break
            if raw.strip().startswith(start):
                on = True
        if on:
            out.append(b)
    return out


def build_doc(cfg, images, key):
    title, rel, opt = cfg.DOCS[key]
    p = os.path.join(cfg.ROOT_ABS, rel)
    if not os.path.isfile(p):
        return f'<p class="miss">파일 없음: {ESC(rel)}</p>', 0
    text = preprocess(open(p, encoding="utf-8", errors="replace").read())
    blocks = blocks_with_ids(rel, text)
    if opt.get("section"):
        blocks = section_range(blocks, opt["section"], opt.get("until_end", False))
    r = Renderer(images, os.path.dirname(p), opt.get("area", os.path.dirname(rel)), opt.get("prefer", ""))
    parts = []
    for bid, kind, a, z, raw in blocks:
        if kind == "table" and opt.get("drop_rows"):
            rows = raw.split("\n")
            keep = rows[:2] + [x for x in rows[2:] if not re.search(opt["drop_rows"], x)]
            if len(keep) <= 2:
                continue
            raw = "\n".join(keep)
        parts.append(f'<div class="blk k-{kind}" data-b="{bid}">{r.block(kind, raw)}</div>')
    return "\n".join(parts), len(parts)


def main(config_path, published=False):
    cfg = load_config(config_path)
    if getattr(cfg, "LIBRARY", False):                 # 논문 서재 모드 (library.py)
        import library
        return library.mark_published(cfg) if published else library.build(cfg)
    root, out = cfg.ROOT_ABS, os.path.join(cfg.ROOT_ABS, cfg.OUT)
    api = types.SimpleNamespace(root=root, cfg=cfg, mtime=lambda rel: mtime(root, rel), today=datetime.date.today())
    if hasattr(cfg, "pre_build"):
        try:
            cfg.pre_build(api)
        except Exception as e:
            print("pre_build 건너뜀:", e)
    os.makedirs(os.path.join(out, "docs"), exist_ok=True)
    for k in [k for k, (t, rel, o) in cfg.DOCS.items() if not os.path.isfile(os.path.join(root, rel))]:
        print("원본 없음, 뺌:", k, cfg.DOCS.pop(k)[1])          # 원본이 없어진 문서는 탭에서 뺌
    for g in cfg.VIEWS:
        for it in g["items"]:
            if "tabs" in it:
                it["tabs"] = [t for t in it["tabs"] if t[0] in cfg.DOCS]
            if it.get("card") not in (None, *cfg.DOCS):
                it.pop("card")
        g["items"] = [it for it in g["items"] if it.get("special") or it.get("tabs")]
    images = Images(root, out)
    meta, manifest, embedded = {}, {}, []
    embed = getattr(cfg, "EMBED_DOCS", True)
    for key, (title, rel, opt) in cfg.DOCS.items():
        h, n = build_doc(cfg, images, key)
        with open(os.path.join(out, "docs", key + ".html"), "w", encoding="utf-8") as f:
            f.write(h)
        if embed:   # 1.3.0: 문서를 페이지 안에도 넣음 — 새 판 게시 뒤 열어 둔 화면이 옛 주소의 docs/*.html을 못 찾는 문제를 없앰
            embedded.append(f'<script type="text/plain" id="doc-{key}">' + re.sub(r"</(script)", r"<\\/\1", h, flags=re.I) + "</script>")
        meta[key] = {"title": title, "src": rel, "mtime": mtime(root, rel), "copy": note_copy(cfg, rel), "blocks": n}
        if opt.get("dates"):
            meta[key]["dates"] = True                   # 1.3.0: 표 첫 칸 날짜에 D-day 칩
        manifest[key] = {"src": rel, **opt}
        print(f"{key:14s} {n:4d} 블록  {rel}")
    files = []
    for g in cfg.VIEWS:
        for it in g["items"]:
            for rel in it.get("files", []):
                files.append([it["title"], rel, mtime(root, rel)])
    for lab, rel in cfg.EXTRA_FILES:
        if os.path.exists(os.path.join(root, rel)):
            files.append([lab, rel, mtime(root, rel)])
    summ = []
    if hasattr(cfg, "summary"):
        try:
            summ = cfg.summary(api) or []
        except Exception as e:
            print("summary 건너뜀:", e)
    data = {"built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "winRoot": cfg.WIN_ROOT, "noteDir": cfg.NOTE_DIR,
            "title": cfg.TITLE, "rules": cfg.RULES, "askExample": cfg.ASK_EXAMPLE, "askTier": getattr(cfg, "ASK_TIER", "default"),
            "config": os.path.relpath(cfg.CONFIG_PATH, root).replace("\\", "/"),
            "engine": DASH_VERSION, "schedule": getattr(cfg, "SCHEDULE", None),
            "views": cfg.VIEWS, "docs": meta, "files": files, "summary": summ}
    tpl = open(os.path.join(HERE, "page.html"), encoding="utf-8").read()
    page = (tpl.replace("__PAGE_TITLE__", ESC(getattr(cfg, "PAGE_TITLE", "") or cfg.TITLE)).replace("__TITLE__", ESC(cfg.TITLE)).replace("__SUBTITLE__", ESC(cfg.SUBTITLE))
            .replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("<!--__DOCS__-->", "\n".join(embedded)))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    with open(os.path.join(root, cfg.MANIFEST), "w", encoding="utf-8") as f:
        json.dump({"docs": manifest, "images": images.used}, f, ensure_ascii=False, indent=1)
    pub = ["docs/" + k + ".html" for k in cfg.DOCS] + sorted(images.used)   # 이번에 쓰지 않은 그림은 게시 목록에서 빠짐
    with open(os.path.join(out, "_publish_files.json"), "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False)
    size = os.path.getsize(os.path.join(out, "index.html")) / 1e6
    if size > 12:
        print(f"주의: index.html {size:.1f} MB — 16 MB 한도에 가까움. 설정에 EMBED_DOCS = False 를 검토")
    print(f"dash={DASH_VERSION} 문서 {len(cfg.DOCS)}개, 그림 {len(images.used)}장, 게시 파일 {len(pub)}개, index {size:.1f} MB → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], published="--published" in sys.argv[2:])   # --published: 방금 게시한 파일을 기록 (library 모드)
