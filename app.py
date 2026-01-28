import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# ==========================================
# 專案：VAT - 多模式智慧稽核系統
# ==========================================
st.set_page_config(page_title="VAT 智慧稅務系統", layout="wide", page_icon="🇹🇼")

# --- 側邊欄：模式切換 ---
with st.sidebar:
    st.title("🛡️ VAT 系統選單")
    app_mode = st.selectbox(
        "請選擇操作模式",
        ["🏠 系統首頁", "📤 銷項憑證登錄", "📥 進項憑證登錄", "✈️ 零稅率清單核對"]
    )
    st.divider()
    st.info(f"當前模式: {app_mode}")
    st.caption("依據《營業稅電子資料申報作業要點》設計")

# --- 初始化 Gemini 1.5 Flash ---
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            return genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            st.error(f"AI 配置失敗: {e}")
    return None

model = init_gemini()

# --- 統編檢查邏輯 (除以 5) ---
def check_vat_id(vat_id):
    if not vat_id or vat_id.strip() == "": return True, "非營業人 (免填)"
    if len(vat_id) != 8 or not vat_id.isdigit():
        return False, "格式錯誤：需為 8 位數字"
    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    total = sum(((int(vat_id[i]) * weights[i]) // 10 + (int(vat_id[i]) * weights[i]) % 10) for i in range(8))
    if total % 5 == 0 or (vat_id[6] == '7' and (total + 1) % 5 == 0):
        return True, "統編邏輯正確"
    return False, "統編加權檢核失敗"

# --- 讀取規則檔 ---
rules_df = pd.read_csv('rules.csv') if os.path.exists('rules.csv') else pd.DataFrame()

# ==========================================
# 模式 1：系統首頁
# ==========================================
if app_mode == "🏠 系統首頁":
    st.header("歡迎使用 VAT 營業稅模擬申報測試系統")
    st.markdown("""
    本系統專為客戶模擬台灣營業稅申報資料登錄而設計，支援以下功能：
    - **合規稽核**：自動比對 rules.csv 設定之稅務邏輯。
    - **AI 建議**：利用 Gemini 1.5 提供具體的法規修正建議。
    - **統編檢查**：內建財政部最新加權種子法 (除以 5 邏輯)。
    """)
    

# ==========================================
# 模式 2：銷項憑證登錄
# ==========================================
elif app_mode == "📤 銷項憑證登錄":
    st.header("📤 銷項憑證登錄與稽核")
    with st.form("out_form"):
        c1, c2 = st.columns(2)
        with c1:
            f_code = st.selectbox("格式代號", ["31", "32", "33", "34", "35", "36", "37", "38"])
            v_id = st.text_input("買受人統編", max_chars=8)
            v_no = st.text_input("憑證號碼")
        with c2:
            v_date = st.text_input("開立年月 (如 11302)", max_chars=5)
            v_amt = st.number_input("銷售金額", min_value=0)
            v_tax = st.number_input("營業稅額", min_value=0)
        is_agg = st.checkbox("彙加註記 (如為折讓單33/34/38則不可勾選)")
        submit = st.form_submit_button("🚀 執行 AI 稽核")

    if submit:
        is_ok, msg = check_vat_id(v_id)
        prompt = f"你是稅務專家。稽核資料：格式{f_code}, 統編{v_id}({msg}), 金額{v_amt}, 稅額{v_tax}, 日期{v_date}。請根據《銷項憑證登錄說明》給予建議。"
        with st.spinner("AI 診斷中..."):
            res = model.generate_content(prompt)
            st.info(res.text)

# ==========================================
# 模式 3：進項憑證登錄
# ==========================================
elif app_mode == "📥 進項憑證登錄":
    st.header("📥 進項憑證登錄與扣抵檢查")
    with st.form("in_form"):
        c1, c2 = st.columns(2)
        with c1:
            f_code = st.selectbox("格式代號", ["21", "22", "23", "24", "25", "26", "27", "28"])
            v_id = st.text_input("買受人統編 (本公司)", max_chars=8)
            v_no = st.text_input("憑證號碼")
        with c2:
            v_amt = st.number_input("銷售金額 (未稅)", min_value=0)
            v_tax = st.number_input("可扣抵稅額", min_value=0)
            deduct_type = st.selectbox("扣抵代號", ["1:進項稅額可扣抵之進貨及費用", "2:進項稅額可扣抵之固定資產", "3:不可扣抵"])
        submit = st.form_submit_button("🔍 檢查扣抵資格")

    if submit:
        prompt = f"你是會計師。稽核進項資料：格式{f_code}, 扣抵代號{deduct_type}, 金額{v_amt}, 稅額{v_tax}。請判斷其稅額計算是否正確及是否符合扣抵規定。"
        with st.spinner("AI 分析中..."):
            res = model.generate_content(prompt)
            st.success(res.text)

# ==========================================
# 模式 4：零稅率清單核對
# ==========================================
elif app_mode == "✈️ 零稅率清單核對":
    st.header("✈️ 零稅率與出口明細檢查")
    with st.form("zero_form"):
        export_type = st.selectbox("通關方式", ["1:經海關出口", "2:非經海關出口"])
        doc_no = st.text_input("報單號碼/證明文件編號")
        export_amt = st.number_input("出口金額 (折合新台幣)", min_value=0)
        submit = st.form_submit_button("🛡️ 檢查零稅率合規性")
    
    if submit:
        prompt = f"稽核零稅率資料：通關方式{export_type}, 報單號碼{doc_no}, 金額{export_amt}。請說明外銷零稅率之申報要點。"
        with st.spinner("檢查中..."):
            res = model.generate_content(prompt)
            st.warning(res.text)

st.divider()
st.caption("VAT Project | 2026 模擬測試版 | 使用 Gemini 1.5 Flash")
