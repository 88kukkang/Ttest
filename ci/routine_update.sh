#!/usr/bin/env bash
# 예약 실행(Claude 루틴)용 일일 갱신 스크립트.
#
#   bash ci/routine_update.sh                  # 수집 실행 → 결과 내려받기 → RESULT=updated|nochange|failed 출력
#   bash ci/routine_update.sh --mark-published # 페이지를 다시 올린 뒤, 올린 상태를 web/published.json 에 기록·push
#
# 수집은 GitHub Actions(moisdb-run, TASK=update)가 하고, 결과는 릴리스 data-latest 에 올라온다.
# 이 스크립트는 그 실행을 일으키고(ci/task.env 의 RUN 값 올려 push), 끝날 때까지 기다린 뒤 결과를 build/latest 에 푼다.
set -uo pipefail
REPO=88kukkang/Ttest
BRANCH=claude/moi-press-release-database-ncgqwa
ASSET=https://github.com/$REPO/releases/download/data-latest/moisdb-latest.tar.gz
OUT=build/latest
cd "$(git rev-parse --show-toplevel)"

sync() {
  git fetch -q origin "$BRANCH"
  git checkout -q "$BRANCH" 2>/dev/null || git checkout -q -b "$BRANCH" "origin/$BRANCH"
  git pull -q --ff-only origin "$BRANCH"
}
field() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2], ''))" "$1" "$2" 2>/dev/null; }

if [ "${1:-}" = "--mark-published" ]; then
  sync
  cp "$OUT/latest.json" web/published.json
  git add web/published.json
  git commit -q -m "web: 페이지 갱신 기록 ($(field web/published.json last_date), $(field web/published.json n_docs)건)" && git push -q origin "$BRANCH"
  echo "기록 완료: $(cat web/published.json)"
  exit 0
fi

sync
status=""
for attempt in 1 2 3; do
  run_no=$(( $(grep '^RUN=' ci/task.env | cut -d= -f2) + 1 ))
  sed -i "s/^TASK=.*/TASK=update/; s/^RUN=.*/RUN=$run_no/" ci/task.env
  git add ci/task.env
  git commit -q -m "ci: 일일 갱신 실행 $(date -u +%F) #$run_no"
  for i in 1 2 3 4; do git push -q origin "$BRANCH" && break; sleep $((2 ** i)); git pull -q --rebase origin "$BRANCH"; done
  sha=$(git rev-parse HEAD)
  run_id=""
  for i in $(seq 1 40); do
    run_id=$(curl -s "https://api.github.com/repos/$REPO/actions/runs?head_sha=$sha" | python3 -c "import json,sys; r=json.load(sys.stdin).get('workflow_runs', []); print(r[0]['id'] if r else '')" 2>/dev/null)
    [ -n "$run_id" ] && break
    sleep 15
  done
  [ -z "$run_id" ] && { echo "실행을 찾지 못함 (시도 $attempt)"; continue; }
  echo "Actions 실행 $run_id (시도 $attempt): https://github.com/$REPO/actions/runs/$run_id"
  for i in $(seq 1 200); do
    status=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$run_id" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status'), d.get('conclusion'))" 2>/dev/null)
    case "$status" in completed*) break ;; esac
    sleep 30
  done
  echo "결과: $status"
  [ "$status" = "completed success" ] && break
  echo "실패 — 행안부가 이 러너 IP 를 막았을 수 있어 새 러너로 다시 시도"
done
if [ "$status" != "completed success" ]; then echo "RESULT=failed"; exit 1; fi

rm -rf "$OUT" && mkdir -p "$OUT"
curl -sSL --retry 3 -o "$OUT/moisdb-latest.tar.gz" "$ASSET" && tar xzf "$OUT/moisdb-latest.tar.gz" -C "$OUT" || { echo "RESULT=failed (릴리스 내려받기 실패)"; exit 1; }
n_new=$(field "$OUT/latest.json" n_docs); last=$(field "$OUT/latest.json" last_date)
n_old=$(field web/published.json n_docs); n_old=${n_old:-0}
cat "$OUT/reports/stats.txt" | head -12
if [ "$n_new" = "$n_old" ]; then echo "RESULT=nochange n_docs=$n_new last_date=$last"; else echo "RESULT=updated n_docs=$n_new last_date=$last new=$((n_new - n_old))"; fi
