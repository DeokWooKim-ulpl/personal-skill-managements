#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eqfix.py - Word(.docx) / PowerPoint(.pptx) 의 텍스트 수식을 네이티브 수식 개체로 바꾸는 도구.

사용법 (3단계):
    python eqfix.py scan  문서.docx                 # 1) 문단 목록 + 수식 후보 출력 (JSON)
    python eqfix.py apply 문서.docx plan.json       # 2) plan 대로 치환 -> 문서_eq.docx (원본은 그대로)
    python eqfix.py check 문서_eq.docx              # 3) 남아 있는 ^, _ 등 잔여 표기 검사

plan.json 형식 (리스트):
    [
      {"para": "p12", "find": "E = mc^2", "latex": "E=mc^{2}"},
      {"para": "p15", "find": "n_eff = 1.45", "latex": "n_{\\mathrm{eff}}=1.45", "display": true},
      {"para": "p20", "find": "cm^-1", "rich": "cm^{-1}"}
    ]
  - para    : scan 이 알려준 문단 ID
  - find    : 그 문단의 raw 텍스트 안에서 바꿀 부분 (정확히 일치해야 함)
  - latex   : 수식 개체(수식 탭)로 넣을 LaTeX
  - rich    : 수식 개체 대신 "진짜 위첨자/아래첨자 서식"으로 넣을 텍스트. ^{..} 위첨자, _{..} 아래첨자
  - display : true 면 가운데 정렬된 독립 수식 (문단 전체가 수식일 때만 적용)
  - nth     : 같은 find 가 문단에 여러 번 나오면 몇 번째인지 (1부터, 기본 1)

필요한 것: python3, lxml, pandoc (LaTeX -> Office 수식 변환에 사용)
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from lxml import etree

# ---------------------------------------------------------------- 네임스페이스
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "a14": "http://schemas.microsoft.com/office/drawing/2010/main",
}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MATH_FONT = "Cambria Math"


def q(tag):
    """'w:r' -> '{namespace}r' (lxml 이 쓰는 이름 형식)"""
    prefix, name = tag.split(":")
    return "{%s}%s" % (NS[prefix], name)


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


# ---------------------------------------------------------------- 문서 열기/저장
class Package:
    """docx/pptx 는 zip 파일임. 필요한 XML 파트만 고쳐서 새 zip 으로 저장함."""

    def __init__(self, path):
        self.path = path
        self.kind = "docx" if path.lower().endswith((".docx", ".docm")) else "pptx"
        if not path.lower().endswith((".docx", ".docm", ".pptx", ".pptm")):
            sys.exit("지원 형식: .docx / .pptx (구형 .doc/.ppt 는 먼저 새 형식으로 저장할 것)")
        self.zin = zipfile.ZipFile(path)
        self.trees = {}  # 파트 이름 -> 파싱된 XML

    def part_names(self):
        names = self.zin.namelist()
        if self.kind == "docx":
            pat = re.compile(r"word/(document|footnotes|endnotes|header\d*|footer\d*)\.xml$")
            order = lambda n: (0 if n == "word/document.xml" else 1, n)
        else:
            pat = re.compile(r"ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml$")
            order = lambda n: (0 if "/slides/" in n else 1, int(re.search(r"(\d+)\.xml$", n).group(1)))
        return sorted([n for n in names if pat.match(n)], key=order)

    def tree(self, name):
        if name not in self.trees:
            self.trees[name] = etree.fromstring(self.zin.read(name))
        return self.trees[name]

    def save(self, out_path):
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in self.zin.infolist():
                if item.filename in self.trees:
                    data = etree.tostring(self.trees[item.filename], xml_declaration=True,
                                          encoding="UTF-8", standalone=True)
                else:
                    data = self.zin.read(item.filename)
                zout.writestr(item, data)


# ---------------------------------------------------------------- 문단/런 읽기
def part_prefix(kind, name):
    """문단 ID 앞부분. docx 본문은 접두사 없음, pptx 는 s3(3번 슬라이드) 등."""
    base = os.path.basename(name)[:-4]
    if kind == "docx":
        return "" if base == "document" else base + "/"
    num = re.search(r"(\d+)$", base).group(1)
    return ("s" if "notes" not in base else "n") + num + "/"


def iter_paragraphs(pkg):
    """(문단ID, 파트이름, 문단요소) 를 문서 순서대로 돌려줌."""
    ptag = q("w:p") if pkg.kind == "docx" else q("a:p")
    for name in pkg.part_names():
        prefix = part_prefix(pkg.kind, name)
        # mc:Fallback(구버전용 사본) 문단은 번호에서 빼야 치환 전후 ID 가 같게 유지됨
        live = [p for p in pkg.tree(name).iter(ptag) if not in_fallback(p)]
        for i, p in enumerate(live):
            yield "%sp%d" % (prefix, i), name, p


def in_fallback(el):
    """mc:Fallback 안쪽(구버전용 사본)은 건드리지 않음."""
    return any(a.tag == q("mc:Fallback") for a in el.iterancestors())


def para_runs(p, kind):
    """문단 안의 텍스트 런 목록. 수식 개체 안쪽 런은 제외."""
    rtag = q("w:r") if kind == "docx" else q("a:r")
    runs = []
    for r in p.iter(rtag):
        skip = False
        for anc in r.iterancestors():
            if anc is p:
                break
            if anc.tag in (q("w:p"), q("a:p"), q("m:oMath"), q("w:txbxContent")):
                skip = True  # 중첩 문단(텍스트 상자)·수식 내부
                break
        if not skip:
            runs.append(r)
    return runs


def run_text(r, kind):
    if kind == "docx":
        out = []
        for c in r:
            if c.tag == q("w:t"):
                out.append(c.text or "")
            elif c.tag == q("w:tab"):
                out.append("\t")
        return "".join(out)
    t = r.find(q("a:t"))
    return (t.text or "") if t is not None else ""


def run_script(r, kind):
    """런의 위첨자/아래첨자 서식: 'sup' / 'sub' / ''"""
    if kind == "docx":
        v = r.find("w:rPr/w:vertAlign", NS)
        val = v.get(q("w:val")) if v is not None else ""
        return {"superscript": "sup", "subscript": "sub"}.get(val, "")
    rpr = r.find(q("a:rPr"))
    b = int(rpr.get("baseline", "0").rstrip("%") or 0) if rpr is not None else 0
    return "sup" if b > 0 else ("sub" if b < 0 else "")


def para_texts(p, kind):
    """(raw 텍스트, 위/아래첨자 서식을 ^{ } _{ } 로 표시한 텍스트)"""
    raw, marked = [], []
    for r in para_runs(p, kind):
        t = run_text(r, kind)
        s = run_script(r, kind)
        raw.append(t)
        marked.append(("^{%s}" if s == "sup" else "_{%s}" if s == "sub" else "%s") % t if t else "")
    return "".join(raw), "".join(marked)


# 수식 후보를 찾는 간단한 규칙 (최종 판단은 사람이/Claude 가 함)
CAND = re.compile(
    r"[\^]|[A-Za-z0-9\)\}]_[A-Za-z0-9\{\(]|\\[A-Za-z]+|[=≈≠≤≥±×÷∝∞∑∫∂∇√→]"
    r"|[α-ωΑ-Ω]|[⁰¹²³⁴-⁹⁺⁻₀-₉]|\bsqrt\b|\$[^$]+\$")


# ---------------------------------------------------------------- scan
def cmd_scan(args):
    pkg = Package(args.file)
    rows, n_math, n_ole = [], 0, 0
    for name in pkg.part_names():
        root = pkg.tree(name)
        n_math += sum(1 for e in root.iter(q("m:oMath")) if not in_fallback(e))
        xml = pkg.zin.read(name)
        n_ole += len(re.findall(rb'ProgID="Equation\.[^"]*"|progId="Equation\.[^"]*"', xml))
    for pid, name, p in iter_paragraphs(pkg):
        if in_fallback(p):
            continue
        raw, marked = para_texts(p, pkg.kind)
        if not raw.strip():
            continue
        cand = bool(CAND.search(raw)) or raw != marked
        if args.all or cand:
            row = {"para": pid, "text": raw}
            if raw != marked:
                row["marked"] = marked  # 이미 위/아래첨자 서식이 걸린 부분 표시
            if args.all:
                row["candidate"] = cand
            if p.find(".//" + q("m:oMath")) is not None:
                row["has_equation"] = True
            rows.append(row)
    result = {
        "file": args.file, "kind": pkg.kind,
        "existing_equation_objects": n_math,
        "legacy_ole_equations": n_ole,  # 구형 수식 편집기 개체(그림처럼 박힌 수식) - 자동 변환 불가
        "paragraphs": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("scan 결과 저장: %s (문단 %d개)" % (args.out, len(rows)))
    else:
        print(text)


# ---------------------------------------------------------------- LaTeX -> OMML
def latex_to_omml(items):
    """items: [(key, latex, display)] -> {key: m:oMath 요소}. 실패한 key 는 빠짐.

    pandoc 으로 '마커 문단 + 수식 문단' 이 반복되는 임시 docx 를 만들고,
    거기서 Office 수식 XML(m:oMath)만 꺼내 옴.
    """
    if not items:
        return {}, {}
    if not shutil.which("pandoc"):
        sys.exit("pandoc 이 필요함. 설치: https://pandoc.org/installing.html "
                 "(또는 pip install pypandoc_binary 후 pandoc 경로 추가)")
    md = []
    for key, latex, display in items:
        d = "$$" if display else "$"
        md.append("EQMARK%s\n\n%s%s%s\n" % (key, d, latex.strip(), d))
    tmp = tempfile.mkdtemp()
    try:
        src, dst = os.path.join(tmp, "eq.md"), os.path.join(tmp, "eq.docx")
        with open(src, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        proc = subprocess.run(
            ["pandoc", src, "-f", "markdown+tex_math_dollars-smart", "-t", "docx", "-o", dst],
            capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit("pandoc 실패:\n" + proc.stderr)
        body = etree.fromstring(zipfile.ZipFile(dst).read("word/document.xml")).find(q("w:body"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    found, key = {}, None
    for para in body.iter(q("w:p")):
        text = "".join(t.text or "" for t in para.iter(q("w:t")))
        mk = re.match(r"EQMARK(\S+)", text)
        if mk:
            key = mk.group(1)
            continue
        om = para.find(".//" + q("m:oMath"))
        if om is not None and key is not None and key not in found:
            found[key] = om
    errors = {k: "LaTeX 를 변환하지 못함 (문법/미지원 명령 확인): " + l
              for k, l, _ in items if k not in found}
    return found, errors


def style_math(omath, kind, src_run):
    """수식 글꼴(Cambria Math)을 지정하고, 원래 글자의 크기·색을 물려줌."""
    for el in list(omath.iter()):
        if isinstance(el.tag, str) and etree.QName(el).namespace == NS["w"]:
            el.getparent().remove(el)
    if kind == "docx":
        src = src_run.find(q("w:rPr")) if src_run is not None else None
        for r in omath.iter(q("m:r")):
            rpr = etree.Element(q("w:rPr"))
            f = etree.SubElement(rpr, q("w:rFonts"))
            f.set(q("w:ascii"), MATH_FONT)
            f.set(q("w:hAnsi"), MATH_FONT)
            if src is not None:
                for tag in ("w:color", "w:sz", "w:szCs", "w:highlight"):
                    e = src.find(q(tag))
                    if e is not None:
                        rpr.append(copy.deepcopy(e))
            mrpr = r.find(q("m:rPr"))
            r.insert(0 if mrpr is None else 1, rpr)
    else:
        src = src_run.find(q("a:rPr")) if src_run is not None else None

        def make(italic):
            rpr = etree.Element(q("a:rPr"))
            if src is not None:
                for att in ("lang", "sz"):
                    if src.get(att):
                        rpr.set(att, src.get(att))
            if "lang" not in rpr.attrib:
                rpr.set("lang", "en-US")
            rpr.set("i", "1" if italic else "0")
            if src is not None:
                fill = src.find(q("a:solidFill"))
                if fill is not None:
                    rpr.append(copy.deepcopy(fill))
            lat = etree.SubElement(rpr, q("a:latin"))
            lat.set("typeface", MATH_FONT)
            lat.set("panose", "02040503050406030204")
            lat.set("pitchFamily", "18")
            lat.set("charset", "0")
            return rpr

        for r in omath.iter(q("m:r")):
            sty = r.find("m:rPr/m:sty", NS)
            upright = sty is not None and sty.get(q("m:val")) in ("p", "b")
            mrpr = r.find(q("m:rPr"))
            r.insert(0 if mrpr is None else 1, make(not upright))
        for c in omath.iter(q("m:ctrlPr")):
            c.append(make(True))
    return omath


# ---------------------------------------------------------------- 런 쪼개기
def set_run_text(r, kind, text):
    """런의 글자를 text 로 교체 (서식은 유지)."""
    if kind == "docx":
        for c in list(r):
            if c.tag in (q("w:t"), q("w:tab")):
                r.remove(c)
        for i, piece in enumerate(text.split("\t")):
            if i:
                etree.SubElement(r, q("w:tab"))
            if piece:
                t = etree.SubElement(r, q("w:t"))
                t.text = piece
                t.set(XML_SPACE, "preserve")
    else:
        t = r.find(q("a:t"))
        if t is None:
            t = etree.SubElement(r, q("a:t"))
        t.text = text


def set_script(r, kind, mode):
    """런에 진짜 위첨자(sup)/아래첨자(sub) 서식을 걸거나(mode='') 해제함."""
    if kind == "docx":
        rpr = r.find(q("w:rPr"))
        if rpr is None:
            rpr = etree.Element(q("w:rPr"))
            r.insert(0, rpr)
        old = rpr.find(q("w:vertAlign"))
        if old is not None:
            rpr.remove(old)
        if mode:
            v = etree.SubElement(rpr, q("w:vertAlign"))
            v.set(q("w:val"), "superscript" if mode == "sup" else "subscript")
    else:
        rpr = r.find(q("a:rPr"))
        if rpr is None:
            rpr = etree.Element(q("a:rPr"))
            rpr.set("lang", "en-US")
            r.insert(0, rpr)
        if mode:
            rpr.set("baseline", "30000" if mode == "sup" else "-25000")
        elif "baseline" in rpr.attrib:
            del rpr.attrib["baseline"]


def parse_rich(s):
    """'cm^{-1}' -> [('cm',''), ('-1','sup')].  ^x, _x (중괄호 없는 한 글자)도 허용."""
    out, i, buf = [], 0, ""
    while i < len(s):
        ch = s[i]
        if ch in "^_" and i + 1 < len(s):
            mode = "sup" if ch == "^" else "sub"
            if s[i + 1] == "{":
                j = s.find("}", i + 2)
                if j < 0:
                    raise ValueError("rich: 닫는 } 없음: " + s)
                seg, i = s[i + 2:j], j + 1
            else:
                seg, i = s[i + 1], i + 2
            if buf:
                out.append((buf, ""))
                buf = ""
            out.append((seg, mode))
        else:
            buf += ch
            i += 1
    if buf:
        out.append((buf, ""))
    return out


def locate(p, kind, find, nth):
    """문단에서 find 의 nth 번째 위치 -> (런 목록, 시작런 index, 시작 offset, 끝런 index, 끝 offset)"""
    runs = para_runs(p, kind)
    texts = [run_text(r, kind) for r in runs]
    full = "".join(texts)
    pos = -1
    for _ in range(nth):
        pos = full.find(find, pos + 1)
        if pos < 0:
            return None
    end = pos + len(find)
    acc, si, ei, so, eo = 0, None, None, 0, 0
    for i, t in enumerate(texts):
        if si is None and pos < acc + len(t):
            si, so = i, pos - acc
        if end <= acc + len(t) and si is not None:
            ei, eo = i, end - acc
            break
        acc += len(t)
    return runs, texts, si, so, ei, eo


def replace_span(p, kind, find, nth, new_nodes_fn):
    """find 구간을 new_nodes_fn(기준 런) 이 만든 요소들로 교체. 성공하면 None, 실패하면 사유."""
    loc = locate(p, kind, find, nth)
    if loc is None:
        return "find 문자열을 문단에서 찾지 못함"
    runs, texts, si, so, ei, eo = loc
    first, last = runs[si], runs[ei]
    parent = first.getparent()
    if any(r.getparent() is not parent for r in runs[si:ei + 1]):
        return "find 구간이 하이퍼링크/변경내용 경계에 걸쳐 있음 (수동 처리 필요)"
    before, after = texts[si][:so], texts[ei][eo:]
    new_nodes = new_nodes_fn(first)
    tail_run = None
    if after:
        tail_run = copy.deepcopy(last)
        set_run_text(tail_run, kind, after)
    idx = parent.index(first)
    for r in runs[si:ei + 1]:
        parent.remove(r)
    if before:
        set_run_text(first, kind, before)
        parent.insert(idx, first)
        idx += 1
    for n in new_nodes:
        parent.insert(idx, n)
        idx += 1
    if tail_run is not None:
        parent.insert(idx, tail_run)
    return None


# ---------------------------------------------------------------- pptx 호환 래핑
def wrap_pptx_shape(p_el):
    """PowerPoint 방식대로 도형을 mc:AlternateContent 로 감쌈.

    Choice(a14) = 수식 개체가 들어간 새 도형, Fallback = 원래 텍스트 도형.
    수식을 모르는 프로그램에서도 원래 글자가 보이도록 하기 위함.
    이미 감싸진 도형이면 아무것도 하지 않음.
    """
    shape = None
    for anc in p_el.iterancestors():
        if anc.tag in (q("mc:Choice"),):
            return
        if anc.tag in (q("p:sp"), q("p:graphicFrame")):
            shape = anc
    if shape is None or shape.getparent() is None:
        return
    if shape.getparent().tag == q("mc:Choice"):
        return
    parent = shape.getparent()
    idx = parent.index(shape)
    ac = etree.Element(q("mc:AlternateContent"), nsmap={"mc": NS["mc"], "a14": NS["a14"]})
    choice = etree.SubElement(ac, q("mc:Choice"))
    choice.set("Requires", "a14")
    fb = etree.SubElement(ac, q("mc:Fallback"))
    fb.append(copy.deepcopy(shape))  # 수정 전 원본
    parent.remove(shape)
    choice.append(shape)
    parent.insert(idx, ac)


# ---------------------------------------------------------------- apply
def cmd_apply(args):
    pkg = Package(args.file)
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    paras = {pid: (name, p) for pid, name, p in iter_paragraphs(pkg)}

    # 1) LaTeX 를 한꺼번에 Office 수식으로 변환
    items = []
    for i, e in enumerate(plan):
        if "latex" in e:
            pid = e.get("para")
            whole = False
            if pid in paras:
                raw, _ = para_texts(paras[pid][1], pkg.kind)
                whole = raw.strip() == e.get("find", "").strip()
            e["_display"] = bool(e.get("display")) and whole
            if e.get("display") and not whole:
                e["_note"] = "문단에 다른 글자가 있어 줄 안(inline) 수식으로 넣음"
            items.append((str(i), e["latex"], e["_display"]))
    omml, errors = latex_to_omml(items)

    # 2) 같은 문단 안에서는 뒤쪽부터 치환해야 앞쪽 위치가 안 밀림
    def sort_key(ie):
        i, e = ie
        pid = e.get("para")
        pos = -1
        if pid in paras:
            raw, _ = para_texts(paras[pid][1], pkg.kind)
            pos = -1
            for _ in range(int(e.get("nth", 1))):
                pos = raw.find(e.get("find", ""), pos + 1)
                if pos < 0:
                    break
        return (pid or "", -pos)

    report = []
    for i, e in sorted(enumerate(plan), key=sort_key):
        pid, find = e.get("para"), e.get("find", "")
        res = {"para": pid, "find": find}
        if pid not in paras:
            res["status"], res["reason"] = "FAIL", "문단 ID 없음"
        elif not find:
            res["status"], res["reason"] = "FAIL", "find 가 비어 있음"
        elif "latex" in e and str(i) in errors:
            res["status"], res["reason"] = "FAIL", errors[str(i)]
        else:
            name, p = paras[pid]
            nth = int(e.get("nth", 1))
            if "latex" in e:
                # nth 는 치환 전 기준. 같은 문단을 뒤에서부터 고치므로 그대로 유효함.
                def make(src_run, _i=str(i), _e=e):
                    om = style_math(copy.deepcopy(omml[_i]), pkg.kind, src_run)
                    if pkg.kind == "docx":
                        if _e["_display"]:
                            para = etree.Element(q("m:oMathPara"))
                            para.append(om)
                            return [para]
                        return [om]
                    holder = etree.Element(q("a14:m"), nsmap={"a14": NS["a14"], "m": NS["m"]})
                    if _e["_display"]:
                        para = etree.SubElement(holder, q("m:oMathPara"))
                        ppr = etree.SubElement(para, q("m:oMathParaPr"))
                        etree.SubElement(ppr, q("m:jc")).set(q("m:val"), "centerGroup")
                        para.append(om)
                    else:
                        holder.append(om)
                    return [holder]

                if pkg.kind == "pptx":
                    if locate(p, pkg.kind, find, nth) is not None:
                        wrap_pptx_shape(p)
                err = replace_span(p, pkg.kind, find, nth, make)
            elif "rich" in e:
                def make(src_run, _e=e):
                    nodes = []
                    for seg, mode in parse_rich(_e["rich"]):
                        r = copy.deepcopy(src_run)
                        set_run_text(r, pkg.kind, seg)
                        set_script(r, pkg.kind, mode)
                        nodes.append(r)
                    return nodes
                try:
                    err = replace_span(p, pkg.kind, find, nth, make)
                except ValueError as ex:
                    err = str(ex)
            else:
                err = "latex 또는 rich 중 하나가 필요함"
            res["status"] = "FAIL" if err else "OK"
            if err:
                res["reason"] = err
            elif e.get("_note"):
                res["note"] = e["_note"]
        report.append((i, res))

    out = args.out or re.sub(r"(\.\w+)$", r"_eq\1", args.file)
    if os.path.abspath(out) == os.path.abspath(args.file):
        sys.exit("원본을 덮어쓸 수 없음. -o 로 다른 이름을 지정할 것.")
    pkg.save(out)
    report = [r for _, r in sorted(report, key=lambda x: x[0])]
    ok = sum(1 for r in report if r["status"] == "OK")
    for r in report:
        if r["status"] != "OK" or "note" in r:
            print(json.dumps(r, ensure_ascii=False))
    print("치환 %d/%d 성공 -> %s" % (ok, len(report), out))
    if ok != len(report):
        sys.exit(1)


# ---------------------------------------------------------------- check
RESIDUAL = re.compile(r"\^|[A-Za-z0-9\)\}]_[A-Za-z0-9\{\(]|\\[A-Za-z]{2,}|\$[^$]+\$")


def cmd_check(args):
    pkg = Package(args.file)
    n_math = 0
    for name in pkg.part_names():
        n_math += sum(1 for e in pkg.tree(name).iter(q("m:oMath")) if not in_fallback(e))
    left = []
    for pid, name, p in iter_paragraphs(pkg):
        if in_fallback(p):
            continue
        raw, _ = para_texts(p, pkg.kind)
        hits = RESIDUAL.findall(raw)
        if hits:
            left.append({"para": pid, "text": raw, "hits": hits})
    print(json.dumps({"file": args.file, "equation_objects": n_math,
                      "residual_paragraphs": left}, ensure_ascii=False, indent=1))
    print("수식 개체 %d개, 잔여 표기(^, _, \\명령, $..$) 문단 %d개" % (n_math, len(left)))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Word/PowerPoint 텍스트 수식 -> 수식 개체 변환")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="문단 목록과 수식 후보 출력")
    s.add_argument("file")
    s.add_argument("--all", action="store_true", help="후보가 아닌 문단도 모두 출력")
    s.add_argument("-o", "--out", help="결과를 JSON 파일로 저장")
    s.set_defaults(fn=cmd_scan)
    a = sub.add_parser("apply", help="plan.json 대로 치환")
    a.add_argument("file")
    a.add_argument("plan")
    a.add_argument("-o", "--out", help="출력 파일 (기본: 원본이름_eq.확장자)")
    a.set_defaults(fn=cmd_apply)
    c = sub.add_parser("check", help="잔여 ^, _ 표기 검사")
    c.add_argument("file")
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
