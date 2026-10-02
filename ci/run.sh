#!/usr/bin/env bash
# GitHub Actions 작업 실행기. ci/task.env 의 TASK 값에 따라 동작한다.
#   recon    실제 사이트 구조 확인 (samples/ 에 원본과 파싱 결과)
#   collect  출범일 이후 전체 수집 → dataset/ 내보내기. 시간 제한에 걸리면 다음 실행에서 이어서 한다
#            (data/ 는 Actions 캐시로 실행 사이에 보존)
set -uo pipefail
source ci/task.env
echo "TASK=${TASK}"
M="moisdb --data-dir data"
INTERVAL="${INTERVAL:-1.5}"
LIST_URL="https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008"

case "${TASK}" in
  recon)
    mkdir -p samples
    echo "러너 공인 IP: $(curl -s --max-time 10 https://api.ipify.org || echo 알수없음)"
    curl -sS -o /dev/null -w "접속 확인: HTTP %{http_code}, %{time_total}s\n" --max-time 30 "$LIST_URL" || echo "접속 실패"
    python ci/recon.py 2>&1 | tee samples/recon_report.txt
    ;;

  collect)
    echo "러너 공인 IP: $(curl -s --max-time 10 https://api.ipify.org || echo 알수없음)"
    # 사이트가 응답하지 않으면 빈 결과를 내보내지 않고 바로 실패 처리한다
    up=""
    for i in 1 2 3 4 5 6; do
      code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 30 "$LIST_URL" 2>/dev/null)
      if [ "$code" = "200" ]; then up=1; break; fi
      echo "접속 확인 실패 ($i/6, HTTP=${code:-없음}) — 60초 후 재시도"; sleep 60
    done
    if [ -z "$up" ]; then echo "행안부 누리집에 접속할 수 없어 중단"; exit 1; fi
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

  *)
    echo "알 수 없는 TASK: ${TASK}"; exit 1 ;;
esac
