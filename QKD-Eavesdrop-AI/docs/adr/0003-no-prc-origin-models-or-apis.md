# 不使用中國或中資來源的模型與 API

競賽須知規定不得使用中國或中資來源的開源模型（例如 DeepSeek）或介接工具（API、MCP 等）進行訓練和推論，違反者會被取消資格。本專案的 AI 只使用 scikit-learn（必要時加 XGBoost），模擬使用 NumPy 與 Qiskit。Qwen、DeepSeek、Yi、GLM 等模型，以及以它們為基礎微調的權重都不採用。這項限制在程式碼裡看不出來，所以新增任何模型、預訓練權重或 AI 相關套件前，都要先確認來源，並記錄在作品說明書的 AI 工具揭露中。依 2026/10/11 參賽進度分析報告補充：禁用清單另含 GLM、Kimi、MiniMax、InternLM／InternVL、BGE／BAAI 嵌入、阿里 GTE、清華 Timer／Sundial，平台避開 RAGFlow、FastGPT、Xinference、LMDeploy、Dify；兩個陷阱是 Llama-Breeze2（視覺編碼器為 InternViT-300M）與 Llama-3.1-TAIDE-R1-8B-Chat（含 DeepSeek 權重），都不可用。事件報告的本地 LLM 建議 Gemma 4 E4B 或 Gemma-3-TAIDE-12b-Chat-2602。
