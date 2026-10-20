from chart_theme import style_chart, save_chart
import pandas as pd
import requests
import yfinance as yf
from plotly.subplots import make_subplots # 이중 축 그래프를 위해 import
import plotly.graph_objects as go
import sys

# --- ⚙️ 설정: 데이터 시작 날짜 ---
START_DATE = '2014-09-17'
# --------------------------------

def get_supply_data(start_date):
    """CoinMetrics에서 비트코인 총공급량 데이터를 가져옵니다."""
    print(f"▶ 1단계: CoinMetrics에서 {start_date}부터 총공급량 데이터를 가져옵니다...")
    try:
        url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        params = {"assets": "btc", "metrics": "SplyCur", "start_time": f"{start_date}T00:00:00Z", "frequency": "1d", "page_size": 10000}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()['data']
        if not data: raise ValueError("데이터를 가져오지 못했습니다.")
        
        df = pd.DataFrame(data)
        df.rename(columns={'time': 'Date', 'SplyCur': 'Supply'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        df['Supply'] = pd.to_numeric(df['Supply'])
        
        print("✔️ 총공급량 데이터 다운로드 완료.")
        return df
    except Exception as e:
        print(f"❌ 총공급량 데이터 다운로드 중 오류 발생: {e}")
        return None

def get_price_data(ticker, start_date):
    """Yahoo Finance에서 특정 티커의 가격 데이터를 가져옵니다."""
    print(f"▶ 2단계: Yahoo Finance에서 '{ticker}' 가격 데이터를 다운로드합니다...")
    try:
        df = yf.download(ticker, start=start_date, end=pd.Timestamp.today(), progress=False)
        if df.empty:
            print("❌ 가격 데이터를 다운로드하지 못했습니다.")
            return None
        
        # <<-- 수정된 부분: MultiIndex 헤더를 단일 헤더로 변환하는 코드 추가 -->>
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.reset_index(inplace=True)
        df = df[['Date', 'Close']]
        df.rename(columns={'Close': 'Price'}, inplace=True)

        print("✔️ 가격 데이터 다운로드 완료.")
        return df
    except Exception as e:
        print(f"❌ 가격 데이터 다운로드 중 오류 발생: {e}")
        return None

# --- 메인 코드 실행 ---
if __name__ == "__main__":
    supply_df = get_supply_data(START_DATE)
    price_df = get_price_data('BTC-USD', START_DATE)

    if supply_df is not None:
        supply_df.to_csv("btc_supply_data.csv", index=False)
        print("✅ 공급량 데이터가 'btc_supply_data.csv' 파일로 저장되었습니다.")
    if price_df is not None:
        price_df.to_csv("btc_price_data.csv", index=False)
        print("✅ 가격 데이터가 'btc_price_data.csv' 파일로 저장되었습니다.")

    if supply_df is None or price_df is None:
        print("\n데이터 다운로드에 실패하여 프로그램을 종료합니다.")
        sys.exit()

    print("\n▶ 3단계: 두 데이터 결합 및 가공...")
    supply_df.set_index('Date', inplace=True)
    price_df.set_index('Date', inplace=True)
    combined_df = supply_df.join(price_df, how='inner')
    combined_df.dropna(inplace=True)

    if combined_df.empty:
        print("⚠️ 공급량 데이터와 가격 데이터의 날짜가 일치하는 구간이 없습니다.")
        sys.exit()
    print("✔️ 데이터 결합 완료.")

    # 4. 이중 축 그래프 생성 (정규화 과정 제거)
    print("▶ 4단계: 이중 축 인터랙티브 그래프 생성...")
    
    # 이중 Y축을 사용하기 위해 subplot 생성
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 가격 데이터 추가 (첫 번째 Y축 - 왼쪽)
    fig.add_trace(
        go.Scatter(x=combined_df.index, y=combined_df['Price'], name="Price (USD)", line=dict(color='darkorange')),
        secondary_y=False,
    )

    # 공급량 데이터 추가 (두 번째 Y축 - 오른쪽)
    fig.add_trace(
        go.Scatter(x=combined_df.index, y=combined_df['Supply'], name="Total Supply", line=dict(color='royalblue')),
        secondary_y=True,
    )

    # 그래프 전체 레이아웃 설정
    fig.update_layout(
    title_text=f'<b>BITCOIN: Price vs. Total Supply (Since {START_DATE})</b>',
    template='plotly_white',
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        # ▼▼▼ 아래 3줄을 추가하여 배경과 테두리를 만듭니다 ▼▼▼
        bgcolor='rgba(255, 255, 255, 0.8)', # 반투명한 흰색 배경
        bordercolor="Black",                 # 검은색 테두리
        borderwidth=1                        # 테두리 두께
    )
,
        # --- ▲▲▲ ------------------------------------------ ▲▲▲ ---
            xaxis=dict(
                rangeselector=dict(buttons=list([dict(count=1, label="1m", step="month", stepmode="backward"), dict(count=3, label="3m", step="month", stepmode="backward"), dict(count=6, label="6m", step="month", stepmode="backward"), dict(step="all")])),
                rangeslider=dict(visible=True), type="date"
            )
        )
    # X축 및 Y축 제목 설정
    #fig.update_xaxes(title_text="Date")#
    fig.update_yaxes(title_text="<b>Price (USD)</b>", secondary_y=False)
    fig.update_yaxes(title_text="<b>Total Supply</b>", secondary_y=True)

    # 5. HTML 파일로 저장
    file_name = f"graph_btc_supply.html"
    style_chart(fig, coin='BTC', left_title='BTC Price (USD)', right_title='총공급량 (BTC)', right_fill=False, right_suffix=' BTC', right_tickformat='.3~s')  # 사이트 다크 테마 적용
    save_chart(fig, file_name)

    print(f"\n✅ 성공! 모든 과정이 완료되었습니다.")
    print(f"결과물은 '{file_name}' 파일로 저장되었습니다.")