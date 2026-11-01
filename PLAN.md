# 한반도 격자 지도 + 피시아이(볼록 렌즈) 확대 효과 — 구현 계획서

> 이 문서는 **다른 AI 모델(또는 개발자)에게 그대로 넘겨서 구현을 맡기기 위한 명세**입니다.
> 맨 아래 "AI에게 줄 프롬프트" 섹션을 복사해서 이 문서와 함께 주면 됩니다.

---

## 0. 목표 (이번 단계의 범위)

1. 대한민국 지도를 **정사각형 셀(박스) 격자**로 표현한다. (도트/픽셀 지도 스타일)
2. 마우스를 지도 위에 올리면 **커서 주변 셀들이 볼록 렌즈(fisheye)처럼 부풀어 오른다.**
   - 단순 확대(zoom)가 아니라, 커서 가까운 셀일수록 크게 + 바깥으로 밀려나고,
     렌즈 반경 밖의 셀은 원래 자리 그대로 있는 **비선형 왜곡**.
   - 커서를 움직이면 렌즈가 **부드럽게 따라온다** (보간/애니메이션).
   - 지도 밖으로 나가면 렌즈가 **서서히 사라지며 원래 모양으로 복귀**한다.
3. **나중에 기능(데이터 색칠, 클릭, 툴팁 등)을 붙이기 쉬운 구조**로 만든다.

### 이번 단계에서 하지 않는 것 (Non-goals)
- 실제 데이터(선거/인구 등) 연결 — 색은 임시(지역별 구분색 또는 랜덤 팔레트)
- 클릭 이벤트 동작, 상세 패널, 라우팅
- 프레임워크(React 등), 번들러, 서버

---

## 1. 기술 스택 (결정사항)

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어 | 순수 HTML + CSS + JavaScript (ES Module) | 빌드 없이 브라우저에서 바로 실행 |
| 렌더링 | **HTML `<canvas>` 2D** | 셀 수천 개를 매 프레임 다시 그려야 하므로 SVG/DOM보다 빠름 |
| 지도 → 격자 변환 | **d3-geo** (CDN, 런타임) | GeoJSON 투영 + `geoContains`로 셀 중심이 육지인지 판정 |
| 지도 데이터 | 대한민국 시·도 경계 GeoJSON | 아래 2절 참고 |
| 로컬 실행 | `npx serve .` 또는 VS Code "Live Server" | `fetch()`로 JSON을 읽으려면 로컬 서버 필요 |

CDN 예시 (버전 고정):
```html
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
```

---

## 2. 지도 데이터

- 출처(권장): GitHub `southkorea/southkorea-maps` 저장소의 시·도 경계 GeoJSON
  - 예: `kostat/2013/json/skorea_provinces_geo_simple.json` (단순화 버전이라 가벼움)
  - 받아서 `data/korea-provinces.geo.json` 으로 저장 (외부 URL에 런타임 의존하지 않기).
- 각 feature의 `properties`에서 **시·도 이름/코드**를 읽어 셀의 `region`으로 저장한다.
  (필드명은 파일을 열어 확인할 것 — 예: `name`, `code` 등)
- **대체안(데이터 못 구할 때):** `data/mask.js`에 ASCII 마스크를 직접 작성
  ```js
  // '#' = 육지 셀, '.' = 빈칸. 한 줄 = 한 행
  export const MASK = [
    "......##....",
    ".....####...",
    // ...
  ];
  ```
  → 이 경우 `region`은 없음(전부 동일 색). 1순위는 GeoJSON 방식.

---

## 3. 파일 구조

```
/
├─ index.html              # 캔버스 1개 + 스크립트 로드
├─ style.css               # 배경색, 캔버스 중앙 정렬, 반응형
├─ data/
│   └─ korea-provinces.geo.json
└─ src/
    ├─ main.js             # 진입점: 데이터 로드 → 격자 생성 → 렌더 루프 시작
    ├─ config.js           # 모든 조절 가능한 숫자(셀 크기, 렌즈 반경, 왜곡 강도, 색상)
    ├─ grid.js             # GeoJSON → 셀 배열 생성 (buildGrid)
    ├─ fisheye.js          # 순수 함수: 점 + 초점 → 왜곡된 위치/배율
    ├─ renderer.js         # 캔버스에 셀 그리기 (draw)
    └─ interaction.js      # 포인터 이벤트, 렌즈 상태(위치/강도) 보간
```

원칙: **`fisheye.js`는 DOM/캔버스를 전혀 모르는 순수 수학 함수**로 둔다. (테스트·재사용 쉬움)

---

## 4. 데이터 모델

```js
// 셀 하나
{
  id: "12_34",        // `${col}_${row}`
  col: 12, row: 34,   // 격자 좌표
  x: 240, y: 680,     // 원래(왜곡 전) 셀 중심의 화면 좌표(px, CSS 픽셀)
  region: "서울특별시", // 소속 시·도 (없으면 null)
  value: null,        // ← 나중에 데이터 붙일 자리
  color: "#7d95c9"    // 현재 표시 색 (지금은 region 기반 임시색)
}

// 렌즈 상태 (interaction.js가 관리)
{
  targetX, targetY,   // 실제 마우스 위치
  x, y,               // 화면에 쓰는 렌즈 중심 (target을 향해 보간)
  targetStrength,     // 지도 위면 1, 밖이면 0
  strength            // 0~1, 보간됨. 왜곡 강도에 곱해짐
}
```

---

## 5. 단계별 구현 (각 단계마다 완료 조건 확인 후 다음 단계로)

### Phase 1 — 기본 뼈대
- `index.html`: `<canvas id="map">` 하나, `style.css`, `src/main.js`(type="module") 로드.
- 배경색 `#efede9` 정도의 밝은 회색(첨부 이미지 느낌).
- 캔버스는 화면 중앙, 최대 높이 90vh 정도. **devicePixelRatio 대응**:
  ```js
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = cssW * dpr; canvas.height = cssH * dpr;
  canvas.style.width = cssW + "px"; canvas.style.height = cssH + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // 이후 좌표는 전부 CSS px 기준
  ```
- ✅ 완료 조건: 빈 캔버스가 레티나 화면에서도 선명하게 뜬다.

### Phase 2 — 격자 지도 생성 (`grid.js`)
1. GeoJSON 로드 → `d3.geoMercator().fitExtent([[pad,pad],[w-pad,h-pad]], geojson)` 로 투영 설정.
2. 캔버스 영역을 `CELL_SIZE`(기본 12px) 간격의 격자로 순회.
3. 각 칸의 **중심 픽셀** → `projection.invert([px, py])` 로 경위도 변환
   → 각 feature에 대해 `d3.geoContains(feature, lonlat)` 이면 육지 셀로 채택, `region` 기록.
4. **작은 섬 누락 방지:** 중심점만 검사하면 울릉도·독도 등 작은 섬이 빠질 수 있음.
   → 셀 내부 3×3 샘플점 중 하나라도 포함되면 채택(옵션 `SAMPLES_PER_CELL`).
5. 결과 셀 배열을 반환. 계산이 무거우면 결과를 `localStorage`가 아니라 **메모리에만** 캐시
   (창 크기 바뀔 때 다시 계산).
- 렌더링: 각 셀을 `CELL_SIZE * CELL_FILL`(기본 0.82, 즉 셀 사이 틈) 크기의 사각형으로 그림.
- 임시 색: 시·도별로 팔레트에서 하나씩 배정 (파랑 `#6f8fd0`, 회색 `#9aa3b2`, 연회색 `#c9cfd9`, 갈색 `#b3a493` 등 이미지 톤).
- ✅ 완료 조건: 첨부 이미지처럼 남한 + 제주도 모양의 박스 지도가 보인다.

### Phase 3 — 피시아이 수학 (`fisheye.js`)
d3 공식 fisheye 플러그인(“circular fisheye”, Sarkar & Brown 계열)과 같은 공식을 쓴다.

```js
// radius: 렌즈 반경(px), distortion: 왜곡 강도(예: 3)
export function createFisheye(radius, distortion) {
  const e  = Math.exp(distortion);
  const k0 = (e / (e - 1)) * radius;
  const k1 = distortion / radius;

  // 반환: 왜곡된 위치(x, y)와 크기 배율(z)
  return function apply(px, py, fx, fy) {
    const dx = px - fx, dy = py - fy;
    const dd = Math.hypot(dx, dy);
    if (dd === 0)       return { x: px, y: py, z: MAX_Z };     // 초점 정중앙
    if (dd >= radius)   return { x: px, y: py, z: 1 };         // 렌즈 밖: 그대로
    const k = (k0 * (1 - Math.exp(-dd * k1))) / dd * 0.75 + 0.25;
    return { x: fx + dx * k, y: fy + dy * k, z: Math.min(k, MAX_Z) };
  };
}
```

- `k > 1` 이면 바깥으로 밀려나고(=부풀어 보임), 반경 경계에서는 `k → 1`이 되어 **렌즈 밖과 이음매 없이** 이어진다.
- **강도(strength) 0~1 페이드:** 렌즈 등장/퇴장 시엔 결과를 원래 값과 선형 보간한다.
  ```js
  x' = px + (r.x - px) * strength;  y' = py + (r.y - py) * strength;
  z' = 1  + (r.z - 1)  * strength;
  ```
- 셀 그리기 크기 = `CELL_SIZE * CELL_FILL * z'`, 중심 = `(x', y')`.
- ⚠️ 주의: 위치와 크기를 각각 왜곡하므로 렌즈 중심부에서 셀끼리 살짝 겹칠 수 있다.
  겹치는 게 거슬리면 아래 "대안 B"를 쓴다.
  - **대안 B (더 정확):** 셀의 **네 꼭짓점을 각각** 왜곡해서 사각형(사다리꼴) 경로로 그린다.
    `ctx.beginPath(); moveTo(c0); lineTo(c1); lineTo(c2); lineTo(c3); closePath(); fill();`
    → 셀들이 절대 겹치지 않고 진짜 볼록렌즈처럼 휘어 보임. 연산은 4배지만 셀 수천 개면 문제없음.
  - 기본은 대안 A(중심+배율)로 만들고, `config.MODE = "center" | "corners"` 로 전환 가능하게.
- ✅ 완료 조건: 콘솔에서 `apply`에 몇 가지 값을 넣어 반경 밖 = 원래 좌표, 중심 근처 = z > 1 확인.

### Phase 4 — 인터랙션 + 애니메이션 루프 (`interaction.js`, `main.js`)
- **Pointer Events** 사용(마우스/터치/펜 통합): `pointermove`, `pointerleave`, `pointerdown`.
- 좌표는 `canvas.getBoundingClientRect()` 기준 CSS px로 변환.
- `pointermove` → `targetX/Y` 갱신, `targetStrength = 1`.
- `pointerleave` → `targetStrength = 0` (위치는 유지 → 렌즈가 그 자리에서 꺼지듯 사라짐).
- `requestAnimationFrame` 루프에서 매 프레임 보간:
  ```js
  lens.x += (lens.targetX - lens.x) * FOLLOW;          // FOLLOW ≈ 0.18
  lens.y += (lens.targetY - lens.y) * FOLLOW;
  lens.strength += (lens.targetStrength - lens.strength) * FADE; // FADE ≈ 0.12
  ```
- **최적화:** strength ≈ 0 이고 변화가 없으면 다시 그리지 않음(idle 시 CPU 0%).
- 처음 진입 시 렌즈가 (0,0)에서 날아오지 않도록, strength가 0일 때 들어온 첫 이동은 `x = targetX`로 바로 점프.
- **그리기 순서:** 확대된 셀이 위로 오도록 `z` 오름차순으로 정렬해서 그리거나,
  렌즈 반경 안 셀만 따로 모아 마지막에 그린다(더 빠름).
- **호버 셀 하이라이트(선택):** 렌즈 중심에 가장 가까운 셀 1개를 노란색(`#e5d400`, 이미지의 노란 셀)으로 표시.
  → 나중에 툴팁/클릭 기능의 기반이 됨. 현재 호버 셀 id를 `onHover(cell)` 콜백으로 내보낸다.
- ✅ 완료 조건: 마우스를 움직이면 볼록 렌즈가 부드럽게 따라오고, 밖으로 나가면 스르륵 복귀.

### Phase 5 — 반응형 & 마무리
- `ResizeObserver`(또는 `resize` 이벤트 + debounce 150ms)로 크기 변경 시 투영·격자 재계산.
- 셀 크기를 화면 크기에 비례하게: `CELL_SIZE = clamp(round(mapHeight / 70), 6, 16)` 정도.
  (세로로 약 70칸 → 이미지와 비슷한 해상도)
- 렌즈 반경도 셀 크기 기준으로: `LENS_RADIUS = CELL_SIZE * 9`.
- 모바일: 손가락으로 누르고 있는 동안 렌즈 표시, 떼면 사라짐.
  캔버스에 `touch-action: none;` (스크롤 방지) — 단, 페이지 스크롤이 필요하면 재검토.
- 선택: 지도 위에 "서울 ●" 같은 라벨 1~2개 (이미지 참고). 라벨 위치도 fisheye를 통과시켜 함께 움직이게.
- ✅ 완료 조건: 창 크기를 바꿔도 지도 비율 유지, 폰 화면에서도 동작.

---

## 6. `config.js` (조절 가능한 값 모음)

```js
export const CONFIG = {
  BG: "#efede9",
  CELL_SIZE: 12,          // px, 자동 계산 시 덮어씀
  CELL_FILL: 0.82,        // 셀 크기 대비 실제 사각형 비율(틈)
  CELL_RADIUS: 1.5,       // 셀 모서리 둥글기(px), 0이면 각진 사각형
  SAMPLES_PER_CELL: 3,    // 3 → 3x3 샘플링(작은 섬 보존)
  LENS_RADIUS_CELLS: 9,   // 렌즈 반경 = 셀 크기 x 이 값
  DISTORTION: 3,          // 왜곡 강도 (2~5 사이 실험)
  MAX_Z: 3,               // 셀 최대 확대 배율 상한
  FOLLOW: 0.18,           // 렌즈가 커서 따라가는 속도 (0~1)
  FADE: 0.12,             // 렌즈 등장/퇴장 속도 (0~1)
  MODE: "center",         // "center" | "corners"
  HOVER_COLOR: "#e5d400",
  PALETTE: ["#6f8fd0", "#9aa3b2", "#c9cfd9", "#b3a493", "#8796b0"],
};
```

---

## 7. 나중 기능을 위한 확장 포인트 (지금은 자리만)

- `cell.value` + `colorScale(value)` → 데이터 색칠 (선거 결과, 인구 등)
- `onHover(cell)` → 툴팁 DOM 띄우기
- `onClick(cell)` → 상세 패널
- 시·도 → 시·군·구 GeoJSON으로 바꾸면 더 세밀한 지역 구분
- 셀 등장 애니메이션(위에서부터 순차적으로 나타나기 등)

---

## 8. 테스트 체크리스트 (구현 후 직접 확인)

- [ ] 남한 윤곽, 제주도, (가능하면) 울릉도가 보인다
- [ ] 렌즈 반경 밖 셀은 전혀 움직이지 않는다
- [ ] 렌즈 경계에서 셀이 "툭" 끊기지 않고 자연스럽게 이어진다
- [ ] 커서를 빠르게 움직여도 부드럽게 따라온다(끊김 없음, 60fps)
- [ ] 지도 밖으로 나가면 서서히 원상복구된다
- [ ] 다시 들어올 때 렌즈가 엉뚱한 곳에서 날아오지 않는다
- [ ] 창 크기 변경 / 레티나 / 모바일 터치에서 정상
- [ ] 아무것도 안 할 때 CPU 사용량이 거의 0 (불필요한 재렌더 없음)
- [ ] 콘솔 에러 없음

---

## 9. AI에게 줄 프롬프트 (복사해서 사용)

```
첨부한 PLAN.md 를 그대로 따라서 구현해줘.

규칙:
- 순수 HTML/CSS/JS(ES Module)만 사용, 빌드 도구·프레임워크 쓰지 마.
- 외부 라이브러리는 d3@7.9.0 (CDN) 하나만.
- PLAN.md의 파일 구조와 config 값 이름을 지켜줘.
- Phase 1 → 5 순서로 진행하고, 각 Phase 완료 조건을 만족하는지 확인한 뒤 다음으로 넘어가.
- 지도 GeoJSON은 southkorea/southkorea-maps 의 시·도 단순화 파일을 data/ 에 저장해서 써.
  못 구하면 PLAN.md 2절의 ASCII 마스크 대체안을 써.
- fisheye.js 는 DOM에 의존하지 않는 순수 함수로 작성해.
- 마지막에 로컬에서 실행하는 방법(npx serve 등)을 알려줘.
```

> 팁: 사용량을 아끼려면 한 번에 다 시키지 말고
> "Phase 1~2만 먼저 해줘" → 확인 → "Phase 3~4 해줘" → 확인 → "Phase 5" 처럼 나눠서 요청하세요.
> 문제 생기면 해당 Phase 번호와 증상만 짧게 전달하면 됩니다.
