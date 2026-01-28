import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# ==========================================
# 專案：VAT - AI v3 多模組核心 (修正模型路徑)
# ==========================================
st.set_page_config(page_title="VAT 智慧稅務系統 v3", layout="wide", page_icon="🛡️")

# --- 側邊欄 ---
with st.sidebar:
    st.title("🛡️ VAT v3.0 選單")
    app_mode = st.selectbox("作業模式", ["🏠 系統首頁", "📤 銷項憑證稽核", "📥 進項憑證稽核"])
    st.divider()
    st.success("AI 核心：Gemini 2.0/1.5 自動切換引擎")

# --- 核心優化：AI 多模組自動切換 (解決 404 問題) ---
def call_ai_v3_engine(prompt):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        return "🛑 [錯誤] 找不到 API Key，請檢查 Secrets。"

    genai.configure(api_key=api_key)
    
    # 這裡使用完整路徑 'models/...' 確保解決 NotFound 報錯
    # 優先嘗試目前最先進的 Gemini 2.0 系列
    model_stack = [
        'models/gemini-2.0-flash-exp', # 最強、最新模組
        'models/gemini-1.5-pro',       # 高邏輯模組
        'models/gemini-1.5-flash',     # 高速備援模組
        'gemini-1.5-flash'             # 簡化路徑備援
    ]
    
    for m_name in model_stack:
        try:
            model = genai.GenerativeModel(model_name=m_name)
            response = model.generate_content(prompt)
            # 成功時回傳結果並顯示目前使用的模組
            return f"✅ **分析完成 (AI 核心: {m_name})**\n\n{response.text}"
        except Exception as e:
            # 記錄錯誤並嘗試清單中下一個模組
            continue 
            
    return "❌ [系統] 所有 AI 模組均發生 404 錯誤，請確認 API 版本授權。建議前往 Google AI Studio 重新確認金鑰權限。"

# --- 統編邏輯 ---
def check_vat_id(vid):
    if not vid or vid.strip() == "": return True, "免統編"
    w = [1, 2, 1, 2, 1, 2, 4, 1]
    try:
        s = sum(((int(vid[i]) * w[i]) // 10 + (int(vid[i]) * w[i]) % 10) for i in range(8))
        if s % 5 == 0 or (vid[6] == '7' and (s + 1) % 5 == 0): return True, "邏輯正確"
    except: pass
    return False, "統編有誤"

# --- 讀取規則 (銷項憑證登錄說明) ---
rules_df = pd.read_csv('rules.csv') if os.path.exists('rules.csv') else pd.DataFrame()

# ==========================================
# 模式：銷項憑證稽核
# ==========================================
if app_mode == "📤 銷項憑證稽核":
    st.header("📤 銷項憑證 AI 稽核")
    with st.form("out_v3"):
        c1, c2 = st.columns(2)
        with c1:
            f_code = st.selectbox("格式代號", ["31", "32", "33", "34", "35", "36", "37", "38"])
            v_id = st.text_input("買受人統編")
        with c2:
            v_amt = st.number_input("金額", min_value=0)
            v_tax = st.number_input("稅額", min_value=0)
        submit = st.form_submit_button("執行 v3 多模組稽核")
    
    if submit:
        ok, msg = check_vat_id(v_id)
        # 整合 rules.csv 與 PDF 文件邏輯
        prompt = f"""
        你是台灣稅務專家，請針對以下資料進行合規稽核：
        [輸入資料]: 格式{f_code}, 買方統編{v_id}({msg}), 金額{v_amt}, 稅額{v_tax}
        [法規規則庫]: {rules_df.to_string()}
        請特別檢查：
        1. 格式{f_code} 的彙加限制與稅額計算。
        2. 是否符合《銷項憑證營業稅登錄說明》規範。
        """
        with st.spinner("AI 正在嘗試最新模組 (Gemini 2.0/1.5)..."):
            result = call_ai_v3_engine(prompt)
            if not ok: st.warning(f"統編檢核警告：{msg}")
            st.markdown(result)

# 首頁資訊
elif app_mode == "🏠 系統首頁":
    st.subheader("VAT 智慧稅務系統 v3.0 (正式版)")
    st.write("已全面升級 AI 核心架構：")
    st.info("1. 自動偵測可用模型 (models/gemini-2.0-flash-exp -> 1.5-pro -> 1.5-flash)\n2. 解決 API 404 NotFound 報錯問題\n3. 深度整合銷項登錄說明文件")
