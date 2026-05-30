# Chart Design System

NL2Chart 에이전트가 Vega-Lite spec을 생성할 때 따르는 디자인 시스템. **6개 테마 색상**(Red·Orange·Yellow·Green·Blue·Purple, 모두 LG 코퍼레이트 레드 #A50034와 같은 deep 톤)을 지원하며, 깔끔하고 데이터가 직관적으로 읽히는 차트를 목표로 한다. 기본 테마는 Red.

전체 철학: **데이터가 가장 강하고, 라벨은 중간, 그리드는 거의 안 보여야 한다.** 색이 아니라 명도/투명도 계층이 시각적 우선순위를 만든다.

---

## 1. Color Tokens

NL2Chart는 **6개 테마 색상**을 지원한다. 모든 테마는 LG Red(#A50034)와 같은 톤 — deep, 채도는 높지만 차분한 계열, HSL의 L≈25~33% — 으로 설계되어 시각적 무게가 일관된다. 데이터 성격이나 시각적 맥락에 맞춰 anchor를 선택하면 된다.

### 1.1 Theme Anchors

| 테마 | Anchor | Mid | Muted | Tint | Dark Variant | 보색 (diverging pair) |
|---|---|---|---|---|---|---|
| Red · 빨강 (LG) | `#A50034` | `#C73659` | `rgba(165,0,52,0.22)` | `rgba(165,0,52,0.08)` | `#D14F70` | Green (`#007A3D`) |
| Orange · 주황 | `#A85400` | `#E07900` | `rgba(168,84,0,0.22)` | `rgba(168,84,0,0.08)` | `#D17730` | Blue (`#003D85`) |
| Yellow · 노랑 | `#A37800` | `#D6A100` | `rgba(163,120,0,0.22)` | `rgba(163,120,0,0.08)` | `#C49936` | Purple (`#5C1E91`) |
| Green · 초록 | `#007A3D` | `#1E9954` | `rgba(0,122,61,0.22)` | `rgba(0,122,61,0.08)` | `#2BAA63` | Red (`#A50034`) |
| Blue · 파랑 | `#003D85` | `#1A66C2` | `rgba(0,61,133,0.22)` | `rgba(0,61,133,0.08)` | `#3070C2` | Orange (`#A85400`) |
| Purple · 보라 | `#5C1E91` | `#7B45B0` | `rgba(92,30,145,0.22)` | `rgba(92,30,145,0.08)` | `#8957BC` | Yellow (`#A37800`) |

테마 선택 가이드 (참고):

- **Red**: LG 브랜드 기본, 임팩트가 필요한 경영 대시보드, 매출/실적
- **Orange**: 따뜻하고 활동적인 인상, 사용자 행동/참여 지표
- **Yellow**: 주의/관찰 뉘앙스, 알림성 데이터 (채도 낮은 amber라 차분함)
- **Green**: 성장/긍정, KPI 달성, 환경/지속가능성 지표
- **Blue**: 신뢰/안정, 운영 메트릭, 기술적 지표
- **Purple**: 분석/실험, R&D, 미래 지향 데이터

### 1.2 Sequential Ramps

히트맵, 농도 매핑, 단일 시리즈의 그라데이션 표현용. 7-stop 구조 (50 → 900), anchor는 **600**.

| 테마 | 50 | 100 | 200 | 400 | 600 (anchor) | 800 | 900 |
|---|---|---|---|---|---|---|---|
| Red    | `#FBE6EC` | `#F2B8C9` | `#E58AA5` | `#C73659` | `#A50034` | `#6E0023` | `#4A0017` |
| Orange | `#FBEDDE` | `#F4D2A6` | `#ECAA60` | `#E07900` | `#A85400` | `#703800` | `#4A2500` |
| Yellow | `#FBF1D9` | `#F4DDA0` | `#E9C25E` | `#D6A100` | `#A37800` | `#6E5000` | `#4A3500` |
| Green  | `#DDF3E5` | `#A8DDBA` | `#6CBE85` | `#1E9954` | `#007A3D` | `#00502A` | `#00351C` |
| Blue   | `#DDE9F8` | `#A6C2EC` | `#6E97DD` | `#1A66C2` | `#003D85` | `#002659` | `#00193D` |
| Purple | `#ECE3F5` | `#C8B0E0` | `#A37DC9` | `#7B45B0` | `#5C1E91` | `#3C0F60` | `#270A40` |

### 1.3 Categorical Palettes (다중 시리즈)

각 테마의 anchor가 가장 강조되도록 보조색은 채도를 낮춘 charcoal과 gray를 우선 배치하고, 그 다음에 다른 테마의 deep color를 보색 순으로 추가한다. **2번(charcoal)과 3번(warm gray)은 모든 테마 공통**.

| 테마 | 1 (anchor) | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Red    | `#A50034` | `#2C2C2A` | `#888780` | `#0F6E56` | `#003D85` | `#7A4D00` |
| Orange | `#A85400` | `#2C2C2A` | `#888780` | `#003D85` | `#5C1E91` | `#007A3D` |
| Yellow | `#A37800` | `#2C2C2A` | `#888780` | `#5C1E91` | `#003D85` | `#A50034` |
| Green  | `#007A3D` | `#2C2C2A` | `#888780` | `#A50034` | `#A85400` | `#5C1E91` |
| Blue   | `#003D85` | `#2C2C2A` | `#888780` | `#A85400` | `#A50034` | `#007A3D` |
| Purple | `#5C1E91` | `#2C2C2A` | `#888780` | `#A37800` | `#007A3D` | `#A50034` |

### 1.4 Diverging Palettes (긍정/부정)

테마 anchor → 중립 cream(`#F1EFE8`) → 보색 anchor. 5-stop.

| 테마 (부정 → 긍정) | 0 | 25 | 50 | 75 | 100 |
|---|---|---|---|---|---|
| Red ↔ Green     | `#A50034` | `#E5A8B8` | `#F1EFE8` | `#A8D5C3` | `#007A3D` |
| Orange ↔ Blue   | `#A85400` | `#E0BC8C` | `#F1EFE8` | `#9DB8DD` | `#003D85` |
| Yellow ↔ Purple | `#A37800` | `#DCC787` | `#F1EFE8` | `#B49BCE` | `#5C1E91` |
| Green ↔ Red     | `#007A3D` | `#8DC6A4` | `#F1EFE8` | `#E5A8B8` | `#A50034` |
| Blue ↔ Orange   | `#003D85` | `#9DB8DD` | `#F1EFE8` | `#E0BC8C` | `#A85400` |
| Purple ↔ Yellow | `#5C1E91` | `#B49BCE` | `#F1EFE8` | `#DCC787` | `#A37800` |

방향성은 데이터 의미에 따라 뒤집을 수 있다 (예: 매출 증감은 Red가 부정, 위험도는 Red가 주의로 강조).

### 1.5 공통 Neutrals (테마 무관)

```json
{
  "text.strong": "rgba(0, 0, 0, 0.85)",
  "text.body":   "rgba(0, 0, 0, 0.70)",
  "text.muted":  "rgba(0, 0, 0, 0.50)",
  "grid":        "rgba(0, 0, 0, 0.06)",
  "reference":   "rgba(0, 0, 0, 0.30)",
  "background":  "transparent"
}
```

다크모드는 흰색 기준 동일 투명도 (`rgba(255, 255, 255, ...)`).

### 1.6 테마 적용 방법

선택한 테마의 `anchor` 값으로 base config (§5)의 `#A50034`를 모두 치환한다. 동일 anchor에서 muted/tint/ramp는 §1.2~1.4 테이블에서 가져와 매핑.

```python
THEMES = {
    "red":    {"anchor": "#A50034", "muted": "rgba(165,0,52,0.22)",  "tint": "rgba(165,0,52,0.08)",  "dark": "#D14F70"},
    "orange": {"anchor": "#A85400", "muted": "rgba(168,84,0,0.22)",  "tint": "rgba(168,84,0,0.08)",  "dark": "#D17730"},
    "yellow": {"anchor": "#A37800", "muted": "rgba(163,120,0,0.22)", "tint": "rgba(163,120,0,0.08)", "dark": "#C49936"},
    "green":  {"anchor": "#007A3D", "muted": "rgba(0,122,61,0.22)",  "tint": "rgba(0,122,61,0.08)",  "dark": "#2BAA63"},
    "blue":   {"anchor": "#003D85", "muted": "rgba(0,61,133,0.22)",  "tint": "rgba(0,61,133,0.08)",  "dark": "#3070C2"},
    "purple": {"anchor": "#5C1E91", "muted": "rgba(92,30,145,0.22)", "tint": "rgba(92,30,145,0.08)", "dark": "#8957BC"},
}
```

---

## 2. Layout & Sizing

### 2.1 동적 너비

차트 전체 너비는 카테고리 수 × 슬롯(step)으로 자동 계산한다. Vega-Lite에서 `width: { step: N }` 한 줄로 처리.

| 카테고리 수 | step (px) | 차트 총 너비 | 비고 |
|---|---|---|---|
| 2–4    | 90–110 | 200–440 | 분기, 카테고리 비교 |
| 5–8    | 70–90  | 360–720 | 주별, 부서별 |
| 9–14   | 45–60  | 450–840 | 월별 |
| 15–24  | 30–40  | 480–960 | 일별(2~3주) |
| 25+    | 25–32  | scroll 또는 faceting | 일별 1개월+ |

Horizontal bar는 step이 행 높이가 된다: **36~44px**. 32 미만이면 답답, 50 이상이면 빈 공간이 거슬린다.

자동 step 계산 함수:
```python
def compute_step(n_categories, container_max=900, min_step=30, max_step=110):
    ideal = container_max / n_categories
    return max(min_step, min(max_step, ideal))
```

### 2.2 차트 높이

너비와 별개로 height는 고정 권장:
- Bar (vertical): 200–280px
- Line: 200–280px (banking to 45° 룰 적용)
- Horizontal bar: step × 카테고리 수 (자동)
- Heatmap, Matrix: 정사각형에 가깝게

### 2.3 Bar 너비

Vega-Lite `scale.paddingInner` (0–1)로 제어. 막대 간격이 막대 너비와 비슷할 때 가장 안정적.

| 카테고리 수 | paddingInner | 막대가 슬롯의 |
|---|---|---|
| 4 이하  | 0.5  | 50% |
| 5–8    | 0.4  | 60% |
| 9–14   | 0.3  | 70% |
| 15+    | 0.2  | 80% |

`paddingOuter`는 0.2 기본값. 좌우 여백을 약간 두면 차트가 답답하지 않다.

`cornerRadiusEnd: 3` — 살짝만 라운드. 큰 라운드는 데이터처럼 보이지 않고 UI 요소처럼 보인다.

### 2.4 Banking to 45° (라인 차트)

라인의 평균 기울기가 45도 근처가 되도록 가로:세로 비율 조정. 보통 시계열은 폭 넓고 높이 짧게(3:1 ~ 2:1). 너무 평평하거나 너무 가파른 라인은 변화량 인식이 떨어진다.

---

## 3. 색 사용 규칙

### 3.1 Mono (1색 + neutral) 사용 시점

다음 중 하나라도 해당하면 mono:

- 단일 시리즈 (한 종류의 값만 시간/카테고리별로 비교)
- 순위/랭킹 차트 (값 자체가 메시지)
- 강조하고 싶은 한 점이 있는 경우 (Q4만 진하게, 나머지는 muted)
- 시계열 단일 라인

판단 질문: **"이 색이 의미를 전달하나, 아니면 그냥 다르게 보이려는 건가?"** 후자면 mono.

### 3.2 Multi-color 사용 시점

색이 정보를 인코딩할 때만:

- 시리즈 자체가 비교 대상 (지역별/부서별/연도별 동시 비교)
- 그룹 막대, 다중 라인, 스택 막대
- 카테고리 간 의미 차이가 중요

### 3.3 시리즈 개수별 처리

| 시리즈 수 | 처리 |
|---|---|
| 1     | mono. 강조는 색이 아닌 값/위치로 |
| 2–3   | 진한 액센트 + 회색, 또는 같은 색 농도 변화 |
| 4–6   | 카테고리 팔레트 전체 사용 |
| 7+    | **faceting (small multiples)로 분할.** 한 차트 내 색만으로 구분 금지 |

### 3.4 강조 패턴

한 차트당 강조 포인트 1개. 강조 막대만 `accent.strong`, 나머지는 `accent.muted`.

```json
{
  "color": {
    "condition": { "test": "datum.quarter === 'Q4'", "value": "#A50034" },
    "value": "rgba(165, 0, 52, 0.22)"
  }
}
```

---

## 4. 숫자 & 단위 포맷팅

### 4.1 단위 자동 환산 (KRW)

최대값이 표시 숫자 1–999 범위에 들어오도록 단위 선택.

| max(value) 범위         | 단위    | divisor |
|------------------------|---------|---------|
| `< 10,000`             | 원      | 1       |
| `10,000 ~ 1억`          | 만원    | 1e4     |
| `1억 ~ 1조`             | 억원    | 1e8     |
| `>= 1조`                | 조원    | 1e12    |

### 4.2 단위 자동 환산 (USD)

| max(value) 범위         | 단위    | divisor |
|------------------------|---------|---------|
| `< $10K`               | $       | 1       |
| `$10K ~ $10M`           | $K      | 1e3     |
| `$10M ~ $10B`           | $M      | 1e6     |
| `>= $10B`               | $B      | 1e9     |

### 4.3 표기 규칙

- **단위는 부제목(subtitle)에**: "단위: 억원". 값 라벨엔 숫자만(`342`), 단위 반복 금지.
- **소수점 최대 1자리**. 가능하면 0자리.
- **천 단위 콤마 항상**: `format: ",.0f"`.
- **혼합 단위 금지**: 한 차트 내 모든 값은 같은 단위. "120억"과 "1.8조"가 같이 나오면 안 된다.
- **음수**: 부호가 단위 앞 (`-$5M`, `-12억`).
- **0과 null 구분**: null은 막대 없거나 회색 점선, 0은 막대 길이 0.

---

## 5. Vega-Lite Base Config

모든 spec에 머지하는 베이스. 한 번 정의해두고 spec generator가 자동 주입. 아래는 **Red 테마 기준**이며, 다른 테마는 §1에서 anchor/ramp/categorical/diverging 값을 가져와 치환한다.

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "background": null,
  "config": {
    "font": "system-ui, -apple-system, 'Pretendard', sans-serif",
    "view": { "stroke": null },

    "axis": {
      "labelFont": "system-ui",
      "labelFontSize": 12,
      "labelColor": "rgba(0,0,0,0.5)",
      "labelPadding": 8,
      "titleFont": "system-ui",
      "titleFontSize": 12,
      "titleColor": "rgba(0,0,0,0.78)",
      "titleFontWeight": 500,
      "titlePadding": 12,
      "domain": false,
      "ticks": false,
      "grid": false
    },
    "axisY": {
      "grid": true,
      "gridColor": "rgba(0,0,0,0.06)",
      "gridWidth": 1,
      "tickCount": 4
    },
    "axisX": { "labelAngle": 0 },

    "bar":   { "color": "#A50034", "cornerRadiusEnd": 3 },
    "line":  { "color": "#A50034", "strokeWidth": 2.5, "interpolate": "monotone" },
    "point": { "filled": true, "size": 60, "color": "#A50034" },
    "area":  { "color": "#A50034", "opacity": 0.1, "interpolate": "monotone" },
    "rule":  { "color": "rgba(0,0,0,0.3)", "strokeDash": [3, 3] },

    "range": {
      "category": ["#A50034", "#2C2C2A", "#888780", "#0F6E56", "#003D85", "#7A4D00"],
      "diverging": ["#A50034", "#E5A8B8", "#F1EFE8", "#A8D5C3", "#007A3D"],
      "ramp": ["#FBE6EC", "#F2B8C9", "#E58AA5", "#C73659", "#A50034", "#6E0023", "#4A0017"]
    },

    "title": {
      "font": "system-ui",
      "fontSize": 14,
      "fontWeight": 500,
      "color": "rgba(0,0,0,0.85)",
      "anchor": "start",
      "offset": 12,
      "subtitleFont": "system-ui",
      "subtitleFontSize": 12,
      "subtitleColor": "rgba(0,0,0,0.5)",
      "subtitlePadding": 4
    },

    "legend": {
      "labelFont": "system-ui",
      "labelFontSize": 12,
      "labelColor": "rgba(0,0,0,0.7)",
      "titleFont": "system-ui",
      "titleFontSize": 12,
      "symbolType": "square",
      "symbolSize": 100,
      "orient": "top",
      "direction": "horizontal",
      "labelOffset": 4
    }
  }
}
```

---

## 6. 자주 쓰는 패턴 (Snippets)

### 6.1 동적 너비 + bar 간격

```json
{
  "width": { "step": 60 },
  "encoding": {
    "x": {
      "field": "month",
      "type": "ordinal",
      "scale": { "paddingInner": 0.4, "paddingOuter": 0.2 }
    }
  }
}
```

### 6.2 한 막대만 강조

```json
{
  "encoding": {
    "color": {
      "condition": { "test": "datum.quarter === 'Q4'", "value": "#A50034" },
      "value": "rgba(165, 0, 52, 0.22)"
    }
  }
}
```

### 6.3 막대 위 값 라벨

```json
{
  "layer": [
    { "mark": "bar" },
    {
      "mark": { "type": "text", "dy": -8, "fontWeight": 500, "color": "rgba(0,0,0,0.78)" },
      "encoding": { "text": { "field": "value", "format": ",.0f" } }
    }
  ]
}
```

### 6.4 단위 환산 (transform)

```json
{
  "transform": [
    { "calculate": "datum.revenue_won / 100000000", "as": "revenue_eok" }
  ],
  "encoding": {
    "y": { "field": "revenue_eok", "type": "quantitative", "axis": { "format": ",.0f" } }
  },
  "title": { "text": "분기별 매출", "subtitle": "단위: 억원" }
}
```

### 6.5 평균 참조선

```json
{
  "layer": [
    { "mark": "bar", "encoding": { "x": {"field": "quarter"}, "y": {"field": "revenue"} } },
    {
      "mark": { "type": "rule", "strokeDash": [3, 3], "color": "rgba(0,0,0,0.3)" },
      "encoding": { "y": { "aggregate": "mean", "field": "revenue" } }
    }
  ]
}
```

### 6.6 라인 + 면적 (시계열)

```json
{
  "layer": [
    {
      "mark": {
        "type": "area",
        "line": { "color": "#A50034", "strokeWidth": 2.5 },
        "color": "#A50034",
        "opacity": 0.1,
        "interpolate": "monotone"
      },
      "encoding": {
        "x": { "field": "month", "type": "ordinal" },
        "y": { "field": "revenue", "type": "quantitative" }
      }
    },
    {
      "mark": { "type": "point", "filled": true, "size": 50, "color": "#A50034" },
      "encoding": {
        "x": { "field": "month", "type": "ordinal" },
        "y": { "field": "revenue", "type": "quantitative" }
      }
    }
  ]
}
```

### 6.7 Faceting (small multiples)

```json
{
  "facet": { "field": "region", "type": "nominal", "columns": 3 },
  "spec": {
    "width": { "step": 40 },
    "height": 120,
    "mark": "line",
    "encoding": {
      "x": { "field": "month", "type": "ordinal" },
      "y": { "field": "revenue", "type": "quantitative" }
    }
  },
  "resolve": { "scale": { "y": "shared" } }
}
```

### 6.8 툴팁

```json
{
  "encoding": {
    "tooltip": [
      { "field": "quarter", "type": "nominal", "title": "분기" },
      { "field": "revenue", "type": "quantitative", "format": ",.0f", "title": "매출(억원)" },
      { "field": "yoy", "type": "quantitative", "format": "+.1%", "title": "전년 대비" }
    ]
  }
}
```

---

## 7. 추가 디자인 기준

### 7.1 정렬 기본값

| 차트 유형 | 정렬 | Vega-Lite |
|---|---|---|
| 순위/랭킹 (제품별, 지역별) | 값 DESC | `sort: "-x"` 또는 `"-y"` |
| 시계열 (월별, 일별) | 시간 ASC | 기본 |
| 자연 순서 (요일, 사이즈, 분기) | 명시 | `sort: ["Mon","Tue",...]` |
| 명목 (지역명) | 알파벳/가나다 | `sort: "ascending"` |

### 7.2 참조선 / 타겟선

- 점선 (`strokeDash: [3, 3]`)
- 회색 30% 투명도 (`rgba(0,0,0,0.3)`)
- 라벨은 우측 끝에 작은 글씨 (font-size 11px)
- 용도: 평균선, 전년 동기, 목표값

### 7.3 툴팁 룰

- 1행: 카테고리 라벨 (강하게)
- 2행: 메인 값 + 단위 (명시적으로 "342억원" — 컨텍스트 없는 숫자 금지)
- 3행: 보조 컨텍스트 (전년 대비 +12% 등, 있을 때만)
- `displayColors: false` — 단일 시리즈에선 색 점이 노이즈

### 7.4 Null vs 0

- **Null** (데이터 없음): 막대 그리지 않거나 회색 점선 placeholder
- **0** (값이 0): 막대 길이 0, 라벨 "0" 표시
- 라인 차트의 null: `defined: false`로 처리, 갭으로 표현

### 7.5 색맹 대응

- 빨강 단독 액센트는 적록 색맹(남성 8%)에 영향 없음 (회색 대비)
- 단 빨강(부정)/녹색(긍정) diverging 사용 시 부호(▲▼ +/-)나 위치도 함께 인코딩
- 색만으로 시리즈 구분 금지 — line은 dash, scatter는 shape, bar는 pattern 병기

### 7.6 Title 위계

- **title**: 무엇 ("분기별 매출")
- **subtitle**: 범위 + 단위 ("2025년 · 단위 억원")
- **footer/source**: 출처 (있을 때만, 회색 작은 글씨로 차트 아래)

### 7.7 Annotation

강조 막대 위에 짧은 설명:
- "Q4 +31% — 신제품 출시 효과"
- font-size 11px
- 액센트 색

### 7.8 Empty State

데이터 0 row일 때 빈 차트 그리지 말 것. "데이터 없음" 메시지 + 회색 placeholder. NL2Chart의 SQL 결과 0 row는 항상 발생 가능 케이스 → spec generator 레벨에서 처리.

### 7.9 Animation

- 초기 로드: 200~400ms ease-out (막대 올라오기, 라인 그려지기)
- 호버 전환: 100ms 미만
- Vega 기본 update animation 활용

---

## 8. NL2Chart 적용 체크리스트

차트 spec 생성 시 매번 확인:

- [ ] base config 머지됨
- [ ] step 값이 카테고리 수에 맞게 계산됨
- [ ] 단위가 자동 결정되고 subtitle에 명시됨
- [ ] 시리즈 1개면 mono, 다중이면 categorical 팔레트
- [ ] 시리즈 7개+면 facet으로 전환됨
- [ ] 정렬 규칙이 차트 유형에 맞게 적용됨
- [ ] 강조 포인트가 있다면 색 condition 적용됨
- [ ] 숫자 format이 ",.0f" 또는 ",.1f"로 통일됨
- [ ] 음수/0/null 케이스 처리됨
- [ ] 0 row일 때 empty state로 대체됨

---

## 9. 색 토큰 빠른 참조

### 9.1 테마별 액센트 (라이트 / 다크)

| 테마 | Anchor (Light) | Anchor (Dark) | Muted (Light) | Muted (Dark) |
|---|---|---|---|---|
| Red    | `#A50034` | `#D14F70` | `rgba(165,0,52,0.22)`   | `rgba(209,79,112,0.28)` |
| Orange | `#A85400` | `#D17730` | `rgba(168,84,0,0.22)`   | `rgba(209,119,48,0.28)` |
| Yellow | `#A37800` | `#C49936` | `rgba(163,120,0,0.22)`  | `rgba(196,153,54,0.28)` |
| Green  | `#007A3D` | `#2BAA63` | `rgba(0,122,61,0.22)`   | `rgba(43,170,99,0.28)`  |
| Blue   | `#003D85` | `#3070C2` | `rgba(0,61,133,0.22)`   | `rgba(48,112,194,0.28)` |
| Purple | `#5C1E91` | `#8957BC` | `rgba(92,30,145,0.22)`  | `rgba(137,87,188,0.28)` |

면적 fill은 muted 알파를 0.08~0.12로 낮춰 사용.

### 9.2 공통 Neutrals (테마 무관)

| 용도 | 라이트 | 다크 |
|---|---|---|
| 본문 텍스트       | `rgba(0,0,0,0.85)`  | `rgba(255,255,255,0.85)` |
| 보조 텍스트 (축 라벨) | `rgba(0,0,0,0.50)`  | `rgba(255,255,255,0.50)` |
| 그리드            | `rgba(0,0,0,0.06)`  | `rgba(255,255,255,0.07)` |
| 참조선            | `rgba(0,0,0,0.30)`  | `rgba(255,255,255,0.30)` |
| Charcoal (categorical #2) | `#2C2C2A` | `#2C2C2A` |
| Warm gray (categorical #3) | `#888780` | `#888780` |
