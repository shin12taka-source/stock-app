import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os
import plotly.express as px

# ページ基本設定
st.set_page_config(page_title="日経225 高機能スクリーニング", layout="wide")

st.title("🚀 日経225 高機能スクリーニングアプリ")
st.write("指標（PER, PBR, ROE, 配当利回り）を総合的に分析し、割安スコアを算出します。")

# --- 用語解説と目安の折りたたみメニュー ---
with st.expander("💡 投資指標の用語解説と目安基準を見る"):
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
    **【重要指標の早見表】**
    | 分類 | 指標 | チェックする目安 |
    | :--- | :--- | :--- |
    | **還元** | 配当利回り | 3.5% 〜 4.5%（高すぎないか確認） |
    | **還元** | 配当性向 | 30% 〜 50%（無理な配当でないか確認） |
    | **割安度** | PER | 15倍以下（利益に対して割安か） |
    | **割安度** | PBR | 1倍前後または1倍割れ（資産に対して割安か） |
    | **稼ぐ力** | ROE | 8%以上（効率よく稼げているか） |
    | **安全性** | 自己資本比率 | 40%以上（倒産リスクが低いか ※金融除く） |
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
# グラフ等を選択して画面がリロードされた時に、取得済みのデータが消えないように保存します。
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
    # 銘柄コードと企業名を結合した検索用リストを作成（例: "7203 - トヨタ自動車"）
    company_options = df_list["銘柄コード"].astype(str) + " - " + df_list["企業名"]
    selected_company_str = st.selectbox("枠内をクリックし、企業名または銘柄コード（数字4桁）を入力してください:", company_options)
    
    # 選択された文字列からコードを抽出し、その企業の「業種」を自動特定する
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
        status_text.text(f"[{i+1}/{total_stocks}] {name} ({code}) のデータを取得中...")
        
        try:
            ticker = yf.Ticker(f"{code}.T")
            info = ticker.info
            
            # --- 配当利回りの異常値対策（ここから） ---
            current_price = info.get("currentPrice", info.get("regularMarketPrice", None))
            div_rate = info.get("dividendRate", None)
            
            # 1株あたり配当金 ÷ 株価 で自前で正確な利回りを計算する
            if pd.notna(div_rate) and pd.notna(current_price) and current_price > 0:
                div_yield = div_rate / current_price
            else:
                # 予備として従来の利回りデータも取得し、異常に大きい場合（20%超え）は100で割って補正
                div_yield = info.get("dividendYield", None)
                if pd.notna(div_yield) and div_yield > 0.2:
                    div_yield = div_yield / 100
            # --- 配当利回りの異常値対策（ここまで） ---

            # 各種指標の取得
            results.append({
                "銘柄コード": code,
                "企業名": name,
                "現在株価": current_price,
                "予想PER": info.get("forwardPE", None),
                "PBR": info.get("priceToBook", None),
                "ROE": info.get("returnOnEquity", None),
                "配当利回り": div_yield,
                "配当性向": info.get("payoutRatio", None)
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
    
    # 独自の割安スコアリング機能（MAX 4点）
    def calculate_score(row):
        score = 0
        if pd.notna(row["予想PER"]) and pd.notna(avg_pe) and row["予想PER"] < avg_pe:
            score += 1 # 業種平均よりPERが低い
        if pd.notna(row["PBR"]) and row["PBR"] < 1.0:
            score += 1 # 解散価値（1倍）を下回っている
        if pd.notna(row["ROE"]) and row["ROE"] >= 0.08:
            score += 1 # ROE 8%以上（日本企業の一般的な目標水準）
        if pd.notna(row["配当利回り"]) and row["配当利回り"] >= 0.03:
            score += 1 # 配当利回りが3%以上（高配当水準）
        return score
        
    df["スコア"] = df.apply(calculate_score, axis=1)
    # スコアを★の数に変換して分かりやすく
    df["割安度"] = df["スコア"].apply(lambda x: "⭐" * int(x))
    
    # スコアが高い順 ＞ 予想PERが低い順 に並び替え（ランキング化）
    df = df.sort_values(by=["スコア", "予想PER"], ascending=[False, True])
    
    st.subheader(f"🏆 {selected_sector} のランキング一覧")
    
    # パーセント表示用の関数
    def format_percent(x):
        return f"{x * 100:.2f}%" if pd.notna(x) else "ー"
        
    display_df = df.copy()
    display_df["ROE"] = display_df["ROE"].apply(format_percent)
    display_df["配当利回り"] = display_df["配当利回り"].apply(format_percent)
    display_df["配当性向"] = display_df["配当性向"].apply(format_percent)
    
    # 列の並び順を整える
    display_df = display_df[["割安度", "銘柄コード", "企業名", "現在株価", "予想PER", "PBR", "ROE", "配当利回り", "配当性向"]]
    
    st.dataframe(
        display_df.style.format({
            "現在株価": "¥{:,.0f}",
            "予想PER": "{:.2f} 倍",
            "PBR": "{:.2f} 倍"
        }),
        use_container_width=True, hide_index=True
    )
    
    st.caption("【⭐の獲得条件】①予想PERが業種平均未満 ②PBR 1.0倍未満 ③ROE 8%以上 ④配当利回り 3%以上")
    st.divider()

    # --- 4. グラフで視覚的に比較 ---
    st.subheader("📊 業種内での指標比較グラフ")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # PERの比較グラフ
        fig_pe = px.bar(df, x="企業名", y="予想PER", title="企業別 予想PER（低いほど割安）", color="予想PER", color_continuous_scale="Blues")
        if pd.notna(avg_pe):
            fig_pe.add_hline(y=avg_pe, line_dash="dash", line_color="red", annotation_text=f"業種平均 ({avg_pe:.1f})")
        st.plotly_chart(fig_pe, use_container_width=True)
        
    with col_chart2:
        # PBRの比較グラフ
        fig_pbr = px.bar(df, x="企業名", y="PBR", title="企業別 PBR（1.0未満が割安）", color="PBR", color_continuous_scale="Blues")
        fig_pbr.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="1.0倍ライン (解散価値)")
        st.plotly_chart(fig_pbr, use_container_width=True)

    st.divider()

    # --- 5. 気になる銘柄の過去の株価チャート ---
    st.subheader("📉 個別銘柄の株価チャート（過去1年）")
    st.write("ランキング表から気になる企業を選んで、チャートの形状を確認しましょう。")
    
    selected_company = st.selectbox("チャートを確認したい企業を選択:", df["企業名"].tolist())
    
    if selected_company:
        # 選択された企業のコードを取得
        target_code = df[df["企業名"] == selected_company]["銘柄コード"].values[0]
        
        with st.spinner(f"{selected_company} のチャートを取得中..."):
            target_ticker = yf.Ticker(f"{target_code}.T")
            hist = target_ticker.history(period="1y")
            
            if not hist.empty:
                # 折れ線グラフを描画
                fig_chart = px.line(hist.reset_index(), x="Date", y="Close", title=f"{selected_company} ({target_code}) - 過去1年の株価推移")
                st.plotly_chart(fig_chart, use_container_width=True)
            else:
                st.warning("チャートデータが取得できませんでした。")