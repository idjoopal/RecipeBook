# AgentiKit — Frontend

Prebuilt MCP 서버의 도구를 시각적으로 조회하고 채팅 형태로 호출할 수 있는 **테스트/시연용 React UI** 입니다. 빌드 산출물(`dist/`)은 백엔드 FastAPI가 `/ui/` 경로로 정적 서빙합니다.

---

## 목차

1. [기능 개요](#1-기능-개요)
2. [기술 스택](#2-기술-스택)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [빌드 / 실행](#4-빌드--실행)
5. [백엔드와의 연결 방식](#5-백엔드와의-연결-방식)
6. [MCP 클라이언트 구현 메모](#6-mcp-클라이언트-구현-메모)
7. [도구 토글 (클라이언트 사이드)](#7-도구-토글-클라이언트-사이드)
8. [테마 / 디자인 토큰](#8-테마--디자인-토큰)
9. [트러블슈팅](#9-트러블슈팅)

---

## 1. 기능 개요

| 기능 | 설명 |
|------|------|
| MCP 연결 | 페이지 로드 시 `/mcp/`로 `initialize` + `tools/list` 호출, 헤더 우측에 상태 뱃지 표시 |
| 도구 카드 패널 | 사이드바에 등록된 MCP 도구 목록. 카드 클릭 시 전체 description + inputSchema(키/타입/required) 펼침 |
| 도구 ON/OFF 토글 | 카드 우측 토글 스위치로 도구를 비활성화. 비활성 도구는 헤더 드롭다운/실행 대상에서 자동 제외. localStorage에 상태 저장 |
| 도구 셀렉터 | 헤더 우측 드롭다운 — 채팅 입력을 어느 도구의 `input`으로 보낼지 선택 |
| 채팅 인터페이스 | 입력창에 텍스트 작성 → 선택된 도구의 `tools/call` 실행 → 결과를 어시스턴트 말풍선으로 표시 |
| 환경변수 관리 모달 | 사이드바 하단 `⚙ Settings` — 백엔드 `/api/admin/env` 로 `.env` 항목 조회/편집, `/api/admin/restart`로 서버 재기동 |

---

## 2. 기술 스택

- **빌드**: Vite 5
- **프레임워크**: React 18 (함수형 컴포넌트 + Hooks)
- **언어**: JavaScript (ESM, JSX) — TypeScript 미사용
- **상태 관리**: 별도 라이브러리 없음. `useState` / `useEffect` / `useCallback` + localStorage
- **HTTP**: 브라우저 내장 `fetch`. MCP SDK 미사용 — Streamable HTTP를 직접 구현 (`src/mcp/client.js`)
- **스타일**: 단일 `App.css` + CSS Custom Properties(`:root` 변수)로 테마 토큰화

---

## 3. 디렉토리 구조

```
frontend/
├── index.html              ← 진입점 HTML (title: AgentiKit)
├── vite.config.js          ← base: '/ui/', dev proxy 설정
├── package.json
└── src/
    ├── main.jsx            ← React root mount
    ├── App.jsx             ← 최상위 컴포넌트. 연결/도구/메시지 상태 관리
    ├── App.css             ← 전역 스타일 + 테마 토큰
    ├── mcp/
    │   └── client.js       ← MCP Streamable HTTP 클라이언트 (initialize/listTools/callTool)
    └── components/
        ├── Header.jsx          ← 로고 + ConnectionBadge + ToolSelector
        ├── ConnectionBadge.jsx ← MCP 연결 상태 점 (ready/connecting/error/restarting)
        ├── ToolSelector.jsx    ← 헤더 우측 도구 선택 드롭다운
        ├── Sidebar.jsx         ← 좌측 패널 컨테이너
        ├── ToolsPanel.jsx      ← 도구 카드 + 토글 + 펼침
        ├── SessionPanel.jsx    ← MCP session id / serverInfo 표시
        ├── ChatWindow.jsx      ← 메시지 리스트 + 스크롤
        ├── Message.jsx         ← user / assistant / error 말풍선
        ├── InputBar.jsx        ← 텍스트 입력 + Send
        └── SettingsModal.jsx   ← Admin API 연동 (.env 편집 / 서버 재기동)
```

---

## 4. 빌드 / 실행

### 의존성 설치

```bash
cd frontend
npm install
```

### 운영용 빌드

```bash
npm run build
```

`frontend/dist/` 생성. 백엔드를 띄운 상태에서 브라우저로 `http://<host>:<port>/ui/` 접속하면 됩니다. (백엔드 `main.py`가 `frontend/dist` 디렉토리 존재 여부를 확인하고 자동으로 `/ui`에 마운트합니다.)

### 개발 모드 (Vite Hot Reload)

```bash
npm run dev
```

기본 포트 `5173`. **백엔드를 별도 프로세스로 띄워두고** Vite가 `/mcp`, `/api`, `/health` 요청을 백엔드로 프록시합니다.

**중요**: 백엔드 포트를 9101이 아닌 다른 포트로 운영 중이라면 [`vite.config.js`](vite.config.js)의 `server.proxy` 대상 포트를 그 포트에 맞춰 주세요.

```js
// vite.config.js
server: {
  proxy: {
    '/mcp': 'http://localhost:32111',
    '/api': 'http://localhost:32111',
    '/health': 'http://localhost:32111',
  },
}
```

`base: '/ui/'`는 운영 빌드용 경로입니다. Vite dev 서버 자체는 `/` 루트로 떠 있으니, dev 모드 접속은 `http://localhost:5173/` 입니다.

---

## 5. 백엔드와의 연결 방식

```
┌─────────────────────────────────────────────────────────┐
│  브라우저                                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AgentiKit (React)                               │   │
│  │   ├─ fetch('/mcp/')          → MCP JSON-RPC      │   │
│  │   ├─ fetch('/api/admin/env')  → Admin API        │   │
│  │   └─ fetch('/health/live')    → 재기동 폴링       │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ same-origin
                         ▼
              ┌──────────────────────┐
              │  FastAPI :PORT       │
              │   /ui  → 정적 서빙    │
              │   /mcp → FastMCP     │
              │   /api/admin/*       │
              │   /api/my-agent/*    │
              │   /health/*          │
              └──────────────────────┘
```

빌드된 SPA는 백엔드와 **같은 origin에서 서빙**되므로 CORS 문제가 없고, 별도의 `BASE_URL` 설정 없이 상대 경로(`/mcp/`, `/api/...`)로 호출합니다.

---

## 6. MCP 클라이언트 구현 메모

[`src/mcp/client.js`](src/mcp/client.js)는 MCP SDK를 쓰지 않고 직접 구현했습니다. 핵심:

- **Transport**: MCP Streamable HTTP (`POST /mcp/`). 헤더 `Accept: application/json, text/event-stream`로 두 가지 응답 형태를 모두 수용.
- **세션 관리**: 첫 응답의 `Mcp-Session-Id` 헤더를 보관하고 이후 모든 요청에 동봉. `initialize` → `notifications/initialized` 순서.
- **SSE 파싱**: 응답이 `text/event-stream`이면 `data:` 라인을 추출해 JSON 파싱, `result` 또는 `error`가 있는 메시지를 최신값으로 유지.
- **트레일링 버퍼 flush**: 일부 응답은 마지막 메시지 뒤 `\n\n` 종결자 없이 stream을 닫습니다. read loop 종료 시 `buffer`에 남은 메시지를 한 번 더 파싱하는 처리가 들어가 있습니다. (이 처리가 빠지면 `tools/list`가 빈 배열을 반환하는 등의 증상이 발생합니다.)

주요 메서드:

| 메서드 | 설명 |
|--------|------|
| `initialize()` | 프로토콜 협상 + `notifications/initialized` 전송. `serverInfo`/`protocolVersion`을 인스턴스에 저장 |
| `listTools()` | `tools/list` 호출. `[{ name, description, inputSchema, ... }]` 반환 |
| `callTool(name, args)` | `tools/call` 호출. `content` 배열에서 `type === 'text'`인 항목만 합쳐 `{ text, elapsed }` 반환 |

---

## 7. 도구 토글 (클라이언트 사이드)

서버의 도구 등록 자체를 끄는 것이 아니라, **UI 차원에서만** 비활성화합니다.

- 상태: `App.jsx`의 `disabledTools: Set<string>`
- 저장소: localStorage 키 `agentikit.disabledTools` (JSON 배열로 직렬화)
- 적용 범위:
  - 헤더 `ToolSelector` 드롭다운에서 제외
  - 입력 전송 시 비활성 도구가 선택돼 있으면 자동으로 다른 enabled 도구로 교체
  - 사이드바 카드는 그대로 보이되 흐리게(grayscale + opacity) 표시
- 서버 측 영향 없음: 다른 MCP 클라이언트는 여전히 그 도구를 볼 수 있습니다.

영구적인 enable/disable이 필요하다면 백엔드 Admin API에 그 기능을 추가하고 클라이언트가 그 상태를 반영하도록 확장할 수 있습니다 (현재는 미구현).

---

## 8. 테마 / 디자인 토큰

라이트 모드 기반 "오로라" 팔레트 — 라벤더 핑크 + 연보라 그라데이션.

`App.css`의 `:root`에 모든 컬러가 CSS 변수로 정의돼 있어, 변수만 교체하면 테마를 통째로 바꿀 수 있습니다.

```css
:root {
  --bg-primary:        #fdfaff;
  --bg-secondary:      #f6ecf7;
  --bg-sidebar:        #efe1f4;
  --bg-hover:          #e7d5ee;
  --bg-input:          #ffffff;
  --bg-message-user:   #f5e6f1;
  --border:            #e5d4ee;
  --text-primary:      #2e1a47;
  --text-secondary:    #6b537a;
  --text-muted:        #9a86b0;
  --accent:            #b06ab3;
  --accent-hover:      #9b4ea8;
  --aurora-gradient:        linear-gradient(135deg, #f472b6 0%, #c084fc 50%, #a78bfa 100%);
  --aurora-gradient-hover:  linear-gradient(135deg, #ec4899 0%, #a855f7 50%, #8b5cf6 100%);
}
```

추가로 다음 요소들이 그라데이션을 사용합니다.

- 로고 텍스트 (`background-clip: text`)
- 헤더 배경 (가로 그라데이션 + blur)
- Send / Primary 버튼
- 도구 카드 이름 텍스트
- 토글 스위치 ON 상태
- 페이지 배경 라디언트 그라데이션 (좌상단 핑크, 우하단 연보라)

다크 모드는 현재 제공하지 않습니다.

---

## 9. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| 사이드바에 "등록된 도구가 없습니다." | 백엔드 MCP `tools/list`가 비어 있음. 백엔드 콘솔에서 `/mcp/` POST 로그를 확인. 사내 보안 게이트웨이가 POST 페이로드를 차단했다면 응답이 HTML 차단 페이지로 떨어집니다. |
| 헤더 뱃지가 빨간색 (`error`) | `initialize` 실패. DevTools Network 탭에서 `/mcp/` 응답을 확인 (HTML 차단 페이지가 가장 흔한 원인). |
| 채팅 결과 메시지가 `MCP HTTP 4xx: <!DOCTYPE html>...` | 백엔드가 응답한 것이 아니라 중간 게이트웨이가 가로채 HTML을 응답한 경우입니다. 같은 머신에서 SSH 터널 / localhost로 우회하거나 HTTPS로 전환하세요. |
| 빌드 후에도 옛 화면이 보임 | 브라우저 캐시. `Ctrl/Cmd + Shift + R`로 강제 새로고침. Vite는 빌드 시 파일명에 hash를 붙이지만 `index.html`만 캐시될 때가 있습니다. |
| Vite dev 서버에서 도구 호출 실패 | `vite.config.js`의 proxy 대상 포트가 실제 백엔드 포트와 다릅니다. 운영 중인 백엔드 포트로 맞춰주세요. |
| 모달의 `restart` 후 영영 reconnect 안 됨 | 백엔드 재기동에 실패한 경우. 백엔드 콘솔 로그를 확인. `/health/live`가 다시 200을 반환할 때까지 1.5초 간격으로 폴링하다 성공하면 자동 reconnect 합니다. |
