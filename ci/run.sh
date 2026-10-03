#!/usr/bin/env bash
# GitHub Actions 작업 실행기. ci/task.env 의 TASK 값에 따라 동작한다.
#   probe    러너에서 각 사이트 접속 가능 여부 점검
#   recon    실제 사이트 구조 확인 (samples/ 에 원본과 파싱 결과)
#   update   매일 갱신: 새 글만 받아 웹 데이터까지 만들어 릴리스 data-latest 에 올림
#   backfill 수집 시작일(moisdb/config.py START_DATE)을 앞당긴 뒤 한 번: 시작일까지 목록을 다시 훑어 옛 글을 받고
#            릴리스까지 갱신. 시간 제한에 걸려 남은 글은 다음 update(또는 backfill 재실행)가 이어 받는다
#   collect  출범일 이후 전체 수집 → dataset/ 내보내기. 시간 제한에 걸리면 다음 실행에서 이어서 한다
#            (data/ 는 Actions 캐시로 실행 사이에 보존)
set -uo pipefail
source ci/task.env
echo "TASK=${TASK}"
M="moisdb --data-dir data"
INTERVAL="${INTERVAL:-1.5}"
LIST_URL="https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008"

# 행안부 방화벽이 일부 클라우드 IP 대역만 막는 것으로 보여, 막힌 러너면 빨리 실패하고 재실행(새 러너)한다
preflight() {
  echo "러너 공인 IP: $(curl -s --max-time 10 https://api.ipify.org || echo 알수없음)"
  for i in 1 2 3; do
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "$LIST_URL" 2>/dev/null)
    if [ "$code" = "200" ]; then return 0; fi
    echo "접속 확인 실패 ($i/3, HTTP=${code:-없음}) — 20초 후 재시도"; sleep 20
  done
  echo "PREFLIGHT_BLOCKED: 이 러너 IP 에서는 행안부 누리집에 접속할 수 없어 중단 — 재실행하면 다른 러너로 시도"
  exit 1
}

# 캐시에 DB 가 없으면 마지막 릴리스(없으면 저장소의 스냅숏)에서 가져와 이어서 한다
seed_db() {
  mkdir -p data reports build
  if [ ! -f data/mois.sqlite3 ]; then
    if gh release download data-latest -p moisdb-latest.tar.gz -D build --clobber 2>/dev/null; then
      tar xzf build/moisdb-latest.tar.gz -C build dataset/mois_press.sqlite3.xz
      xz -dc build/dataset/mois_press.sqlite3.xz > data/mois.sqlite3
    else
      xz -dc dataset/mois_press.sqlite3.xz > data/mois.sqlite3
    fi
    touch data/.discover_done
  fi
}
count_docs() { python -c "import sqlite3; print(sqlite3.connect('data/mois.sqlite3').execute(\"SELECT count(*) FROM releases WHERE source='mois' AND status='fetched'\").fetchone()[0])"; }

# 분석 단계 → 내보내기 → 웹 데이터 → 릴리스 data-latest 에 덮어쓰기. 인자: 시작 전 수집 건수
publish_release() {
  local before="$1"
  $M extract --retry-errors
  timeout "${DL_MINUTES:-15}m" $M download --interval "$INTERVAL" || true   # 추출 실패분의 다른 형식(PDF 등)
  $M extract
  $M build-text
  $M tokenize
  $M stats | tee reports/stats.txt
  python ci/export_dataset.py
  python ci/build_web_data.py web
  python ci/build_hub.py
  python - <<'PY'
import json, sqlite3
c = sqlite3.connect("data/mois.sqlite3")
n, first, last = c.execute("SELECT count(*), min(published_date), max(published_date) FROM releases WHERE source='mois' AND status='fetched'").fetchone()
left = c.execute("SELECT count(*) FROM releases WHERE source='mois' AND status!='fetched'").fetchone()[0]
json.dump({"n_docs": n, "first_date": first, "last_date": last, "not_fetched": left}, open("build/latest.json", "w"))
print("latest:", n, first, "~", last, "미수집", left)
PY
  echo "새로 들어온 보도자료: $(( $(count_docs) - before ))건"
  tar czf build/moisdb-latest.tar.gz dataset web/index.html web/docs.b64.txt web/cloud.b64.txt reports/stats.txt -C build latest.json
  gh release view data-latest >/dev/null 2>&1 || gh release create data-latest --title "최신 수집 데이터" --notes "매일 자동으로 덮어쓰는 최신 데이터: DB(dataset/), 웹 페이지와 데이터(web/), 수집 현황(reports/stats.txt)."
  gh release upload data-latest build/moisdb-latest.tar.gz build/latest.json --clobber
}

case "${TASK}" in
  recon)
    mkdir -p samples
    echo "러너 공인 IP: $(curl -s --max-time 10 https://api.ipify.org || echo 알수없음)"
    curl -sS -o /dev/null -w "접속 확인: HTTP %{http_code}, %{time_total}s\n" --max-time 30 "$LIST_URL" || echo "접속 실패"
    python ci/recon.py 2>&1 | tee samples/recon_report.txt
    ;;

  probe)
    # 접속 경로 점검: 어느 사이트가 이 러너에서 열리는지
    echo "러너 공인 IP: $(curl -s --max-time 10 https://api.ipify.org || echo 알수없음)"
    getent hosts www.mois.go.kr www.korea.kr apis.data.go.kr || true
    for u in "$LIST_URL" "http://www.mois.go.kr/" "https://www.korea.kr/briefing/pressReleaseList.do" \
             "https://apis.data.go.kr/1371000/pressReleaseService/pressReleaseList" "https://www.google.com/"; do
      curl -sS -o /dev/null -w "HTTP %{http_code}  connect=%{time_connect}s total=%{time_total}s  $u\n" --max-time 25 "$u" \
        || echo "실패  $u"
    done
    ;;

  collect)
    preflight
    mkdir -p data reports
    # 목록 전체 훑기는 한 번만. 끝까지 성공해야 표시 파일을 남기고, 이후에는 새 글만 확인한다
    if [ -f data/.discover_done ]; then
      $M discover --until-known --interval "$INTERVAL"
    else
      $M discover --interval "$INTERVAL" && touch data/.discover_done
    fi
    timeout "${FETCH_MINUTES:-270}m" $M fetch --retry-errors --interval "$INTERVAL" \
      || echo "fetch 중단(시간 제한 등) — 다음 실행에서 이어서 진행"
    timeout 20m $M download --retry-errors --interval "$INTERVAL" || true
    $M extract --retry-errors
    timeout 20m $M download --interval "$INTERVAL" || true   # 추출 실패분의 다른 형식(PDF 등)
    $M extract
    $M build-text
    $M tokenize
    fetched=$(python -c "import sqlite3; print(sqlite3.connect('data/mois.sqlite3').execute(\"SELECT count(*) FROM releases WHERE status = 'fetched'\").fetchone()[0])")
    if [ "$fetched" -gt 0 ]; then
      $M stats | tee reports/stats.txt
      python ci/export_dataset.py | tee -a reports/stats.txt
    else
      echo "수집된 글이 없어 내보내기를 건너뜀"; exit 1
    fi
    ;;

  update)
    # 매일 갱신: 새 글만 받아 웹 데이터까지 만들고 GitHub 릴리스(data-latest)에 올린다.
    preflight
    seed_db
    before=$(count_docs)
    $M discover --until-known --interval "$INTERVAL"
    timeout 60m $M fetch --retry-errors --interval "$INTERVAL" || echo "fetch 중단 — 다음 실행에서 이어서"
    timeout 15m $M download --retry-errors --interval "$INTERVAL" || true
    publish_release "$before"
    ;;

  backfill)
    # 시작일까지 목록을 다시 훑어 옛 글을 받는다 (약 1,900건이면 상세·첨부에 2~3시간)
    preflight
    seed_db
    before=$(count_docs)
    $M discover --interval "$INTERVAL"
    timeout "${FETCH_MINUTES:-230}m" $M fetch --retry-errors --interval "$INTERVAL" \
      || echo "fetch 중단(시간 제한) — 남은 글은 다음 update 나 backfill 재실행이 이어 받음"
    timeout 30m $M download --retry-errors --interval "$INTERVAL" || true
    DL_MINUTES=20 publish_release "$before"
    ;;

  *)
    echo "알 수 없는 TASK: ${TASK}"; exit 1 ;;
esac
