import pandas as pd
from bs4 import BeautifulSoup
import os

def format_flow(value):
    """숫자를 $+- 기호와 M을 붙인 문자열로 변환합니다."""
    # 숫자가 아닌 값이 들어올 경우를 대비
    if not isinstance(value, (int, float)):
        return str(value)
    sign = "+" if value >= 0 else ""
    return f"${sign}{value:,.1f}M"

def update_website_flows(csv_path='bitcoin_etf_total_flow.csv', html_path='index.html'):
    """
    CSV 파일에서 BTC ETF 유입량 데이터를 읽어 HTML 파일을 업데이트합니다.
    컬럼 이름을 하드코딩하는 대신 위치(첫번째, 두번째 열)를 기준으로 데이터를 처리하여 안정성을 높였습니다.
    """
    try:
        # 1. 데이터 로딩
        df = pd.read_csv(csv_path)

        # 컬럼 이름 대신 위치로 지정 (첫번째: 날짜, 두번째: 유입량)
        date_column_name = df.columns[0]
        flow_column_name = df.columns[1]

        # 2. 데이터 계산
        df[date_column_name] = pd.to_datetime(df[date_column_name])
        df = df.sort_values(by=date_column_name, ascending=False).reset_index(drop=True)

        latest_flow = df.loc[0, flow_column_name]
        five_day_flow = df.loc[0:4, flow_column_name].sum()

        print(f"계산 완료:")
        print(f"- 최신 1일 유입량: {format_flow(latest_flow)}")
        print(f"- 최근 5일 유입량: {format_flow(five_day_flow)}")

        # 3. HTML 파일 읽기 및 수정
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        one_day_element = soup.find(id='1d-flow')
        five_day_element = soup.find(id='5d-flow')

        if one_day_element:
            one_day_element.string = format_flow(latest_flow)
            one_day_element['style'] = f"color: {'blue' if latest_flow >= 0 else 'red'}; font-weight: bold;"
        
        if five_day_element:
            five_day_element.string = format_flow(five_day_flow)
            five_day_element['style'] = f"color: {'blue' if five_day_flow >= 0 else 'red'}; font-weight: bold;"

        # 4. 업데이트된 내용으로 HTML 파일 저장 (덮어쓰기)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
            
        print(f"\n성공: '{html_path}' 파일이 최신 유입량으로 업데이트되었습니다.")

    except FileNotFoundError:
        print(f"오류: '{csv_path}' 또는 '{html_path}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"스크립트 실행 중 오류가 발생했습니다: {e}")

# 스크립트 실행
if __name__ == "__main__":
    update_website_flows()