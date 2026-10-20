"""CryptoFlow 차트 공통 다크 테마.

모든 Plotly 차트(ETF 흐름 2개, 공급량 2개)를 사이트 색상에 맞춰 같은 스타일로 그립니다.
사용법:
    from chart_theme import style_chart, save_chart
    style_chart(fig, coin="BTC", left_title="BTC Price (USD)", right_title="ETF 누적 순유입 (US$M)")
    save_chart(fig, "graph_btc.html")
"""
import plotly.graph_objects as go

# 사이트(index.html)와 같은 색상
BG = "#1A2233"          # 차트가 들어가는 패널 배경
TEXT = "#E5ECF6"
MUTED = "#8c9db3"
GRID = "rgba(140, 157, 179, 0.12)"
LINE = "#2a3f5f"
ACCENT = "#FFB800"
COIN_COLORS = {"BTC": "#f7931a", "ETH": "#627eea"}
SECONDARY = "#2dd4bf"   # 누적 유입·공급량 선 (가격 색과 구분되는 청록색)
EMA_COLORS = ["#c4b5fd", "#f9a8d4", "#94a3b8"]
FONT = "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def style_chart(fig, coin, left_title, right_title, right_fill=True, right_suffix="",
                right_tickformat=",.0f", right_tickprefix="", right_ticksuffix=""):
    """가격(왼쪽 축)·보조 지표(오른쪽 축) 이중 축 차트에 다크 테마를 적용합니다."""
    coin_color = COIN_COLORS[coin]

    # --- 선 색상: 왼쪽 축 첫 선 = 코인 가격, EMA = 연한 점선, 오른쪽 축 = 청록 + 은은한 채우기
    ema_i = 0
    for trace in fig.data:
        if not isinstance(trace, go.Scatter):
            continue
        name = (trace.name or "").upper()
        on_right = getattr(trace, "yaxis", None) == "y2"
        if "EMA" in name:
            trace.update(line=dict(color=EMA_COLORS[ema_i % len(EMA_COLORS)], width=1.2, dash="dot"),
                         hovertemplate="%{y:$,.0f}<extra>%{fullData.name}</extra>")
            ema_i += 1
        elif on_right:
            trace.update(line=dict(color=SECONDARY, width=2),
                         fill="tozeroy" if right_fill else None,
                         fillcolor=_hex_to_rgba(SECONDARY, 0.08),
                         hovertemplate=right_tickprefix + "%{y:,.0f}" + right_suffix + "<extra>%{fullData.name}</extra>")
        else:
            trace.update(line=dict(color=coin_color, width=2),
                         hovertemplate="%{y:$,.2f}<extra>%{fullData.name}</extra>")

    axis_common = dict(gridcolor=GRID, zeroline=False, linecolor=LINE)
    fig.update_layout(
        template="plotly_dark",
        title=None,  # 사이트 섹션 제목과 중복되지 않도록 차트 내부 제목은 숨김
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family=FONT, color=TEXT, size=12),
        margin=dict(l=10, r=10, t=56, b=10),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0f1420", bordercolor=LINE, font=dict(family=FONT, color=TEXT, size=12)),
        legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom",
                    bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color=MUTED, size=12),
                    itemclick="toggle", itemdoubleclick="toggleothers"),
        xaxis=dict(
            **axis_common,
            tickfont=dict(color=MUTED, size=11),
            type="date",
            showspikes=True, spikecolor=MUTED, spikethickness=1, spikedash="dot", spikemode="across",
            rangeslider=dict(visible=True, thickness=0.07, bgcolor="#151b2b", bordercolor=LINE, borderwidth=1),
        ),
    )
    # 기존 스크립트의 버튼 설정과 섞이지 않도록 범위 버튼은 통째로 교체
    fig.layout.xaxis.rangeselector = dict(
        buttons=[dict(count=1, label="1M", step="month", stepmode="backward"),
                 dict(count=3, label="3M", step="month", stepmode="backward"),
                 dict(count=6, label="6M", step="month", stepmode="backward"),
                 dict(count=1, label="1Y", step="year", stepmode="backward"),
                 dict(step="all", label="전체")],
        x=0, xanchor="left", y=1.02, yanchor="bottom",
        bgcolor="#232e42", activecolor=ACCENT, bordercolor=LINE, borderwidth=1,
        font=dict(color=TEXT, size=11),
    )
    fig.update_xaxes(title_text=None)  # 날짜 축은 제목 없이 (눈금만으로 충분)
    fig.update_yaxes(**axis_common, secondary_y=False,
                     title=dict(text=left_title, font=dict(color=coin_color, size=12)),
                     tickfont=dict(color=coin_color, size=11), tickmode="auto", nticks=7, tickprefix="$", tickformat="~s")
    fig.update_yaxes(**axis_common, secondary_y=True, showgrid=False,
                     title=dict(text=right_title, font=dict(color=SECONDARY, size=12)),
                     tickfont=dict(color=SECONDARY, size=11), tickmode="auto", nticks=7,
                     tickformat=right_tickformat, tickprefix=right_tickprefix, ticksuffix=right_ticksuffix)
    return fig


def save_chart(fig, file_name):
    """사이트 iframe에 꽉 차고, 배경이 패널과 이어지도록 저장합니다."""
    html = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",
        default_width="100%",
        default_height="100%",
        config={"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]},
    )
    style = (f"<style>html,body{{margin:0;height:100%;background:{BG};overflow:hidden}}"
             f".plotly-graph-div{{height:100vh!important}}</style>")
    html = html.replace("<head>", "<head><meta charset=\"utf-8\">" + style, 1)
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 차트 저장 완료: {file_name}")
