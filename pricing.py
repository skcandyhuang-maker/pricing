import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 頁面基本設定
st.set_page_config(page_title="SkyCloud 競品成本分析工具", layout="wide")

st.title("🛡️ CDN & DDoS 成本試算工具 (SkyCloud vs 國際競品)")
st.markdown("本工具旨在協助業務人員快速評估 SkyCloud 與 Cloudflare, AWS, Akamai 的成本差異。")

# --- 側邊欄：參數輸入 ---
st.sidebar.header("⚙️ 需求參數設定")
traffic_gb = st.sidebar.slider("每月預估流量 (GB)", min_value=100, max_value=50000, value=3000, step=100)
request_m = st.sidebar.slider("每月請求數 (M/百萬次)", min_value=1, max_value=500, value=10)
waf_rules = st.sidebar.number_input("WAF 規則配置數量", min_value=1, value=5)

# 匯率參數 (1 USD = 32 NTD)
usd_to_ntd = 32.0

# --- 計算邏輯 ---
def get_analysis_data(traffic, requests, rules):
    results = []
    
    # 1. SkyCloud (SkyAnti-DDoS 30天方案)
    # 邏輯：年付 500,000 / 12 = 41,666。內含 2000GB，超量 4.18/GB。
    sky_base = 500000 / 12
    sky_overage = max(0, traffic - 2000) * 4.18
    results.append({
        "服務商": "SkyCloud (SkyAnti-DDoS)",
        "月基礎費": sky_base,
        "流量費用": sky_overage,
        "WAF/其他": 0,
        "預估總月費": sky_base + sky_overage
    })

    # 2. Cloudflare (Enterprise 估算值)
    # 邏輯：月基礎費約 $3,000 USD。內含流量通常較多 (假設 5000GB)。
    cf_base = 3000 * usd_to_ntd
    cf_overage = max(0, traffic - 5000) * 1.5
    results.append({
        "服務商": "Cloudflare (Ent.)",
        "月基礎費": cf_base,
        "流量費用": cf_overage,
        "WAF/其他": 0,
        "預估總月費": cf_base + cf_overage
    })

    # 3. AWS (CloudFront + Shield Advanced)
    # 邏輯：Shield Adv $3,000/月。流量約 $0.085/GB。WAF 基礎費 + 規則費 + 請求費。
    aws_base = 3000 * usd_to_ntd
    aws_traffic = traffic * 0.085 * usd_to_ntd
    aws_waf = (5 + rules * 1 + requests * 0.6) * usd_to_ntd
    results.append({
        "服務商": "AWS (Shield Adv.)",
        "月基礎費": aws_base,
        "流量費用": aws_traffic,
        "WAF/其他": aws_waf,
        "預估總月費": aws_base + aws_traffic + aws_waf
    })

    return pd.DataFrame(results)

df = get_analysis_data(traffic_gb, request_m, waf_rules)

# --- 畫面呈現 ---

# 1. 成本結構堆疊圖
fig = go.Figure()
categories = ["月基礎費", "流量費用", "WAF/其他"]
for cat in categories:
    fig.add_trace(go.Bar(name=cat, x=df["服務商"], y=df[cat]))

fig.update_layout(barmode='stack', title="預估每月成本結構 (NTD)", yaxis_title="新台幣 (NTD)")
st.plotly_chart(fig, use_container_width=True)

# 2. 詳細數據表
st.subheader("📋 費用明細對照")
st.dataframe(
    df.style.format({
        "月基礎費": "{:,.0f}", 
        "流量費用": "{:,.0f}", 
        "WAF/其他": "{:,.0f}", 
        "預估總月費": "{:,.0f}"
    }), 
    use_container_width=True
)

# 3. 業務洞察
cheapest = df.loc[df["預估總月費"].idxmin(), "服務商"]
st.info(f"💡 **競爭優勢分析**：在目前的參數設定下，**{cheapest}** 的年度預算最具有競爭力。")
if traffic_gb <= 2000:
    st.success("🎯 SkyCloud 亮點：客戶目前流量在 2TB 以內，選擇 SkyCloud 可完全免除超量流量費！")
