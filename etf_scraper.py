"""Farside Investors 현물 ETF 일별 순유입 데이터 수집 (BTC/ETH 공용).

2026-06 Farside 페이지 구조 변경으로 BTC 스크립트가 고정 인덱스(all_tables[1])로
푸터 표를 읽어 빈 CSV를 저장하던 문제를 고치기 위해 만든 공용 모듈입니다.

- 'Date'와 'Total' 열이 있는 표를 내용으로 찾습니다 (표 순서가 바뀌어도 동작).
- (1,113.7) 같은 천 단위 쉼표·괄호 음수를 올바르게 숫자로 바꿉니다.
- 아직 집계 중인 오늘 행('-' 칸이 남은 마지막 행)은 제외합니다.
- 수집 결과가 이상하면 예외를 던지고, save_flow_csv()는 기존 CSV를 덮어쓰지 않습니다.
"""
import os
import re
import time
from io import StringIO

import pandas as pd

FARSIDE_URLS = {
    "BTC": "https://farside.co.uk/bitcoin-etf-flow-all-data/",
    "ETH": "https://farside.co.uk/ethereum-etf-flow-all-data/",
}
MIN_ROWS = 100  # 정상 데이터라면 수백 행 이상이어야 함


def fetch_html(url, wait_seconds=5):
    """헤드리스 크롬으로 페이지 HTML을 가져옵니다 (Farside는 단순 요청을 차단)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(url)
        time.sleep(wait_seconds)
        return driver.page_source
    finally:
        driver.quit()


def _to_number(value):
    """'(1,113.7)' -> -1113.7, '655.3' -> 655.3, '-' / '' -> NaN"""
    s = str(value).strip().replace(",", "")
    if s in ("", "-", "nan", "None"):
        return float("nan")
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        number = float(s)
    except ValueError:
        return float("nan")
    return -number if negative else number


def _flat_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[-1]) for c in df.columns]
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_flow_table(html):
    """페이지 HTML에서 일별 Total 순유입(US$m) 표를 찾아 [Date, Total] DataFrame으로 반환."""
    tables = pd.read_html(StringIO(html), flavor="html5lib")
    candidates = []
    for table in tables:
        table = _flat_columns(table.copy())
        if "total" in [c.lower() for c in table.columns] and len(table.columns) >= 3:
            candidates.append(table)
    if not candidates:
        raise ValueError(f"Total 열이 있는 표를 찾지 못했습니다 (표 {len(tables)}개 검사).")
    table = max(candidates, key=len)  # 가장 긴 표 = 전체 일별 데이터

    cols_lower = [c.lower() for c in table.columns]
    # BTC 표는 첫 열 제목이 'Date', ETH 표는 비어 있음 → 'date'가 없으면 첫 열을 날짜로 사용
    date_col = table.columns[cols_lower.index("date")] if "date" in cols_lower else table.columns[0]
    total_col = table.columns[cols_lower.index("total")]
    fund_cols = [c for c in table.columns if c not in (date_col, total_col)]

    table["Date"] = pd.to_datetime(table[date_col].astype(str).str.strip(), format="%d %b %Y", errors="coerce")
    table = table.dropna(subset=["Date"]).reset_index(drop=True)  # 빈 행, 'Total'/'Average' 요약 행 제거

    # 마지막 행이 아직 집계 중(일부 펀드 칸이 '-')이면 제외 — 전날엔 숫자가 있던 칸이 '-'인 경우
    if len(table) >= 2:
        last, prev = table.iloc[-1], table.iloc[-2]
        pending = [c for c in fund_cols
                   if str(last[c]).strip() == "-" and str(prev[c]).strip() not in ("-", "", "nan")]
        if pending:
            print(f"ℹ️ {last['Date'].date()} 데이터는 아직 집계 중이라 제외합니다 (미집계: {', '.join(pending)})")
            table = table.iloc[:-1]

    out = pd.DataFrame({"Date": table["Date"], "Total": table[total_col].map(_to_number)})
    missing = out["Total"].isna().sum()
    if missing:
        print(f"⚠️ Total 값이 비어 있는 날 {missing}일은 0으로 처리합니다.")
        out["Total"] = out["Total"].fillna(0.0)
    out = out.drop_duplicates("Date", keep="last").sort_values("Date").reset_index(drop=True)

    if len(out) < MIN_ROWS:
        raise ValueError(f"수집된 행이 {len(out)}개뿐이라 비정상으로 판단합니다.")
    return out


def scrape_etf_flow(coin):
    """coin='BTC' 또는 'ETH'. 실패 시 None 반환."""
    url = FARSIDE_URLS[coin]
    print(f"▶ Farside에서 {coin} ETF 유입량 데이터를 수집합니다: {url}")
    try:
        df = parse_flow_table(fetch_html(url))
        print(f"✔️ {coin} ETF 데이터 {len(df)}일치 수집 완료 (최근: {df['Date'].iloc[-1].date()}, "
              f"{df['Total'].iloc[-1]:+.1f}M)")
        return df
    except Exception as e:
        print(f"❌ {coin} ETF 데이터 수집 실패: {e}")
        return None


def save_flow_csv(df, csv_path):
    """정상 데이터만 저장. 기존 파일보다 크게 짧아지면 덮어쓰지 않습니다."""
    if df is None or len(df) < MIN_ROWS:
        print(f"⚠️ 새 데이터가 없거나 너무 짧아 '{csv_path}'를 그대로 둡니다.")
        return False
    if os.path.exists(csv_path):
        try:
            old_rows = len(pd.read_csv(csv_path))
        except Exception:
            old_rows = 0
        if len(df) < old_rows * 0.9:
            print(f"⚠️ 새 데이터({len(df)}행)가 기존({old_rows}행)보다 많이 짧아 덮어쓰지 않습니다.")
            return False
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    out.to_csv(csv_path, index=False)
    print(f"💾 '{csv_path}' 저장 완료 ({len(out)}행)")
    return True


def load_flow_csv(csv_path):
    """기존 CSV를 불러옵니다 (수집 실패 시 차트를 그릴 때 사용)."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    if len(df) < MIN_ROWS:
        return None
    df["Date"] = pd.to_datetime(df["Date"])
    return df
