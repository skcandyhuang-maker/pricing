import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 頁面配置 ---
st.set_page_config(page_title="SkyCloud 費用對比工具", layout="wide")

st.title("SkyCloud vs 通路 CDN/WAF 競品試算 v1")
st.markdown("針對 FAE 與業務設計，快速比對包含 DDoS、WAF 及流量的綜合持有成本。")

# --- 側邊欄：動態參數輸入 ---
st.sidebar.header(" 客戶需求參數")
traffic_gb = st.sidebar.number_input("每月預估流量 (GB)", min_value=0, value=3000, step=500)
request_m = st.sidebar.number_input("每月請求數 (M/百萬次)", min_value=0, value=10, step=1)
waf_rules = st.sidebar.number_input("WAF 規則配置數量", min_value=1, value=5)

st.sidebar.markdown("---")
# 關鍵開關：進階 DDoS 防護
enable_ddos = st.sidebar.toggle("啟用進階 Tbps 級 DDoS 防護 (企業級)", value=True)
st.sidebar.caption("💡 開啟後，公有雲將加入 Shield Advanced / Cloud Armor Enterprise 等昂貴訂閱費。")

# 匯率預設 (1 USD = 32 NTD)
usd_to_ntd = 32.0

# --- 計算邏輯 ---
def calculate_all_vendors(traffic, requests, rules, ddos_on):
    data = []
    
    # 1. SkyCloud (SkyAnti-DDoS 方案)
    sky_monthly_base = 500000 / 12  # 年付50萬
    sky_overage = max(0, traffic - 2000) * 4.18
    data.append({
        "服務商": "SkyCloud",
        "基礎固定費": sky_monthly_base,
        "流量費用": sky_overage,
        "WAF/請求費": 0,
        "進階DDoS費": 0, # 已內含
        "總計": sky_monthly_base + sky_overage
    })

    # 2. AWS (CloudFront + Shield)
    aws_traffic = traffic * 0.085 * usd_to_ntd
    aws_waf = (5 + rules * 1 + requests * 0.6) * usd_to_ntd
    aws_ddos = (3000 * usd_to_ntd) if ddos_on else 0
    data.append({
        "服務商": "AWS",
        "基礎固定費": 0,
        "流量費用": aws_traffic,
        "WAF/請求費": aws_waf,
        "進階DDoS費": aws_ddos,
        "總計": aws_traffic + aws_waf + aws_ddos
    })

    # 3. GCP (Cloud CDN + Armor)
    gcp_traffic = traffic * 0.08 * usd_to_ntd
    gcp_waf = (5 + rules * 0.6 + requests * 0.75) * usd_to_ntd
    gcp_ddos = (3000 * usd_to_ntd) if ddos_on else 0
    data.append({
        "服務商": "GCP",
        "基礎固定費": 0,
        "流量費用": gcp_traffic,
        "WAF/請求費": gcp_waf,
        "進階DDoS費": gcp_ddos,
        "總計": gcp_traffic + gcp_waf + gcp_ddos
    })

    # 4. Azure (Front Door Premium)
    # Premium 版內含 WAF，基礎費較高
    az_base = 10560
    az_traffic = traffic * 0.17 * usd_to_ntd # Premium 流量較貴
    az_ddos = (2944 * usd_to_ntd) if ddos_on else 0
    data.append({
        "服務商": "Azure",
        "基礎固定費": az_base,
        "流量費用": az_traffic,
        "WAF/請求費": 0,
        "進階DDoS費": az_ddos,
        "總計": az_base + az_traffic + az_ddos
    })

    # 5. Cloudflare (Enterprise 估值)
    cf_base = 3000 * usd_to_ntd
    cf_traffic = max(0, traffic - 5000) * 1.5
    data.append({
        "服務商": "Cloudflare",
        "基礎固定費": cf_base,
        "流量費用": cf_traffic,
        "WAF/請求費": 0,
        "進階DDoS費": 0,
        "總計": cf_base + cf_traffic
    })

    # 6. Akamai (Enterprise 估值)
    ak_base = 4000 * usd_to_ntd
    ak_traffic = traffic * 2.0
    data.append({
        "服務商": "Akamai",
        "基礎固定費": ak_base,
        "流量費用": ak_traffic,
        "WAF/請求費": 0,
        "進階DDoS費": 0,
        "總計": ak_base + ak_traffic
    })

    return pd.DataFrame(data)

df = calculate_all_vendors(traffic_gb, request_m, waf_rules, enable_ddos)

# --- 視覺化呈現 ---
col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()
    parts = ["基礎固定費", "流量費用", "WAF/請求費", "進階DDoS費"]
    for p in parts:
        fig.add_trace(go.Bar(name=p, x=df["服務商"], y=df[p]))
    
    fig.update_layout(barmode='stack', title="每月持有成本結構 (NTD)", height=500)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💡 銷售話術建議")
    best_option = df.loc[df["總計"].idxmin(), "服務商"]
    if enable_ddos:
        st.success(f"**目前防禦優先模式下：**\nSkyCloud 的固定年費優勢極大。公有雲 (AWS/GCP/Azure) 因為需要額外支付每個月近 10 萬台幣的 DDoS 訂閱費，導致總持有成本飆升。")
    else:
        st.warning(f"**目前基礎模式下：**\n雖然某些公有雲看似便宜，但別忘了他們不包含 Tbps 級的攻擊防禦與 WAF 規則上限，一旦遭遇攻擊，費用將無法控管。")

# 數據明細表
st.subheader(" 費用細項對照表 (NTD)")
st.dataframe(df.style.format("{:,.0f}", subset=["基礎固定費", "流量費用", "WAF/請求費", "進階DDoS費", "總計"]), use_container_width=True)

# 功能矩陣對比
st.subheader(" 功能規格對比")
matrix = {
    "項目": ["Tbps 級 DDoS 防護", "WAF 規則上限", "免費 SSL 憑證額度", "日誌推送 (S3)", "技術支援"],
    "SkyCloud": ["✅ 內建 (無上限)", "✅ 25 組域名內建", "✅ 25 張", "✅ 支援", "✅ FAE 在地支援"],
    "三大公有雲": ["⚠️ 需昂貴加購", "❌ 逐條計費", "⚠️ 需搭配管理費", "✅ 支援", "❌ 按件計費/全英文"],
}
st.table(pd.DataFrame(matrix))
