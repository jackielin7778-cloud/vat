import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# ==========================================
# 專案名稱：VAT - 智慧稅務稽核系統
# ==========================================
st.set_page_config(page_title="VAT 智慧稅務系統", layout="wide", page_icon="🇹🇼")

# --- 側邊欄：多模式選擇 (各種 Mode) ---
with st.sidebar:
    st.title("🛡️ VAT 系統選單")
    app_mode = st.selectbox(
        "請選擇作業模式",
        ["🏠 系統首頁", "📤 銷項憑證登錄 (Output)", "📥 進項憑證登錄 (Input)", "✈️ 零稅率清單核對"]
    )
    st.divider()
    st.info(f"當前模式: {app_mode}")

# --- 修正後的模型初始化 (解決 NotFound 問題) ---
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🛑 錯誤：未在 Secrets 中設定 GOOGLE_API_KEY。")
        return None
    
    try:
        genai.configure(api_key=api_key)
        # 嘗試使用最穩定的完整路徑名稱
        # 若 'gemini-1.5-flash' 報 404，SDK 會自動尋找對應的 v1 版本
        model_instance = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
        return model_instance
    except Exception as e:
        st.error(f"❌ AI 配置失敗: {e}")
        return None

model = init_gemini()

# --- 統編檢查邏輯 (除以 5) ---
def check_vat_id_v2(vat_id):
    if not vat_id or vat_id.strip() == "": return True, "非營業人 (免填)"
    if len(vat_id) != 8 or not vat_id.isdigit():
        return False, "格式錯誤：需為 8 位數字"
    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    total = sum(((int(vat_id[i]) * weights[i]) // 10 + (int(vat_id[i]) * weights[i]) % 10) for i in range(8))
    if total % 5 == 0 or (vat_id[6] == '7' and (total + 1) % 5 == 0):
        return True, "統編邏輯正確"
    return False, "加權檢核失敗 (不符 5 的倍數)"

# 讀取規則檔
rules_df = pd.read_csv('rules.csv') if os.path.exists('rules.csv') else pd.DataFrame()

# ==========================================
# 模式：系統首頁
# ==========================================
if app_mode == "🏠 系統首頁":
    st.header("歡迎使用 VAT 營業稅模擬申報稽核系統")
    st.write("本系統結合了「硬核統編邏輯檢查」與「AI 稅務法規診斷」。")
    
    st.info("請從左側選單選擇作業模式進行測試。")

# ==========================================
# 模式：銷項憑證登錄
# ==========================================
elif app_mode == "📤 銷項憑證登錄 (Output)":
    st.header("📤 銷項憑證登錄稽核 (格式 31-38)")
    with st.form("out_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_code = st.selectbox("格式代號", ["31", "32", "33", "34", "35", "36", "37", "38"])
            v_id = st.text_input("買受人統編", max_chars=8)
            v_no = st.text_input("發票/憑證號碼")
        with col2:
            v_date = st.text_input("開立年月 (5碼，如 11302)")
            v_amt = st.number_input("銷售金額", min_value=0)
            v_tax = st.number_input("營業稅額", min_value=0)
        is_agg = st.checkbox("彙加註記")
        submit = st.form_submit_button("🚀 執行 AI 稽核")

    if submit:
        is_ok, id_msg = check_vat_id_v2(v_id)
        if model:
            prompt = f"你是台灣稅務審核員。請稽核：格式{f_code}, 統編{v_id}({id_msg}), 金額{v_amt}, 稅額{v_tax}, 日期{v_date}, 彙加{is_agg}。參考規則：{rules_df.to_string()}"
            with st.spinner("AI 診斷中..."):
                try:
                    res = model.generate_content(prompt)
                    if not is_ok: st.warning(f"⚠️ 統編檢查：{id_msg}")
                    else: st.success(f"✅ 統編檢查：{id_msg}")
                    st.markdown("### 🤖 AI 專家稽核意見")
                    st.info(res.text)
                except Exception as e:
                    st.error(f"AI 呼叫失敗：{e}")

# ==========================================
# 模式：進項憑證登錄
# ==========================================
elif app_mode == "📥 進項憑證登錄 (Input)":
    st.header("📥 進項憑證扣抵稽核 (格式 21-28)")
    with st.form("in_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_code = st.selectbox("格式代號", ["21", "22", "23", "24", "25", "28"])
            v_id = st.text_input("供應商統編", max_chars=8)
            deduct_code = st.selectbox("扣抵代號", ["1:進項可扣抵進貨費用", "2:進項可扣抵固定資產", "3:不可扣抵"])
        with col2:
            v_amt = st.number_input("銷售金額 (未稅)", min_value=0)
            v_tax = st.number_input("可扣抵稅額", min_value=0)
        submit = st.form_submit_button("🔍 執行進項稽核")

    if submit:
        is_ok, id_msg = check_vat_id_v2(v_id)
        if model:
            prompt = f"你是會計師。稽核進項資料：格式{f_code}, 供應商統編{v_id}({id_msg}), 扣抵代號{deduct_code}, 金額{v_amt}, 稅額{v_tax}。請分析稅額計算與扣抵合法性。"
            with st.spinner("分析中..."):
                try:
                    res = model.generate_content(prompt)
                    st.info(res.text)
                except Exception as e:
                    st.error(f"AI 異常：{e}")

# ==========================================
# 模式：零稅率核對
# ==========================================
elif app_mode == "✈️ 零稅率清單核對":
    st.header("✈️ 零稅率出口明細核對")
    with st.form("zero_form"):
        export_type = st.selectbox("通關方式", ["1:經海關出口", "2:非經海關出口"])
        doc_no = st.text_input("報單/證明文件編號")
        v_amt = st.number_input("出口金額 (TWD)", min_value=0)
        submit = st.form_submit_button("🛡️ 檢查零稅率合規")
    
    if submit:
        if model:
            prompt = f"你是審核員。零稅率稽核：通關方式{export_type}, 文件編號{doc_no}, 金額{v_amt}。請說明外銷零稅率申報注意事項。"
            with st.spinner("稽核中..."):
                try:
                    res = model.generate_content(prompt)
                    st.warning(res.text)
                except Exception as e:
                    st.error(f"AI 異常：{e}")

st.divider()
st.caption("VAT Project | 2026 | Powered by Gemini 1.5 Flash")
