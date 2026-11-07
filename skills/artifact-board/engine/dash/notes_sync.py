# -*- coding: utf-8 -*-
"""artifact-board 연구 대시보드(dash): 질문·답·메모 → 원본 md의 '노트 사본'에 끼워 넣음 (원본은 건드리지 않음).

    python -X utf8 notes_sync.py <프로젝트의 dash_config.py> <threads 덤프 폴더 또는 json> [--sums <summaries 덤프 폴더>] [--backup]

--backup: 받은 덤프(threads·summaries)를 그대로 <설정 BACKUP_DIR, 기본 NOTE_DIR 옆 backup/>/<날짜_시각>.json 에 보관함
  (원본 JSON 백업; 복원은 restore.py). 최근 BACKUP_KEEP_DAYS(기본 30)일치 + 달마다 첫 것은 남기고 나머지는 지움.

threads.json = 대시보드 db 의 threads 컬렉션을 내보낸 것 (Claude가 ArtifactData list 로 받아 저장).
  [ {id, doc, src, block, section, quote, turns:[{q,a,at}], memo, memoAt, createdAt, updatedAt}, ... ]
  또는 {"documents":[{"id":..., "data":{...}}]} 꼴도 받음.
결과: <설정 NOTE_DIR>/<원본이름>__노트.md (원본 전체 + 해당 문단 바로 아래 콜아웃)
      + 00_노트_모음.md (전체 목록). 마지막 줄에 meta/sync 로 쓸 JSON 을 출력함.
논문 서재(LIBRARY) 모드: 블록 ID 는 논문 key 기준이고 원본 경로는 manifest 에서 찾음(파일을 옮겨도 됨).
  사본에서는 `<!-- pdf2md:generated` 표시 줄을 빼서 pdf2md·paper-qa 가 논문으로 세지 않게 함.
  --sums 를 주면 Claude 요약(db summaries)을 <설정 SUM_DIR>/<원본이름>__요약.md 와 00_요약_모음.md 로도 씀.
"""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blocks import blocks_with_ids, preprocess  # noqa: E402
from build import load_config, note_name  # noqa: E402

ROOT = NOTE_DIR = None
MARK_RE = re.compile(r"^<!--\s*pdf2md:generated.*?-->\s*$", re.M | re.S)


def load(path, need=("src", "block")):
    if os.path.isdir(path):   # ArtifactData list out_dir 결과: <dir>/<collection>/<id>.json (각 파일 {id, data, version} 또는 본문)
        d = []
        for dp, dn, fn in os.walk(path):
            for f in fn:
                if f.endswith(".json"):
                    x = json.load(open(os.path.join(dp, f), encoding="utf-8"))
                    d.append(dict(x["data"], id=x.get("id", f[:-5])) if isinstance(x.get("data"), dict) else dict(x, id=x.get("id", f[:-5])))
        return [t for t in d if all(t.get(k) for k in need)]
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict) and "documents" in d:
        d = [dict(x.get("data", {}), id=x.get("id")) for x in d["documents"]]
    elif isinstance(d, dict):
        d = [dict(v, id=k) for k, v in d.items()]
    return [t for t in d if all(t.get(k) for k in need)]


def day(iso):
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def quote_lines(text, depth=1):
    p = "> " * depth
    return [(p + l).rstrip() for l in str(text).replace("\r", "").split("\n")]


def callouts(t):
    out = []
    turns = t.get("turns") or []
    if turns:
        first = turns[0]
        out.append(f"> [!question]+ Q. {first['q'].strip()} ({day(first.get('at', ''))} · 대시보드 Claude)")
        if t.get("quote"):
            out += quote_lines(f"선택한 문장: \"{t['quote'].strip()}\"")
        out.append(">")
        out += quote_lines(first.get("a", ""))
        for u in turns[1:]:
            out.append(">")
            out.append(f"> > [!question]+ Q. {u['q'].strip()} ({day(u.get('at', ''))} · 이어서 물음)")
            out += quote_lines(u.get("a", ""), 2)
    if t.get("memo"):
        if out:
            out.append("")
        out.append(f"> [!tip]+ 내 메모 ({day(t.get('memoAt') or t.get('updatedAt', ''))})")
        if t.get("quote") and not turns:
            out += quote_lines(f"선택한 문장: \"{t['quote'].strip()}\"")
            out.append(">")
        out += quote_lines(t["memo"])
    return out


def strip_mark(raw):
    """사본에서 pdf2md 표시 주석을 안내 줄로 바꿈 (인덱스 도구가 논문으로 세지 않게)."""
    return MARK_RE.sub("<!-- 대시보드 노트 사본 (pdf2md 표시 제거됨) -->", raw)


def load_raw(path, collection):
    """덤프 폴더에서 한 컬렉션의 문서를 {id, version, data} 그대로 (백업용)."""
    out = []
    if not path:
        return out
    if os.path.isdir(path):
        if os.path.isdir(os.path.join(path, collection)):     # ArtifactData list out_dir 전체를 준 경우 → 그 컬렉션 폴더만
            path = os.path.join(path, collection)
        for dp, dn, fn in os.walk(path):
            for f in sorted(fn):
                if not f.endswith(".json"):
                    continue
                x = json.load(open(os.path.join(dp, f), encoding="utf-8"))
                if isinstance(x.get("data"), dict):
                    out.append({"id": x.get("id", f[:-5]), "version": x.get("version"), "data": x["data"]})
                else:
                    out.append({"id": x.get("id", f[:-5]), "version": None, "data": x})
    else:
        for t in load(path, ()):
            out.append({"id": t.get("id"), "version": None, "data": {k: v for k, v in t.items() if k != "id"}})
    return out


def backup_dir(cfg):
    d = getattr(cfg, "BACKUP_DIR", None)
    return os.path.normpath(os.path.join(cfg.ROOT_ABS, d)) if d else os.path.join(os.path.dirname(os.path.normpath(os.path.join(cfg.ROOT_ABS, cfg.NOTE_DIR))), "backup")


def write_backup(cfg, threads_path, sums_path, now):
    """원본 JSON 백업 한 파일 + 오래된 것 정리. 돌려주는 값: (파일 경로, 문서 수)."""
    bd = backup_dir(cfg)
    os.makedirs(bd, exist_ok=True)
    data = {"artifact": getattr(cfg, "ARTIFACT_URL", ""), "config": os.path.basename(cfg.CONFIG_PATH), "at": now.strftime("%Y-%m-%d %H:%M"),
            "atIso": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "collections": {"threads": load_raw(threads_path, "threads"), "summaries": load_raw(sums_path, "summaries"),
                            "reqs": load_raw(sums_path, "reqs")}}
    n = sum(len(v) for v in data["collections"].values())
    name = now.strftime("%Y-%m-%d_%H%M") + ".json"
    with open(os.path.join(bd, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    # 정리: 최근 KEEP 일치 + 달마다 첫 파일은 남김
    keep_days = int(getattr(cfg, "BACKUP_KEEP_DAYS", 30))
    files = sorted(f for f in os.listdir(bd) if re.match(r"^\d{4}-\d{2}-\d{2}_\d{4}\.json$", f))
    first_of_month, removed = set(), 0
    for f in files:
        ym = f[:7]
        if ym not in first_of_month:
            first_of_month.add(ym)
            continue
        age = (now.date() - datetime.date.fromisoformat(f[:10])).days
        if age > keep_days:
            os.remove(os.path.join(bd, f))
            removed += 1
    print(f"백업: {os.path.join(bd, name)} (문서 {n}건, 오래된 백업 {removed}개 지움, 보관 {len(files) - removed}개)")
    return os.path.join(bd, name), n


def main(config_path, path, sums_path=None, backup=False):
    global ROOT, NOTE_DIR
    cfg = load_config(config_path)
    ROOT, NOTE_DIR = cfg.ROOT_ABS, os.path.normpath(os.path.join(cfg.ROOT_ABS, cfg.NOTE_DIR))
    if backup:
        write_backup(cfg, path, sums_path, datetime.datetime.now())
    library = bool(getattr(cfg, "LIBRARY", False))
    manifest = {}
    if library:
        try:
            manifest = json.load(open(os.path.normpath(os.path.join(ROOT, cfg.MANIFEST)), encoding="utf-8")).get("docs", {})
        except (OSError, ValueError):
            print("manifest 없음 — 먼저 build.py 를 돌릴 것")
    threads = load(path, ("doc", "block") if library else ("src", "block"))
    os.makedirs(NOTE_DIR, exist_ok=True)
    sum_threads = [t for t in threads if str(t["block"]).startswith("sum:")]   # Claude 요약 문단에 단 노트 → 요약 md 로
    threads = [t for t in threads if not str(t["block"]).startswith("sum:")]
    by_src = {}
    for t in threads:
        if library:
            key = t["doc"]
            src = manifest.get(key, {}).get("src") or t.get("src")
            if not src:
                continue
            t["_idkey"] = key
            t["src"] = src
        by_src.setdefault(t["src"], []).append(t)
    now = datetime.datetime.now()
    written = []
    for src, ts in sorted(by_src.items()):
        p = os.path.join(ROOT, src)
        if not os.path.isfile(p):
            print("원본 없음:", src)
            continue
        raw = open(p, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
        lines = raw.split("\n")
        idkey = ts[0].get("_idkey") or src
        blocks = blocks_with_ids(idkey, preprocess(raw))
        end = {bid: z for bid, kind, a, z, r in blocks}
        first_h1 = next((z for bid, kind, a, z, r in blocks if kind == "h"), -1)
        ins, lost = {}, []
        for t in sorted(ts, key=lambda x: x.get("createdAt", "")):
            b = t["block"]
            at = first_h1 if b.startswith("_doc:") else end.get(b)
            if at is None:
                lost.append(t)
            else:
                ins.setdefault(at, []).append(t)
        out = []
        fm_end = -1
        if lines and lines[0].strip() == "---":
            fm_end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
        head = ["", f"> [!info] 대시보드 노트 사본 — 원본 `{src}` 에 대시보드에서 단 질문·답·메모를 해당 문단 아래에 넣은 것. "
                    f"원본은 고치지 않음. 이 파일은 동기화 때마다 새로 만들어지므로 여기에 직접 쓰지 말 것. ({now:%Y-%m-%d %H:%M})", ""]
        if fm_end < 0:
            out += head
        for i, ln in enumerate(lines):
            out.append(ln)
            if i == fm_end:
                out += head
            for t in ins.get(i, []):
                out += [""] + callouts(t) + [""]
        if lost:
            out += ["", "## 대시보드 노트 — 원본 문단을 다시 찾지 못한 것", "",
                    "원본 문장이 바뀌어 자리를 잃은 노트임. 대시보드에서 보던 위치(절)를 함께 적음.", ""]
            for t in lost:
                out += [f"**위치: {t.get('section') or '(문서 처음)'}**", ""] + callouts(t) + [""]
        name = note_name(cfg, src)
        text = "\n".join(out)
        if library:
            text = strip_mark(text)
        with open(os.path.join(NOTE_DIR, name), "w", encoding="utf-8") as f:
            f.write(text)
        written.append((src, name, len(ts), len(lost)))
        print(f"{name}: 노트 {len(ts)}건 (자리 못 찾음 {len(lost)})")
    # 전체 모음
    idx = [f"# 대시보드 질문·메모 모음 ({now:%Y-%m-%d %H:%M} 동기화)", "",
           f"총 {len(threads)}건. 문서별 사본은 같은 폴더의 `*__노트.md` (본문 해당 문단 바로 아래에 들어 있음).", ""]
    for src, ts in sorted(by_src.items()):
        idx += [f"## {ts[0].get('docTitle') or os.path.basename(src)}", "", f"원본 `{src}` → 사본 `{note_name(cfg, src)}`", ""]
        for t in sorted(ts, key=lambda x: x.get("updatedAt", ""), reverse=True):
            idx += [f"### {t.get('section') or '(문서 전체)'} · {day(t.get('updatedAt', ''))}", ""] + callouts(t) + [""]
    with open(os.path.join(NOTE_DIR, "00_노트_모음.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    meta = {"at": now.strftime("%m-%d %H:%M"), "atIso": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "count": len(threads) + len(sum_threads), "files": len(written)}
    if sums_path:
        meta["sums"] = write_sums(cfg, manifest, sums_path, now, sum_threads)
    elif sum_threads:
        print(f"요약 문단 노트 {len(sum_threads)}건은 --sums 가 있어야 요약 md 에 들어감")
    print("META " + json.dumps(meta, ensure_ascii=False))


def sum_block_id(chunk):
    """page.html 의 h32: djb2 over UTF-16 code units, base36. 'sum:' 접두."""
    h = 5381
    b = chunk.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h = ((h * 33) ^ (b[i] | (b[i + 1] << 8))) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while h:
        h, r = divmod(h, 36)
        out = digits[r] + out
    return "sum:" + (out or "0")


def sum_chunks(text):
    text = re.sub(r"^\s*그림\s*[:：].*$", "", str(text or "").replace("\r", ""), count=1, flags=re.M)
    out = []
    for c in [c.strip() for c in re.split(r"\n{2,}", text) if c.strip()]:
        i = c.find("\n")                                  # page.html sumChunks 와 같은 규칙: "## 제목\n본문" 은 둘로
        if re.match(r"^#{1,4}\s", c) and i > 0:
            out += [c[:i].strip(), c[i + 1:].strip()]
        else:
            out.append(c)
    return [c for c in out if c]


FIGREF_RE = re.compile(r"\[\[\s*(fig(?:ure)?|tab(?:le)?)\.?\s*([A-Za-z0-9][A-Za-z0-9\-]*)\s*\]\]", re.I)


def fig_label(kind, num):
    return ("Fig " if kind.lower().startswith("f") else "Tab ") + num


def inline_figs(text):
    return [fig_label(m.group(1), m.group(2)) for m in FIGREF_RE.finditer(text)]


def load_fig_files(cfg):
    """_figures/_index.jsonl → {(doc_id, 'Fig 1'): (파일 이름, 캡션)}"""
    p = os.path.join(cfg.ROOT_ABS, getattr(cfg, "FIG_INDEX", "_figures/_index.jsonl"))
    out = {}
    if not os.path.isfile(p):
        return out
    for ln in open(p, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") in ("FIG", "TAB") and d.get("file"):
            label = ("Fig " if d["type"] == "FIG" else "Tab ") + str(d.get("label") or "")
            out[(d.get("doc_id"), label.strip())] = (d["file"], str(d.get("caption") or ""))
    return out


def split_fig_notes(text):
    """'## 그림 설명' 절을 떼어 (본문, {라벨: 설명}) — page.html splitFigNotes 와 같은 규칙."""
    s = str(text or "").replace("\r", "")
    m = re.search(r"^##\s*그림\s*설명.*$", s, re.M)
    if not m:
        return s, {}
    main, notes = s[:m.start()], {}
    for piece in re.split(r"^###\s*", s[m.end():], flags=re.M):
        head, _, body = piece.partition("\n")
        f = FIGREF_RE.search(head)
        if f and body.strip():
            notes[fig_label(f.group(1), f.group(2))] = body.strip()
    return main, notes


def fig_md(fig_index, key, label):
    f = fig_index.get((key, label))
    if not f:
        return []
    cap = re.sub(r"\s+", " ", f[1]).strip()
    return [f"![[{f[0]}]]", f"*{label}. {cap[:300]}*" if cap else f"*{label}*", ""]


def write_sums(cfg, manifest, sums_path, now, sum_threads=()):
    """Claude 요약(db summaries) → SUM_DIR/<원본이름>__요약.md (요약 문단에 단 노트는 그 문단 아래) + 00_요약_모음.md"""
    sum_dir = os.path.normpath(os.path.join(cfg.ROOT_ABS, getattr(cfg, "SUM_DIR", cfg.NOTE_DIR)))
    os.makedirs(sum_dir, exist_ok=True)
    sm_dir = os.path.join(sums_path, "summaries") if os.path.isdir(sums_path) and os.path.isdir(os.path.join(sums_path, "summaries")) else sums_path
    sums = load(sm_dir, ("key", "text"))
    rq_dir = os.path.join(sums_path, "reqs") if os.path.isdir(sums_path) else ""
    reqs = load(rq_dir, ("key", "text")) if rq_dir and os.path.isdir(rq_dir) else []   # 추가 요청(db reqs) — 같은 덤프 폴더의 reqs/
    fig_index = load_fig_files(cfg)
    notes_by_key, reqs_by_key = {}, {}
    for t in sum_threads:
        notes_by_key.setdefault(t["doc"], []).append(t)
    for r in reqs:
        reqs_by_key.setdefault(r["key"], []).append(r)
    by_key = {s["key"]: s for s in sums}
    keys = sorted(set(by_key) | set(reqs_by_key), key=lambda k: ((by_key.get(k) or reqs_by_key[k][0]).get("year", ""), (by_key.get(k) or reqs_by_key[k][0]).get("title", "")))
    idx = [f"# Claude 요약 모음 ({now:%Y-%m-%d %H:%M} 동기화)", "", f"총 {len(sums)}편 (추가 요청 {len(reqs)}건). 논문별 파일은 같은 폴더의 `*__요약.md`.", ""]
    placed = 0
    for key in keys:
        s = by_key.get(key)
        rlist = sorted(reqs_by_key.get(key, []), key=lambda x: x.get("at", ""))
        meta_src = s or rlist[0]
        src = manifest.get(key, {}).get("src") or meta_src.get("src") or ""
        stem = os.path.splitext(os.path.basename(src))[0] if src else key
        name = f"{stem}__요약.md"
        notes = sorted(notes_by_key.pop(key, []), key=lambda x: x.get("createdAt", ""))
        title = meta_src.get("title", "")
        body = ["---", f'title: "{title.replace(chr(34), "")}"', f"year: {meta_src.get('year', '')}", f"source: \"{src}\"",
                f"summary_by: 대시보드 Claude", f"summary_at: {day((s or {}).get('at', ''))}", f"requests: {len(rlist)}", "---", "",
                f"# {title or stem} — Claude 핵심 요약", "",
                f"> [!info] 원본 `{src}` 의 초록·결론·절 핵심·그림 캡션을 보고 만든 한글 요약(과 추가 요청의 답). 동기화 때마다 새로 쓰므로 여기에 직접 쓰지 말 것 (대시보드에서 고칠 것).", ""]
        lost = list(notes)

        def put_notes(bid):
            nonlocal placed
            for t in [t for t in notes if t["block"] == bid]:
                body.extend(callouts(t) + [""])
                lost.remove(t)
                placed += 1

        def put_text(text, figs_all, shown):   # 요약·요청 답 공통: 문단 + 그림 + 그림 설명 + 그 자리 노트
            main, fig_notes = split_fig_notes(text)

            def put_fig(l):   # 그림 (Obsidian 링크, 볼트 안 _figures/) + 한글 캡션·보는 법 + 거기에 단 노트
                body.extend(fig_md(fig_index, key, l) or [f"*{l} (원본 md 의 같은 번호 그림)*", ""])
                if l in fig_notes:
                    body.extend(["> [!abstract]+ " + l + " 설명"] + quote_lines(fig_notes[l]) + [""])
                    put_notes(sum_block_id(re.sub(r"\s+", " ", fig_notes[l]).strip()))

            for chunk in sum_chunks(main):
                bid = sum_block_id(re.sub(r"\s+", " ", chunk).strip())      # ID 는 [[Fig n]] 표시가 든 원문 기준
                labels = [l for l in inline_figs(chunk) if l not in shown and not shown.add(l)]
                body.append(FIGREF_RE.sub(lambda m: f"**[{fig_label(m.group(1), m.group(2))}]**", chunk))
                body.append("")
                for l in labels:
                    put_fig(l)
                put_notes(bid)
            rest = [l for l in (figs_all or []) if l not in shown]
            if rest:
                body.extend(["", "**그 밖에 보면 좋은 그림**", ""])
                for l in rest:
                    put_fig(l)

        if s:
            put_text(s["text"], s.get("figs"), set())
        else:
            body += ["*(핵심 요약은 아직 안 만듦 — 아래는 추가 요청의 답)*", ""]
        if rlist:
            body += ["", "## 추가 요청", ""]
            for r in rlist:
                body += [f"### 요청: {r.get('q', '').strip()} ({day(r.get('at', ''))}{' · 전체 개요로 답함' if r.get('mode') == 'overview' else ''})", ""]
                put_text(r["text"], r.get("figs"), set())
        if lost:
            body += ["", "## 자리를 잃은 노트 (요약이 바뀌어 문단을 찾지 못함)", ""]
            for t in lost:
                body += callouts(t) + [""]
        with open(os.path.join(sum_dir, name), "w", encoding="utf-8") as f:
            f.write("\n".join(body))
        one = re.search(r"## 한 줄 요약\s*\n(.*?)(?=\n## |\Z)", s["text"], re.S) if s else None
        idx += [f"## {meta_src.get('year', '')}, {title or stem}", "", f"원본 `{src}` → `{name}`" + (f" · 추가 요청 {len(rlist)}건" if rlist else ""), "",
                (one.group(1).strip() if one else (s["text"][:300].strip() if s else "(핵심 요약 없음)")), ""]
    for key, ts in notes_by_key.items():   # 요약이 지워진 논문의 노트
        idx += [f"## (요약 없음) {ts[0].get('docTitle') or key}", ""]
        for t in ts:
            idx += callouts(t) + [""]
    with open(os.path.join(sum_dir, "00_요약_모음.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    print(f"요약 md {len(keys)}편 (요약 {len(sums)}, 추가 요청 {len(reqs)}건, 요약 문단 노트 {len(sum_threads)}건, 자리 찾음 {placed}) → {sum_dir}")
    return len(sums)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sp = sys.argv[sys.argv.index("--sums") + 1] if "--sums" in sys.argv else None
    main(sys.argv[1], sys.argv[2], sp, backup="--backup" in sys.argv)
