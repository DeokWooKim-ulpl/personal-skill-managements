# -*- coding: utf-8 -*-
"""artifact-board 연구 대시보드(dash) 공용: 마크다운을 '블록'(문단·표·목록·상자·수식·그림·제목)으로 나누고 HTML로 바꿈.

블록 ID = sha1(원본 상대경로 | 블록 원문)[:10]. 같은 문장이면 생성할 때마다 같은 ID가 나오므로
대시보드에서 단 질문·메모를 원본 md 사본의 같은 자리에 다시 꽂을 수 있음 (notes_sync.py).
줄 번호를 지키려고 지우는 부분(YAML 머리말, HTML 주석, pandoc 표식)은 빈 줄로 바꿈.
"""
import hashlib, html, os, re, urllib.parse

ESC = lambda s: html.escape(str(s), quote=True)


# ------------------------------------------------------------------ 전처리 (줄 수 유지)
def _blank(m):
    return "\n" * m.group(0).count("\n")


def preprocess(text):
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\A---\n.*?\n---\n", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"<!--.*?-->", _blank, text, flags=re.S)
    text = re.sub(r"```\{=openxml\}.*?```", _blank, text, flags=re.S)
    text = re.sub(r"^:::.*$", "", text, flags=re.M)
    text = text.replace(" {.unnumbered}", "").replace("⟦BR⟧", "<br>")
    return text


# ------------------------------------------------------------------ 블록 나누기
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
IMG_RE = re.compile(r"!\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(((?:[^()\s]|\([^()]*\)|\s(?!\"))+)(?:\s+\"[^\"]*\")?\)")
OBS_RE = re.compile(r"!\[\[([^\]]+)\]\]")


def split_blocks(text):
    """[(kind, first_line, last_line, raw)] — 줄 번호는 0부터, last_line 포함."""
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        st = i
        if re.match(r"^#{1,6}\s", s):
            out.append(("h", st, st, ln))
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                i += 1
            out.append(("code", st, min(i, n - 1), "\n".join(lines[st:i + 1])))
            i += 1
            continue
        if s.startswith("$$"):
            if s.count("$$") >= 2 and len(s) > 2:
                out.append(("math", st, st, ln))
                i += 1
                continue
            i += 1
            while i < n and "$$" not in lines[i]:
                i += 1
            out.append(("math", st, min(i, n - 1), "\n".join(lines[st:i + 1])))
            i += 1
            continue
        if s.startswith("|"):
            while i < n and lines[i].strip().startswith("|"):
                i += 1
            out.append(("table", st, i - 1, "\n".join(lines[st:i])))
            continue
        if s.startswith(">"):
            while i < n and lines[i].strip().startswith(">"):
                i += 1
            out.append(("quote", st, i - 1, "\n".join(lines[st:i])))
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            i += 1
            continue
        if LIST_RE.match(ln):
            i += 1
            while i < n:
                t = lines[i]
                if not t.strip():
                    # 빈 줄 다음에 목록이 이어지면 같은 목록
                    if i + 1 < n and (LIST_RE.match(lines[i + 1]) or lines[i + 1].startswith("  ")):
                        i += 1
                        continue
                    break
                if LIST_RE.match(t) or t.startswith(("  ", "\t")):
                    i += 1
                    continue
                break
            out.append(("list", st, i - 1, "\n".join(lines[st:i]).rstrip("\n")))
            continue
        if (IMG_RE.fullmatch(s) or OBS_RE.fullmatch(s)):
            out.append(("img", st, st, ln))
            i += 1
            continue
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|\$\$|\||>)", lines[i].strip()) \
                and not (i > st and LIST_RE.match(lines[i])):
            i += 1
        out.append(("p", st, i - 1, "\n".join(lines[st:i])))
    return out


def block_id(src_rel, raw, seen):
    norm = re.sub(r"\s+", " ", raw).strip()
    b = hashlib.sha1((src_rel + "|" + norm).encode("utf-8")).hexdigest()[:10]
    k = seen.get(b, 0)
    seen[b] = k + 1
    return b if k == 0 else f"{b}-{k}"


def blocks_with_ids(src_rel, text):
    seen = {}
    return [(block_id(src_rel, raw, seen), kind, a, b, raw) for kind, a, b, raw in split_blocks(text)]


# ------------------------------------------------------------------ 그림 찾기
class Images:
    """그림 경로 → 게시용 webp (img/<hash>.webp). 경로는 md 파일 기준, Obsidian ![[이름]]은 area 폴더에서 찾음."""

    def __init__(self, root, out_dir, max_w=1100, q=74):
        self.root, self.out_dir, self.max_w, self.q = root, out_dir, max_w, q
        self.idx, self.used = {}, {}

    def _index(self, area):
        if area not in self.idx:
            m = {}
            for dp, dn, fn in os.walk(os.path.join(self.root, area)):
                dn[:] = [d for d in dn if d not in ("완료", "__pycache__")]
                for f in fn:
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                        m.setdefault(f, []).append(os.path.join(dp, f))
            self.idx[area] = m
        return self.idx[area]

    def find(self, area, name, prefer=""):
        m = self._index(area)
        names = [name[:-7] + ".jpg", name] if name.endswith("_py.jpg") else [name]
        for nm in names:
            c = m.get(nm, [])
            if c:
                return sorted(c, key=lambda p: (prefer not in p if prefer else 0, "(수정)" not in p, len(p)))[0]
        return None

    def publish(self, path):
        from PIL import Image
        st = os.stat(path)
        key = hashlib.sha1(f"{path}|{st.st_mtime}|{self.max_w}".encode("utf-8")).hexdigest()[:14]
        rel = f"img/{key}.webp"
        out = os.path.join(self.out_dir, rel)
        if not os.path.exists(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
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
            im.save(out, "WEBP", quality=self.q, method=6)
        self.used[rel] = path
        return rel


# ------------------------------------------------------------------ HTML 변환
class Renderer:
    def __init__(self, images, base_dir, area, prefer=""):
        self.images, self.base, self.area, self.prefer = images, base_dir, area, prefer

    def _img(self, alt, url):
        url = urllib.parse.unquote(url.strip())
        if url.startswith(("http:", "https:", "data:")):
            return ""
        p = os.path.normpath(os.path.join(self.base, url))
        if not os.path.isfile(p):                                  # 프로젝트 루트 기준 경로 (예: 97_논문/…/Fig1.png)
            p = os.path.normpath(os.path.join(self.images.root, url))
        if not os.path.isfile(p):
            p = self.images.find(self.area, os.path.basename(url), self.prefer) or ""
        if not p or not os.path.isfile(p):
            return f'<p class="miss">[그림 없음: {ESC(os.path.basename(url))}]</p>'
        src = self.images.publish(p)
        cap = f"<figcaption>{self.inline(alt, figs=False)}</figcaption>" if alt else ""
        return f'<figure><img loading="lazy" src="{src}" alt="">{cap}</figure>'

    def _obs(self, name):
        name = name.split("|")[0].strip()
        p = self.images.find(self.area, os.path.basename(name), self.prefer)
        if not p:
            return f'<p class="miss">[그림 없음: {ESC(name)}]</p>'
        return f'<figure><img loading="lazy" src="{self.images.publish(p)}" alt=""></figure>'

    def inline(self, s, figs=True):
        keep, fg = [], []

        def stash(m):
            keep.append(m.group(0))
            return f"\x00{len(keep) - 1}\x00"

        def fig(m):
            fg.append(self._img(m.group(1), m.group(2)) if figs else "")
            return f"\x01{len(fg) - 1}\x01"

        def obs(m):
            fg.append(self._obs(m.group(1)) if figs else "")
            return f"\x01{len(fg) - 1}\x01"
        codes = []

        def code(m):
            codes.append("<code>" + ESC(m.group(1)) + "</code>")
            return f"\x02{len(codes) - 1}\x02"
        s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)   # OCR 찌꺼기 제어문자 (자리표시 \x00~\x02 와 겹치면 깨짐)
        s = re.sub(r"`([^`]+)`", code, s)
        s = IMG_RE.sub(fig, s)
        s = OBS_RE.sub(obs, s)
        s = re.sub(r"\$\$.+?\$\$|(?<![\\$])\$[^$\n]+?\$", stash, s)
        s = ESC(s)
        s = re.sub(r"&lt;br\s*/?&gt;", "<br>", s)
        s = re.sub(r"&lt;(/?)(sup|sub)&gt;", r"<\1\2>", s)
        s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
        s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
        s = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", s)

        def link(m):
            text, url = m.group(1), html.unescape(m.group(2))
            if url.startswith("http"):
                return f'<a href="{ESC(url)}" target="_blank" rel="noopener">{text}</a>'
            return f'<span class="lnk" title="{ESC(urllib.parse.unquote(url))}">{text}</span>'
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
        s = re.sub(r"\x00(\d+)\x00", lambda m: ESC(keep[int(m.group(1))]), s)
        s = re.sub(r"\x02(\d+)\x02", lambda m: codes[int(m.group(1))], s)
        return re.sub(r"\x01(\d+)\x01", lambda m: fg[int(m.group(1))], s)

    # -- 블록별
    def table(self, raw):
        rows = [r for r in raw.split("\n") if r.strip()]
        cells = lambda r: [c.strip() for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
        head = cells(rows[0])
        body = [cells(r) for r in rows[2:]] if len(rows) > 1 and re.match(r"^\|?\s*:?-{2,}", rows[1].strip()) else [cells(r) for r in rows[1:]]
        t = ['<div class="tbl"><table><thead><tr>' + "".join(f"<th>{self.inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
        for r in body:
            t.append("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in r) + "</tr>")
        return "".join(t) + "</tbody></table></div>"

    def lst(self, raw):
        items, stack, out = [], [], []
        cur = None
        for ln in raw.split("\n"):
            m = LIST_RE.match(ln)
            if m:
                cur = [len(m.group(1).replace("\t", "    ")), m.group(2)[0].isdigit(), ln[m.end():]]
                items.append(cur)
            elif cur is not None and ln.strip():
                cur[2] += " " + ln.strip()
        for ind, ordered, txt in items:
            while stack and ind < stack[-1][0]:
                out.append("</li></ol>" if stack.pop()[1] else "</li></ul>")
            if not stack or ind > stack[-1][0]:
                out.append("<ol>" if ordered else "<ul>")
                stack.append((ind, ordered))
            else:
                out.append("</li>")
            out.append("<li>" + self.inline(txt))
        while stack:
            out.append("</li></ol>" if stack.pop()[1] else "</li></ul>")
        return "".join(out)

    CO = {"abstract": "보충 개념", "example": "해설", "warning": "주의", "question": "질문", "info": "안내",
          "tip": "팁", "note": "메모", "important": "중요"}

    def quote(self, raw):
        body = [re.sub(r"^\s*>\s?", "", l) for l in raw.split("\n")]
        m = re.match(r"^\[!(\w+)\]([-+]?)\s*(.*)$", body[0]) if body else None
        inner = self.render_plain("\n".join(body[1:] if m else body))
        if not m:
            return f"<blockquote>{inner}</blockquote>"
        kind, fold, title = m.group(1).lower(), m.group(2), m.group(3).strip() or self.CO.get(m.group(1).lower(), m.group(1))
        opn = "" if (fold == "-" or kind == "note") else " open"
        return f'<details class="co co-{ESC(kind)}"{opn}><summary>{self.inline(title)}</summary>{inner}</details>'

    def block(self, kind, raw):
        if kind == "h":
            m = re.match(r"^\s*(#{1,6})\s+(.*)$", raw)
            lv = min(len(m.group(1)), 6)
            return f"<h{lv}>{self.inline(m.group(2).strip())}</h{lv}>"
        if kind == "code":
            body = "\n".join(raw.split("\n")[1:-1])
            return f"<pre><code>{ESC(body)}</code></pre>"
        if kind == "math":
            return f'<div class="mathd">{ESC(raw.strip())}</div>'
        if kind == "table":
            return self.table(raw)
        if kind == "quote":
            return self.quote(raw)
        if kind == "list":
            return self.lst(raw)
        if kind == "img":
            return self.inline(raw.strip())
        return "<p>" + self.inline(raw.replace("\n", " ")) + "</p>"

    def render_plain(self, text):
        return "".join(self.block(k, raw) for k, a, b, raw in split_blocks(text))
