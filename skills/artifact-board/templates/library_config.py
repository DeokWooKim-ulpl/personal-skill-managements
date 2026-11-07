# -*- coding: utf-8 -*-
"""논문 서재 대시보드(dash LIBRARY 모드) 설정 견본 — 논문 폴더마다 하나씩 복사해서 고침 (SKILL.md 0-6항).

    python -I "%USERPROFILE%/.claude/skills/artifact-board/engine/dash/build.py" "<이 파일>"
    python -I "…/build.py" "<이 파일>" --published      ← 게시한 뒤 기록 (다음부터 바뀐 문서만 _publish_changed.json 에)

원본 md·_figures 는 읽기만 함. 이 파일과 OUT·NOTE_DIR·SUM_DIR·MANIFEST 는 논문 폴더 **바깥**에 둠
(pdf2md 는 PDF 짝 없는 md 를 다른 문서에 붙이고, paper-qa 는 pdf2md 표시가 있는 md 를 논문으로 세므로).
"""
LIBRARY = True
LITE = True                                       # 원문 글·수식 그림은 싣지 않고 요약용 그림·표만 (False: 원문·번역 탭도 생김, 용량 2배쯤)
TITLE = "논문 서재 — ○○"
SUBTITLE = "○○ 논문 모음 · 요약 · 질문·메모"
ROOT = "../../○○ 논문 폴더"                       # 이 파일 기준 논문 폴더
OUT = "../_paper-dash/○○/site"                   # ROOT 기준 — 게시할 사이트 (index.html, docs/, search/)
NOTE_DIR = "../_paper-dash/○○/노트사본"           # 질문·메모 md 사본
SUM_DIR = "../_paper-dash/○○/요약"                # Claude 요약 md
MANIFEST = "../_paper-dash/○○/manifest.json"
ARTIFACT_URL = ""                                 # 첫 게시 뒤 적음
# BACKUP_DIR = "../_paper-dash/○○/backup"        # db 원본 JSON 백업 (notes_sync --backup, 기본: NOTE_DIR 옆 backup/)
# BACKUP_KEEP_DAYS = 30                           # 이 일수보다 오래된 백업은 지움 (달마다 첫 것은 남김)
ONLY_PDF2MD = False                               # True 면 `<!-- pdf2md:generated` 표시가 있는 md 만
# EXCLUDE_DIRS = {"_figures", "_to_delete", "_legacy", "__pycache__", ".obsidian", ".trash", ".git", "_ai_queue", "node_modules"}
# EXCLUDE_PREFIXES = ("_tools", "_삭제대기", "_paper-dash")
# FIG_INDEX = "_figures/_index.jsonl"             # 그림 캡션 (없으면 md 안 캡션만)
IMG_MAX_W = 900                                   # 그림 가로 최대 px (문서 안에 webp data URI 로 들어감)
IMG_Q = 70
ASK_EXAMPLE = "예: 이 논문에서 모드잠금이 안정되는 조건이 뭔지 쉽게 설명해 줘"
RULES = """너는 레이저·광학 논문 서재의 해설 도우미다. 독자는 레이저광학·비선형광학·가우스빔을 아는 대학원생이다.
규칙:
- 한국어로 답한다. 배경 개념부터 차근차근, 왜 그런지(물리적 이유)를 설명한다.
- 수식은 $...$ 또는 $$...$$ LaTeX로 쓰고, 기호의 뜻을 바로 풀어 준다. 가능하면 숫자 예를 하나 든다.
- 아래 [문서 발췌]를 먼저 근거로 삼는다. 발췌에 없는 일반 지식으로 답하는 부분은 문장 끝에 "(일반 지식)"이라고 표시한다.
- 확실하지 않은 수치·인용은 지어내지 말고 "발췌에서 확인할 수 없음"이라고 말한다.
- 길이는 질문에 맞춘다(보통 400–1200자). 마지막 줄에 "한 줄 요약: ..."을 붙인다."""
# SUM_RULES = "…"   # Claude 핵심 요약 버튼의 지시문 (비우면 page.html 의 기본: 한 줄 요약·연구 질문·방법·핵심 결과·의의·그림)
# REQ_RULES = "…"   # 요약 아래 "추가 요청"(절 요약·목차 정리)의 지시문 (비우면 page.html 의 기본)


# def summary(api):  # 첫 화면 숫자 칸 (선택). api.papers = 논문 목록
#     return [{"label": "논문", "value": f"{len(api.papers)}편"}]
