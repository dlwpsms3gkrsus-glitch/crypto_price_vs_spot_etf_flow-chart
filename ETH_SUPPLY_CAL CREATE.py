import pandas as pd
import requests
import json
import sys

def get_full_supply_data():
    """CoinMetrics에서 전체 이더리움 총공급량 데이터를 가져옵니다."""
    print("▶ 1단계: 전체 이더리움 공급량 데이터를 다운로드합니다...")
    try:
        # 이더리움 출시일부터 전체 데이터를 요청합니다.
        start_date = "2015-07-30"
        url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        params = {
            "assets": "eth",
            "metrics": "SplyCur",
            "start_time": f"{start_date}T00:00:00Z",
            "frequency": "1d",
            "page_size": 10000
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json().get('data', [])
        if not data:
            raise ValueError("데이터를 가져오지 못했습니다.")
        
        df = pd.DataFrame(data)
        df.rename(columns={'time': 'Date', 'SplyCur': 'Supply'}, inplace=True)
        # 날짜 형식만 남도록 정리 (YYYY-MM-DD)
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df['Supply'] = pd.to_numeric(df['Supply'])
        
        print("✔️ 전체 공급량 데이터 다운로드 완료.")
        return df
    except Exception as e:
        print(f"❌ 총공급량 데이터 다운로드 중 오류 발생: {e}")
        return None

# --- 메인 코드 실행 ---
if __name__ == "__main__":
    supply_df = get_full_supply_data()

    if supply_df is None:
        sys.exit("\n프로그램을 종료합니다.")

    # DataFrame을 JavaScript가 사용할 JSON 데이터로 변환
    data_json = supply_df.to_json(orient='records')

    # 2. 최종 HTML 코드 생성
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>이더리움 공급량 증가 계산기</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }}
            .calculator {{ width: 500px; padding: 30px; background-color: white; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); }}
            h1 {{ text-align: center; color: #333; }}
            .input-group {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            .input-field {{ display: flex; flex-direction: column; width: 48%; }}
            .input-field label {{ margin-bottom: 8px; font-weight: bold; color: #555; }}
            .input-field input[type="date"] {{ padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; }}
            button {{ width: 100%; padding: 12px; font-size: 18px; font-weight: bold; color: white; background-color: #007bff; border: none; border-radius: 6px; cursor: pointer; transition: background-color 0.3s; }}
            button:hover {{ background-color: #0056b3; }}
            #results {{ margin-top: 25px; padding-top: 20px; border-top: 1px solid #eee; }}
            .result-item {{ font-size: 1.1em; margin: 12px 0; display: flex; justify-content: space-between; }}
            .result-item .label {{ color: #333; }}
            .result-item .value {{ font-weight: bold; color: #0056b3; font-size: 1.2em; }}
        </style>
    </head>
    <body>
        <div class="calculator">
            <h1>이더리움 공급량 계산기</h1>
            <div class="input-group">
                <div class="input-field">
                    <label for="startDate">시작일 (Start Date)</label>
                    <input type="date" id="startDate">
                </div>
                <div class="input-field">
                    <label for="endDate">종료일 (End Date)</label>
                    <input type="date" id="endDate">
                </div>
            </div>
            <button id="calculateBtn">계산하기</button>
            <div id="results" style="display: none;">
                <div class="result-item">
                    <span class="label">📈 증가된 ETH의 양:</span>
                    <span class="value" id="supply-increase-abs"></span>
                </div>
                <div class="result-item">
                    <span class="label">📊 기간 내 증가율:</span>
                    <span class="value" id="supply-increase-pct"></span>
                </div>
            </div>
        </div>

        <script>
            // Python에서 생성한 전체 공급량 데이터를 가져옵니다.
            const supplyData = {data_json};

            // 날짜를 키로, 공급량을 값으로 하는 객체를 만들어 검색 속도를 높입니다.
            const supplyMap = new Map(supplyData.map(item => [item.Date, item.Supply]));

            const calculateBtn = document.getElementById('calculateBtn');
            
            calculateBtn.addEventListener('click', () => {{
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;

                if (!startDate || !endDate) {{
                    alert("시작일과 종료일을 모두 선택해주세요.");
                    return;
                }}
                if (startDate >= endDate) {{
                    alert("종료일은 시작일보다 이후 날짜여야 합니다.");
                    return;
                }}

                const startSupply = supplyMap.get(startDate);
                const endSupply = supplyMap.get(endDate);

                if (startSupply === undefined || endSupply === undefined) {{
                    alert("선택하신 날짜에 대한 데이터가 없습니다. 다른 날짜를 선택해주세요.");
                    return;
                }}

                const increaseAbs = endSupply - startSupply;
                const increasePct = (increaseAbs / startSupply) * 100;

                document.getElementById('supply-increase-abs').textContent = `${{increaseAbs.toLocaleString(undefined, {{maximumFractionDigits: 4}})}} ETH`;
                document.getElementById('supply-increase-pct').textContent = `${{increasePct.toFixed(4)}} %`;
                document.getElementById('results').style.display = 'block';
            }});
        </script>
    </body>
    </html>
    """

    # 3. HTML 파일로 저장
    file_name = "eth_supply_calculator.html"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"\\n✅ 성공! 동적 계산기가 '{file_name}' 파일로 저장되었습니다.")