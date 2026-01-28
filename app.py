import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# ==========================================
# 1. 專案名稱：VAT (Value Added Tax)
# ==========================================
st.set_page_config(page_title="VAT 台灣營業稅模擬系統", layout="wide", page_icon="🇹🇼")

# 設定標題與副標題
st.title("🇹🇼 VAT 營業稅申報資料模擬檢查系統")
st.markdown("---")

# 從 Streamlit Secrets 讀取 Gemini API 金鑰
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🛑 錯誤：請在 Streamlit Secrets 中設定 GOOGLE_API_KEY。")

# 初始化 Gemini Pro
model = genai.GenerativeModel('gemini-pro')

# ==========================================
# 2. 核心邏輯函數 (詳細註解版)
# ==========================================

def load_rules():
    """ 讀取 rules.csv，若不存在則提示用戶 """
    if os.path.exists('rules.csv'):
        return pd.read_csv('rules.csv')
    return None

def check_taiwan_tax_id_v2(tax_id):
    """
    台灣統一編號最新檢查邏輯 (除以 5)
    1. 統編 8 位數分別乘以權數 [1, 2, 1, 2, 1, 2, 4, 1]
    2. 取乘積之十位與個位相加
    3. 最終總和必須能被 5 整除 (餘數為 0)
    """
    if not tax_id:
        return True, "非營業人 (免輸入統編)"
    
    if len(tax_id) != 8 or not tax_id.isdigit():
        return False, "統編格式錯誤：需為 8 位數字"
    
    weight = [1, 2, 1, 2, 1, 2, 4, 1]
    
    def get_digit_sum(val):
        # 拆解十位與個位相加 (例如 28 -> 2+8=10)
        return (val // 10) + (val % 10)

    # 加權乘積之和
    total_sum = sum(get_digit_sum(int(tax_id[i]) * weight[i]) for i in range(8))
    
    # 邏輯判斷：除以 5 整除
    if total_sum % 5 == 0:
        return True, "統編正確"
    
    # 特殊處理：倒數第二位為 '7' 的舊案邏輯，總和+1若能被5整除也過
    if tax_id[6] == '7' and (total_sum + 1) % 5 == 0:
        return True, "統編正確 (含特殊號碼 7)"
            
    return False, f"統編邏輯異常 (加權和 {total_sum} 無法被 5 整除)"

# ==========================================
# 3. Streamlit 介面佈局
# ==========================================

# 載入外部規則
rules_df = load_rules()

with st.sidebar:
    st.header("📊 VAT 專案選單")
    # 提供進銷項選擇
    category = st.radio("申報類別", ["銷項 (Output)", "進項 (Input)"])
    st.markdown("---")
    st.caption("依據《銷項憑證營業稅登錄說明》規範設計")

# 主輸入區塊
st.subheader(f"🔍 資料錄入模擬：{category}")

with st.form("vat_form"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### [基本資料]")
        # 依 PDF 文件更新格式代碼
        invoice_type = st.selectbox("格式代號", ["31", "32", "33", "34", "35", "36", "37", "38", "21", "22", "25"])
        tax_id = st.text_input("買受人統編 (8碼)", max_chars=8)
        invoice_no = st.text_input("憑證號碼 (10碼)", max_chars=10)
        
    with col2:
        st.markdown("##### [金額資訊]")
        sales_amt = st.number_input("銷售金額 (未稅/總計)", min_value=0)
        tax_amt = st.number_input("稅額", min_value=0)
        is_aggregate = st.checkbox("彙加註記 (Aggregate)")
        
    with col3:
        st.markdown("##### [日期與類別]")
        date_ym = st.text_input("開立年月 (如 11302)", max_chars=5)
        tax_type = st.selectbox("課稅別", ["1:應稅", "2:零稅率", "3:免稅", "F:作廢", "D:空白"])

    # 表單送出按鈕
    submit_btn = st.form_submit_button("🚀 執行 VAT 合規檢查")

# ==========================================
# 4. 檢查邏輯與 AI 分析回饋
# ==========================================

if submit_btn:
    # 第一步：執行統編硬核檢查
    is_id_ok, id_msg = check_taiwan_tax_id_v2(tax_id)
    
    # 第二步：準備 AI 分析需要的 Context
    rules_text = rules_df.to_string(index=False) if rules_df is not None else "依台灣稅務規範。"
    
    # 第三步：優化 AI Prompt (針對 VAT 專案)
    analysis_prompt = f"""
    你是台灣營業稅務專家。請審核專案 VAT 的以下數據是否符合《銷項憑證營業稅登錄說明》：
    
    【系統規則 (rules.csv)】:
    {rules_text}
    
    【使用者資料】:
    - 格式代號: {invoice_type}
    - 統編: {tax_id} (邏輯檢核結果: {id_msg})
    - 銷售額: {sales_amt}
    - 稅額: {tax_amt}
    - 開立年月: {date_ym}
    - 課稅別: {tax_type}
    - 彙加註記: {is_aggregate}
    
    請依以下結構回覆分析：
    1. **合規診斷**：(例如：格式32稅額應為0、折讓單33/34/38不得彙加、銷售額計算等)。
    2. **異常提醒**：若有違反規定請明確指出。
    3. **具體修正建議**：引導使用者完成正確申報。
    """

    with st.spinner("AI 正在稽核中..."):
        try:
            response = model.generate_content(analysis_prompt)
            
            # 顯示統編結果
            if not is_id_ok:
                st.error(f"📍 統編檢核：{id_msg}")
            else:
                st.success(f"📍 統編檢核：{id_msg}")
            
            # 顯示 AI 報告
            st.markdown("---")
            st.markdown("### 🤖 VAT AI 稽核分析報告")
            st.info(response.text)
            
        except Exception as e:
            st.error(f"發生錯誤：{e}")

# 頁尾
st.divider()
st.caption("VAT Project | 2026 模擬測試版本")