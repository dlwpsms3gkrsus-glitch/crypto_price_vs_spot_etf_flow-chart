"""매일 업데이트 후 ETF 데이터가 정상인지 확인합니다.
문제가 있으면 실패 코드로 끝나 GitHub Actions 실행이 '실패'로 표시되고 이메일 알림이 갑니다.
(이전에는 수집이 실패해도 '성공'으로 표시되어 BTC 데이터가 몇 달간 비어 있었음)
"""
import sys
from datetime import date, timedelta

import pandas as pd

MAX_AGE_DAYS = 6  # 주말·미국 공휴일 고려
problems = []
for path in ["bitcoin_etf_total_flow.csv", "ethereum_etf_total_flow.csv"]:
    try:
        df = pd.read_csv(path)
    except Exception as e:
        problems.append(f"{path}: 읽기 실패 ({e})")
        continue
    if len(df) < 100:
        problems.append(f"{path}: 데이터가 {len(df)}행뿐입니다")
        continue
    last = pd.to_datetime(df["Date"]).max().date()
    age = (date.today() - last).days
    status = "OK" if age <= MAX_AGE_DAYS else "오래됨"
    print(f"{path}: {len(df)}행, 최근 날짜 {last} ({age}일 전) {status}")
    if age > MAX_AGE_DAYS:
        problems.append(f"{path}: 최근 데이터가 {last}로 {age}일 전입니다 (Farside 수집 실패 의심)")

if problems:
    print("\n❌ ETF 데이터 점검 실패:\n- " + "\n- ".join(problems))
    sys.exit(1)
print("✅ ETF 데이터 점검 통과")
