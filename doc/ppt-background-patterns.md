# PPT Background Patterns

PPT 슬라이드의 **배경 디자인 요소**만 정의한 패턴 카탈로그. HTML로 먼저 그리고 PPTX로 렌더링하는 워크플로우에서 슬라이드 마스터/템플릿 레벨로 쓸 수 있도록 구성.

배경 패턴은 **HTML을 통째로 PNG로 렌더링하여 슬라이드 배경 이미지로 삽입**한다. 텍스트·차트·데이터 레이어는 그 위에 PPTX 네이티브 요소로 별도 레이어링.

## 제약 사항

- ✅ 솔리드 색상만 — 그라데이션 금지
- ✅ 기하 도형 (사각형, 원, 선) 만 — 장식 아이콘/일러스트 금지
- ✅ 큰 typographic 요소는 배경 앵커 용도로만 (본문 내 bullet 대체 X)

색은 모두 `ppt-color-palette.md`에서 정의한 테마 토큰을 사용한다 (`--theme-strong`, `--theme-soft` 등).

---

## Pattern 01 — Horizontal Bands

상단 얇은 색 띠. 본문에 절제된 브랜드 존재감.

```
┌─────────────────────────────┐
│           ANCHOR            │  (얇은 띠, 8~12%)
├─────────────────────────────┤
│                             │
│            WHITE            │
│                             │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); display: flex; flex-direction: column;">
  <div style="height: 10%; background: var(--theme-strong);"></div>
  <div style="flex: 1;"><!-- content area --></div>
</div>
```

**용도**: 본문 슬라이드의 가벼운 브랜딩, 챕터 첫 슬라이드  
**띠 두께**: 6~12% (얇게) / 20~25% (중간) / 50% (강한 분할)  
**변형**: 상단만 / 하단만 / 상+하 둘 다 (얇게)

---

## Pattern 02 — Side Strip

한쪽 가장자리에 얇은 세로 색 띠. 가장 절제된 브랜드 표시.

```
┌──┬──────────────────────────┐
│  │                          │
│ A│         WHITE            │
│  │                          │
└──┴──────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; display: flex; background: var(--surface-white);">
  <div style="width: 5%; background: var(--theme-strong);"></div>
  <div style="flex: 1;"><!-- content area --></div>
</div>
```

**용도**: 시리즈 본문 슬라이드 (브랜드 일관성), 챕터 색 코딩  
**띠 두께**: 3~8% 권장. 그 이상이면 Pattern 04로 전환  
**활용**: 같은 챕터 슬라이드들에 일관 적용하면 챕터 식별 단서가 됨

---

## Pattern 03 — Corner Block

한 모서리에 작은 색상 블록. 미니멀한 강조.

```
┌─────────────────────────┬──┐
│                         │ A│
│                         └──┤
│         WHITE              │
│                            │
└────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); position: relative;">
  <div style="position: absolute; top: 0; right: 0; width: 14%; height: 22%; background: var(--theme-strong);"></div>
  <!-- content area -->
</div>
```

**용도**: 본문 슬라이드의 매우 절제된 강조, "조용한" 브랜딩  
**크기**: 가로 10~18% × 세로 18~28%  
**위치 옵션**: 우상단(기본) / 우하단 / 좌상단 / 좌하단

---

## Pattern 04 — Asymmetric Two-Block

크기가 다른 두 색 블록. 강한 시각 분할.

```
┌──────────┬──────────────────┐
│          │                  │
│  DEEPEST │      WHITE       │
│          │                  │
└──────────┴──────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; display: flex;">
  <div style="width: 38%; background: var(--theme-deepest);"><!-- left (white text) --></div>
  <div style="width: 62%; background: var(--surface-white);"><!-- right (dark text) --></div>
</div>
```

**용도**: Cover, 좌: 타이틀 / 우: 설명 식의 강한 분할 구성  
**비율**: 38:62 (황금비 근사) / 40:60 / 33:67  
**변형**: 좌측을 anchor / deepest / charcoal 중 선택

---

## Pattern 05 — Outline Frame

콘텐츠 영역 둘레의 얇은 테두리. 잡지/에디토리얼 느낌.

```
┌─────────────────────────────┐
│ ┌─────────────────────────┐ │
│ │                         │ │
│ │         WHITE           │ │
│ │                         │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); padding: 4%;">
  <div style="height: 100%; box-sizing: border-box; border: 2px solid var(--theme-strong);">
    <!-- content -->
  </div>
</div>
```

**용도**: 인용(quote) 슬라이드, 프리미엄 콘텐츠, 명함 스타일 cover  
**테두리 두께**: 1.5~3pt. 두꺼우면 답답함  
**여백**: 슬라이드 끝에서 3~5%, 테두리 안쪽에서 5~7% 내부 패딩

---

## Pattern 06 — Circle Accent (Cropped)

큰 원의 일부가 모서리에서 노출. 부드러운 임팩트.

```
┌─────────────────────────────┐
│                             │
│         WHITE               │
│                       ╱─────│
│                      │ ANC  │
│                       ╲─────│
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); position: relative; overflow: hidden;">
  <div style="position: absolute; bottom: -40%; right: -15%; width: 50%; aspect-ratio: 1; border-radius: 50%; background: var(--theme-strong);"></div>
  <!-- content -->
</div>
```

**용도**: Cover 슬라이드의 부드러운 변형, 오프닝/마무리 슬라이드  
**원 크기**: 슬라이드 너비의 40~60% 직경  
**위치**: 우하단(기본) / 우상단 / 좌상단 / 좌하단  
**변형**: `theme-soft` 톤으로 바꾸면 절제된 느낌

---

## Pattern 07 — Numbered Backdrop

큰 숫자가 muted 톤으로 배경에 깔림. 섹션 마커 용도.

```
┌─────────────────────────────┐
│                             │
│   ██  ██     섹션 제목      │
│  ██  ██     설명 텍스트     │
│   ██  ██                    │
│                             │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); position: relative;">
  <div style="position: absolute; top: 5%; left: 3%; font-size: 24rem; font-weight: 700; line-height: 0.9; color: var(--theme-soft); user-select: none;">01</div>
  <!-- content on top -->
</div>
```

**용도**: Section Divider, 순차 챕터 표시 (01, 02, 03...)  
**숫자 색**: `--theme-soft` (100 ramp) 권장. tint(50)는 너무 흐림  
**위치**: 좌측 정렬, 좌단에서 살짝 잘려도 모던한 느낌  
**주의**: 배경 앵커 용도만. 본문 슬라이드에서는 사용 금지

---

## Pattern 08 — Title Rule

타이틀 아래 얇은 가로 선 하나. 정형화된 보고서 양식의 기본형.

```
┌─────────────────────────────┐
│                             │
│ Title text here             │
│ ─────────────────────────── │
│                             │
│         Content             │
│                             │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); padding: 4% 5%;">
  <div style="font-size: 22pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.4em;">
    분기별 매출 분석
  </div>
  <div style="height: 1pt; background: var(--theme-strong); margin-bottom: 4%;"></div>
  <div><!-- content area --></div>
</div>
```

**용도**: 컨설팅·임원·분석 리포트의 표준 본문 슬라이드  
**Rule 색**: theme-strong (기본) / charcoal (중립) / theme-mid (절제)  
**Rule 두께**: 0.5pt (최소) / 1pt (기본) / 1.5pt (강조)  
**Rule 너비**: full-width (기본) / 타이틀 길이만큼 / 슬라이드 폭의 30~50%

---

## Pattern 09 — Header Band

상단 색상 밴드 안에 타이틀. 명확한 헤더 구조.

```
┌─────────────────────────────┐
│██ Title text here          ██│
├─────────────────────────────┤
│                             │
│         Content             │
│                             │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); display: flex; flex-direction: column;">
  <div style="height: 14%; background: var(--theme-strong); display: flex; align-items: center; padding: 0 5%;">
    <div style="font-size: 20pt; font-weight: 600; color: var(--surface-white);">
      분기별 매출 분석
    </div>
  </div>
  <div style="flex: 1; padding: 3% 5%;"><!-- content --></div>
</div>
```

**용도**: 챕터 시작 슬라이드, 명확한 분류가 필요한 본문  
**밴드 높이**: 12~16% 권장  
**Pattern 01과의 차이**: Pattern 01은 장식 띠, Pattern 09는 타이틀이 밴드 안에 직접 들어감  
**변형**: 밴드 우측에 챕터 번호·페이지 번호 배치 가능

---

## Pattern 10 — Title Block with Meta + Rule

메타 정보(섹션/챕터) + 타이틀 + 가로 선의 3단 헤더.

```
┌─────────────────────────────┐
│ SECTION 02 · 매출 분석      │
│                             │
│ Title text here             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                             │
│         Content             │
│                             │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); padding: 4% 5%;">
  <div style="font-size: 10pt; font-weight: 500; color: var(--text-muted); letter-spacing: 0.1em; margin-bottom: 0.6em;">
    SECTION 02 · 매출 분석
  </div>
  <div style="font-size: 24pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.6em;">
    분기별 매출 성장률
  </div>
  <div style="height: 1.5pt; background: var(--theme-strong); margin-bottom: 4%;"></div>
  <div><!-- content --></div>
</div>
```

**용도**: 구조가 명확한 챕터형 보고서, 인덱스가 중요한 긴 덱(20장 이상)  
**메타 텍스트**: ALL CAPS, letter-spacing 강조, font-size 9~11pt, color muted  
**변형**: 메타 자리에 페이지 번호 / 작성일자 / 작성자명

---

## Pattern 11 — Report Sandwich

상단 rule + 하단 rule이 콘텐츠를 감싸는 정형 보고서 양식.

```
┌─────────────────────────────┐
│ Title                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                             │
│         Content             │
│                             │
│ ─────────────────────────── │
│ Source · Page 1 / 12        │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); padding: 4% 5%; display: flex; flex-direction: column;">
  <div style="font-size: 22pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.4em;">
    분기별 매출 분석
  </div>
  <div style="height: 1.5pt; background: var(--theme-strong);"></div>

  <div style="flex: 1; padding: 3% 0;"><!-- content area --></div>

  <div style="height: 0.5pt; background: var(--border-subtle);"></div>
  <div style="display: flex; justify-content: space-between; font-size: 9pt; color: var(--text-muted); padding-top: 0.6em;">
    <span>출처: 2025 사업보고서</span>
    <span>Page 5 / 24</span>
  </div>
</div>
```

**용도**: IR / 감사 / 이사회 자료, 출처 표기가 중요한 분석 자료  
**Top rule**: 1~1.5pt, theme-strong  
**Bottom rule**: 0.5pt, `--border-subtle`. 진하면 답답함  
**일관성 필수**: 채택하면 모든 본문 슬라이드에 동일 적용

---

## Pattern 12 — Header + Footer Sandwich

앵커 색 헤더 밴드 + 흰 콘텐츠 + tint 색 푸터 밴드. 상하 컬러 밴드가 콘텐츠를 감싸는 구조.

```
┌─────────────────────────────┐
│██ Title here               ██│  (anchor, 헤더 밴드)
├─────────────────────────────┤
│                             │
│         Content             │
│                             │
├─────────────────────────────┤
│ Source              Page 5  │  (tint, 푸터 밴드)
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); display: flex; flex-direction: column;">
  <div style="height: 16%; background: var(--theme-strong); display: flex; align-items: center; padding: 0 5%;">
    <div style="font-size: 20pt; font-weight: 600; color: var(--surface-white);">
      분기별 매출 분석
    </div>
  </div>

  <div style="flex: 1; padding: 3% 5%;"><!-- content --></div>

  <div style="height: 12%; background: var(--theme-tint); display: flex; align-items: center; padding: 0 5%; justify-content: space-between;">
    <span style="font-size: 9pt; color: var(--theme-strong);">출처: 2025 사업보고서</span>
    <span style="font-size: 9pt; color: var(--theme-strong);">Page 5 / 24</span>
  </div>
</div>
```

**용도**: 출처·페이지가 명시적으로 분리되어야 하는 공식 보고서, IR 자료  
**헤더 높이**: 14~18%  
**푸터 높이**: 10~14% (헤더보다 약간 얇게)  
**Pattern 11과의 차이**: Pattern 11은 얇은 rule선, Pattern 12는 밴드 자체가 컨테이너  
**푸터 색**: theme-tint (50 ramp) — anchor와 같은 색 계열이지만 연해서 시각 계층 유지

---

## Pattern 13 — Side Panel + Title Rule

좌측 앵커 색 패널 + 세로 구분선 + 오른쪽 내부 가로 rule. 세로·가로 구조가 동시에 적용.

```
┌──────┬──────────────────────┐
│      │ Title                │
│  S   │ ──────────────────── │
│  E   │                      │
│  C   │    Content           │
│      │                      │
└──────┴──────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; display: flex;">
  <div style="width: 18%; background: var(--theme-strong); display: flex; align-items: center; justify-content: center;">
    <div style="writing-mode: vertical-rl; transform: rotate(180deg); font-size: 11pt; font-weight: 500; color: var(--theme-soft); letter-spacing: 0.1em;">
      SECTION 02
    </div>
  </div>
  <div style="width: 1px; background: var(--theme-strong);"></div>
  <div style="flex: 1; padding: 5% 5%; display: flex; flex-direction: column;">
    <div style="font-size: 20pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.4em;">
      분기별 매출 분석
    </div>
    <div style="height: 1pt; background: var(--theme-strong); margin-bottom: 4%;"></div>
    <div style="flex: 1;"><!-- content --></div>
  </div>
</div>
```

**용도**: 챕터 식별이 중요한 긴 덱, 섹션별 색 코딩 + 보고서 구조가 동시에 필요한 경우  
**패널 너비**: 15~20%  
**패널 텍스트**: `writing-mode: vertical-rl; transform: rotate(180deg)` — 아래에서 위로 읽히는 방향  
**세로 구분선**: 1px, theme-strong 또는 --border-subtle (절제된 버전)  
**활용**: 패널 색을 챕터마다 다르게 하면 챕터 구분 역할을 겸함

---

## Pattern 14 — Split Content Zones

제목·rule 헤더 아래 콘텐츠 영역이 본문 존(좌)과 KPI/하이라이트 존(우)으로 분리.

```
┌─────────────────────────────┐
│ META · Title                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                    │        │
│   CONTENT (60%)    │  KPI   │
│                    │  ZONE  │
│                    │ (tint) │
└─────────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); padding: 4% 5%; display: flex; flex-direction: column; box-sizing: border-box;">
  <div style="font-size: 10pt; color: var(--text-muted); letter-spacing: 0.1em; margin-bottom: 0.4em;">SECTION 02 · 매출 분석</div>
  <div style="font-size: 22pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.5em;">분기별 매출 성장률</div>
  <div style="height: 1.5pt; background: var(--theme-strong); margin-bottom: 3%;"></div>

  <div style="flex: 1; display: flex; gap: 0;">
    <div style="flex: 3; padding-right: 4%;"><!-- 본문 콘텐츠 --></div>
    <div style="width: 1px; background: var(--border-subtle);"></div>
    <div style="flex: 2; padding-left: 4%; background: var(--theme-tint);"><!-- KPI 영역 --></div>
  </div>
</div>
```

**용도**: 본문 + KPI/통계를 같은 슬라이드에서 구조적으로 분리해야 할 때  
**콘텐츠:KPI 비율**: 3:2 (기본) / 2:1 / 1:1 (동등 비교)  
**KPI 존 배경**: theme-tint (50 ramp) — 강조 콘텐츠가 올라갈 영역임을 암시  
**세로 구분선**: --border-subtle (0.5~1pt)로 부드럽게

---

## Pattern 15 — Accent Column + Rule

얇은 앵커 상단 스트립 + 소프트 tint 세로 컬럼 + 내부 가로 rule. 절제된 구조감.

```
┌──────────────────────────────┐
│ ──────────── ANCHOR STRIP ── │  (얇은 상단 스트립, 4%)
├──┬───────────────────────────┤
│  │ Title                     │
│T │ ─────────────────────     │  (가로 rule)
│I │                           │
│N │    Content                │
│T │                           │
└──┴───────────────────────────┘
```

```html
<div class="slide" style="aspect-ratio: 16/9; background: var(--surface-white); position: relative;">
  <div style="position: absolute; top: 0; left: 0; width: 100%; height: 4%; background: var(--theme-strong);"></div>
  <div style="position: absolute; top: 4%; left: 0; width: 7%; height: 96%; background: var(--theme-tint);"></div>

  <div style="position: relative; z-index: 2; padding: 8% 5% 5% 12%;">
    <div style="font-size: 22pt; font-weight: 600; color: var(--text-title); margin-bottom: 0.4em;">
      분기별 매출 분석
    </div>
    <div style="height: 1pt; background: var(--theme-strong); margin-bottom: 4%;"></div>
    <div><!-- content --></div>
  </div>
</div>
```

**용도**: 구조감은 있지만 강한 색 블록 없이 가볍게 가고 싶은 본문  
**상단 스트립**: 3~5% (너무 두꺼우면 Pattern 01과 구분 안 됨)  
**세로 컬럼**: 6~8%, theme-tint (50 ramp) — anchor 색이면 Pattern 02와 같아짐  
**내부 여백**: 좌측 컬럼 두께 + 2~3% 추가 margin으로 콘텐츠 구분

---

## 패턴 → 슬라이드 역할 매핑

| 슬라이드 역할 | 1순위 패턴 | 2순위 패턴 |
|---|---|---|
| Cover / Title | 04 Asymmetric · 05 Outline · 06 Circle | 01 Horizontal · 03 Corner |
| Section Divider | 07 Numbered Backdrop · 09 Header Band | 04 Asymmetric |
| 본문 (보고서형, 정형) | 08 Title Rule · 11 Report Sandwich | 10 Title+Meta+Rule |
| 본문 (보고서형, 복합) | 12 Header+Footer · 13 Side Panel · 14 Split Zones | 15 Accent Column |
| 본문 (일반) | 02 Side Strip · 01 Horizontal | 03 Corner Block |
| Stats / KPI | 08 Title Rule · 14 Split Zones | 02 Side Strip |
| Quote / Insight | 05 Outline Frame | 03 Corner |
| Closing | 04 Asymmetric · 06 Circle | 09 Header Band |

---

## 조합 규칙 (한 덱 안에서)

1. **한 덱 = 최대 3종 패턴**. Cover 패턴 1 + 본문 패턴 1 + Divider 패턴 1 정도가 sweet spot.
2. **본문 패턴은 모든 본문 슬라이드에 동일하게**. 슬라이드마다 패턴이 바뀌면 일관성 깨짐.
3. **Cover와 Closing은 같은 패턴**. 수미상관 효과로 덱이 완결돼 보임.
4. **Divider는 본문과 강하게 대비**. 본문이 light면 Divider는 dark.
5. **색은 한 테마만**. 다른 테마를 한 덱에 섞지 말 것.
6. **패턴 위에 패턴 쌓지 말 것**. 배경 패턴은 슬라이드당 항상 한 개.
7. **보고서형 패턴(08~15) 안에서도 하나만**. Pattern 10(meta+rule)을 쓰면서 13(side panel)도 같이 쓰면 구조가 충돌.

---

## 안티패턴 (금지 사항)

- ❌ 그라데이션 채우기 (linear-gradient, radial-gradient 등 일체)
- ❌ Drop shadow를 패턴 요소에 적용 (배경은 평면이어야 함)
- ❌ 장식용 아이콘 (체크, 별, 화살표 등) — 콘텐츠 안의 의미 있는 아이콘은 OK, 배경 장식 X
- ❌ 사선 줄무늬, 도트 패턴, 격자 패턴 같은 "텍스처" — solid color만
- ❌ 슬라이드 가장자리에 두꺼운 색 바 + 추가 장식선 (AI슬라이드처럼 보임)
- ❌ Title 아래 자동 액센트 라인
- ❌ 한 슬라이드에 색 블록 3개 이상 (시각 노이즈)
- ❌ Numbered backdrop(07)을 본문 슬라이드에서 (Divider 전용)
