# 스킬 관리 현황 (2026-11-07 기준)

## 폴더 구조
- `skills/` : 유지하는 직접 제작 스킬 (원본 백업 + 수정본)
- `archive/` : 삭제 결정된 스킬의 원본 백업
- `dist/` : claude.ai 재업로드용 zip

## 유지 (skills/)

| 스킬 | 핵심 기능 | 비고 |
|---|---|---|
| detail-references | 본문 인용·참고문헌 전수 대조·교정, 원문 직접 발췌, 3-Pass 검토, `[Pass]/[Modify]/[Fail]` 판정, 참고문헌 전용 검증 모드(대체 블록) | reference-check 기능 병합 (2026-11-07) |
| numeric-check | 수치·단위·수식을 원본과 3-Pass 대조 | 원본 그대로 |
| ai-pingpong | Gemini↔Claude 누적 마크다운 교차 검토 | 원본 그대로 |
| paper-scout | 주제 → 논문 조사·포화 판정 → 리포트·원고 | 원본 그대로 |
| md-slot-finisher | 로컬 PDF→md 도구 산출물의 빈 칸 채우기 | 원본 그대로 |
| matlab-code | MATLAB 그림 서식 규칙 기반 코드 생성 | 원본 그대로 |
| artifact-board | 마크다운 원고 → claude.ai 연구 대시보드(목차·읽기 칸·문단별 질문·메모 저장·노트 동기화) / 탭 보고판 아티팩트 생성·갱신 | PC 로컬 스킬. PROJECTS.md(로컬 경로·아티팩트 URL)와 .git·캐시는 제외하고 업로드 |

## 삭제 (archive/)

| 스킬 | 사유 |
|---|---|
| reference-check | detail-references로 병합 |
| ms-contents-organization | 사용자 결정 |
| pdf-to-md | 사용자 결정 |
| paper-translate-summary | 최근 미사용 (마지막 수정 2026-07-10, 번역은 md-slot-finisher 경로로 대체된 것으로 보임) |

## reference-check → detail-references 병합 내역
- 추가: 3-Pass 반복 검토, 문맥 적합성(Cherry-picking) 검증, 서지 정보(제목·DOI 포함) 오기 교정, 항목별 판정, 모드 B(참고문헌 전용 검증 + Replacement Block), reference-check·ai-pingpong 인용 검증 트리거
- 변경: 수식 표기 규칙은 CLAUDE.md 기준(`$` 안쪽 공백 없음)으로 통일 (reference-check의 "공백 1칸" 규칙 폐기)
- 유지: detail-references 기존 규칙 전부 (인용 번호 형식, 원문 서지 복사, verbatim 발췌)

## Anthropic 제공 스킬 (관리 대상 아님)
pdf, docx, xlsx, pptx, skill-creator, docs, google-workspace, deep-research, chrome-browser, built-in-browser, computer-use, morning, import-memory
