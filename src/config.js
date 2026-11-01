export const CONFIG = {
  BG: "#efede9",
  CELL_SIZE: 12,          // px, 자동 계산 시 덮어씀
  ROWS_TARGET: 70,        // 지도 세로 방향 셀 개수 목표 (CELL_SIZE 자동 계산용)
  CELL_FILL: 0.82,        // 셀 크기 대비 실제 사각형 비율(틈)
  CELL_RADIUS: 1.5,       // 셀 모서리 둥글기(px), 0이면 각진 사각형
  SAMPLES_PER_CELL: 3,    // 3 → 3x3 샘플링(작은 섬 보존)
  LENS_RADIUS_CELLS: 9,   // 렌즈 반경 = 셀 크기 x 이 값 (런타임에 LENS_RADIUS(px)로 계산)

  LENS_FALLOFF: "soft",   // "soft"(반경 밖까지 부드럽게 퍼짐) | "hard"(반경 안만)

  // soft 전용
  SOFT_SPREAD: 2,         // 효과가 0이 되는 거리 = 반경 x 이 값 (1.5~2.5 실험)
  SOFT_AMOUNT: 1.0,       // 중심 배율 = 1 + 이 값. 최대 1.2 (넘으면 셀이 꼬임)

  // hard 전용
  DISTORTION: 3,          // 왜곡 강도 (2~5 사이 실험)
  MAX_Z: 3,               // 셀 최대 확대 배율 상한

  FOLLOW: 0.18,           // 렌즈가 커서 따라가는 속도 (0~1)
  FADE: 0.12,             // 렌즈 등장/퇴장 속도 (0~1)
  MODE: "center",         // "center" | "corners"
  HOVER_COLOR: "#e5d400",
  PALETTE: ["#6f8fd0", "#9aa3b2", "#c9cfd9", "#b3a493", "#8796b0"],

  LABELS: [
    { text: "서울", lon: 126.978, lat: 37.566 },
  ],
};
