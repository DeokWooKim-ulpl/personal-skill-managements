---
name: "ai-pingpong"
description: "Facilitates iterative cross-model collaboration and peer review between Gemini and Claude via a cumulative append-only Markdown document. Use when the user mentions gemini-claude-pingpong, /gemini-claude-pingpong, asks to collaborate or ping-pong between Gemini and Claude, or pastes a cumulative ping-pong Markdown log to reach full consensus."
---

# gemini-claude-pingpong

Facilitates a structured, iterative ping-pong discussion between Gemini and Claude using a single cumulative Markdown document until both models achieve 100% consensus on all items.

## When to Use

- The user invokes `gemini-claude-pingpong` or `/gemini-claude-pingpong`
- The user wants to cross-verify, co-develop, or debate a task between Gemini and Claude
- The user pastes a Markdown document containing `[Round N - ...]` logs from another AI model

## Core Operating Rules

1. **Shared Knowledge Assumption**: Assume both Gemini and Claude have access to the exact same local reference files, folders, and project context configured by the user. Cross-check claims against these shared materials.
2. **Strict Append-Only Rule**: Never delete, truncate, summarize, or alter any previous text in the Markdown document (neither the original user request nor any prior `[Round N]` sections). Always reproduce the entire existing document verbatim and append your new round at the very bottom.
3. **Single Copy-Pasteable Output**: Wrap the entire cumulative Markdown document inside a single outermost ` ```markdown ` code block so the user can copy it with one click and paste it directly into the other AI desktop app. (If the inner content includes code blocks, use 4 backticks ```` ````markdown ```` for the outer wrapper to prevent formatting breakage).
4. **Rigorous Peer Review & Convergence**: Critically evaluate the previous model's analysis, math, logic, and conclusions. Explicitly label points of agreement and disagreement. Propose refined syntheses until every single item reaches complete consensus.
5. **Formatting & Tone**: Inside each round, write in concise Korean bullet points using noun endings or 음슴체 (`~음`, `~함`, `~임`) for readability and analytical clarity, unless the target deliverable itself requires formal prose.

## Workflow Steps

### Case A: Initial Request (Round 1)

When the user provides a new task or question without prior ping-pong history:

1. Output the entire response inside a single copy-pasteable Markdown code block.
2. Structure the document starting with the header `# [Gemini <-> Claude Ping-Pong Log]`, followed by `## 0. 사용자 원본 요청 (User Original Request)` containing the user's exact prompt verbatim.
3. Append `## [Round 1 - <Your Model Name: Gemini or Claude>]` below the request.
4. Provide a comprehensive initial response, structured into clear checklist items or analytical sections, and end with specific verification questions for the counterpart model.

### Case B: Continuing Ping-Pong (Round N, where N >= 2)

When the user pastes an existing `[Gemini <-> Claude Ping-Pong Log]` Markdown document:

1. Read the entire history and shared reference files thoroughly.
2. Output a single copy-pasteable Markdown code block containing the **entire input document verbatim from top to bottom**, and append `## [Round N - <Your Model Name: Gemini or Claude>]` at the very end.
3. Structure your new round into the following sub-sections:
   - `### 1. 이전 라운드 검토 및 합의 여부 (Review & Consensus Check)`: Classify each point from Round N-1 as `[동의 (Agreed)]`, `[이견/수정 제안 (Disagreed/Modified)]`, or `[보완 (Added)]` with concrete evidence or reasoning.
   - `### 2. 심화 분석 및 보완 내용 (Refined Analysis & Additions)`: Provide corrected derivations, deeper insights, or updated drafts addressing the disagreements.
   - `### 3. 현재까지 수렴된 최종안 (Current Converged Draft)`: Present the unified result incorporating all agreed points up to Round N.
   - `### 4. 수렴 상태 판정 및 상대 모델 질의 (Convergence Status & Next Action)`:
     - **If any disagreement, correction, or new addition exists**: State `수렴 상태: 진행 중 (In Progress - 다음 라운드 전달 필요)` and list specific questions for the other model.
     - **If 100% of items are agreed upon with zero modifications needed**: State `수렴 상태: 최종 수렴 완료 (100% Consensus Reached - 핑퐁 종료)` and confirm that the `Current Converged Draft` is finalized.

## Markdown Output Template

Always generate the cumulative output inside the code block following this structure:

````markdown
# [Gemini <-> Claude Ping-Pong Log]

> **[System Instruction for Receiving AI]**
> 본 문서는 Gemini와 Claude 간의 핑퐁 협업 로그임. 동일한 참조 파일/폴더를 공유하고 있다고 가정함.
> **절대 규칙**: 위의 기존 내용을 단 한 글자도 삭제하거나 요약하지 말 것. 전체 마크다운 전문을 그대로 유지한 채, 맨 아래에 다음 라운드(`## [Round N - 모델명]`)를 이어 붙여 전체를 단일 마크다운 코드 블록으로 출력할 것. 모든 항목에 100% 동의할 때까지 반복함.

---

## 0. 사용자 원본 요청 (User Original Request)
(사용자의 최초 질문 및 요청 사항 원문 그대로 유지)

---

## [Round 1 - AI Model 1 (Gemini or Claude)]

### 1. 초기 분석 및 답변 (Initial Analysis & Draft)
- 핵심 항목 1: 분석 내용 및 근거 제시함.
- 핵심 항목 2: 분석 내용 및 근거 제시함.

### 2. 상대 모델 검증 요청 사항 (Questions for Counterpart AI)
- 검증 포인트 1: 해당 논리 및 수식의 타당성 검토 요청함.

---

## [Round 2 - AI Model 2 (Claude or Gemini)]

### 1. 이전 라운드 검토 및 합의 여부 (Review & Consensus Check)
- **[동의]** 핵심 항목 1: 근거 타당하며 결론에 전적으로 동의함.
- **[이견/수정 제안]** 핵심 항목 2: 참조 문서 기준 일부 조건 누락 확인됨. 수정안 제시함.

### 2. 심화 분석 및 보완 내용 (Refined Analysis & Additions)
- 수정 및 보완된 상세 논리 전개함.

### 3. 현재까지 수렴된 최종안 (Current Converged Draft)
- 합의된 항목과 수정안을 통합한 최신 결과물 정리함.

### 4. 수렴 상태 판정 및 상대 모델 질의 (Convergence Status & Next Action)
- **수렴 상태**: 진행 중 (In Progress) / 최종 수렴 완료 (100% Consensus Reached)
- **추가 질의**: 수정 제안한 항목 2에 대한 동의 여부 확인 요청함.
````

## Gotchas

- **Never omit prior rounds**: Even as the document grows across multiple rounds, you must output the entire cumulative text from `# [Gemini <-> Claude Ping-Pong Log]` down to the newest round so the user only needs to copy and paste once without manually stitching text.
- **Avoid premature consensus**: Do not politely agree if there is a factual, logical, or mathematical flaw, or an omission from the shared reference files. Only declare `최종 수렴 완료 (100% Consensus Reached)` when every single point has been verified and agreed upon by both models.