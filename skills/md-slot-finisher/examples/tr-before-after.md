# 번역 칸 채우기 예시

규칙: `> (번역 필요)` 줄만 바꿈. 표식 줄·원문은 그대로. 번역문 줄마다 앞에 `> `.
아래 원문 위치·표식 번호는 설명용 가상값임.

## 1. 본문 단락

전:
```
The laser operated at a repetition rate of 80 MHz. The beam waist $\omega_0$ was set to 25 μm
by adjusting the curvature of mirror M2, which minimized the thermal lensing effect.

<!-- TR P00012 h=3fa9c1d2e4b5 -->
> (번역 필요)
<!-- /TR -->
```

후:
```
The laser operated at a repetition rate of 80 MHz. The beam waist $\omega_0$ was set to 25 μm
by adjusting the curvature of mirror M2, which minimized the thermal lensing effect.

<!-- TR P00012 h=3fa9c1d2e4b5 -->
> 레이저는 80 MHz 의 반복률(repetition rate)로 동작함. 빔 허리 $\omega_0$는 거울 M2 의 곡률을
> 조정해 25 μm 로 맞췄으며, 이로써 열 렌즈 효과(thermal lensing effect)를 최소화함.
<!-- /TR -->
```

- 두 문장 모두 번역함 (합치기·생략 없음).
- 수식 `$\omega_0$` 를 그대로 옮기고 바로 뒤에 조사를 붙임.
- 새 용어는 `_glossary.md` 맨 아래에 줄 추가 (용어집에 이미 있으면 그 번역 사용).
- 번역문 말투는 `AI_INSTRUCTIONS.md` 규칙이 우선함. 위 예시의 어미는 설명용임.

## 2. 제목

전:
```
## 3. Experimental Setup

<!-- TR P00013 h=7b21e09c44fa -->
> (번역 필요)
<!-- /TR -->
```

후:
```
## 3. Experimental Setup

<!-- TR P00013 h=7b21e09c44fa -->
> 3. 실험 장치
<!-- /TR -->
```

- 원문 제목 줄(`## 3. Experimental Setup`)은 고치지 않음. 번호는 원문대로 둠.

## 3. 그림 캡션

전:
```
![](_figures/D335259a3/fig2.png)
Fig. 2. Output power versus pump power. The slope efficiency is 31%.

<!-- TR P00014 h=c0de5511ab37 -->
> (번역 필요)
<!-- /TR -->
```

후:
```
![](_figures/D335259a3/fig2.png)
Fig. 2. Output power versus pump power. The slope efficiency is 31%.

<!-- TR P00014 h=c0de5511ab37 -->
> 그림 2. 펌프 출력에 따른 출력. 기울기 효율(slope efficiency)은 31% 임.
<!-- /TR -->
```

- 그림 링크 줄은 고치지 않음.

---

## 잘못된 예 1: 요약해 버린 번역 (금지)

```
<!-- TR P00012 h=3fa9c1d2e4b5 -->
> 레이저 동작 조건과 빔 허리 설정을 설명함.
<!-- /TR -->
```

- 원문 두 문장의 수치(80 MHz, 25 μm)·M2·열 렌즈 내용이 모두 빠짐. 원문의 모든 문장을 번역해야 함.

## 잘못된 예 2: 표식을 지운 경우 (금지)

```
레이저는 80 MHz 의 반복률(repetition rate)로 동작함. 빔 허리 $\omega_0$는 ...
```

- `<!-- TR P00012 h=3fa9c1d2e4b5 -->` 와 `<!-- /TR -->` 가 사라지고 `> ` 도 없음.
- 도구가 칸을 찾지 못해 번역이 저장되지 않고, `--check` 가 표식 손상으로 지적함.
- 바꿀 때는 표식 줄까지 포함해서 찾고, 표식 줄은 그대로 다시 씀 (SKILL.md "파일을 고치는 방법").
