# PPT Color Palette

PPT 슬라이드용 컬러 시스템. 차트(`chart-design-system.md`)와 동일한 6 테마 anchor를 공유하되, **슬라이드의 큰 표면적·투사 환경·먼 거리 가독성**을 고려한 별도 색 운용 규칙을 정의한다.

핵심 차이: 차트에서 색은 데이터 인코딩(작은 면적), PPT에서 색은 공간 분할과 시선 유도(큰 면적). PPT는 대비를 강하게, 텍스트는 절대 안 보이는 일 없도록.

---

## 1. Theme Anchors (참조)

차트 시스템과 동일한 6 테마. 자세한 ramp/categorical/diverging는 `chart-design-system.md` §1 참조.

| 테마 | Anchor | Mid | Dark Variant |
|---|---|---|---|
| Red    | `#A50034` | `#C73659` | `#D14F70` |
| Orange | `#A85400` | `#E07900` | `#D17730` |
| Yellow | `#A37800` | `#D6A100` | `#C49936` |
| Green  | `#007A3D` | `#1E9954` | `#2BAA63` |
| Blue   | `#003D85` | `#1A66C2` | `#3070C2` |
| Purple | `#5C1E91` | `#7B45B0` | `#8957BC` |

---

## 2. Background Tiers (테마별 배경 농도)

각 테마는 슬라이드 배경용 5단계 농도 시스템을 가진다. Sequential ramp에서 추출.

| 농도 | 용도 | Red | Orange | Yellow | Green | Blue | Purple |
|---|---|---|---|---|---|---|---|
| **Deepest** (ramp 800) | 프리미엄 cover, closing | `#6E0023` | `#703800` | `#6E5000` | `#00502A` | `#002659` | `#3C0F60` |
| **Strong** (anchor 600) | 표지, 섹션 디바이더 | `#A50034` | `#A85400` | `#A37800` | `#007A3D` | `#003D85` | `#5C1E91` |
| **Mid** (ramp 400) | 강조 블록, 콜아웃 | `#C73659` | `#E07900` | `#D6A100` | `#1E9954` | `#1A66C2` | `#7B45B0` |
| **Soft** (ramp 100) | 콜아웃 박스 배경 | `#F2B8C9` | `#F4D2A6` | `#F4DDA0` | `#A8DDBA` | `#A6C2EC` | `#C8B0E0` |
| **Tint** (ramp 50) | 본문 배경 살짝 변화 | `#FBE6EC` | `#FBEDDE` | `#FBF1D9` | `#DDF3E5` | `#DDE9F8` | `#ECE3F5` |

테마와 무관한 공통 배경:
- **White**: `#FFFFFF` — 본문 슬라이드 기본
- **Cream surface**: `#F8F7F4` — 본문 슬라이드 대안 (덜 sharp한 느낌)
- **Charcoal**: `#2C2C2A` — 다크 cover, 다크 closing

---

## 3. Surface & Container Colors

슬라이드 내부의 카드, 콜아웃, 컨테이너 색.

| 요소 | Light 슬라이드에서 | Dark 슬라이드에서 |
|---|---|---|
| 일반 카드 배경 | `#F8F7F4` (cream) | `rgba(255,255,255,0.08)` |
| 강조 카드 배경 | 테마 anchor (600) | 테마 mid (400) |
| 콜아웃 박스 | 테마 soft (100) | 테마 deepest (800) |
| 카드 테두리 | `#EBEAE3` (0.5px) | `rgba(255,255,255,0.15)` |
| 디바이더 라인 | `#EBEAE3` 또는 anchor 30% | `rgba(255,255,255,0.20)` |

**원칙: 한 슬라이드에 카드 종류는 최대 2개.** 일반 카드 + 강조 카드 1개. 카드 종류가 많아지면 시각적 위계가 무너진다.

---

## 4. Text-on-Background Contrast Matrix

배경별로 안전한 텍스트 색. 모든 조합은 WCAG AA (대형 텍스트) 이상 충족.

### 4.1 White / Cream 배경 (`#FFFFFF` / `#F8F7F4`)

| 텍스트 역할 | 색 |
|---|---|
| 제목 (Title) | `#2C2C2A` (charcoal) |
| 본문 (Body) | `#55554F` |
| 보조 (Muted) | `#8E8D87` |
| 강조 텍스트 | 테마 anchor |
| 하이퍼링크 | 테마 anchor (밑줄 없음, 굵게로 구분) |

### 4.2 Anchor 배경 (예: `#A50034`)

| 텍스트 역할 | 색 |
|---|---|
| 제목/본문 | `#FFFFFF` (white) |
| 보조 | 테마 100 (예: `#F2B8C9`) |
| 비활성 | 테마 200 (예: `#E58AA5`) at 70% opacity |

**금지**: anchor 배경 위 charcoal/검정 텍스트 (대비 부족), anchor 배경 위 다른 테마 anchor 텍스트.

### 4.3 Deepest 배경 (예: `#6E0023`)

| 텍스트 역할 | 색 |
|---|---|
| 제목/본문 | `#FFFFFF` |
| 보조 | 테마 200 |
| 강조 | 테마 50 (예: `#FBE6EC`) |

### 4.4 Soft 배경 (예: `#F2B8C9`)

| 텍스트 역할 | 색 |
|---|---|
| 제목 | 테마 deepest (예: `#6E0023`) |
| 본문 | `#2C2C2A` |
| 강조 | 테마 anchor |

**금지**: soft 배경 위 white 텍스트 (대비 부족).

### 4.5 Tint 배경 (예: `#FBE6EC`)

거의 white와 동일하게 다루되, 강조 색이 테마 anchor면 시각적 통일감 ↑.

### 4.6 Charcoal 배경 (`#2C2C2A`)

| 텍스트 역할 | 색 |
|---|---|
| 제목/본문 | `#FFFFFF` |
| 보조 | `#B8B7B0` |
| 강조 | 테마 mid 또는 dark variant (anchor는 너무 진해서 안 보일 수 있음) |

---

## 5. 콜아웃 & 강조 색 페어

본문 슬라이드 안에서 한 부분을 강조할 때 쓰는 배경+텍스트 조합.

| 콜아웃 유형 | 배경 | 텍스트 |
|---|---|---|
| 정보 (info) | 테마 soft (100) | 테마 deepest (800) |
| 핵심 인사이트 (key insight) | 테마 anchor | white |
| 인용 (quote) | white + 좌측 4px anchor 선 | charcoal |
| 경고/주의 (캡션용) | 테마 tint (50) | 테마 anchor |
| 통계 박스 | cream `#F8F7F4` | charcoal + anchor 숫자 |

---

## 6. 슬라이드 역할별 컬러 스킴

PPT 덱은 슬라이드 역할이 다양함. 역할별로 권장 색 스킴 정의.

### 6.1 Cover / Title 슬라이드

**목적**: 강한 첫인상, 주제 각인.

| 배경 | 제목 텍스트 | 부제 | 메타 (날짜 등) |
|---|---|---|---|
| 테마 anchor | white | 테마 100 | 테마 200 |
| 테마 deepest | white | 테마 200 | 테마 400 |
| white | charcoal + 좌측 anchor 색 블록 | `#55554F` | `#8E8D87` |
| charcoal | white | 테마 mid | `#B8B7B0` |

### 6.2 Section Divider

**목적**: 챕터 구분, 호흡.

| 배경 | 챕터 번호 | 챕터 명 |
|---|---|---|
| 테마 anchor | 테마 200 (큰 outline 숫자) | white |
| 테마 deepest | 테마 mid | white |

### 6.3 Content 본문 슬라이드

**목적**: 정보 전달.

| 배경 | 제목 | 본문 | 강조 |
|---|---|---|---|
| white | charcoal | `#55554F` | 테마 anchor |
| cream `#F8F7F4` | charcoal | `#55554F` | 테마 anchor |
| 테마 tint (50) | 테마 deepest | charcoal | 테마 anchor |

**원칙: 본문 슬라이드는 90% 이상 white/cream/tint 배경.** anchor 배경 본문은 가독성 약함.

### 6.4 Stats / KPI 슬라이드

**목적**: 큰 숫자로 임팩트.

| 배경 | 큰 숫자 | 라벨 | 강조 카드 (Q4 같은) |
|---|---|---|---|
| white | 테마 anchor (60-72pt) | `#8E8D87` | anchor 배경 + white 숫자 |

### 6.5 Closing 슬라이드

**목적**: 마무리, 콜투액션.

| 배경 | 텍스트 |
|---|---|
| 테마 anchor 또는 charcoal | white |
| 테마 deepest | white + 강조엔 mid |

Cover와 같은 톤이면 "수미상관" 효과로 덱이 완결돼 보임.

---

## 7. 테마별 PPT 컬러 빠른 참조

각 테마의 핵심 6색 (배경 5단계 + 다크 변형) 모아둠. 디자인 도구에 변수로 등록.

### Red · 빨강 (LG)
```
deepest  #6E0023   strong   #A50034   mid     #C73659
soft     #F2B8C9   tint     #FBE6EC   dark    #D14F70
```

### Orange · 주황
```
deepest  #703800   strong   #A85400   mid     #E07900
soft     #F4D2A6   tint     #FBEDDE   dark    #D17730
```

### Yellow · 노랑
```
deepest  #6E5000   strong   #A37800   mid     #D6A100
soft     #F4DDA0   tint     #FBF1D9   dark    #C49936
```

### Green · 초록
```
deepest  #00502A   strong   #007A3D   mid     #1E9954
soft     #A8DDBA   tint     #DDF3E5   dark    #2BAA63
```

### Blue · 파랑
```
deepest  #002659   strong   #003D85   mid     #1A66C2
soft     #A6C2EC   tint     #DDE9F8   dark    #3070C2
```

### Purple · 보라
```
deepest  #3C0F60   strong   #5C1E91   mid     #7B45B0
soft     #C8B0E0   tint     #ECE3F5   dark    #8957BC
```

---

## 8. CSS Variables (HTML 렌더링용)

HTML→PPTX 파이프라인에서 CSS 변수로 등록.

```css
:root {
  /* 활성 테마 — Red 기준, 다른 테마는 anchor 값만 치환 */
  --theme-deepest: #6E0023;
  --theme-strong:  #A50034;
  --theme-mid:     #C73659;
  --theme-soft:    #F2B8C9;
  --theme-tint:    #FBE6EC;
  --theme-dark:    #D14F70;

  /* 테마 무관 공통 */
  --surface-white:    #FFFFFF;
  --surface-cream:    #F8F7F4;
  --surface-charcoal: #2C2C2A;

  --text-title:  #2C2C2A;
  --text-body:   #55554F;
  --text-muted:  #8E8D87;
  --text-faint:  #B8B7B0;

  --border-subtle: #EBEAE3;
}
```

---

## 9. 안티패턴 (금지 사항)

- ❌ 한 슬라이드에 anchor 색을 4번 이상 사용 (의미 인플레이션)
- ❌ 다른 두 테마 색을 한 슬라이드에서 동시 사용 (모노테마 원칙)
- ❌ Soft/Tint 배경 위 white 텍스트 (대비 부족)
- ❌ Anchor 배경 위 charcoal/검정 텍스트
- ❌ Title을 cream/beige 톤 색에 두는 것 (대비 부족, 흐릿함)
- ❌ 한 덱에서 슬라이드마다 테마 색을 바꾸기 (한 덱 = 한 테마 원칙)
- ❌ 본문 슬라이드 전체를 anchor 배경으로 깔기 (눈 피로)
