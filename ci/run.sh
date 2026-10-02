#!/usr/bin/env bash
# GitHub Actions 작업 실행기. ci/task.env 의 TASK 값에 따라 동작한다.
set -uo pipefail
source ci/task.env
echo "TASK=${TASK}"

case "${TASK}" in
  recon)
    mkdir -p samples
    curl -sS -o /dev/null -w "접속 확인: HTTP %{http_code}, %{time_total}s\n" --max-time 30 \
      "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008" || echo "접속 실패"
    python ci/recon.py 2>&1 | tee samples/recon_report.txt
    ;;
  *)
    echo "알 수 없는 TASK: ${TASK}"; exit 1 ;;
esac
