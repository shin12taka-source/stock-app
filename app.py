import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os
import plotly.express as px

# ページ基本設定
st.set_page_config(page_title="日経225 高機能スクリーニング", layout="wide")

st.title("🚀 日経225 高機能スクリーニングアプリ")
st.write("指標（PER, PBR, ROE, 配当利回り、配当性向、自己資本比率）を総合的に分析し、割安スコアを算出します。")

# --- 用語解説と目安の折りたたみメニュー ---
with st.expander("💡 投資指標とグループ分けの解説を見る"):
    st.markdown("""
    配当金重視や全体のバランスを考えた運用において、投資先の企業が「安全か」「割安か」「しっかり還元してくれるか」を見極めるための代表的な指標です。

    ### 1. 配当と株主還元を見る指標（最重要）
    * **配当利回り（%）**
      * **意味:** 株価に対して年間で何%の配当が出るか。
      * **目安:** 日本株平均は2%前後。高配当株を狙うなら3.5%〜4.5%がひとつの目安（5%超は業績悪化リスクに注意）。
    * **配当性向（%）**
      * **意味:** 会社が稼いだ純利益のうち、何%を配当金の支払いに回しているか。
      * **目安:** 30%〜50%が適正ゾーン。高すぎると無理して配当を出している（減配リスク）可能性あり。
    * **DOE（株主資本配当率）**
      * **意味:** 会社の純資産に対して何%の配当を出しているか。
      * **メリット:** 純利益は年ごとの業績でブレますが、純資産は急変動しにくいため、DOEを基準にする企業は配当が安定しやすい。

    ### 2. 株価の割安・割高を見る指標
    * **PER（株価収益率 / 倍）**
      * **意味:** 企業の「利益」に対して、株価が何倍まで買われているか（元を取るのに何年かかるか）。
      * **目安:** 15倍前後が平均。10〜12倍以下なら割安、20倍以上なら割高とされることが多い。
    * **PBR（株価純資産倍率 / 倍）**
      * **意味:** 企業の「解散価値（純資産）」に対して、株価が何倍か。
      * **目安:** 1倍が基準。1倍割れは資産価値よりも株価が安い「割安株（バリュー株）」。

    ### 3. 企業の稼ぐ力と安全性を見る指標
    * **ROE（自己資本利益率 / %）**
      * **意味:** 株主から集めたお金を使って、どれだけ効率よく利益を出しているか。
      * **目安:** 8%〜10%以上あれば「稼ぐ力が強い優良企業」。
    * **自己資本比率（%）**
      * **意味:** 返済不要の自己資金が全体の何%を占めているか（財務の安全性）。
      * **目安:** 一般企業なら40%以上あると安心（※金融業を除く）。

    ---
    ### 4. 業種特性による4つのグループ分け（分散投資の目安）
    リスクを分散させるため、相関性の異なる（違う動きをする）業種を組み合わせます。

    * **🛡️ ディフェンシブ** (情報・通信、食料品、医薬品、陸運など)
      * **期待される効果:** 景気に左右されにくく、安定した収益が見込める。相場下落時のクッション役。
    * **💰 高配当・バリュー** (銀行業、保険業、卸売業など)
      * **期待される効果:** 高めの配当利回りで、利益の土台（年3〜4%など）を作る。金利上昇に強い。
    * **🏭 景気敏感（シクリカル）** (輸送用機器、機械、鉄鋼など)
      * **期待される効果:** 景気拡大期に業績が伸びやすく値上がり益を狙える。為替の影響も受けやすい。
    * **🚀 成長（グロース）** (電気機器、サービス業など)
      * **期待される効果:** AIやDXなどのテーマ性を持ち、市場平均以上の大きな株価上昇を牽引する。
    """)
# ----------------------------------------

# --- 1. CSVデータの読み込み ---
csv_file = "nikkei225.csv"
if not os.path.exists(csv_file):
    st.error(f"エラー: '{csv_file}' が見つかりません。同じフォルダにあるか確認してください。")
    st.stop()

@st.cache_data
def load_data():
    return pd.read_csv(csv_file)

df_list = load_data()
sectors = df_list["業種"].unique()

# --- 重要：セッションステート（記憶領域）の初期化 ---
if "analyzed_data" not in st.session_state:
    st.session_state.analyzed_data = None
if "last_sector" not in st.session_state:
    st.session_state.last_sector = None

# --- 検索機能の追加 ---
st.subheader("🔍 検索条件の設定")
search_mode = st.radio("検索方法を選んでください:", ["業種から一括検索", "特定の銘柄から同業他社を検索（コード・企業名）"])

if search_mode == "業種から一括検索":
    selected_sector = st.selectbox("分析したい業種を選択してください:", sectors)
else:
    company_options = df_list["銘柄コード"].astype(str) + " - " + df_list["企業名"]
    selected_company_str = st.selectbox("枠内をクリックし、企業名または銘柄コード（数字4桁）を入力してください:", company_options)
    
    selected_code = int(selected_company_str.split(" - ")[0])
    selected_sector = df_list[df_list["銘柄コード"] == selected_code]["業種"].values[0]
    selected_name = df_list[df_list["銘柄コード"] == selected_code]["企業名"].values[0]
    
    st.info(f"💡 「{selected_name}」は【{selected_sector}】です。この業種内の同業他社と比較します。")

# 違う業種が選ばれたらデータをリセット
if selected_sector != st.session_state.last_sector:
    st.session_state.analyzed_data = None

target_stocks = df_list[df_list["業種"] == selected_sector]
# --------------------

# --- 2. データ取得処理 ---
if st.button(f"「{selected_sector}」のデータを取得＆分析"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(target_stocks)
    
    for i, (index, row) in enumerate(target_stocks.iterrows()):
        code = str(row["銘柄コード"])
        name = row["企業名"]
        sector_name = row["業種"] # 業種データを追加で取得
        status_text.text(f"[{i+1}/{total_stocks}] {name} ({code}) のデータを取得中...")
        
        try:
            ticker = yf.Ticker(f"{code}.T")
            info = ticker.info
            
            # --- 配当利回りの異常値対策 ---
            current_price = info.get("currentPrice", info.get("regularMarketPrice", None))
            div_rate = info.get("dividendRate", None)
            
            if pd.notna(div_rate) and pd.notna(current_price) and current_price > 0:
                div_yield = div_rate / current_price
            else:
                div_yield = info.get("dividendYield", None)
                if pd.notna(div_yield) and div_yield > 0.2:
                    div_yield = div_yield / 100

            # --- 自己資本比率の概算計算（負債比率から逆算） ---
            debt_to_equity = info.get("debtToEquity", None)
            equity_ratio = 1 / ((debt_to_equity / 100) + 1) if pd.notna(debt_to_equity) else None

            # 各種指標の取得
            results.append({
                "業種": sector_name, # グループ判定用に業種を保存
                "銘柄コード": code,
                "企業名": name,
                "現在株価": current_price,
                "予想PER": info.get("forwardPE", None),
                "PBR": info.get("priceToBook", None),
                "ROE": info.get("returnOnEquity", None),
                "配当利回り": div_yield,
                "配当性向": info.get("payoutRatio", None),
                "自己資本比率": equity_ratio
            })
        except Exception as e:
            st.error(f"{name}の取得エラー: {e}")
        
        time.sleep(2) # API制限回避
        progress_bar.progress((i + 1) / total_stocks)
        
    status_text.text("データ取得完了！分析を開始します...")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    # 取得したデータをセッション（記憶）に保存
    st.session_state.analyzed_data = pd.DataFrame(results)
    st.session_state.last_sector = selected_sector

# --- 3. 分析・スコアリング・表示処理 ---
if st.session_state.analyzed_data is not None:
    df = st.session_state.analyzed_data.copy()
    
    # 業種平均PERの算出
    avg_pe = df["予想PER"].mean()
    
    # --- 独自の割安スコアリング機能（MAX 6点） ---
    def calculate_score(row):
        score = 0
        if pd.notna(row["予想PER"]) and pd.notna(avg_pe) and row["予想PER"] < avg_pe:
            score += 1 # ①業種平均よりPERが低い
        if pd.notna(row["PBR"]) and row["PBR"] < 1.0:
            score += 1 # ②解散価値（1倍）を下回っている
        if pd.notna(row["ROE"]) and row["ROE"] >= 0.08:
            score += 1 # ③ROE 8%以上
        if pd.notna(row["配当利回り"]) and row["配当利回り"] >= 0.035:
            score += 1 # ④配当利回りが3.5%以上
        if pd.notna(row["配当性向"]) and 0.30 <= row["配当性向"] <= 0.50:
            score += 1 # ⑤配当性向が30%〜50%の適正ゾーン
        if pd.notna(row["自己資本比率"]) and row["自己資本比率"] >= 0.40:
            score += 1 # ⑥自己資本比率が40%以上
        return score
        
    df["スコア"] = df.apply(calculate_score, axis=1)
    df["割安度"] = df["スコア"].apply(lambda x: "⭐" * int(x))

    # --- 💡 画像資料に基づいた4つの投資グループ分類 ---
    def classify_sector(sector):
        if sector in ["情報・通信業", "食料品", "医薬品", "陸運業"]:
            return "🛡️ ディフェンシブ"
        elif sector in ["銀行業", "保険業", "卸売業"]:
            return "💰 高配当・バリュー"
        elif sector in ["輸送用機器", "機械", "鉄鋼"]:
            return "🏭 景気敏感(シクリカル)"
        elif sector in ["電気機器", "サービス業"]:
            return "🚀 成長(グロース)"
        else:
            return "📊 その他"

    df["投資グループ"] = df["業種"].apply(classify_sector)
    # ---------------------------------------------
    
    # スコアが高い順 ＞ 予想PERが低い順 に並び替え
    df = df.sort_values(by=["スコア", "予想PER"], ascending=[False, True])
    
    st.subheader(f"🏆 {selected_sector} のランキング一覧")
    
    # パーセント表示用の関数
    def format_percent(x):
        return f"{x * 100:.2f}%" if pd.notna(x) else "ー"
        
    display_df = df.copy()
    display_df["ROE"] = display_df["ROE"].apply(format_percent)
    display_df["配当利回り"] = display_df["配当利回り"].apply(format_percent)
    display_df["配当性向"] = display_df["配当性向"].apply(format_percent)
    display_df["自己資本比率"] = display_df["自己資本比率"].apply(format_percent)
    
    # 列の名前を変更
    display_df = display_df.rename(columns={
        "予想PER": "予想PER (利益の割安度)",
        "PBR": "PBR (資産の割安度)",
        "ROE": "ROE (稼ぐ力)",
        "自己資本比率": "自己資本比率 (安全性)",
        "配当利回り": "配当利回り (還元率)",
        "配当性向": "配当性向 (配当の余力)"
    })
    
    # 列の並び順を整える
    display_df = display_df[[
        "割安度", "投資グループ", "銘柄コード", "企業名", "現在株価", 
        "予想PER (利益の割安度)", "PBR (資産の割安度)", 
        "ROE (稼ぐ力)", "自己資本比率 (安全性)", 
        "配当利回り (還元率)", "配当性向 (配当の余力)"
    ]]
    
    st.dataframe(
        display_df.style.format({
            "現在株価": "¥{:,.0f}",
            "予想PER (利益の割安度)": "{:.2f} 倍",
            "PBR (資産の割安度)": "{:.2f} 倍"
        }),
        use_container_width=True, hide_index=True
    )
    
    st.caption("【⭐の獲得条件(MAX 6つ)】①予想PERが業種平均未満 ②PBR 1.0倍未満 ③ROE 8%以上 ④配当利回り 3.5%以上 ⑤配当性向 30%〜50% ⑥自己資本比率 40%以上")
    st.divider()

    # --- 4. グラフで視覚的に比較 ---
    st.subheader("📊 業種内での指標比較グラフ")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_pe = px.bar(df, x="企業名", y="予想PER", title="企業別 予想PER（低いほど割安）", color="予想PER", color_continuous_scale="Blues")
        if pd.notna(avg_pe):
            fig_pe.add_hline(y=avg_pe, line_dash="dash", line_color="red", annotation_text=f"業種平均 ({avg_pe:.1f})")
        st.plotly_chart(fig_pe, use_container_width=True)
        
    with col_chart2:
        fig_pbr = px.bar(df, x="企業名", y="PBR", title="企業別 PBR（1.0未満が割安）", color="PBR", color_continuous_scale="Blues")
        fig_pbr.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="1.0倍ライン (解散価値)")
        st.plotly_chart(fig_pbr, use_container_width=True)

    st.divider()

    # --- 5. 気になる銘柄の過去の株価チャート ---
    st.subheader("📉 個別銘柄の株価チャート（過去1年）")
    st.write("ランキング表から気になる企業を選んで、チャートの形状を確認しましょう。")
    
    selected_company = st.selectbox("チャートを確認したい企業を選択:", df["企業名"].tolist())
    
    if selected_company:
        target_code = df[df["企業名"] == selected_company]["銘柄コード"].values[0]
        
        with st.spinner(f"{selected_company} のチャートを取得中..."):
            target_ticker = yf.Ticker(f"{target_code}.T")
            hist = target_ticker.history(period="1y")
            
            if not hist.empty:
                fig_chart = px.line(hist.reset_index(), x="Date", y="Close", title=f"{selected_company} ({target_code}) - 過去1年の株価推移")
                st.plotly_chart(fig_chart, use_container_width=True)
            else:
                st.warning("チャートデータが取得できませんでした。")