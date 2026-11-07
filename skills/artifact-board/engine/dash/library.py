# -*- coding: utf-8 -*-
"""artifact-board 연구 대시보드(dash) — 논문 서재(library) 모드 (2026-11-06).

설정 파일에 `LIBRARY = True` 가 있으면 build.py 가 이 모듈로 넘어옴.
DOCS 를 손으로 적지 않고 ROOT 아래를 훑어 논문 md 를 모두 고른 뒤, 논문마다
    docs/<key>.html   = <section data-part="legacy">(📑 기존 정리본)</section>
                        <section data-part="body">(📖 원문 전체 또는 문서 전체)</section>
                        <script type="application/json" data-part="brief">요약용 발췌·그림 목록</script>
를 만듦. 그림은 webp data URI 로 문서 안에 넣음 (아티팩트 파일 수 한도 511개 때문).
    search/full.json  = 본문 역색인 (단어 → 논문 번호)
    _state.json       = 문서별 md 해시 (안 바뀐 문서는 다시 만들지 않음), 게시 기록
    _publish_files.json / _publish_changed.json = 전체 / 아직 게시 안 된 파일 목록

설정 키 (LIBRARY 모드): TITLE, SUBTITLE, ROOT, OUT, NOTE_DIR, SUM_DIR, MANIFEST, RULES, ASK_EXAMPLE, ARTIFACT_URL,
    ONLY_PDF2MD(False: 모든 md), EXCLUDE_DIRS, EXCLUDE_PREFIXES, FIG_INDEX(_figures/_index.jsonl 상대경로),
    IMG_MAX_W(900), IMG_Q(70), BUNDLE_OVER(480: 논문 수가 이보다 많으면 폴더별 묶음 파일), summary(api) 선택.
원본 md 와 _figures 는 읽기만 함.
"""
import base64, datetime, hashlib, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blocks import ESC, Images, Renderer, blocks_with_ids, preprocess, IMG_RE  # noqa: E402

DEFAULT_EXCLUDE = {"_figures", "_to_delete", "_legacy", "__pycache__", ".obsidian", ".trash", ".git", "_ai_queue", "node_modules"}
DEFAULT_PREFIXES = ("_tools", "_삭제대기", "_paper-dash")
MARK = "<!-- pdf2md:generated"
FIGNAME_RE = re.compile(r"__(Fig|Tab|Eq)([A-Za-z0-9\-]*)_p(\d+)\.(png|jpg|jpeg|webp)$", re.I)
KEY_RE = re.compile(r"[^A-Za-z0-9_-]")
DOC_VERSION = "2"        # 문서 HTML 을 만드는 규칙이 바뀔 때만 올림 (올리면 모든 문서를 다시 만들어 다시 게시해야 함). 2: 절별 본문(sections)


# ------------------------------------------------------------------ YAML 머리말 (간단 파서)
def parse_yaml(text):
    m = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    d, key = {}, None
    for ln in m.group(1).split("\n"):
        if not ln.strip():
            continue
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", ln)
        if mm:
            key, v = mm.group(1), mm.group(2).strip()
            if v.startswith(("'", '"')) and v.endswith(v[0]) and len(v) >= 2:
                v = v[1:-1]
            d[key] = [] if v == "" else v
        elif key and re.match(r"^\s+-\s+", ln):
            if not isinstance(d.get(key), list):
                d[key] = []
            d[key].append(re.sub(r"^\s+-\s+", "", ln).strip().strip("'\""))
    return d


# ------------------------------------------------------------------ 폴더 훑기
def natkey(name):
    """사람이 읽는 순서: "1_…, 2_…, 10_…" (숫자는 수로, 글자는 대소문자 무시). 폴더 트리·논문 순서에 씀."""
    return [(0, int(t)) if t.isdigit() else (1, t.lower()) for t in re.split(r"(\d+)", name)]


def scan(cfg):
    root = cfg.ROOT_ABS
    ex = {x.lower() for x in getattr(cfg, "EXCLUDE_DIRS", DEFAULT_EXCLUDE)}
    pre = tuple(getattr(cfg, "EXCLUDE_PREFIXES", DEFAULT_PREFIXES))
    only = getattr(cfg, "ONLY_PDF2MD", False)
    out, keys = [], {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted((d for d in dn if d.lower() not in ex and not d.startswith(pre)), key=natkey)
        for f in sorted(fn, key=natkey):
            if not f.lower().endswith(".md"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            is_p2m = MARK in text[:6000]
            if only and not is_p2m:
                continue
            y = parse_yaml(text)
            if not is_p2m and not y.get("title") and not re.match(r"^\d{4}, ", f):
                continue                                   # 논문이 아닌 메모 md 는 뺌
            stem = f[:-3]
            key = y.get("doc_id") if isinstance(y.get("doc_id"), str) and y.get("doc_id") else "P" + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8]
            key = KEY_RE.sub("", key)
            if key in keys:
                n = 2
                while f"{key}-{n}" in keys:
                    n += 1
                key = f"{key}-{n}"
            keys[key] = rel
            ym = re.match(r"^(\d{4}), (.+)$", stem)
            title = y.get("title") if isinstance(y.get("title"), str) and y.get("title") else (ym.group(2) if ym else stem)
            year = str(y.get("year") or (ym.group(1) if ym else ""))[:4]
            tags = y.get("tags") if isinstance(y.get("tags"), list) else ([y["tags"]] if isinstance(y.get("tags"), str) else [])
            st = os.stat(p)
            out.append({
                "k": key, "rel": rel, "folder": os.path.dirname(rel), "t": title, "y": year,
                "a": y.get("first_author") if isinstance(y.get("first_author"), str) else "",
                "j": y.get("journal") if isinstance(y.get("journal"), str) else "",
                "doi": y.get("doi") if isinstance(y.get("doi"), str) else "",
                "tags": [str(t).split("/")[-1] for t in tags],
                "pdf": y.get("source_pdf") if isinstance(y.get("source_pdf"), str) else "",
                "p2m": is_p2m, "size": st.st_size,
                "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "st": {"tr": str(y.get("status_translation") or ""), "sum": str(y.get("status_summary") or ""),
                       "fig": str(y.get("status_figures") or ""), "text": str(y.get("status_text") or "")},
                "_text": text,
            })
    return out


# ------------------------------------------------------------------ 그림을 data URI 로
class InlineImages(Images):
    """webp 로 줄인 그림을 data URI 로 돌려줌. 변환 결과는 OUT/_cache 에 두어 다시 만들지 않음."""

    def __init__(self, root, out_dir, max_w=900, q=70):
        super().__init__(root, out_dir, max_w, q)
        self.cache = os.path.join(out_dir, "_cache")
        os.makedirs(self.cache, exist_ok=True)
        self.bytes = 0

    def publish(self, path):
        from PIL import Image
        st = os.stat(path)
        key = hashlib.sha1(f"{os.path.basename(path)}|{st.st_size}|{int(st.st_mtime)}|{self.max_w}|{self.q}".encode("utf-8")).hexdigest()[:16]
        cp = os.path.join(self.cache, key + ".webp")
        if not os.path.exists(cp):
            im = Image.open(path)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            if im.width > self.max_w:
                im = im.resize((self.max_w, round(im.height * self.max_w / im.width)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=self.q, method=4)
            with open(cp, "wb") as f:
                f.write(buf.getvalue())
        data = open(cp, "rb").read()
        self.bytes += len(data)
        self.used[os.path.relpath(path, self.root).replace("\\", "/")] = len(data)
        return "data:image/webp;base64," + base64.b64encode(data).decode("ascii")


class PaperRenderer(Renderer):
    """그림 파일 이름(…__Fig1_p002.png)에서 종류·번호를 읽어 figure 에 data-fig 를 붙이고, 수식 그림은 class=eq."""

    def __init__(self, images, base_dir, area):
        super().__init__(images, base_dir, area, "")
        self.figs = []

    def _img(self, alt, url):
        h = super()._img(alt, url)
        m = FIGNAME_RE.search(url.strip())
        if not m or not h.startswith("<figure"):
            return h
        kind, num, page = m.group(1).title(), m.group(2), m.group(3)
        if kind == "Eq":
            return h.replace("<figure>", '<figure class="eq">', 1)
        label = f"{kind} {num}" if num else kind
        self.figs.append({"label": label, "kind": kind, "page": int(page), "cap": ""})
        return h.replace("<figure>", f'<figure data-fig="{ESC(label)}">', 1)


# ------------------------------------------------------------------ 문서 한 편
H2_LEGACY = "📑"
H2_BODY = "📖"


def split_parts(blocks):
    """(머리, 기존 정리본, 원문) 블록 묶음. 📑/📖 표식이 없으면 전부 원문."""
    il = ib = None
    for i, (bid, kind, a, z, raw) in enumerate(blocks):
        if kind == "h" and raw.lstrip().startswith("## "):
            if il is None and H2_LEGACY in raw:
                il = i
            elif ib is None and H2_BODY in raw:
                ib = i
    if il is None and ib is None:
        return [], [], blocks
    if il is None:
        return blocks[:ib], [], blocks[ib:]
    if ib is None:
        return blocks[:il], blocks[il:], []
    if il < ib:
        return blocks[:il], blocks[il:ib], blocks[ib:]
    return blocks[:ib], blocks[il:], blocks[ib:il]


def text_of(raw):
    s = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    s = IMG_RE.sub(" ", s)
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"[*_`#|]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def brief_of(paper, head, legacy, body, figs, fig_index):
    """요약 프롬프트에 쓸 발췌: 초록·결론·기존 정리본의 요약·그림 캡션·절 제목."""
    def para_text(bl):
        return [text_of(r) for bid, k, a, z, r in bl if k in ("p", "list", "quote") and "(번역 필요)" not in r]

    # 초록: 원문 첫 h3 전까지의 문단 중 긴 것 2개 (+ 바로 뒤 번역)
    first_h3 = next((i for i, b in enumerate(body) if b[1] == "h" and re.match(r"^\s*#{3,}\s", b[4])), len(body))
    cand = []
    for i, (bid, k, a, z, r) in enumerate(body[1:first_h3], 1):
        if k == "p" and len(r) > 200:
            tr = body[i + 1][4] if i + 1 < len(body) and body[i + 1][1] == "quote" and "(번역 필요)" not in body[i + 1][4] else ""
            cand.append((len(r), text_of(r), text_of(tr)))
    cand.sort(reverse=True)
    abstract = "\n".join(c[1] + ("\n(번역) " + c[2] if c[2] else "") for c in cand[:2])
    # 절 제목
    heads = [text_of(r) for bid, k, a, z, r in body if k == "h" and re.match(r"^\s*#{3}\s", r)]
    # 결론: conclusion/summary/결론 제목부터 같은 급 다음 제목 전까지
    concl = ""
    for i, (bid, k, a, z, r) in enumerate(body):
        if k == "h" and re.search(r"conclu|summary and|^\s*#+\s*summary|결론|요약", r, re.I):
            lv = len(re.match(r"^\s*(#+)", r).group(1))
            j = i + 1
            while j < len(body) and not (body[j][1] == "h" and len(re.match(r"^\s*(#+)", body[j][4]).group(1)) <= lv):
                j += 1
            concl = "\n".join(para_text(body[i + 1:j]))
            break
    # 기존 정리본의 요약 부분: 요약/Summary/핵심 제목 아래 (번역·전수 추출 제목이 나오면 멈춤)
    kp, on = [], False
    for bid, k, a, z, r in legacy:
        if k == "h":
            if re.search(r"번역|Translation|전수|Verbatim|Extraction|원문", r):
                on = False
            elif re.search(r"요약|Summary|핵심|정리|해설", r):
                on = True
            continue
        if on and k in ("p", "list", "quote", "table"):
            kp.append(text_of(r))
    keypoints = "\n".join(kp)
    # 그림 캡션: md 의 그림 다음 굵은 문단 또는 _figures 인덱스
    caps = {}
    for i, (bid, k, a, z, r) in enumerate(body):
        m = IMG_RE.search(r) if k == "img" else None
        fm = FIGNAME_RE.search(m.group(2)) if m else None
        if fm and fm.group(1).lower() != "eq":
            label = f"{fm.group(1).title()} {fm.group(2)}"
            for j in range(i + 1, min(i + 3, len(body))):
                if body[j][1] == "p" and re.match(r"^\s*\**\s*(Fig|Table|TABLE|FIG)", body[j][4]):
                    caps[label] = text_of(body[j][4])[:400]
                    break
    for f in figs:
        f["cap"] = caps.get(f["label"]) or fig_index.get((paper["k"], f["label"]), "")[:400]
    return {
        "title": paper["t"], "year": paper["y"], "author": paper["a"], "journal": paper["j"],
        "abstract": abstract[:5000], "headings": heads[:40], "conclusion": concl[:4000], "keypoints": keypoints[:9000],
        "figs": [{"label": f["label"], "cap": f["cap"]} for f in figs][:60],
    }


def load_fig_index(cfg):
    rel = getattr(cfg, "FIG_INDEX", "_figures/_index.jsonl")
    p = os.path.join(cfg.ROOT_ABS, rel)
    idx = {}
    if not os.path.isfile(p):
        return idx
    for ln in open(p, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") in ("FIG", "TAB") and d.get("caption"):
            label = f"{'Fig' if d['type'] == 'FIG' else 'Tab'} {d.get('label') or ''}".strip()
            idx[(d.get("doc_id"), label)] = str(d["caption"])
    return idx


def render_blocks(r, blocks):
    return "\n".join(f'<div class="blk k-{kind}" data-b="{bid}">{r.block(kind, raw)}</div>' for bid, kind, a, z, raw in blocks)


def sections_of(head, legacy, body):
    """절별 본문 글자 [{h: 제목, l: 제목 급, t: 글}] — 요약 탭의 '요청'(절 요약·목차 정리)에 보낼 자료.
    원문(📖)이 있으면 원문 절, 없으면 기존 정리본. 번역 인용·그림은 뺌(영문 원문으로 충분, 용량 절반)."""
    src = body if body else (head + legacy)
    out, cur = [], {"h": "(머리말)", "l": 0, "t": []}
    for bid, k, a, z, raw in src:
        if k == "h":
            m = re.match(r"^\s*(#+)\s+(.*)$", raw)
            if cur["t"] or cur["l"]:
                out.append(cur)
            cur = {"h": text_of(m.group(2))[:200], "l": len(m.group(1)), "t": []}
        elif k in ("p", "list", "table"):
            t = text_of(raw)
            if t and "(번역 필요)" not in raw:
                cur["t"].append(t)
    out.append(cur)
    return [{"h": s["h"], "l": s["l"], "t": "\n".join(s["t"])} for s in out if s["t"] or s["l"]]


def build_paper(cfg, images, paper, fig_index):
    rel, text = paper["rel"], paper.pop("_text")
    blocks = blocks_with_ids(paper["k"], preprocess(text))        # ID 기준 = key (파일을 옮겨도 노트 자리 유지)
    head, legacy, body = split_parts(blocks)
    r = PaperRenderer(images, os.path.join(cfg.ROOT_ABS, os.path.dirname(rel)), os.path.dirname(rel))
    if getattr(cfg, "LITE", False):
        # 가벼운 모드: 원문 글·수식 그림은 빼고, 요약에 붙일 그림·표(+바로 뒤 캡션 문단)만 둠
        keep = []
        all_blocks = head + legacy + body
        for i, b in enumerate(all_blocks):
            m = IMG_RE.search(b[4]) if b[1] == "img" else None
            fm = FIGNAME_RE.search(m.group(2)) if m else None
            if fm and fm.group(1).lower() != "eq":
                keep.append(b)
                if i + 1 < len(all_blocks) and all_blocks[i + 1][1] == "p" and re.match(r"^\s*\**\s*(Fig|Table|TABLE|FIG)", all_blocks[i + 1][4]):
                    keep.append(all_blocks[i + 1])
        h_legacy, h_body = "", render_blocks(r, keep)
    else:
        h_legacy = render_blocks(r, legacy)
        h_body = render_blocks(r, head + body) if body or not legacy else render_blocks(r, head)
    brief = brief_of(paper, head, legacy, body, r.figs, fig_index)
    sections = sections_of(head, legacy, body)
    html = (f'<section data-part="legacy">{h_legacy}</section>\n<section data-part="body">{h_body}</section>\n'
            f'<script type="application/json" data-part="brief">{json.dumps(brief, ensure_ascii=False).replace("</", "<\\/")}</script>\n'
            f'<script type="application/json" data-part="sections">{json.dumps(sections, ensure_ascii=False).replace("</", "<\\/")}</script>')
    # 검색용 본문 글자 (역색인)
    words = " ".join(text_of(raw) for bid, k, a, z, raw in blocks if k != "img")
    return html, len(blocks), len(r.figs), bool(legacy), words, brief


# ------------------------------------------------------------------ 역색인
TOK_LATIN = re.compile(r"[a-z0-9][a-z0-9+\-]*[a-z0-9]|[a-z0-9]")
TOK_HANGUL = re.compile(r"[가-힣]+")


def tokens(text):
    s = text.lower()
    out = set()
    for w in TOK_LATIN.findall(s):
        if 2 <= len(w) <= 30:
            out.add(w)
    for w in TOK_HANGUL.findall(s):
        if len(w) == 1:
            out.add(w)
        for i in range(len(w) - 1):
            out.add(w[i:i + 2])
    return out


# ------------------------------------------------------------------ 생성
def build(cfg):
    from build import DASH_VERSION, mtime
    root = cfg.ROOT_ABS
    out = os.path.normpath(os.path.join(root, cfg.OUT))
    os.makedirs(os.path.join(out, "docs"), exist_ok=True)
    os.makedirs(os.path.join(out, "search"), exist_ok=True)
    state_p = os.path.join(out, "_state.json")
    try:
        state = json.load(open(state_p, encoding="utf-8"))
    except (OSError, ValueError):
        state = {"docs": {}, "published": {}}
    papers = scan(cfg)
    fig_index = load_fig_index(cfg)
    images = InlineImages(root, out, getattr(cfg, "IMG_MAX_W", 900), getattr(cfg, "IMG_Q", 70))
    index, docs_meta, manifest, made, briefs = {}, {}, {}, 0, {}
    words_cache_p = os.path.join(out, "_words.json")
    try:
        words_cache = json.load(open(words_cache_p, encoding="utf-8"))
    except (OSError, ValueError):
        words_cache = {}
    keep_keys = set()
    for i, p in enumerate(papers):
        key = p["k"]
        keep_keys.add(key)
        sha = hashlib.sha1((p["_text"] + "|" + DOC_VERSION + f"|{images.max_w}|{images.q}|{int(bool(getattr(cfg, 'LITE', False)))}").encode("utf-8")).hexdigest()[:16]
        doc_p = os.path.join(out, "docs", key + ".html")
        prev = state["docs"].get(key)
        if prev and prev.get("sha") == sha and os.path.isfile(doc_p) and key in words_cache:
            p.pop("_text")
            p.update({"blocks": prev["blocks"], "nfig": prev["nfig"], "legacy": prev["legacy"]})
            words = words_cache[key]
            briefs[key] = prev.get("brief", {})
        else:
            html, nb, nf, has_legacy, words, brief = build_paper(cfg, images, p, fig_index)
            with open(doc_p, "w", encoding="utf-8") as f:
                f.write(html)
            p.update({"blocks": nb, "nfig": nf, "legacy": has_legacy})
            state["docs"][key] = {"sha": sha, "blocks": nb, "nfig": nf, "legacy": has_legacy, "size": len(html.encode("utf-8")),
                                  "brief": {"abstract": brief["abstract"][:400]}}
            words_cache[key] = words
            briefs[key] = state["docs"][key]["brief"]
            made += 1
            print(f"{key:12s} {nb:5d} 블록 {nf:3d} 그림  {rel_short(p['rel'])}")
        p["ex"] = (briefs.get(key) or {}).get("abstract", "")[:400]
        for t in tokens(words):
            index.setdefault(t, []).append(i)
        docs_meta[key] = {"title": p["t"], "src": p["rel"], "mtime": p["mtime"], "copy": f"{cfg.NOTE_DIR}/{note_name(p)}", "blocks": p["blocks"]}
        manifest[key] = {"src": p["rel"], "title": p["t"], "year": p["y"]}
    # 없어진 논문의 상태·사본 정리
    for k in [k for k in state["docs"] if k not in keep_keys]:
        state["docs"].pop(k)
        words_cache.pop(k, None)
        try:
            os.remove(os.path.join(out, "docs", k + ".html"))
        except OSError:
            pass
    with open(words_cache_p, "w", encoding="utf-8") as f:
        json.dump(words_cache, f, ensure_ascii=False)
    # 역색인
    with open(os.path.join(out, "search", "full.json"), "w", encoding="utf-8") as f:
        json.dump({"n": len(papers), "idx": index}, f, ensure_ascii=False, separators=(",", ":"))
    # 폴더 트리
    tree = {}
    for p in papers:
        node = tree
        for part in (p["folder"].split("/") if p["folder"] else []):
            node = node.setdefault("_d", {}).setdefault(part, {})
        node.setdefault("_p", []).append(p["k"])
    # 화면 데이터
    pub_papers = [{k: v for k, v in p.items() if k not in ("_text",)} for p in papers]
    summ = []
    api = __import__("types").SimpleNamespace(root=root, cfg=cfg, mtime=lambda rel: mtime(root, rel), today=datetime.date.today(), papers=pub_papers)
    if hasattr(cfg, "summary"):
        try:
            summ = cfg.summary(api) or []
        except Exception as e:
            print("summary 건너뜀:", e)
    if not summ:
        n_sum = sum(1 for p in papers if p["legacy"] or "완료" in p["st"]["sum"])
        summ = [{"label": "논문", "value": f"{len(papers)}편", "sub": f"pdf2md {sum(1 for p in papers if p['p2m'])}편"},
                {"label": "md에 요약 있음", "value": f"{n_sum}편", "sub": f"없음 {len(papers) - n_sum}편"},
                {"label": "그림·표", "value": f"{sum(p['nfig'] for p in papers)}장", "sub": "문서 안에 포함"}]
    note_dir_abs = os.path.normpath(os.path.join(root, cfg.NOTE_DIR))
    sum_dir = getattr(cfg, "SUM_DIR", cfg.NOTE_DIR)
    data = {"built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "winRoot": cfg.WIN_ROOT, "noteDir": cfg.NOTE_DIR,
            "noteDirWin": note_dir_abs.replace("/", "\\"), "sumDir": sum_dir, "sumDirWin": os.path.normpath(os.path.join(root, sum_dir)).replace("/", "\\"),
            "title": cfg.TITLE, "rules": cfg.RULES, "askExample": cfg.ASK_EXAMPLE, "sumRules": getattr(cfg, "SUM_RULES", ""),
            "reqRules": getattr(cfg, "REQ_RULES", ""),
            "askTier": getattr(cfg, "ASK_TIER", "default"),
            "config": os.path.relpath(cfg.CONFIG_PATH, root).replace("\\", "/"), "engine": DASH_VERSION,
            "views": [{"group": "정리", "items": [{"id": "home", "title": "첫 화면", "special": "home"},
                                               {"id": "search", "title": "검색", "special": "search"},
                                               {"id": "sums", "title": "Claude 요약 모음", "special": "sums"},
                                               {"id": "notes", "title": "내 질문·메모 모음", "special": "notes"},
                                               {"id": "files", "title": "파일 위치", "special": "files"}]}],
            "docs": docs_meta, "files": [], "summary": summ,
            "library": {"papers": pub_papers, "tree": tree, "version": DASH_VERSION, "lite": bool(getattr(cfg, "LITE", False)), "figsTab": bool(getattr(cfg, "SHOW_FIGS_TAB", not getattr(cfg, "LITE", False)))}}
    tpl = open(os.path.join(HERE, "page.html"), encoding="utf-8").read()
    page = (tpl.replace("__PAGE_TITLE__", ESC(getattr(cfg, "PAGE_TITLE", "") or cfg.TITLE)).replace("__TITLE__", ESC(cfg.TITLE)).replace("__SUBTITLE__", ESC(cfg.SUBTITLE))
            .replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    man_p = os.path.normpath(os.path.join(root, cfg.MANIFEST))
    os.makedirs(os.path.dirname(man_p), exist_ok=True)
    with open(man_p, "w", encoding="utf-8") as f:
        json.dump({"library": True, "docs": manifest, "noteDir": cfg.NOTE_DIR, "sumDir": sum_dir}, f, ensure_ascii=False, indent=1)
    # 게시 목록: 전체 / 아직 게시 안 된 것 (게시 뒤 build.py --published 로 표시)
    files = ["docs/" + p["k"] + ".html" for p in papers] + ["search/full.json"]
    cur = {"docs/" + k: v["sha"] for k, v in state["docs"].items()}
    changed = [f for f in files if f.startswith("docs/") and state["published"].get(f[:-5]) != cur.get(f[:-5])] + ["search/full.json"]
    state["current"] = cur
    with open(os.path.join(out, "_publish_files.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, ensure_ascii=False)
    with open(os.path.join(out, "_publish_changed.json"), "w", encoding="utf-8") as f:
        json.dump(changed, f, ensure_ascii=False)
    with open(state_p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    total = sum(v.get("size", 0) for v in state["docs"].values()) + os.path.getsize(os.path.join(out, "index.html")) + os.path.getsize(os.path.join(out, "search", "full.json"))
    print(f"dash={DASH_VERSION} library: 논문 {len(papers)}편 (새로 만든 문서 {made}), 그림 {sum(p['nfig'] for p in papers)}장, "
          f"게시 파일 {len(files) + 1}개 (아직 게시 안 됨 {len(changed)}개), 전체 약 {total / 1e6:.1f} MB, 역색인 {os.path.getsize(os.path.join(out, 'search', 'full.json')) / 1e6:.1f} MB → {out}")
    if len(files) + 1 > 500:
        print("주의: 게시 파일이 500개를 넘음. 아티팩트 한도(511)에 가까움 — 폴더별 묶음(BUNDLE) 전환이 필요함.")


def rel_short(rel, n=70):
    return rel if len(rel) <= n else "…" + rel[-n:]


def note_name(p):
    return os.path.splitext(os.path.basename(p["rel"]))[0] + "__노트.md"


def mark_published(cfg):
    out = os.path.normpath(os.path.join(cfg.ROOT_ABS, cfg.OUT))
    state_p = os.path.join(out, "_state.json")
    state = json.load(open(state_p, encoding="utf-8"))
    state["published"] = dict(state.get("current", {}))
    state["publishedAt"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(state_p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    with open(os.path.join(out, "_publish_changed.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    print(f"게시 기록함: 문서 {len(state['published'])}개 ({state['publishedAt']})")
