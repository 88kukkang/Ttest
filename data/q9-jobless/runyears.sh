for y in 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026; do
  e=12; [ $y = 2026 ] && e=09
  for try in 1 2 3; do timeout 300 node fetch2.js 050030030 ${y}01 yr_$y.json ${y}$e > log_$y.txt 2>&1; [ -s yr_${y}_2.json ] && break; done
  echo "$y $(ls -la yr_${y}_2.json 2>/dev/null | awk '{print $5}')"
done
