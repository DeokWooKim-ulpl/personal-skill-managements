# 스킬 목록 및 핵심 기능 (2026-11-07 기준)

총 23개. 출처: 직접 제작(plugin) 10개 / Anthropic 제공 13개 (manifest.json 기준).

## A. 직접 제작 스킬 (10개)

| 스킬 | 핵심 기능 | 규모 | 비고 |
|---|---|---|---|
| paper-translate-summary | 광학·레이저 논문 전 섹션 정밀 번역 + 핵심 정리 → 단일 .md. 상단에 Optics Express 서지 표기, 수식·단위 렌더링 규칙 | 101줄 | 핵심 |
| pdf-to-md | PDF → 마크다운 + Figure PNG 추출(figures 폴더). 외국어→한국어 | 173줄 | 핵심 |
| detail-references | 본문 인용·참고문헌 전수 대조·교정, 원문 문장 직접 발췌 | 62줄 | 핵심 |
| reference-check | 참고문헌·인용 발췌문을 원본과 3-Pass 검토 후 교정본 제공 | 65줄 | detail-references와 일부 중복 |
| numeric-check | 수치·단위·수식을 원본과 3-Pass 대조, 불일치 리포트 | 63줄 | 핵심 |
| paper-scout | 주제 → 논문 조사·다운로드 요청서·포화 판정 → 아이디어별 40쪽+ 리포트·논문 원고 | 360줄 | 강력하나 무거움 |
| md-slot-finisher | 로컬 PDF→md 도구 산출물의 빈 칸(TR/SUM/LEGACY/YAML)만 채움 | 88줄 + 보조 4파일 | 로컬 도구 전용 |
| matlab-code | MATLAB 스크립트 생성 (LaTeX 축 라벨, 그림 서식 규칙) | 45줄 | 유용 |
| ai-pingpong | Gemini↔Claude 누적 마크다운 교차 검토 | 97줄 | 사용 빈도 확인 필요 |
| ms-contents-organization | Word/PPT 선택 영역 정리(첨자·표·띄어쓰기, 내용 무변경) | 10줄 | 짧고 설명 빈약 |

## B. Anthropic 제공 스킬 (13개, 삭제·업로드 대상 아님)

| 스킬 | 기능 |
|---|---|
| pdf / docx / xlsx / pptx | 각 파일 형식 읽기·생성·편집 |
| skill-creator | 스킬 제작·개선·평가 |
| docs / google-workspace | Claude Docs, Google Docs·Sheets·Slides 작업 |
| deep-research | 다중 소스 조사 보고서 |
| chrome-browser / built-in-browser / computer-use | 브라우저·데스크톱 제어 |
| morning | 아침 브리핑 |
| import-memory | 타 AI 메모리 가져오기 |
