"""即時監控儀表板（C 組，任務 C1、C3）。

執行：streamlit run app/dashboard.py

版面：
- 側欄：距離、良性故障（老化、漂移、雜散光）、攻擊（截取重送、PNS、致盲）與比例、開始／暫停
- 主畫面：即時 QBER 與誘騙比曲線、七類診斷＋信心度、門檻法判斷並排
- 行動：攻擊 → 中止金鑰並告警；老化 → 派工檢修；漂移 → 偏振校正；本地 LLM 寫事件報告
- 分頁「實驗結果」：讀 reports/ 的圖
先用假模型（隨機或簡單規則）把畫面做完，B 組 model.pkl 好了再換上。
"""

import streamlit as st

st.set_page_config(page_title="QKD 鏈路 AI 健康診斷", layout="wide")
st.title("QKD 鏈路 AI 健康診斷")
st.info("C1：儀表板雛形尚未實作。請依 docs/project-plan.md 的 C 組章節開發。")
