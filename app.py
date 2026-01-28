import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# ==========================================
# 專案：VAT 營業稅智慧稽核系統 v3.1
# 更新：新增進銷項完整欄位與對應檢查標準
# ==========================================
st.set_page_config(page_title="VAT v3.1 智慧稅務", layout="wide", page_icon="🛡️")

# --- 側邊欄：功能模式 ---
with st.sidebar:
    st.title("🛡️ VAT v3.1 控制中心")
    app_mode = st.selectbox(
        "切換作業模式",
        ["🏠 系統首頁", "📤 銷項憑證登錄", "📥 進項憑證登錄", "✈️ 零稅率清單"]
    )
    st.divider()
    st.info("AI 引擎狀態：自動偵測最新世代模型")
    st.caption("版本：v3.1 (多模組 Failover 已啟動)")

# --- 核心邏輯：AI 多模組自動切換引擎 (V3 核心機制) ---
def call_vat_ai_v3(prompt):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        return "🛑 [錯誤] 找不到 API Key，請在 Streamlit Secrets 設定。"

    genai.configure(api_key=api_key)
    
    # 模型嘗試清單：2.0 Lite -> 2.0 Standard -> 3.0 Preview -> 1.5 Fallback
    models_to_try = [
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-2.0-flash',
        'gemini-3-flash-preview',
        'gemini-1.5-flash'
    ]
    
    for m_name in models_to_try:
        try:
            full_path = m_name if m_name.startswith('models/') else f"models/{m_name}"
            model = genai.GenerativeModel(model_name=full_path)
            response = model.generate_content(prompt)
            return f"✅ **AI 稽核完成** (模組: `{m_name}`)\n\n{response.text}"
        except Exception:
            continue 
            
    return "❌ 所有 AI 模組呼叫失敗，請檢查 API Key 權限。"

# --- 核心邏輯：統編檢查 (除以 5) ---
def validate_tax_id(tax_id):
    if not tax_id or tax_id.strip() == "": return True, "非營業人 (免填)"
    if len(tax_id) != 8 or not tax_id.isdigit(): return False, "格式錯誤 (需8位)"
    w = [1, 2, 1, 2, 1, 2, 4, 1]
    total = sum(((int(tax_id[i]) * w[i]) // 10 + (int(tax_id[i]) * w[i]) % 10) for i in range(8))
    if total % 5 == 0 or (tax_id[6] == '7' and (total + 1) % 5 == 0):
        return True, "統編檢核成功"
    return False, "統編邏輯錯誤"

# ==========================================
# UI 介面處理
# ==========================================

if app_mode == "🏠 系統首頁":
    st.header("歡迎使用 VAT v3.1 系統")
    st.markdown("""
    ### 本次新增欄位與稽核標準：
    - **開立年月日**：格式需為 YYYYMMDD 或 民國年月日。
    - **發票起訖號**：檢查是否為 8 位數字，且訖號應大於或等於起號。
    - **課稅別**：1:應稅、2:零稅率、3:免稅。
    - **扣抵代號**：1:進項可扣抵進貨、2:進項可扣抵固定資產。
    - **通關方式**：1:經海關、2:非經海關。
    """)
    st.info("系統已鎖定 v3.0 多模組驗證機制，優先呼叫最新 Gemini 2.0/3.0 系列。")

elif app_mode == "📤 銷項憑證登錄":
    st.header("📤 銷項憑證登錄 (含新欄位檢核)")
    
    with st.form("vat_out_v31"):
        col1, col2, col3 = st.columns(3)
        with col1:
            f_code = st.selectbox("格式代號", ["31", "32", "33", "34", "35", "37"])
            v_date_full = st.text_input("開立年月日 (如 1130201)", help="民國年月日共7碼")
            tax_id_seller = st.text_input("銷貨人統編 (公司)", max_chars=8)
            tax_id_buyer = st.text_input("買受人統編", max_chars=8)
        with col2:
            inv_start = st.text_input("發票起號 (8碼)", max_chars=8)
            inv_end = st.text_input("發票訖號 (8碼)", max_chars=8)
            tax_type = st.selectbox("課稅別", ["1:應稅", "2:零稅率", "3:免稅"])
        with col3:
            v_amt = st.number_input("銷售金額", min_value=0)
            v_tax = st.number_input("營業稅額", min_value=0)
            customs_mode = st.selectbox("通關方式", ["0:不適用", "1:經海關", "2:非經海關"])
        
        is_agg = st.checkbox("彙加註記")
        submit = st.form_submit_button("🚀 執行 v3.1 智慧稽核")

    if submit:
        # 1. 本地基礎檢查
        seller_ok, _ = validate_tax_id(tax_id_seller)
        buyer_ok, _ = validate_tax_id(tax_id_buyer)
        
        # 2. 建立專用 AI Prompt
        prompt = f"""
        你是台灣營業稅專家。請根據《營業稅申報作業要點》稽核以下資料：
        
        [基本資料]
        - 格式: {f_code} | 開立日期: {v_date_full} | 課稅別: {tax_type}
        - 銷貨人統編: {tax_id_seller} | 買受人統編: {tax_id_buyer}
        - 發票區間: {inv_start} 至 {inv_end}
        - 金額: {v_amt} | 稅額: {v_tax} | 通關方式: {customs_mode} | 彙加: {is_agg}
        
        [檢查標準]
        1. 稅額檢核：課稅別為'1:應稅'時，稅額是否等於金額的 5%？
        2. 零稅率檢核：課稅別為'2:零稅率'時，通關方式不可為'0'。
        3. 發票號碼：訖號是否小於起號？(起:{inv_start}, 訖:{inv_end})。
        4. 格式限制：彙加註記與格式{f_code}是否衝突？
        5. 銷貨人統編是否正確？({tax_id_seller})
        """
        
        with st.spinner("多模組 AI 驗證中..."):
            result = call_vat_ai_v3(prompt)
            if not seller_ok: st.error(f"📍 銷貨人統編異常")
            if not buyer_ok: st.warning(f"📍 買受人統編檢核注意")
            st.markdown("---")
            st.info(result)

elif app_mode == "📥 進項憑證登錄":
    st.header("📥 進項憑證登錄 (含扣抵代號)")
    with st.form("vat_in_v31"):
        col1, col2 = st.columns(2)
        with col1:
            f_code_in = st.selectbox("進項格式", ["21", "22", "23", "25", "28"])
            deduct_id = st.selectbox("扣抵代號", ["1:進項可扣抵進貨費用", "2:進項可扣抵固定資產", "3:不可扣抵(不可報)"])
        with col2:
            v_amt_in = st.number_input("金額 (未稅)", min_value=0)
            v_tax_in = st.number_input("稅額", min_value=0)
        
        submit_in = st.form_submit_button("🔍 執行進項稽核")
    
    if submit_in:
        prompt_in = f"稽核進項資料：格式{f_code_in}, 扣抵代號{deduct_id}, 金額{v_amt_in}, 稅額{v_tax_in}。請判斷其稅額計算與扣抵合法性。"
        with st.spinner("AI 分析中..."):
            result = call_vat_ai_v3(prompt_in)
            st.markdown(result)

elif app_mode == "✈️ 零稅率清單":
    st.header("✈️ 零稅率出口明細")
    st.info("此處欄位會根據'課稅別: 2'自動對齊通關方式與報單號碼。")

st.divider()
st.caption("VAT Project v3.1 | 2026 | 已鎖定多模組驗證機制")
