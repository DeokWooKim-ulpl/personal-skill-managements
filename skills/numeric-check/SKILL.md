---
name: "numeric-check"
description: "Verifies numerical values (physical quantities, measurements, units) and mathematical formulas in documents against attached reference materials. Performs strict 3-pass cross-checking to detect typos, unit errors, and discrepancies. Use when the user invokes numeric-check, /numeric-check, or asks to fact-check numbers, parameters, units, or equations against source materials."
---

# numeric-check

첨부된 원본 자료(논문, 실험 데이터, 참고문헌, 사양서 등)를 바탕으로 검토 대상 문서에 삽입된 **수치(물리량, 측정값, 실험 파라미터, 단위 등) 및 수식**의 정확성을 전수 대조 및 검증하는 전용 스킬임. 문체나 일반 문장 윤문 등 비수치적 요소는 완전히 배제하고, 오직 수치 및 수식의 일치 여부, 단위 오기, 전사 오타만을 집중적으로 판별함.

## When to Use

- 사용자가 `numeric-check`, `/numeric-check`, `수치 검증`, `수식 검증`, `수치 팩트체크`를 요청할 때
- 작성 중인 원고, 보고서, 논문 초안 등에 삽입된 수치, 측정값, 오차 범위, 단위, 수식이 원본 자료와 일치하는지 확인할 때
- 수식 내 첨자, 지수, 기호, 상수 값 등의 전사 오타(transcription error)를 잡아내고자 할 때

## Core Principles & 3-Pass Verification System

검토의 완결성과 누락 방지를 위해 대상 문서를 처음부터 끝까지 **총 3회 반복 전수 검토(3-Pass Inspection)**를 수행함.

### Pass 1: 전수 추출 및 원본 1:1 대조 (Extraction & Source Mapping)

- 검토 대상 문서에 등장하는 모든 수치, 물리량(측정값, 계산값, 오차 범위, 유효숫자), 단위, 수식을 빠짐없이 추출함.
- 첨부된 원본 자료(논문, 보고서, 데이터셋 등)의 해당 위치(페이지, 표, 그림 캡션, 본문 단락 등)를 찾아 1:1로 정확히 대조함.

### Pass 2: 단위, 차원, 표기 및 오타 정밀 검사 (Unit & Typography Audit)

- **단위 및 차원 확인**: 단위 환산 오류(예: nm vs $\mu\text{m}$, mW vs W, dBm vs mW) 및 단위 누락/오기 집중 점검.
- **수식 및 첨자 정밀 검증**: 첨자(subscript/superscript), 부호($+$, $-$, $\pm$), 그리스 문자, 괄호 닫힘, 변수 표기 오류 등을 집중 확인.
- **자릿수 및 유효숫자 확인**: 소수점 위치, 10의 거듭제곱(지수부), 유효숫자 표기 불일치 점검.

### Pass 3: 누락 및 교차 정합성 최종 점검 (Omission & Final Consistency Check)

- Pass 1과 Pass 2에서 놓친 잠재적 불일치 항목이나 모호한 인용 여부를 역방향으로 재검증.
- 동일 문서 내 앞뒤 수치 간 상충(모순) 여부 및 표/그림/본문 간 교차 정합성 확인.
- 최종 검증 보고서 작성.

## Execution Rules & Output Format

1. **분석 범위 한정**: 문체, 문법, 서술 구조 등 비수치적 요소에 대한 평가는 일절 배제함.
2. **수식 및 단위 표기**: 수식 및 단위는 엄격한 LaTeX 형식으로 명확히 표기함.
3. **어조**: 간결하고 명확한 꼭지형식(음슴체)으로 결과를 보고함.

### Report Template

검토 결과는 아래 구조로 보고함:

```markdown
### 1. 3-Pass 검토 요약
- 대상 문서 내 확인된 총 수치/수식 항목 수: N개
- 정상 일치 항목 수: N개
- 불일치/오타/단위 오류 발견 항목 수: N개

### 2. 불일치 및 오류 항목 상세 (수정 필요)
| 검토 항목 | 본문 표기 | 원본 자료 표기 (출처/위치) | 판정 (오타/단위/수치 불일치) | 권장 수정안 |
| :--- | :--- | :--- | :--- | :--- |
| ... | ... | ... | ... | ... |

- 상세 분석 및 원인 설명 (각 항목별 구체적인 대조 근거 서술)

### 3. 정상 일치 항목 목록 (주요 핵심 수치/수식)
| 검토 항목 | 본문 표기 | 원본 자료 표기 (출처/위치) | 판정 |
| :--- | :--- | :--- | :--- |
| ... | ... | ... | 일치 확인 |
```