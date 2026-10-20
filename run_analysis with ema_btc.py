import pandas as pd
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from io import StringIO # FutureWarning 방지를 위해 추가
from etf_scraper import scrape_etf_flow as scrape_flow, save_flow_csv, load_flow_csv

def scrape_etf_flow():
    """Farside Investors에서 BTC 현물 ETF 일별 순유입 데이터를 수집합니다 (공용 모듈 사용)."""
    return scrape_flow("BTC")

def get_btc_price():
    """
    yfinance를 사용하여 BTC 가격 데이터를 다운로드하고 데이터프레임으로 반환합니다.
    """
    print(" étape 2: yfinance에서 BTC 가격 데이터를 다운로드합니다...")
    try:
        df_price = yf.download('BTC-USD', start='2024-01-11')
        if df_price.empty:
            print("❌ yfinance 실패: BTC 가격 데이터를 가져올 수 없습니다.")
            return None

        # yfinance가 반환하는 다중 레벨 컬럼 인덱스를 단일 레벨로 평탄화합니다.
        if isinstance(df_price.columns, pd.MultiIndex):
            df_price.columns = df_price.columns.get_level_values(0)
            
        df_price.reset_index(inplace=True)
        print("✅ BTC 가격 데이터 다운로드 완료!")
        return df_price
        
    except Exception as e:
        print(f"❌ BTC 가격 다운로드 중 오류 발생: {e}")
        return None

def create_chart(df_price, df_flow):
    """
    두 개의 데이터프레임을 병합하고, 누적 합계 및 EMA를 계산하여
    최종 인터랙티브 HTML 차트를 생성합니다.
    """
    print(" étape 3: 데이터 병합 및 최종 차트 생성을 시작합니다...")
    try:
        # 데이터 병합
        merged_df = pd.merge(df_price, df_flow, on='Date', how='left')
        merged_df['Total'] = merged_df['Total'].fillna(0)
        
        # --- ▼▼▼ 핵심 수정 부분: EMA 계산 ▼▼▼ ---
        # ETF 누적 유입량 계산
        merged_df['Cumulative_Inflow'] = merged_df['Total'].cumsum()

        # 20, 60, 120일 지수이동평균선(EMA) 계산
        ema_periods = [20, 60, 120]
        for period in ema_periods:
            merged_df[f'EMA_{period}'] = merged_df['Close'].ewm(span=period, adjust=False).mean()
        # --- ▲▲▲ ----------------------------------- ▲▲▲ ---

        # Plotly 차트 생성
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # BTC 가격 (종가) 추가
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['Close'], name='BTC Price (종가)', line=dict(color='royalblue', width=2)), secondary_y=False)
        
        # --- ▼▼▼ 핵심 수정 부분: EMA 그래프 추가 ▼▼▼ ---
        # 계산된 EMA들을 차트에 추가
        colors = ['#FF6F91', '#FF9671', '#FFC75F'] # EMA 선 색상
        for i, period in enumerate(ema_periods):
            fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df[f'EMA_{period}'], name=f'EMA {period}-day',
                                     line=dict(color=colors[i], width=1.5, dash='dot'),
                                     visible='legendonly'), # 기본적으로 숨김 처리
                          secondary_y=False)
        # --- ▲▲▲ --------------------------------------- ▲▲▲ ---

        # ETF 누적 유입량 추가
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['Cumulative_Inflow'], name='ETF Cumulative Inflow', line=dict(color='darkorange', width=2)), secondary_y=True)
        
        fig.update_layout(
            title_text='<b>BTC Price vs. Spot ETF Cumulative Net Inflow</b>',
            xaxis_title='Date',
            legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top', bgcolor='rgba(255, 255, 255, 0.5)'),
            xaxis=dict(
                rangeselector=dict(buttons=list([dict(count=1, label="1m", step="month", stepmode="backward"), dict(count=3, label="3m", step="month", stepmode="backward"), dict(count=6, label="6m", step="month", stepmode="backward"), dict(step="all")])),
                rangeslider=dict(visible=True), type="date"
            )
        )
        fig.update_yaxes(title_text='<b>BTC Price (USD)</b>', color='royalblue', secondary_y=False)
        fig.update_yaxes(title_text='<b>ETF Cumulative Net Inflow (US$M)</b>', color='darkorange', secondary_y=True)

        # HTML 파일로 저장
        file_name = 'graph_btc.html'
        fig.write_html(file_name)

        print(f"✅ 최종 그래프 생성 완료! '{file_name}' 파일을 확인해주세요.")

    except Exception as e:
        print(f"❌ 차트 생성 중 오류 발생: {e}")

# --- 메인 실행 블록 ---
if __name__ == '__main__':
    etf_data = scrape_etf_flow()
    # 수집 실패 시 기존 CSV를 지우지 않고, 기존 데이터로 차트를 그립니다.
    if not save_flow_csv(etf_data, 'bitcoin_etf_total_flow.csv'):
        etf_data = load_flow_csv('bitcoin_etf_total_flow.csv')

    price_data = get_btc_price()
    if price_data is not None:
        price_data.to_csv('btc_price_2024-01-11_to_today.csv', index=False)
        print("💾 'btc_price_2024-01-11_to_today.csv' 파일 저장 완료.")

    if etf_data is not None and price_data is not None:
        create_chart(price_data, etf_data)
    else:
        print("\n❗️데이터 수집 과정에 문제가 있어 차트를 생성하지 못했습니다.")
