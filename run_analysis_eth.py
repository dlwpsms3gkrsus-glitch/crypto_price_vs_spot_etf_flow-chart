from chart_theme import style_chart, save_chart
import pandas as pd
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from io import StringIO
from etf_scraper import scrape_etf_flow as scrape_flow, save_flow_csv, load_flow_csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_etf_flow():
    """Farside Investors에서 ETH 현물 ETF 일별 순유입 데이터를 수집합니다 (공용 모듈 사용)."""
    return scrape_flow("ETH")

def get_price_data(ticker, start_date):
    """Yahoo Finance에서 특정 티커의 가격 데이터를 가져옵니다."""
    print(f"▶ 2단계: Yahoo Finance에서 '{ticker}' 가격 데이터를 다운로드합니다...")
    try:
        df = yf.download(ticker, start_date, progress=False)
        
        if df.empty:
            print("❌ 가격 데이터를 다운로드하지 못했습니다.")
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.reset_index(inplace=True)

        print("✔️ 가격 데이터 다운로드 완료.")
        return df
    except Exception as e:
        print(f"❌ 가격 데이터 다운로드 중 오류 발생: {e}")
        return None

def create_chart(price_df, etf_df):
    """가격과 ETF 유입량 데이터를 병합하여 최종 차트를 생성합니다."""
    print("▶ 3단계: 데이터 병합 및 최종 차트 생성을 시작합니다...")
    try:
        merged_df = pd.merge(price_df[['Date', 'Close']], etf_df, on='Date', how='inner')
        merged_df.sort_values('Date', inplace=True)

        merged_df['Cumulative_Flow'] = merged_df['Total'].cumsum()
        
        merged_df['EMA_20'] = merged_df['Close'].ewm(span=20, adjust=False).mean()
        merged_df['EMA_60'] = merged_df['Close'].ewm(span=60, adjust=False).mean()
        merged_df['EMA_120'] = merged_df['Close'].ewm(span=120, adjust=False).mean()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # --- ▼▼▼ [UI 수정] BTC 차트와 색상 통일 ▼▼▼ ---
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['Close'], name='ETH Price', line=dict(color='royalblue', width=1.5)), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['EMA_20'], name='EMA 20-Day', line=dict(color='black', width=1, dash='dash'), visible='legendonly'), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['EMA_60'], name='EMA 60-Day', line=dict(color='green', width=1, dash='dash'), visible='legendonly'), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['EMA_120'], name='EMA 120-Day', line=dict(color='red', width=1, dash='dash'), visible='legendonly'), secondary_y=False)
        
        fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df['Cumulative_Flow'], name='Cumulative Inflow', line=dict(color='darkorange', width=2)), secondary_y=True)
        # --- ▲▲▲ ---------------------------------- ▲▲▲ ---

        fig.update_layout(
            title_text='<b>ETH Price vs Cumulative Spot ETF Net Inflow</b>',
            # --- ▼▼▼ [UI 수정] BTC 차트와 배경/범례 스타일 통일 ▼▼▼ ---
            plot_bgcolor='#E5ECF6', # 플롯 배경색
            paper_bgcolor='white',  # 전체 배경색
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=0.02,
                bgcolor='rgba(255, 255, 255, 0.6)',
                bordercolor="Black",
                borderwidth=1
            ),
            # --- ▲▲▲ ------------------------------------------ ▲▲▲ ---
            xaxis=dict(
                rangeselector=dict(buttons=list([dict(count=1, label="1m", step="month", stepmode="backward"), dict(count=3, label="3m", step="month", stepmode="backward"), dict(count=6, label="6m", step="month", stepmode="backward"), dict(step="all")])),
                rangeslider=dict(visible=True), type="date"
            )
        )
        # --- ▼▼▼ [UI 수정] BTC 차트와 축 색상 통일 ▼▼▼ ---
        fig.update_yaxes(title_text='<b>ETH Price (USD)</b>', color='royalblue', secondary_y=False)
        fig.update_yaxes(title_text='<b>ETF Cumulative Net Inflow (US$M)</b>', color='darkorange', secondary_y=True)
        # --- ▲▲▲ ---------------------------------- ▲▲▲ ---

        file_name = 'graph_eth.html'
        style_chart(fig, coin='ETH', left_title='ETH Price (USD)', right_title='ETF 누적 순유입 (US$M)', right_suffix='M', right_tickprefix='$', right_ticksuffix='M')  # 사이트 다크 테마 적용
        save_chart(fig, file_name)
        print(f"✅ 최종 그래프 생성 완료! '{file_name}' 파일을 확인해주세요.")

    except Exception as e:
        print(f"❌ 차트 생성 중 오류 발생: {e}")

# --- 메인 실행 블록 ---
if __name__ == '__main__':
    etf_data = scrape_etf_flow()
    price_data = None

    # 수집 실패 시 기존 CSV를 지우지 않고, 기존 데이터로 차트를 그립니다.
    if not save_flow_csv(etf_data, 'ethereum_etf_total_flow.csv'):
        etf_data = load_flow_csv('ethereum_etf_total_flow.csv')

    if etf_data is not None and not etf_data.empty:
        start_date = etf_data['Date'].min().strftime('%Y-%m-%d')
        price_data = get_price_data('ETH-USD', start_date)

        if price_data is not None:
            price_data.to_csv('ethereum_price_data.csv', index=False)
            print("💾 'ethereum_price_data.csv' 파일 저장 완료.")
            create_chart(price_data, etf_data)
    else:
        print("ETF 데이터가 없어 분석을 진행할 수 없습니다.")
