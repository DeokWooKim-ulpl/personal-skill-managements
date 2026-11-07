# -*- coding: utf-8 -*-
"""artifact-board 엔진: 마크다운 원고 폴더를 탭 달린 claude.ai 아티팩트 보고판(HTML)으로 만든다. LLM을 쓰지 않는다.

기능
  - 큰 탭 = src_dir 안의 폴더 하나, 작은 탭 = 그 폴더 안의 md 하나 (이름 규칙 NN_토큰_이름)
  - 과제별 탭은 hooks 모듈의 tabs_before(api) / tabs_after(api)가 만든다 (예: 오늘 보고)
  - 읽기목록(선택): 논문마다 별도 페이지(번역 MD + PDF 그림 쪽 이미지)를 site_dir/papers/에 만든다
  - 입력함(db "inbox"): 탭마다 "의견 보내기", data-kind 버튼, 보낸 의견·답 목록
  - 질문 창(sample): 지금 보는 탭 내용을 붙여 보는 사람의 사용량으로 묻고 답한다
  - MathJax 수식, 밝은/어두운 테마, 모바일 폭

사용
  python -I board.py <board.config.json>           보고판 생성
  python -I board.py --init <과제 폴더> [제목]      새 과제에 설정 파일과 원고 폴더를 만든다
  python -I board.py --notes-sync <설정> <노트.json>  (1.5.0) db 노트를 md 사본(notes.md_dir)에 콜아웃으로 붙인다
표준출력 마지막 두 줄: "index changed|unchanged", "papers changed|unchanged"
"""
import sys, re, html, hashlib, datetime, pathlib, json, importlib.util, types

ENGINE_VERSION = "1.5.0"
CONFIG_VERSION = 1
HERE = pathlib.Path(__file__).resolve().parent
MATHJAX = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg-full.min.js"
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@600;700&display=swap">')

DEFAULTS = {
    "config_version": 1,
    "title": "보고판",
    "page_title": "",          # 브라우저 탭·갤러리 제목. 비우면 title
    "kicker": "",
    "header_note": "",
    "lang": "ko",
    "root": ".",
    "out_html": "board/board.html",
    "hash_file": "board/board.hash",
    "site_dir": "board/site",
    "src_dir": "board/src",
    "reading_list": "",
    "papers_dir": "",
    "clean_paper_md": True,
    "hooks": "",
    "lazy_tabs": False,        # 1.3.0: True면 큰 탭 내용을 site_dir/tabs/<토큰>.html로 따로 쓰고 보고판은 틀만 가짐 (갱신 게시 때 읽을 본문을 작게)
    "tab_images": "files",     # 탭 그림: "files"(site_dir/tabimg로 게시) | "inline"(WebP로 줄여 HTML에 data URI로 넣음 — 게시 파일 수 한도(511)를 넘길 때)
    "inline_images": {"max_width": 1000, "quality": 72},
    "status_columns": ["상태", "status", "Status"],
    "chips": [["수정필요", "no"], ["보류", "mute"], ["완성", "ok"], ["✅", "ok"], ["확정", "ok"],
              ["작성중", "ac"], ["대기", "mid"], ["검증", "mid"]],
    "inbox": {"enabled": True, "kinds": ["답변", "이의", "스킵", "수정 요청", "질문", "기타"],
              "processed_by": "다음 처리 때 반영됩니다.",
              "placeholder": "예: \"이 식의 근거가 이상함\", \"3번째 문단을 더 쉽게 고쳐 줘\"",
              "summary": "이 탭에 의견 보내기 (답·이의·스킵·수정 요청)",
              "send": "보내기", "tab_label": "의견·답", "list_title": "보낸 의견과 처리 결과",
              "list_intro": "각 탭 아래 \"의견 보내기\"나 질문 창에서 보낸 내용이 여기에 쌓이고, 처리한 쪽이 답을 적습니다.",
              "reply_prefix": "답: "},
    "chat": {"enabled": True, "title": "질문 창", "fab": "질문하기",
             "note": "지금 보고 있는 탭 내용을 함께 보내 답합니다. 문장을 드래그해 선택한 뒤 물으면 그 부분을 중심으로 설명합니다.",
             "placeholder": "예: 이 탭의 핵심을 쉽게 설명해 줘",
             "rules": "너는 이 보고판의 해설 도우미다. 한국어로, 배경부터 차근차근, 필요하면 수식($...$ LaTeX)과 숫자 예를 들어 설명한다. "
                      "아래 [페이지 내용]을 우선 근거로 삼고, 페이지에 없는 일반 지식으로 답할 때는 그렇다고 밝힌다. "
                      "확실하지 않은 수치는 지어내지 말고 모른다고 말한다. 사용자가 문서 수정을 원하면 어떤 문장을 어떻게 바꾸면 좋을지 구체적인 수정안을 제시한다.",
             "default_tier": "default", "max_turns": 12, "page_chars": 24000,
             "log": True, "log_collection": "chatlog"},   # 1.3.0: 질문·답을 db에 남김 (처리하는 쪽이 질문 기록 원고로 정리)
    "extra_css": "",           # 1.5.0: 이 보고판에만 더할 CSS (hooks가 만든 탭의 모양 등)
    "hide_single_sub": False,  # 1.5.0: True면 작은 탭이 하나뿐인 큰 탭은 작은 탭 줄을 숨김
    "reading_tab": True,     # 1.5.0: False면 읽기목록 큰 탭을 따로 만들지 않음 (논문 페이지는 만듦, hooks가 api.reading_group으로 원하는 곳에 붙임)
    # 1.5.0: 노트(문단에 붙는 질문·답·내 메모). 문장을 선택 → [질문하기]/[메모] → 그 문단 바로 아래 카드로 붙고 db에 저장됨.
    # md_dir: --notes-sync가 "원본 md + 노트" 사본을 쓰는 폴더(root 기준). 원본 md는 건드리지 않음.
    "notes": {"enabled": False, "collection": "notes", "md_dir": "", "tab_label": "내 노트", "ask_tier": "default",
              "max_context": 30000,
              "hint": "문장을 드래그해 선택하면 [질문하기]·[메모] 버튼이 뜹니다. 질문과 답, 내 메모는 그 문단 바로 아래에 붙고 '내 노트' 탭에 모입니다."},
    "strings": {"back": "← 보고판으로 돌아가기", "reading_tab": "공부할 논문", "no_md": "번역 없음",
                "fig_badge": "그림 {n}쪽", "th_order": "순서", "th_paper": "논문", "th_why": "왜 읽나",
                "why_label": "이 논문을 읽는 이유", "pdf_label": "원문 PDF",
                "md_label": "요약 · 번역 · 해설",
                "md_warn": "이 번역 MD는 자동으로 만든 것이라 원문과 다르거나 줄여져 있을 수 있습니다. 수식과 수치는 아래 원문 쪽 이미지로 확인하세요.",
                "no_md_text": "이 논문은 아직 번역 MD가 없습니다. 그림 페이지와 위의 읽는 이유를 먼저 보세요.",
                "fig_label": "원문 그림·표·수식 ({n}쪽)",
                "fig_note": "PDF에서 그림이나 표 캡션이 있는 쪽을 그대로 옮겼습니다. 스캔본은 전체 쪽입니다.",
                "fig_cap": "원문 {p}쪽 (그림·표가 있는 쪽)", "generated": "생성"},
}


def merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- 마크다운 → HTML
class MD:
    def __init__(self, cfg):
        self.status_cols = cfg["status_columns"]
        self.chips = cfg["chips"]
        self.root, self.base, self.images = None, None, {}      # 탭 그림: 게시 경로 → 원본(root 기준)
        self.inline_mode = cfg.get("tab_images") == "inline"
        self.inline_opt = cfg.get("inline_images", {})
        self.cache_dir = None                                     # inline 그림 변환 결과 캐시 (site_dir/_inline_cache)

    IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

    def image(self, alt, url):
        """원고 md의 ![설명](경로) → figure. 경로는 md 파일 기준, 없으면 root 기준. root 밖·없는 파일은 지움."""
        if not self.root or url.startswith(("http:", "https:", "data:")):
            return ""
        for b in (self.base, self.root):
            f = (b / url).resolve() if b else None
            if f and f.is_file() and f.suffix.lower() in self.IMG_EXT and self.root in f.parents:
                rel = str(f.relative_to(self.root)).replace("\\", "/")
                cap = f"<figcaption>{esc(alt)}</figcaption>" if alt else ""
                if self.inline_mode:
                    src = self.inline_src(f)
                    if src:
                        return f'<figure class="fig"><img loading="lazy" src="{src}" alt="{esc(alt)}">{cap}</figure>'
                key = "tabimg/" + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12] + f.suffix.lower()
                self.images[key] = rel
                cap = f"<figcaption>{esc(alt)}</figcaption>" if alt else ""
                return f'<figure class="fig"><img loading="lazy" src="{key}" alt="{esc(alt)}">{cap}</figure>'
        return ""

    def inline_src(self, f):
        """그림을 max_width로 줄인 WebP data URI로 바꿈. 결과는 캐시해 다음 생성 때 다시 인코딩하지 않음."""
        import base64
        w, q = int(self.inline_opt.get("max_width", 1000)), int(self.inline_opt.get("quality", 72))
        data = f.read_bytes()
        h = hashlib.sha1(data + f"{w}:{q}".encode()).hexdigest()[:16]
        c = self.cache_dir / (h + ".webp") if self.cache_dir else None
        if c and c.exists():
            out = c.read_bytes()
        else:
            try:
                from PIL import Image
                import io
                im = Image.open(io.BytesIO(data))
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA")
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                elif im.mode != "RGB":
                    im = im.convert("RGB")
                if im.width > w:
                    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                b = io.BytesIO()
                im.save(b, "WEBP", quality=q, method=6)
                out = b.getvalue()
            except Exception:
                return ""                                         # Pillow 없음·손상 파일 → 파일 방식으로 넘어감
            if c:
                c.parent.mkdir(parents=True, exist_ok=True)
                c.write_bytes(out)
        return "data:image/webp;base64," + base64.b64encode(out).decode()

    def md_file(self, path, hshift=1, toc=False, toc_title="목차", inline_images=None):
        """원고 폴더 밖 md 파일 하나를 HTML로 (그림 경로 기준 = 그 파일 폴더). toc=True면 h2·h3 목차를 맨 위에 붙임."""
        path = pathlib.Path(path)
        old, self.base = self.base, path.parent
        old_mode = self.inline_mode
        if inline_images is not None:
            self.inline_mode = bool(inline_images)
        try:
            h = self.to_html(path.read_text(encoding="utf-8"), hshift)
        finally:
            self.base, self.inline_mode = old, old_mode
        if not toc:
            return h
        items, n = [], [0]

        def tag(m):
            n[0] += 1
            hid = f"toc-{hashlib.sha1(str(path).encode()).hexdigest()[:6]}-{n[0]}"
            items.append((m.group(1), hid, re.sub(r"<[^>]+>", "", m.group(2))))
            return f'<h{m.group(1)} id="{hid}">{m.group(2)}</h{m.group(1)}>'
        h = re.sub(r"<h([23])>(.*?)</h\1>", tag, h)
        if len(items) < 3:
            return h
        lis = "".join(f'<li class="l{lv}"><a href="javascript:void 0" data-goto="{hid}">{t}</a></li>' for lv, hid, t in items)
        return f'<details class="toc"><summary>{esc(toc_title)} ({len(items)})</summary><ul>{lis}</ul></details>' + h

    def inline(self, s):
        """수식($…$, $$…$$)은 건드리지 않고 나머지만 변환."""
        keep = []

        def stash(m):
            keep.append(m.group(0))
            return f"\x00{len(keep) - 1}\x00"
        figs = []

        def fig(m):
            figs.append(self.image(m.group(1), m.group(2).strip()))
            return f"\x01{len(figs) - 1}\x01"
        s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", fig, s)
        s = re.sub(r"\$\$.+?\$\$|\$[^$\n]+?\$", stash, s)
        s = esc(s)
        s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
        s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)

        def link(m):
            text, url = m.group(1), m.group(2)
            if url.startswith("http"):
                return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
            if url.startswith("papers/") or url.startswith("#"):
                return f'<a href="{url}">{text}</a>'
            return f'<span class="lnk" title="{url}">{text}</span>'
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)
        s = re.sub(r"\x00(\d+)\x00", lambda m: esc(keep[int(m.group(1))]), s)
        return re.sub(r"\x01(\d+)\x01", lambda m: figs[int(m.group(1))], s)

    def chip(self, s):
        t = self.inline(s)
        for key, cls in self.chips:
            if key in s and len(s) < 60:
                return f'<span class="chip {cls}">{t}</span>'
        return t

    @staticmethod
    def split_row(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    def to_html(self, text, hshift=1):
        inline, split_row = self.inline, self.split_row
        text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)        # YAML 머리말 제거
        out, lines, i = [], text.splitlines(), 0
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                i += 1
                continue
            if ln.strip().startswith("<!--"):                          # HTML 주석(자동 구역 표식 등)은 보이지 않게 (1.4.1)
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                i += 1
                continue
            if ln.strip().startswith("```"):
                buf, i = [], i + 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    buf.append(esc(lines[i]))
                    i += 1
                out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
                i += 1
                continue
            if ln.strip().startswith("$$"):                            # 독립 수식 블록
                buf = [ln]
                if not (ln.strip().endswith("$$") and len(ln.strip()) > 2):
                    i += 1
                    while i < len(lines):
                        buf.append(lines[i])
                        if lines[i].strip().endswith("$$"):
                            break
                        i += 1
                out.append('<div class="math">' + esc("\n".join(buf)) + "</div>")
                i += 1
                continue
            if re.match(r"^\s*(-{3,}|\*{3,})\s*$", ln):
                out.append("<hr>")
                i += 1
                continue
            m = re.match(r"^(#{1,6})\s+(?:#+\s+)?(.*)", ln)
            if m:
                lvl = min(len(m.group(1)) + hshift, 6)
                out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
                i += 1
                continue
            if ln.startswith(">"):
                buf = []
                while i < len(lines) and lines[i].startswith(">"):
                    buf.append(lines[i][1:].lstrip())
                    i += 1
                out.append('<div class="quote">' + self.to_html("\n".join(buf), hshift) + "</div>")
                continue
            if ln.lstrip().startswith("|"):
                rows = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    rows.append(lines[i])
                    i += 1
                head = split_row(rows[0])
                body = [split_row(r) for r in rows[1:] if not re.match(r"^\s*\|[\s:|-]+\|\s*$", r)]
                st = {k for k, h in enumerate(head) if any(c in h for c in self.status_cols)}
                t = ['<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in head) + "</tr></thead><tbody>"]
                for r in body:
                    t.append("<tr>" + "".join(f"<td>{self.chip(c) if k in st else inline(c)}</td>" for k, c in enumerate(r)) + "</tr>")
                out.append("".join(t) + "</tbody></table></div>")
                continue
            if re.match(r"^\s*([-*]|\d+[.)])\s+", ln):
                stack, buf = [], []
                while i < len(lines) and (re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i])
                                          or (lines[i].startswith("   ") and lines[i].strip() and stack)):
                    cur = lines[i]
                    if not re.match(r"^\s*([-*]|\d+[.)])\s+", cur):          # 목록 항목의 이어지는 줄
                        buf.append(" " + inline(cur.strip()))
                        i += 1
                        continue
                    ind = len(cur) - len(cur.lstrip())
                    tag = "ol" if re.match(r"^\s*\d+[.)]", cur) else "ul"
                    item = inline(re.sub(r"^\s*([-*]|\d+[.)])\s+", "", cur))
                    if not stack or ind > stack[-1][0]:
                        buf.append(f"<{tag}>")
                        stack.append((ind, tag))
                    else:
                        while stack and ind < stack[-1][0]:
                            buf.append(f"</li></{stack[-1][1]}>")
                            stack.pop()
                        buf.append("</li>")
                    buf.append(f"<li>{item}")
                    i += 1
                while stack:
                    buf.append(f"</li></{stack[-1][1]}>")
                    stack.pop()
                out.append("".join(buf))
                continue
            if re.match(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$", ln):            # 그림만 있는 줄
                out.append(inline(ln.strip()))
                i += 1
                continue
            buf = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\s*\||\s*([-*]|\d+[.)])\s|\s*\$\$|\s*```)", lines[i]):
                buf.append(inline(lines[i].strip()))
                i += 1
            if buf:
                out.append("<p>" + " ".join(buf) + "</p>")
            else:
                out.append(f"<p>{inline(ln)}</p>")
                i += 1
        return "\n".join(out)


# ---------------------------------------------------------------- 원고 폴더 탭
def name_parts(stem):
    m = re.match(r"^\d+_([A-Za-z0-9-]+)_(.+)$", stem)
    return (m.group(1), m.group(2)) if m else (re.sub(r"\W", "", stem)[:12] or "x", stem)


def src_tabs(src, md):
    """작은 탭 = (토큰, 이름, html, 원본 md 경로(root 기준)) — 4번째 값은 1.5.0 노트용"""
    tops = []
    for d in sorted(p for p in src.iterdir() if p.is_dir()) if src.exists() else []:
        tok, lab = name_parts(d.name)
        subs = []
        for f in sorted(d.glob("*.md")):
            st, sl = name_parts(f.stem)
            md.base = f.parent
            rel = f.resolve().relative_to(md.root).as_posix() if md.root and md.root in f.resolve().parents else ""
            subs.append((st, sl, md.to_html(f.read_text(encoding="utf-8"), 1), rel))
            md.base = None
        if subs:
            tops.append((tok, lab, subs))
    return tops


# ---------------------------------------------------------------- 읽기목록 · 논문 페이지
CAP = re.compile(r"^\s*(Fig\.?|FIG\.?|Figure|FIGURE|Table|TABLE)\s*\.?\s*\d", re.M)


def figure_pages(pdf, key, imgdir):
    """그림·표 캡션이 있는 쪽을 JPEG로 렌더링 (스캔본이면 전 쪽, 최대 14쪽). 이미 있으면 다시 만들지 않음."""
    try:
        import fitz
    except ImportError:
        return []
    out = sorted(imgdir.glob(f"{key}_p*.jpg"))
    if out:
        return out
    try:
        doc = fitz.open(pdf)
    except Exception:
        return []
    texts = [pg.get_text() for pg in doc]
    scanned = sum(len(t.strip()) for t in texts) < 200
    pages = [k for k, t in enumerate(texts) if scanned or CAP.search(t)][:14]
    for k in pages:
        pix = doc[k].get_pixmap(matrix=fitz.Matrix(1.45, 1.45))
        f = imgdir / f"{key}_p{k + 1:02d}.jpg"
        f.write_bytes(pix.tobytes("jpeg", jpg_quality=72))
        out.append(f)
    return out


def parse_reading_list(path):
    """## 묶음 이름 | 토큰  /  - 키 | 제목 | 연도 | 읽는 이유 | 번역MD | PDF | 메모(선택)"""
    groups, cur = [], None
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(.+?)\s*\|\s*([a-z0-9-]+)\s*$", ln)
        if m:
            cur = {"label": m.group(1), "tok": m.group(2), "intro": [], "items": []}
            groups.append(cur)
        elif cur and ln.startswith("- ") and ln.count("|") >= 5:
            f = [x.strip() for x in ln[2:].split("|")]
            cur["items"].append(dict(key=f[0], title=f[1], year=f[2], why=f[3], md=f[4], pdf=f[5],
                                     note=f[6] if len(f) > 6 else ""))
        elif cur and ln.strip() and not ln.startswith("#"):
            cur["intro"].append(ln)
    return groups


def clean_paper_md(t):
    """자동 번역 MD의 흔한 손상을 화면용으로만 복원 (원본 파일은 건드리지 않음).
    - 역슬래시가 제어문자로 바뀐 LaTeX(\\t \\b \\f \\a \\v \\r), \\nu 등이 줄바꿈으로 끊긴 것
    - Notion 내보내기 이스케이프, 위키 주석 줄, 개인 메일 주소, Google Drive 파일 ID"""
    t = t.replace("\r\n", "\n")
    for c, rep in (("\t", "\\t"), ("\x08", "\\b"), ("\x0c", "\\f"), ("\x07", "\\a"), ("\x0b", "\\v"), ("\r", "\\r")):
        t = t.replace(c, rep)
    lines, out = t.split("\n"), []
    for ln in lines:
        if out:
            prev = out[-1]
            single = len(re.findall(r"(?<!\$)\$(?!\$)", prev))
            double = prev.count("$$")
            if (single % 2 or (double % 2 and not prev.strip().startswith("$$"))) and re.match(r"^(u|abla|eq|ot)\b", ln):
                out[-1] = prev + "\\n" + ln
                continue
        out.append(ln)
    t = "\n".join(l for l in out if not any(k in l for k in ("wiki:auto", "저장 위치", "drive.google", "드라이브 ID", "Drive ID")))
    t = t.replace("\\\\{", "\\{").replace("\\\\}", "\\}")
    for a, b in (("\\_", "_"), ("\\!", "!"), ("\\<", "<"), ("\\~", "~"), ("\\&", "&"), ("\\*", "*"), ("\\#", "#")):
        t = t.replace(a, b)
    t = re.sub(r"[\w.+-]+@(?:gmail|naver|daum|hanmail|hotmail|yahoo|outlook)\.\w+", "(개인 이메일 생략)", t)
    t = re.sub(r"\(?`?\b1[A-Za-z0-9_-]{25,40}\b`?\)?", "", t)
    return re.sub(r"(?m)^(\s*)\\-", r"\1-", t)


PAGE_CSS_EXTRA = """
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:14px}
.gallery figure{margin:0;background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:8px;display:flex;flex-direction:column;gap:6px}
.gallery img{width:100%;height:auto;border-radius:3px;background:#fff}
.gallery figcaption{font-size:12.5px;color:var(--muted)}
.back{font-size:14px}
"""


# ---------------------------------------------------------------- 페이지 틀
CSS = (HERE / "board.css").read_text(encoding="utf-8")
NOTES_CSS = (HERE / "notes.css").read_text(encoding="utf-8")
NAV_JS = "<script>\n" + (HERE / "nav.js").read_text(encoding="utf-8") + "</script>"
INTERACT_TPL = (HERE / "interact.js").read_text(encoding="utf-8")
NOTES_TPL = (HERE / "notes.js").read_text(encoding="utf-8")
MJ_CFG = ("<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$']]},"
          "svg:{fontCache:'global'},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>")


def shell(title, inner, lang="ko", extra_css="", standalone=False):
    head = ("" if not standalone else f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">')
    head += f"<title>{esc(title)}</title>\n"
    if not standalone:
        head += '<meta name="claude:viewport-fit-sides" content="cover">\n'
    head += FONTS + f"\n<style>{CSS}{extra_css}</style>\n{MJ_CFG}\n<script src=\"{MATHJAX}\" async></script>\n"
    if standalone:
        head += "</head><body>"
    tail = "" if not standalone else "</body></html>"
    return head + f'<div class="wrap">{inner}</div>' + tail


def interact_js(cfg, notes=None):
    """notes: 1.5.0 노트 기능이 켜졌을 때 JS에 넘길 {docs, synced, ...} (꺼져 있으면 None → 예전과 같은 출력)"""
    if not (cfg["inbox"]["enabled"] or cfg["chat"]["enabled"] or notes):
        return ""
    data = {"name": cfg["title"], "inbox": cfg["inbox"], "chat": cfg["chat"]}
    if notes:
        data["notes"] = notes
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return ("<script>\nvar BOARD=" + blob + ";\n" + INTERACT_TPL + "</script>"
            + ("<style>" + NOTES_CSS + "</style><script>\n" + NOTES_TPL + "</script>" if notes else ""))


def norm_text(s):
    """노트 위치 맞추기용: 공백·문장부호·마크다운 기호를 지운 소문자 글자열 (notes.js의 norm과 같은 규칙)"""
    s = re.sub(r"\$[^$]*\$", "", s)
    return re.sub(r"[\W_]+", "", s, flags=re.U).lower()


# ---------------------------------------------------------------- 실행
class Board:
    def __init__(self, cfg_path):
        self.cfg_path = pathlib.Path(cfg_path).resolve()
        raw = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        if raw.get("config_version", 1) > CONFIG_VERSION:
            sys.exit(f"설정 버전 {raw['config_version']}은 엔진 {ENGINE_VERSION}보다 새것입니다. 스킬을 업데이트하세요.")
        self.cfg = merge(DEFAULTS, raw)
        self.root = (self.cfg_path.parent / self.cfg["root"]).resolve()
        self.md = MD(self.cfg)
        self.md.root = self.root
        self.md.cache_dir = self.p(self.cfg["site_dir"]) / "_inline_cache"
        self.S = self.cfg["strings"]

    def p(self, rel):
        return (self.root / rel) if rel else None

    # ------------------------------------------------ 1.5.0 노트: 문서 등록부 (data-doc ↔ 원본 md ↔ 노트 사본)
    def notes_on(self):
        return bool(self.cfg["notes"].get("enabled"))

    def doc_copy(self, doc, md):
        """노트 사본 경로(root 기준): md_dir/<doc>__<원본 파일 이름>"""
        d = self.cfg["notes"].get("md_dir") or ""
        return f"{d.rstrip('/')}/{doc}__{pathlib.PurePosixPath(md).name}" if (d and md) else ""

    def reg_doc(self, doc, title, md):
        """문서 하나를 등록하고 그 문서 컨테이너에 붙일 속성 문자열을 돌려줌. 노트가 꺼져 있으면 ''."""
        if not self.notes_on():
            return ""
        md = md or ""
        t = html.unescape(re.sub(r"<[^>]+>", "", str(title)))[:80]
        self.docs[doc] = {"title": t, "md": md, "copy": self.doc_copy(doc, md)}
        return (f' data-doc="{esc(doc)}" data-title="{esc(t)}"' + (f' data-md="{esc(md)}"' if md else "")
                + (f' data-copy="{esc(self.docs[doc]["copy"])}"' if self.docs[doc]["copy"] else ""))

    def notes_js_data(self):
        n = self.cfg["notes"]
        st = self.p(n["md_dir"]) / ".sync.json" if n.get("md_dir") else None
        synced = json.loads(st.read_text(encoding="utf-8")) if st and st.exists() else {}
        return {"collection": n["collection"], "tab_label": n["tab_label"], "ask_tier": n["ask_tier"], "hint": n["hint"],
                "max_context": n["max_context"], "root_abs": str(self.root), "md_dir": n.get("md_dir", ""),
                "md_dir_abs": str(self.p(n["md_dir"])) if n.get("md_dir") else "", "synced": synced}

    def rel(self, md):
        """md 경로(문자열·Path, root 기준이나 절대) → root 기준 posix 문자열. root 밖이면 ''."""
        if not md:
            return ""
        p = pathlib.Path(md)
        p = (p if p.is_absolute() else self.root / p).resolve()
        return p.relative_to(self.root).as_posix() if self.root in p.parents else ""

    def srcbar(self, doc):
        """문서 맨 위 '파일 위치' 줄 (원본·노트 사본 경로 + 복사 버튼). 노트가 꺼져 있거나 md가 없으면 ''."""
        d = self.docs.get(doc) if self.notes_on() else None
        if not d or not d["md"]:
            return ""
        rows = [("원본", d["md"])] + ([("노트 사본", d["copy"])] if d["copy"] else [])
        cells = "".join(f'<span class="sb-item"><span class="sb-k">{k}</span><code class="sb-path" title="{esc(str(self.root / v))}">{esc(pathlib.PurePosixPath(v).name)}</code>'
                        f'<button type="button" class="sb-copy" data-copy="{esc(str(self.root / v))}" title="전체 경로 복사">경로 복사</button></span>' for k, v in rows)
        return f'<div class="srcbar"><span class="sb-ico" aria-hidden="true">📁</span>{cells}</div>'

    def page(self, key, title, html, back=True, md=None):
        """보고판과 별도로 게시할 독립 페이지(site_dir/key)를 만들고 files에 올림. 긴 문서는 본문 대신 이렇게 붙여
        보고판 HTML을 작게 유지함 (게시 때 보고판 전체를 읽어야 하므로). 반환값 = 보고판에서 걸 링크 경로.
        md(1.5.0): 원본 md 경로(root 기준 문자열이나 Path) — 노트가 켜져 있으면 이 페이지에서도 노트를 달 수 있고 파일 위치가 뜸."""
        site = self.p(self.cfg["site_dir"])
        dst = site / key
        dst.parent.mkdir(parents=True, exist_ok=True)
        top = f'<p class="back"><a href="#" onclick="history.back();return false">{esc(self.S["back"])}</a></p>' if back else ""
        doc = "page-" + re.sub(r"[^A-Za-z0-9]+", "-", key.rsplit(".", 1)[0]).strip("-")
        attrs = self.reg_doc(doc, title, self.rel(md))
        pg = shell(title[:40], top + self.srcbar(doc) + html, self.cfg["lang"], PAGE_CSS_EXTRA + self.cfg["extra_css"], standalone=True)
        if attrs:
            pg = pg.replace('<div class="wrap">', f'<div class="wrap"{attrs}>', 1)
        pg = pg.replace("</body></html>", NAV_JS + getattr(self, "ijs", "") + "</body></html>")
        dst.write_text(pg, encoding="utf-8")
        self.extra_files[key] = dst.relative_to(self.root).as_posix()
        return key

    def api(self):
        return types.SimpleNamespace(root=self.root, cfg=self.cfg, path=self.p, esc=esc, md_to_html=self.md.to_html, md_file=self.md.md_file,
                                     page=self.page, rel=self.rel, reading_group=self.reading_group, doc_block=self.doc_block,
                                     inline=self.md.inline, chip=self.md.chip, split_row=self.md.split_row)

    def doc_block(self, doc, title, md, html_):
        """1.5.0: 작은 탭 하나에 md 문서를 여러 개 넣을 때 문서마다 감싸는 블록 (노트·파일 위치가 문서별로 붙음).
        이때 그 작은 탭은 4번째 값을 None으로 넘김. 노트가 꺼져 있으면 html_을 그대로 감싸기만 함."""
        attrs = self.reg_doc(doc, title, self.rel(md))
        return f'<div class="docpart"{attrs}>{self.srcbar(doc)}{html_}</div>'

    def reading_group(self, tok, intro=True):
        """1.5.0: 읽기목록 묶음 하나(토큰)를 표 HTML로. 묶음이 없으면 ''. hooks가 아무 탭에나 붙일 때 씀."""
        g = next((g for g in getattr(self, "groups", []) if g["tok"] == tok), None)
        return self.group_html(g, intro) if g else ""

    def load_hooks(self):
        h = self.cfg["hooks"]
        if not h:
            return None
        path = self.p(h)
        spec = importlib.util.spec_from_file_location("board_hooks", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def paper_pages(self, groups, ijs):
        S, md, site = self.S, self.md, self.p(self.cfg["site_dir"])
        papers = self.p(self.cfg["papers_dir"]) or self.root
        pdir, imgdir = site / "papers", site / "papers" / "img"
        imgdir.mkdir(parents=True, exist_ok=True)
        files = {}
        pd_name = self.cfg["papers_dir"] or "."
        for g in groups:
            for it in g["items"]:
                mdf = papers / it["md"] if it["md"] not in ("", "-") else None
                pdf = papers / it["pdf"] if it["pdf"] not in ("", "-") else None
                it["has_md"] = bool(mdf and mdf.exists())
                it["has_pdf"] = bool(pdf and pdf.exists())
                imgs = figure_pages(pdf, it["key"], imgdir) if it["has_pdf"] else []
                it["nimg"] = len(imgs)
                body = [f'<p class="back"><a href="#" onclick="history.back();return false">{esc(S["back"])}</a></p>',
                        f'<span class="label">{esc(S["reading_tab"])} · {esc(g["label"])}</span><h1>{md.inline(it["title"])}</h1>',
                        f'<p class="meta">{esc(it["year"])} · {esc(S["pdf_label"])}: <code>{esc(pd_name)}/{esc(it["pdf"])}</code></p>',
                        f'<section class="panel todo"><span class="label">{esc(S["why_label"])}</span>{md.to_html(it["why"])}'
                        + (md.to_html(it["note"]) if it["note"] else "") + "</section>"]
                if it["has_md"]:
                    t = mdf.read_text(encoding="utf-8")
                    body.append(f'<section class="panel"><span class="label">{esc(S["md_label"])}</span>'
                                f'<div class="quote"><p>{esc(S["md_warn"])}</p></div>'
                                + md.to_html(clean_paper_md(t) if self.cfg["clean_paper_md"] else t, 1) + "</section>")
                else:
                    body.append(f'<section class="panel"><span class="label">{esc(S["md_label"])}</span><p class="meta">{esc(S["no_md_text"])}</p></section>')
                if imgs:
                    figs = "".join(f'<figure><img loading="lazy" src="img/{f.name}" alt="{esc(it["title"])} {int(f.stem.split("_p")[-1])}">'
                                   f'<figcaption>{esc(S["fig_cap"].format(p=int(f.stem.split("_p")[-1])))}</figcaption></figure>' for f in imgs)
                    body.append(f'<section class="panel"><span class="label">{esc(S["fig_label"].format(n=len(imgs)))}</span>'
                                f'<p class="meta">{esc(S["fig_note"])}</p><div class="gallery">{figs}</div></section>')
                doc = "paper-" + re.sub(r"[^A-Za-z0-9]+", "-", it["key"]).strip("-")
                attrs = self.reg_doc(doc, it["title"], self.rel(mdf) if it["has_md"] else "")
                if attrs:
                    body.insert(3, self.srcbar(doc))
                page = shell(it["title"][:40], "\n".join(body), self.cfg["lang"], PAGE_CSS_EXTRA, standalone=True)
                if attrs:
                    page = page.replace('<div class="wrap">', f'<div class="wrap"{attrs}>', 1)
                page = page.replace("</body></html>", ijs + "</body></html>")
                (pdir / f"{it['key']}.html").write_text(page, encoding="utf-8")
                files[f"papers/{it['key']}.html"] = str((pdir / f"{it['key']}.html").relative_to(self.root)).replace("\\", "/")
                for f in imgs:
                    files[f"papers/img/{f.name}"] = str(f.relative_to(self.root)).replace("\\", "/")
        return files

    def group_html(self, g, intro=True):
        S, md, rows = self.S, self.md, []
        for n, it in enumerate(g["items"], 1):
            badges = ("" if it["has_md"] else f'<span class="chip mute">{esc(S["no_md"])}</span> ') + \
                     (f'<span class="chip ac">{esc(S["fig_badge"].format(n=it["nimg"]))}</span>' if it["nimg"] else "")
            rows.append(f'<tr><td class="num">{n}</td><td><a href="papers/{esc(it["key"])}.html"><strong>{md.inline(it["title"])}</strong></a>'
                        f'<br><span class="meta">{esc(it["year"])}</span> {badges}</td><td>{md.inline(it["why"])}</td></tr>')
        return ((md.to_html("\n".join(g["intro"]), 1) if intro else "")
                + f'<div class="tbl"><table><thead><tr><th>{esc(S["th_order"])}</th><th>{esc(S["th_paper"])}</th><th>{esc(S["th_why"])}</th></tr></thead><tbody>'
                + "".join(rows) + "</tbody></table></div>")

    def reading_tab(self, groups):
        return ("read", self.S["reading_tab"], [(g["tok"], g["label"], self.group_html(g)) for g in groups])

    def run(self):
        cfg, S = self.cfg, self.S
        out, hashf, site = self.p(cfg["out_html"]), self.p(cfg["hash_file"]), self.p(cfg["site_dir"])
        src = self.p(cfg["src_dir"])
        src.mkdir(parents=True, exist_ok=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        site.mkdir(parents=True, exist_ok=True)
        self.docs = {}
        ijs = interact_js(cfg, self.notes_js_data() if self.notes_on() else None)
        self.ijs, self.extra_files = ijs, {}
        hooks, api = self.load_hooks(), self.api()

        rl = self.p(cfg["reading_list"])
        groups = parse_reading_list(rl) if rl and rl.exists() else []
        self.groups = groups
        files = self.paper_pages(groups, ijs) if groups else {}
        tops = (list(hooks.tabs_before(api)) if hooks and hasattr(hooks, "tabs_before") else []) + src_tabs(src, self.md) \
            + ([self.reading_tab(groups)] if groups and cfg["reading_tab"] else []) \
            + (list(hooks.tabs_after(api)) if hooks and hasattr(hooks, "tabs_after") else [])
        files.update(self.extra_files)                          # hooks가 api.page로 만든 독립 페이지
        ib = cfg["inbox"]
        for key, rel in self.md.images.items():                 # 탭 그림은 site_dir/tabimg/에 복사해 같이 게시
            dst, srcf = site / key, self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or dst.read_bytes() != srcf.read_bytes():
                dst.write_bytes(srcf.read_bytes())
            files[key] = str(dst.relative_to(self.root)).replace("\\", "/")
        if ib["enabled"] and not any('id="inbox-list"' in x[2] for _, _, subs in tops for x in subs):
            tops.append(("inbox", ib["tab_label"], [("list", ib["tab_label"],
                         f'<h2>{esc(ib["list_title"])}</h2><p>{esc(ib["list_intro"])}</p><div id="inbox-list"><p class="meta">…</p></div>')]))

        nav = '<nav class="top" role="tablist">' + "".join(
            f'<button type="button" role="tab" data-t="{t}" aria-selected="false">{esc(l)}</button>' for t, l, _ in tops) + "</nav>"
        panes, full, tabs_dir, tab_dig = [], [], site / "tabs", {}
        lazy = cfg.get("lazy_tabs")
        for t, l, subs in tops:
            sn = '<nav class="sub" role="tablist">' + "".join(
                f'<button type="button" role="tab" data-s="{x[0]}" aria-selected="false">{esc(x[1])}</button>' for x in subs) + "</nav>"
            if len(subs) == 1 and cfg["hide_single_sub"]:
                sn = sn.replace('<nav class="sub"', '<nav class="sub one"', 1)
            secs = []
            for x in subs:                                       # 작은 탭 = (토큰, 이름, html[, 원본 md]) — 4번째 값은 1.5.0 노트용
                s, sl, h = x[:3]                                 # 4번째가 None이면 탭 자체는 노트 문서가 아님 (안에 api.doc_block이 여럿 있을 때)
                none = len(x) > 3 and x[3] is None
                attrs = "" if none else self.reg_doc(f"{t}-{s}", sl, self.rel(x[3]) if len(x) > 3 else "")
                secs.append(f'<section class="panel" id="sub-{t}-{s}"{attrs} hidden>{"" if none else self.srcbar(f"{t}-{s}")}{h}</section>')
            body = "".join(secs)
            full.append(f'<div id="top-{t}" hidden>{sn}{body}</div>')
            if lazy:
                tabs_dir.mkdir(parents=True, exist_ok=True)
                (tabs_dir / f"{t}.html").write_text(body, encoding="utf-8")
                files[f"tabs/{t}.html"] = (tabs_dir / f"{t}.html").relative_to(self.root).as_posix()
                tab_dig[t] = hashlib.sha256(body.encode("utf-8")).hexdigest()
                panes.append(f'<div id="top-{t}" hidden data-src="tabs/{t}.html">{sn}<p class="lazy meta">불러오는 중…</p></div>')
            else:
                panes.append(full[-1])
        body = nav + "\n".join(panes)
        content = nav + "\n".join(full)                       # 변경 판단은 탭 내용 전체로 함
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        inner = ('<header>' + (f'<span class="label">{esc(cfg["kicker"])}</span>' if cfg["kicker"] else "")
                 + f'<h1>{esc(cfg["title"])}</h1><p class="meta">{esc(S["generated"])} {now}'
                 + (" · " + cfg["header_note"] if cfg["header_note"] else "") + '</p></header>' + body)
        out.write_text(shell(cfg["page_title"] or cfg["title"], inner, cfg["lang"], cfg["extra_css"]) + NAV_JS + ijs, encoding="utf-8")
        (site / "index.html").write_text(shell(cfg["page_title"] or cfg["title"], inner, cfg["lang"], cfg["extra_css"], standalone=True)
                                         .replace("</body></html>", NAV_JS + ijs + "</body></html>"), encoding="utf-8")

        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        changed_tabs = []
        if lazy:                                                 # 바뀐 탭 파일 목록 (갱신 게시 때 이 파일만 files로 넘김)
            mf = tabs_dir / "manifest.json"
            old_tabs = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
            mf.write_text(json.dumps(tab_dig, ensure_ascii=False, indent=0), encoding="utf-8")
            changed_tabs = [k for k, v in tab_dig.items() if old_tabs.get(k) != v]
        old = hashf.read_text(encoding="utf-8").strip() if hashf.exists() else ""
        hashf.write_text(digest, encoding="utf-8")
        if self.notes_on():                                      # 노트 사본을 만들 때 쓰는 문서 등록부 (--notes-sync)
            (site / "notes_docs.json").write_text(json.dumps(self.docs, ensure_ascii=False, indent=1), encoding="utf-8")
        fj = site / "files.json"
        pdig = hashlib.sha256(json.dumps({k: v for k, v in files.items() if not k.startswith("tabs/")}, sort_keys=True, ensure_ascii=False).encode() +
                              b"".join((self.root / v).read_bytes() for k, v in sorted(files.items()) if k.endswith(".html") and not k.startswith("tabs/"))).hexdigest()
        pold = json.loads(fj.read_text(encoding="utf-8")).get("digest", "") if fj.exists() else ""
        fj.write_text(json.dumps({"digest": pdig, "files": files}, ensure_ascii=False, indent=1), encoding="utf-8")
        nimg = sum(1 for k in files if k.startswith("papers/img/"))
        ntab = sum(1 for k in files if k.startswith("tabimg/"))
        extra = hooks.stats(api) if hooks and hasattr(hooks, "stats") else ""
        print(f"engine={ENGINE_VERSION} tops={len(tops)} papers={len(files) - nimg - ntab} images={nimg} tabimg={ntab} {extra}".rstrip())
        if lazy:
            print("tabs changed: " + (",".join(f"tabs/{k}.html" for k in changed_tabs) or "-"))
        print("index " + ("changed" if digest != old else "unchanged"))
        print("papers " + ("changed" if pdig != pold else "unchanged"))


# ---------------------------------------------------------------- 1.5.0 노트 → md 사본
def md_plain(s):
    """md 한 덩어리를 화면 글자에 가깝게: 링크·그림·HTML 태그·표 구분선 제거"""
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"<[^>]+>", "", s)
    return norm_text(s)


def md_blocks(text):
    """md를 덩어리(문단·제목·목록 전체·표 전체·인용·코드·수식 블록)로 나눔 → [(시작줄, 끝줄)] (끝줄 포함)"""
    lines, out, i = text.split("\n"), [], 0
    if lines and lines[0].strip() == "---":                   # YAML 머리말
        j = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), 0)
        i = j + 1
    kind = lambda ln: ("blank" if not ln.strip() else "fence" if ln.strip().startswith("```") else "math" if ln.strip().startswith("$$")
                       else "head" if re.match(r"^#{1,6}\s", ln) else "quote" if ln.startswith(">") else "table" if ln.lstrip().startswith("|")
                       else "list" if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln) else "para")
    while i < len(lines):
        k = kind(lines[i])
        if k == "blank":
            i += 1
            continue
        s = i
        if k in ("fence", "math"):
            end = "```" if k == "fence" else "$$"
            if not (k == "math" and lines[i].strip().endswith("$$") and len(lines[i].strip()) > 2):
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(end) and not (k == "math" and lines[i].strip().endswith("$$")):
                    i += 1
        elif k == "head":
            pass
        else:
            while i + 1 < len(lines):
                nk = kind(lines[i + 1])
                if nk == k or (k == "list" and nk == "para" and lines[i + 1].startswith((" ", "\t"))):
                    i += 1
                elif k == "list" and nk == "blank" and i + 2 < len(lines) and kind(lines[i + 2]) == "list":
                    i += 2
                else:
                    break
        out.append((s, i))
        i += 1
    return lines, out


def note_items(raw):
    """ArtifactData 목록 출력이나 내보낸 JSON을 [{id, ...필드}]로 맞춤"""
    if isinstance(raw, dict):
        for k in ("documents", "docs", "items", "results", "data"):
            if isinstance(raw.get(k), list):
                raw = raw[k]
                break
        else:
            raw = [dict(v, id=k) for k, v in raw.items() if isinstance(v, dict)]
    out = []
    for x in raw or []:
        if not isinstance(x, dict):
            continue
        d = dict(x.get("data") or x.get("fields") or {}) if isinstance(x.get("data") or x.get("fields"), dict) else dict(x)
        d["id"] = x.get("id") or x.get("doc_id") or d.get("id") or ""
        if d.get("deleted"):
            continue
        out.append(d)
    return out


def local_time(iso):
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso or "")[:16].replace("T", " ")


def callout(n, depth=1):
    """노트 하나 → Obsidian 콜아웃 줄들"""
    pre = "> " * depth
    out, qa = [], [x for x in (n.get("qa") or []) if isinstance(x, dict)]
    quote = re.sub(r"\s+", " ", str(n.get("quote") or "")).strip()
    when = local_time(n.get("created"))
    if qa:
        out.append(f"{pre}[!question]+ Q. {re.sub(r'\s+', ' ', str(qa[0].get('q', ''))).strip()}")
    else:
        out.append(f"{pre}[!note]+ 📝 내 메모")
    out.append(f"{pre}*{when} · 보고판 노트" + (f' · 선택한 부분: "{quote[:300]}"' if quote else "") + "*")
    for k, x in enumerate(qa):
        if k:
            out += [pre.rstrip(), f"{pre}**Q{k + 1}. {re.sub(r'\s+', ' ', str(x.get('q', ''))).strip()}**"]
        out.append(pre.rstrip())
        ans = re.sub(r"(?m)^\s*#{1,6}\s+(.+)$", r"**\1**", str(x.get("a", "")).strip())   # 답 속 제목은 굵은 글씨로 (콜아웃 안에서 너무 커지지 않게)
        out += [(pre + ln) if ln.strip() else pre.rstrip() for ln in ans.split("\n")]
    memo = str(n.get("memo") or "").strip()
    if memo and qa:
        out += [pre.rstrip(), f"{pre}> [!note] 📝 내 메모"] + [(f"{pre}> " + ln) if ln.strip() else f"{pre}>" for ln in memo.split("\n")]
    elif memo:
        out += [pre.rstrip()] + [(pre + ln) if ln.strip() else pre.rstrip() for ln in memo.split("\n")]
    return out


def notes_sync(cfg_path, notes_json):
    """db 노트 목록(JSON 파일) → 원본 md마다 '원본 + 노트 콜아웃' 사본, 노트 모음 md, 동기화 표시용 batch 파일.
    원본 md는 읽기만 함. 사본은 매번 원본에서 새로 만들므로 사본을 손으로 고치면 다음 동기화 때 덮어씀."""
    b = Board(cfg_path)
    n_cfg = b.cfg["notes"]
    if not n_cfg.get("md_dir"):
        sys.exit("notes.md_dir 설정이 없습니다.")
    out_dir = b.p(n_cfg["md_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    reg_f = b.p(b.cfg["site_dir"]) / "notes_docs.json"
    reg = json.loads(reg_f.read_text(encoding="utf-8")) if reg_f.exists() else {}
    src_p = pathlib.Path(notes_json)
    iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")   # 읽기 시점. 페이지의 toISOString()과 같은 꼴 (문자열 비교용)
    if src_p.is_dir():                                         # ArtifactData list의 out_dir 덤프: <dir>/<id>.json (또는 <dir>/notes/<id>.json)
        d = src_p / n_cfg["collection"] if (src_p / n_cfg["collection"]).is_dir() else src_p
        raw = [dict(json.loads(f.read_text(encoding="utf-8")), id=f.stem) for f in sorted(d.glob("*.json"))]
    else:
        raw = json.loads(src_p.read_text(encoding="utf-8"))
    notes = note_items(raw)
    now = datetime.datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M")
    by_doc = {}
    for n in sorted(notes, key=lambda x: str(x.get("created", ""))):
        by_doc.setdefault(n.get("doc", ""), []).append(n)
    written, lost_total = [], 0
    for doc, ns in by_doc.items():
        info = reg.get(doc) or {}
        md = info.get("md") or ns[0].get("md") or ""
        src = b.root / md if md else None
        if not (src and src.is_file()):
            continue
        lines, blocks = md_blocks(src.read_text(encoding="utf-8").replace("\r\n", "\n"))
        norms = [md_plain("\n".join(lines[s:e + 1])) for s, e in blocks]
        after, lost, whole = {}, [], []
        for n in ns:
            if not n.get("quote") and not n.get("bnorm"):         # 문서 전체에 단 노트 → 맨 위
                whole.append(n)
                continue
            q, bn = norm_text(str(n.get("quote") or "")), str(n.get("bnorm") or "")
            hit = None
            if len(q) >= 4:
                hit = next((k for k, t in enumerate(norms) if q in t and (not bn or bn[:20] in t)), None)
                hit = hit if hit is not None else next((k for k, t in enumerate(norms) if q in t), None)
            if hit is None and len(bn) >= 8:
                hit = next((k for k, t in enumerate(norms) if bn[:40] in t or (len(t) >= 8 and t in bn)), None)
            (after.setdefault(hit, []).append(n) if hit is not None else lost.append(n))
        top = blocks[0][0] if blocks else len(lines)
        res = lines[:top] + [f"> [!info] 노트 사본 — 원본 `{md}` 에 보고판에서 단 질문·답·메모를 붙인 파일입니다 (마지막 동기화 {stamp}).",
                             "> 원본은 바뀌지 않습니다. 메모를 고치려면 보고판에서 고치세요. 이 파일을 직접 고치면 다음 동기화 때 덮어씁니다.", ""]
        for n in whole:
            res += callout(n) + [""]
        for k, (s, e) in enumerate(blocks):
            res += lines[s:e + 1]
            for n in after.get(k, []):
                res += [""] + callout(n) + [""]
            nxt = blocks[k + 1][0] if k + 1 < len(blocks) else len(lines)
            res += lines[e + 1:nxt]
        if lost:
            res += ["", "## 위치를 찾지 못한 노트", "", "원본 문장이 바뀌어 붙일 자리를 찾지 못한 노트입니다.", ""]
            for n in lost:
                res += callout(n) + [""]
        dst = b.root / (info.get("copy") or b.doc_copy(doc, md))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("\n".join(res).rstrip() + "\n", encoding="utf-8")
        written.append((doc, info.get("title") or ns[0].get("title") or doc, dst, len(ns)))
        lost_total += len(lost)
    # 노트 모음 (문서별)
    idx = [f"# 내 노트 모음", "", f"> 보고판에서 단 질문·답·메모 전체입니다. 마지막 동기화 {stamp}, 노트 {len(notes)}개.", ""]
    for doc, ns in by_doc.items():
        info = reg.get(doc) or {}
        title = info.get("title") or ns[0].get("title") or doc
        copy = info.get("copy") or ""
        idx += [f"## {title}", ""]
        if copy:
            idx += [f"- 노트 사본: [{pathlib.PurePosixPath(copy).name}](<{pathlib.PurePosixPath(copy).name}>)", ""]
        for n in ns:
            idx += callout(n) + [""]
    (out_dir / "00_노트 모음.md").write_text("\n".join(idx).rstrip() + "\n", encoding="utf-8")
    keep = {d.resolve() for _, _, d, _ in written}               # 노트가 모두 지워진 문서의 옛 사본은 지움 (이 함수가 만든 <doc>__*.md만)
    for f in out_dir.glob("*__*.md"):
        if f.resolve() not in keep:
            f.unlink()
            print(f"removed {b.rel(f) or f}")
    meta = {"time": iso, "notes": len(notes), "docs": len(written)}
    (out_dir / ".sync.json").write_text(json.dumps(dict(meta, local=stamp), ensure_ascii=False), encoding="utf-8")
    # 페이지에 '반영됨'을 알리는 문서 하나: db <collection>_meta/sync ← 이 파일 (ArtifactData set, file_path)
    (out_dir / ".sync_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    for doc, title, dst, k in written:
        print(f"wrote {b.rel(dst) or dst}  ({k} notes)")
    print(f"notes={len(notes)} docs={len(written)} lost={lost_total}")
    print(f"meta: collection={n_cfg['collection']}_meta doc_id=sync file={out_dir / '.sync_meta.json'}")


def init(project, title):
    project = pathlib.Path(project).resolve()
    cfgf = project / "board.config.json"
    if cfgf.exists():
        sys.exit(f"이미 있음: {cfgf}")
    tpl = json.loads((HERE.parent / "templates" / "board.config.json").read_text(encoding="utf-8"))
    tpl["title"] = title or tpl["title"]
    cfgf.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    first = project / tpl["src_dir"] / "01_main_개요"
    first.mkdir(parents=True, exist_ok=True)
    (first / "01_intro_소개.md").write_text(f"# {tpl['title']}\n\n이 파일을 고치거나 같은 폴더에 md를 더하면 작은 탭이 생깁니다.\n", encoding="utf-8")
    print(f"created {cfgf}")
    print(f"created {first}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "--init":
        init(a[1] if len(a) > 1 else ".", a[2] if len(a) > 2 else "")
    elif a[0] == "--version":
        print(ENGINE_VERSION)
    elif a[0] == "--notes-sync":
        notes_sync(a[1], a[2])
    else:
        Board(a[0]).run()
