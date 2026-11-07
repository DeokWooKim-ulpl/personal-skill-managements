# -*- coding: utf-8 -*-
"""연구 대시보드(dash) 설정 견본 — 프로젝트로 복사해서 고침 (SKILL.md 0-2항).

    python -I "%USERPROFILE%/.claude/skills/artifact-board/engine/dash/build.py" "<이 파일>"

경로는 모두 프로젝트 루트(ROOT) 기준 상대경로. 원본 md는 읽기만 함.
넣을 내용은 최신·정리된 결과만: 할 일·받을 논문은 반드시, 논문화·설계 결과는 상세히.
"""
import datetime

TITLE = "○○ 과제 연구 대시보드"
SUBTITLE = "과제 한 줄 설명 · 기관"
ROOT = "../.."                                  # 이 파일 기준 프로젝트 루트
OUT = "보고/대시보드_site"                       # 게시할 사이트 폴더
NOTE_DIR = "보고/대시보드_노트"                   # 질문·메모가 들어간 md 사본 폴더
MANIFEST = "보고/대시보드_manifest.json"          # 노트 동기화용 (게시 안 함)
ARTIFACT_URL = ""                                # 첫 게시 뒤 적음
ASK_EXAMPLE = "예: 이 식이 왜 이렇게 되는지 쉽게 설명해 줘"
ASK_TIER = "default"                             # 답 모델 기본값: "quick"(Haiku) | "default"(Sonnet) | "complex"(Opus). 보는 사람이 화면에서 바꿀 수 있음
RULES = """너는 ○○ 과제 연구 대시보드의 해설 도우미다. 독자는 이 분야가 처음인 대학원생이다.
규칙:
- 한국어로 답한다. 배경 개념부터 차근차근, 왜 그런지(물리적 이유)를 설명한다.
- 수식은 $...$ 또는 $$...$$ LaTeX로 쓰고, 기호의 뜻을 바로 풀어 준다. 가능하면 숫자 예를 하나 든다.
- 아래 [문서 발췌]를 먼저 근거로 삼는다. 발췌에 없는 일반 지식으로 답하는 부분은 문장 끝에 "(일반 지식)"이라고 표시한다.
- 확실하지 않은 수치·인용은 지어내지 말고 "발췌에서 확인할 수 없음"이라고 말한다.
- 길이는 질문에 맞춘다(보통 400–1200자). 마지막 줄에 "한 줄 요약: ..."을 붙인다."""

# key(영문·숫자·하이픈): (제목, 원본 md, 옵션)  옵션: section, until_end, area, prefer, drop_rows
DOCS = {
    "todo": ("할 일·받을 논문", "보고/할일.md", {"drop_rows": r"\|\s*완료\s*\|?\s*$"}),
    "p1": ("논문 1 원고", "논문/P1_원고.md", {}),
    "d1": ("설계서 1", "설계서/D1.md", {"area": "설계서"}),
}

VIEWS = [
    {"group": "오늘", "items": [{"id": "today", "title": "할 일·받을 논문", "summary": True, "tabs": [["todo", "할 일"]]}]},
    {"group": "논문화", "items": [{"id": "p1", "title": "논문 1", "tabs": [["p1", "원고"]],
                                  "notice": "최신 결정 한 줄 (없으면 이 키를 지움)", "files": ["논문/P1_원고.md"]}]},
    {"group": "설계서", "items": [{"id": "d1", "title": "설계서 1", "tabs": [["d1", "설계서"]]}]},
    {"group": "정리", "items": [{"id": "notes", "title": "내 질문·메모 모음", "special": "notes"},
                               {"id": "files", "title": "파일 위치", "special": "files"}]},
]

EXTRA_FILES = [("기록", "보고/업무보드.md")]       # 파일 위치 화면에만 나오는 결과물


def summary(api):
    """첫 화면 숫자 칸 (선택). api.root, api.today, api.mtime(rel)"""
    dd = (datetime.date(2026, 12, 31) - api.today).days
    return [{"label": "연말", "value": f"D-{dd}", "sub": "2026-12-31"}]
