# CHANGELOG

## dash 1.3.0 — 2026-11-07 (프로젝트B 연구 대시보드에만 있던 기능을 엔진으로, 모든 dash 대시보드에 적용)
- **일정·D-day**: 화면 `"schedule": True` + 설정 `SCHEDULE`(start·end·tiles·marks) → 기한 칸과 과제 기간 막대(오늘 위치·지난 비율·다음 기한). 숫자 칸에 `date`를 주면 D-day를 페이지를 연 날 기준으로 계산(30일 안 주황·지난 것 흐리게·D+n), 일정 화면으로 가는 링크. 문서 옵션 `dates`면 표 첫 칸 날짜에 D-day 칩·지난 행 흐리게.
- **문서 내장**: 문서 HTML을 index.html 안(`<script type="text/plain" id="doc-…">`)에도 넣음 — 새 판 게시 뒤 열어 둔 화면에서도 문서가 열림. `EMBED_DOCS = False`로 끔, index 12 MB 넘으면 경고. 서재 모드 제외.
- **그림 실패 처리**: 한 번 다시 시도, 그래도 안 되면 표시 + 새로 고침 안내.
- **대시보드 전체 점검** 버튼("파일 위치 · 점검" 화면): 문서·그림 전수, 탭 연결, 저장소·Claude 질문·동기화 버튼, 엔진 판. 서재 모드는 연결 상태만.
- 설정 `PAGE_TITLE`: 브라우저 탭·갤러리 제목을 TITLE과 따로 (사용자가 갤러리에서 바꾼 이름 유지). 7개 대시보드 설정에 지금 갤러리 이름을 적음.
- 숫자 칸 최소 폭 150 → 118 px, `a.tile`(누를 수 있는 칸).
- 새 도구 `publish_diff.py`(바뀐 파일만 게시, `--mark`, `--state/--changed`), `watch.py`(원고 바뀌면 자동 재생성, `--dir`, `WATCH_DIRS`). 프로젝트A 논문학습 `_작업/publish_diff.py`·프로젝트B 논문학습 `watch_build.py`는 이것을 부르는 얇은 실행 파일로 바꿈(명령·상태 파일 그대로).
- 프로젝트B 과제 연구 대시보드를 프로젝트 안 엔진 복사본에서 이 엔진으로 옮김(`_도구/dash_config.py`). docs 블록 ID 그대로(원고가 바뀐 todo 2블록 제외) → 기존 노트 자리 유지.
- SKILL.md: 0-1·0-2·0-3에 위 기능, `NOTE_NAME`·`WATCH_DIRS`·`EMBED_DOCS`·`SCHEDULE` 설정 설명. PROJECTS.md: 프로젝트B 연구 대시보드 행 갱신, 02 서재 경로의 깨진 문자() 고침.
- 같은 날 16:31 세션 분기 때 엔진 4개 파일이 1.0.0 첫판으로 되돌려진 것을 커밋본(1.2.0)으로 복구한 뒤 작업함 (되돌려진 내용은 stash@{0}에 보관).

## 1.6.0 — 2026-11-06 (dash 1.0.0)
- **연구 대시보드(dash) 형태 추가** — 프로젝트B 과제 연구 대시보드(11-06)를 일반화해 `engine/dash/`로 옮김: `build.py`(설정 파일 하나로 생성), `blocks.py`(블록 분할·ID·HTML), `page.html`(왼쪽 목차·읽기 칸·문단별 질문·스레드 편집·메모·숨기기·노트 모음·파일 위치·상태 줄·노트 동기화 버튼), `notes_sync.py`(스레드 → 원본 md 노트 사본, META).
- 프로젝트별 내용(제목, 질문 도우미 규칙, 질문 예시, 숫자 칸, 문서·화면 목록)은 설정 `dash_config.py`로 뺌 (`templates/dash_config.py`).
- 프로젝트B 판과 달라진 점: 첫 화면은 첫 묶음의 첫 화면(전에는 'today' 고정), 숫자 칸은 설정의 `summary()`가 주는 목록, 그림 경로를 프로젝트 루트 기준으로도 찾음, 탭이 하나도 남지 않은 화면은 목차에서 뺌.
- SKILL.md: 0항(연구 대시보드)을 기본 형태로 추가, 기존 탭 보고판은 그 뒤로. 1.5.0의 board 노트 기능은 그대로 두되 새 프로젝트는 dash를 쓰게 함.

## 1.5.0 — 2026-11-06
- 노트 기능(설정 `notes`, 기본 꺼짐): 문장 선택 → 질문하기/메모 → 문단 아래 카드(db `notes`, 실시간), 카드 안 이어 묻기·내 정리, 질문 창 답 → 노트로 붙이기, `#notes-all`·`#notes-recent` 목록. engine/notes.js, notes.css (노트가 켜진 보고판에만 들어감).
- `--notes-sync <설정> <덤프 폴더|json>`: db 노트를 원본 md + Obsidian 콜아웃 사본(`notes.md_dir`)과 `00_노트 모음.md`로. 반영 시각은 db `notes_meta/sync`.
- 문서 맨 위 📁 파일 위치 줄(원본·노트 사본 경로 복사). 작은 탭 4번째 값 = 원본 md, `api.page(md=)`, `api.doc_block`, `api.reading_group`, `api.rel`.
- 설정 `reading_tab`, `hide_single_sub`, `extra_css`.
- nav.js: 본문 안 `#큰탭-작은탭` 링크를 누르면 그 탭으로 감 (전에는 동작하지 않았음).
- interact.js: 질문 창 답마다 `board:qa` 이벤트.
- 회귀 확인: 프로젝트A 보고판(v1 설정)·프로젝트C 보고판 index unchanged, `--init` 정상. 프로젝트B 과제는 11-06에 자체 대시보드(dash/)로 옮겨 이 엔진을 쓰지 않음.

## 1.4.1 — 2026-11-05
- md의 HTML 주석 줄(`<!-- … -->`)을 화면에 보이지 않게 함. 원고 안에 프로그램이 다시 쓰는 자동 구역 표식(예: `<!-- auto:papers start -->` … `<!-- auto:papers end -->`)을 둘 수 있음. 프로젝트B 보고판의 "받을 논문" 표가 이 방식임.

## 1.4.0 — 2026-11-05
- 질문 창의 "선택한 부분" 옆에 [선택 해제] 버튼: 원하지 않는 선택을 질문에서 뺌 (문서 선택도 함께 풂). "새 대화"도 선택을 지움.
- 탭 분리 구조 `lazy_tabs` (설정, 기본 False): 큰 탭 내용을 `site_dir/tabs/<토큰>.html`로 따로 쓰고 보고판 본문은 탭 틀만 가짐. 탭을 처음 열 때 불러오며(nav.js), 불러온 뒤 MathJax 조판과 `board:pane` 이벤트로 입력함·질문 창을 붙임(interact.js). 생성 로그에 `tabs changed: …` 줄을 출력하고, 변경 판단(index changed)은 탭 내용 전체로 함. 이유: 갱신 게시 때 지금 올라가 있는 본문 전체를 읽어야 하는데, 본문이 수백 KB를 넘으면 자동 회차가 게시하지 못함.
- papers 변경 판단(`papers changed`)에서 `tabs/` 파일을 뺌.

## 1.3.0 — 2026-11-05
- 고침: 질문 창의 "이 대화를 수정 요청으로 보내기"와 한 번 누르는 버튼(`button.act`, 예: 논문 스킵)이 동작하지 않던 문제. 원인은 아티팩트 안에서 막혀 있는 `window.prompt`였음. 이제 수정 요청은 질문 창 입력 칸에 적은 말을 그대로 보내고(대화는 ctx로 함께), `button.act`는 버튼 옆에 메모 칸과 [보내기][취소]를 펼침.
- 질문 창 크기 조절: 창 왼쪽 위 손잡이를 끌어 넓히고 높임, 두 번 누르면 원래 크기. 크기는 브라우저에 기억함(localStorage, 실패해도 동작).
- 질문 기록: 질문 창의 질문·답 한 쌍마다 db `chatlog`에 `{where, sel, q, a, tier, page, turn, created, status}`를 남김(설정 `chat.log`, `chat.log_collection`). 정리는 처리하는 쪽이 함 (SKILL.md 3-1항).
- 독립 페이지(`docs/`)에서도 입력함·질문 창 위치 표시가 맞게 함.

## 1.2.0 — 2026-11-04
- hooks용 `api.md_file(path, hshift, toc, inline_images)`: 원고 폴더 밖 md 파일을 그림 경로 기준(그 파일 폴더)째로 변환. `toc=True`면 h2·h3 목차(누르면 그 절로 이동, nav.js `data-goto`)를 맨 위에 붙임.
- hooks용 `api.page(key, title, html)`: 긴 문서를 보고판 본문 대신 독립 페이지(`site_dir/key`)로 만들고 files에 올림. 보고판 HTML을 작게 유지하려는 것(갱신 게시 때 보고판 전체를 읽어야 하므로).
- 설정 `tab_images`("files"|"inline")와 `inline_images`(max_width, quality): inline이면 그림을 WebP로 줄여 data URI로 넣음(변환 결과는 site_dir/_inline_cache에 캐시). 게시 파일 수 한도(511)를 넘길 때 독립 페이지에 쓰는 용도이며, 보고판 본문에는 권하지 않음(본문이 커짐).
- nav.js: 탭이 없는 독립 페이지에서 오류가 나지 않게 함. 목차 CSS 추가.
- 회귀 확인: 프로젝트A 과제에서 hooks를 바꾸기 전 index unchanged.

## 1.1.0 — 2026-11-04
- 원고 md의 그림 `![설명](경로)`를 탭에 넣음: 경로는 md 파일 기준, 없으면 root 기준(root 밖 파일은 무시). 그림은 `site_dir/tabimg/`에 복사되고 `files.json`에 `tabimg/…`로 들어가 `papers changed` 때 함께 게시함.
- `page_title` 설정 추가: 브라우저 탭·갤러리 제목을 본문 제목(`title`)과 따로 정함. 비우면 `title`.
- 생성 로그에 `tabimg=N` 표시. 회귀 확인: 프로젝트A 과제 탭 본문 해시 그대로(index unchanged), `--init` 빈 프로젝트에서 그림 탭 정상.

## 1.0.0 — 2026-11-04
- 프로젝트A의 `build_report_page.py`에서 범용 엔진을 분리함: 원고 폴더 탭, 읽기목록 논문 페이지, 입력함(db `inbox`), 질문 창(sample), MathJax, 다크 모드.
- 프로젝트별 내용은 `board.config.json`과 `hooks`(tabs_before / tabs_after / stats)로 뺌.
- `--init`으로 새 프로젝트 설정을 만듦. 입력함 목록을 둘 탭이 없으면 엔진이 "의견·답" 탭을 붙임.
- 회귀 확인: 프로젝트A 과제에서 탭 본문 해시가 이전 생성기와 같음(index unchanged).

## dash 1.1.4 — 2026-11-06
- 논문 서재: 폴더·논문 순서를 사람이 읽는 숫자 순(`natkey`: 1_, 2_, …, 10_)으로. 전에는 글자 순이라 10_·11_ 이 2_ 앞에 왔음.

## dash 1.2.0 — 2026-11-06
- 논문 서재 "추가 요청": 요약 카드 아래 요청 상자(빠른 칩 4개) → 요청마다 카드(db `reqs`), 요청 고치기·답 고치기·다시·삭제, 문단 질문·메모. 긴 논문·학위논문·서적용으로 절 번호·낱말로 관련 절 본문만 골라 보냄(`pickSections`, 60k자 한도), 못 고르면 전체 개요. `REQ_RULES` 설정.
- library.py `DOC_VERSION` 2: 문서에 `data-part="sections"`(절별 영문 본문, 번역 인용·그림 제외) 추가 → 모든 문서 재생성·재게시 필요.
- notes_sync: `reqs` 컬렉션을 백업과 요약 md(`## 추가 요청`)에 반영, summaries 는 덤프의 summaries/ 폴더만 읽음. 밤 정리 예약 prompt 도 `reqs` 를 받게 고침.

## dash 1.1.6 — 2026-11-06
- 백업·복원: `notes_sync.py … --backup` 이 db 덤프(threads·summaries)를 `BACKUP_DIR`(기본 NOTE_DIR 옆 `backup/`)에 `<날짜_시각>.json` 으로 날것 그대로 보관(최근 `BACKUP_KEEP_DAYS`=30일 + 달마다 첫 것). `restore.py <backup.json> <out> [--current <덤프>] [--only] [--force]` 가 ArtifactData batch 용 `batch_NNN.json`(50건씩, 있는 문서는 updatedAt 비교·if_version)을 만듦. SKILL 0-7항. 02 서재에서 백업→복원 파일 생성까지 확인.

## dash 1.1.5 — 2026-11-06
- 논문 서재 `LITE = True`(설정): 문서 HTML 에 원문 글·수식 그림을 싣지 않고 요약에 붙일 그림·표(+캡션 문단)와 발췌(brief)만 둠. 화면은 요약·질문·메모 탭만(그림·표 탭은 `SHOW_FIGS_TAB`). 검색 역색인·요약·질문은 그대로. 문서 해시에 LITE 가 들어가 켜고 끄면 전부 다시 만듦.

## dash 1.1.3 — 2026-11-06
- 논문 서재 요약: 지시문에 `## 그림 설명` 절(본문에서 가리킨 그림마다 `### [[Fig n]]` + 한글 캡션 + 보는 법)을 더함. 화면은 그 절을 본문으로 그리지 않고 각 그림 바로 아래에 "Fig n 설명" 블록으로 붙임(질문·메모 가능, ID = 설명 글자의 해시). 요약 md 사본(`--sums`)도 그림 링크 아래에 `[!abstract]` 콜아웃으로 같은 설명과 노트를 넣음.

## dash 1.1.2 — 2026-11-06
- 논문 서재 요약: 그림을 뒤에 모으지 않고 본문에 녹임. 요약 지시문이 그림을 설명하는 문장 끝에 `[[Fig n]]`/`[[Tab n]]` 을 붙이게 하고, 화면은 그 자리에 번호 칩, 그 문단 바로 아래에 그림을 넣음(한 그림은 한 번). `[[…]]` 로 안 들어간 그림만 뒤에. 요약 md 사본(`--sums`)도 같은 문단 아래에 `![[그림파일]]` Obsidian 링크 + 캡션(`_figures/_index.jsonl`에서 파일 이름).

## dash 1.1.1 — 2026-11-06
- 논문 서재: 요약 탭에 md 의 기존 정리본을 붙이지 않음(원문·번역 탭 위에 접힌 상자로만). Claude 요약을 문단 블록(`sum:<djb2>` ID)으로 그려 문단마다 질문·메모 가능. notes_sync `--sums` 가 그 노트를 요약 md 의 같은 문단 아래에 넣음(`sum_block_id` = page.html `h32`). `library.DOC_VERSION` 을 문서 해시에 씀(엔진 버전을 올려도 문서를 다시 만들지 않게).

## dash 1.1.0 — 2026-11-06
- 답 모델 고르기 (위쪽 "답 모델": 빠름·보통·깊게 = Haiku·Sonnet·Opus 등급, 브라우저에 기억, 못 쓰는 등급은 흐림, 답마다 등급 표시). 질문·이어 묻기·다시 묻기·논문 요약에 적용, 메모 초안은 빠름 그대로. 설정 `ASK_TIER`로 기본값 (build.py·library.py가 DATA.askTier로 넘김).
- `engine/dash/rebuild_all.py`: PROJECTS.md의 dash 대시보드를 한꺼번에 다시 생성하고 게시할 URL·경로를 출력 (SKILL 0-3항).
- 논문 서재(LIBRARY) 모드 `engine/dash/library.py`: 설정에 `LIBRARY = True` 면 ROOT 를 훑어 논문 md 전부를 문서로 만듦(YAML 서지, `doc_id` 를 key 로). 문서 HTML 은 `📑 기존 정리본`/`📖 원문` 두 부분 + 요약용 발췌(brief) JSON. 그림은 webp data URI 로 문서 안에(파일 수 한도). 역색인 `search/full.json`. `_state.json` 으로 바뀐 md 만 다시 만들고, `--published` 로 게시 기록 → `_publish_changed.json`.
- page.html: LIBRARY 일 때 왼쪽 검색창+폴더 트리, 논문 화면 탭(요약·원문·번역·그림·표·질문·메모), Claude 핵심 요약 버튼(db `summaries`, 그림 자동 삽입, 고치기·다시·삭제), 검색 화면(본문까지 찾기), 요약 모음, 첫 화면(최근 바뀐 md). 같은 문서 중복 fetch 방지. 기존 dash 프로젝트 화면은 그대로(회귀: 프로젝트A docs 37개 해시 동일).
- notes_sync.py: LIBRARY 모드에서 key 기준 블록 ID·manifest 로 원본 경로(파일 이동 허용), 사본에서 pdf2md 표시 제거, `--sums` 로 Claude 요약 md(`SUM_DIR`) 생성.
- templates/library_config.py 추가. SKILL.md 0-6항.

## dash 1.0.1 — 2026-11-06
- 설정에 `NOTE_NAME(rel)`이 있으면 노트 사본 이름을 그것으로 정함 (여러 폴더에 같은 파일 이름이 있는 원고용, 예: 논문마다 `01_card_요약카드.md`). 없으면 예전과 같음.
