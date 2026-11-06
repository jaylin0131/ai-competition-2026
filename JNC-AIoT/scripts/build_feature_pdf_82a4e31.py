"""產生「魚塭閉環第一版（commit 82a4e31）功能說明」PDF：IoT 用在哪、AI 決策用在哪。

用法（在專案根目錄）：python3 scripts/build_feature_pdf_82a4e31.py docs/魚塭閉環第一版_功能說明_82a4e31.pdf
需要 reportlab、Pillow 與 macOS 內建黑體。
"""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("H", "/System/Library/Fonts/STHeiti Light.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont("HB", "/System/Library/Fonts/STHeiti Medium.ttc", subfontIndex=0))
pdfmetrics.registerFontFamily("H", normal="H", bold="HB", italic="H", boldItalic="HB")

OUT = sys.argv[1]
NAVY = colors.HexColor("#1F3A5F")
TEAL = colors.HexColor("#2A7F8E")
LIGHT = colors.HexColor("#EAF2F5")
GRID = colors.HexColor("#B8C7CF")
ORANGE = colors.HexColor("#C8641E")
NOTE_BG = colors.HexColor("#FFF6E8")

base = ParagraphStyle("b", fontName="H", fontSize=9.5, leading=14.5, wordWrap="CJK")
small = ParagraphStyle("s", parent=base, fontSize=8.5, leading=12.5)
mono = ParagraphStyle("m", parent=base, fontSize=7.8, leading=11)
cellh = ParagraphStyle("ch", parent=small, fontName="HB", textColor=colors.white)
h1 = ParagraphStyle("h1", parent=base, fontName="HB", fontSize=14, leading=20, textColor=NAVY,
                    spaceBefore=10, spaceAfter=6)
h2 = ParagraphStyle("h2", parent=base, fontName="HB", fontSize=11, leading=16, textColor=TEAL,
                    spaceBefore=8, spaceAfter=3)
title = ParagraphStyle("t", parent=base, fontName="HB", fontSize=20, leading=28, textColor=NAVY)
sub = ParagraphStyle("st", parent=base, fontSize=11, leading=17, textColor=colors.HexColor("#444444"))
bullet = ParagraphStyle("bl", parent=base, leftIndent=12, bulletIndent=2)


def P(t, s=base):
    return Paragraph(t, s)


def bl(items, s=bullet):
    return [Paragraph(i, s, bulletText="•") for i in items]


def table(rows, widths, header=True, style=small, extra=None):
    data = []
    for r_i, row in enumerate(rows):
        data.append([c if not isinstance(c, str) else
                     Paragraph(c, cellh if (header and r_i == 0) else style) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    ts = [("GRID", (0, 0), (-1, -1), 0.5, GRID),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        ts += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
        ts += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(rows), 2)]
    if extra:
        ts += extra
    t.setStyle(TableStyle(ts))
    return t


def note(text, color=ORANGE, bg=NOTE_BG):
    t = Table([[Paragraph(text, base)]], colWidths=[174 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def person(code, name, info):
    head = Table([[Paragraph(f"<font color='white'><b>{code}</b></font>", h2),
                   Paragraph(f"<font color='white'><b>{name}</b></font>", h2)]],
                 colWidths=[22 * mm, 152 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), ORANGE), ("BACKGROUND", (1, 0), (1, 0), TEAL),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    rows = []
    for k, v in info:
        if isinstance(v, list):
            v = [Paragraph(x, small, bulletText="•") for x in v]
        else:
            v = Paragraph(v, small)
        rows.append([Paragraph(f"<b>{k}</b>", small), v])
    body = Table(rows, colWidths=[22 * mm, 152 * mm])
    body.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return [Spacer(1, 6), KeepTogether([head, body])]


def on_page(c, d):
    c.saveState()
    c.setFont("H", 8)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawString(18 * mm, 10 * mm, "2026 全國 AI 專題創意競賽｜企業命題 AI 應用組｜魚塭閉環第一版 功能說明（commit 82a4e31）")
    c.drawRightString(192 * mm, 10 * mm, f"{d.page}")
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.2)
    c.line(18 * mm, 285 * mm, 192 * mm, 285 * mm)
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm,
                      title="JNC-AIoT 魚塭閉環第一版 功能說明", author="參賽團隊")
doc.addPageTemplates([PageTemplate(frames=[Frame(18 * mm, 16 * mm, 174 * mm, 265 * mm, id="f")],
                                   onPage=on_page)])
W = 174 * mm
s = []

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent

from reportlab.platypus import Image as RLImage

h1.keepWithNext = h2.keepWithNext = 1  # 標題不要單獨留在頁尾
tiny = ParagraphStyle("tiny", parent=small, fontSize=7.8, leading=11)
code = ParagraphStyle("code", parent=base, fontSize=8, leading=11.5)
FIG = ROOT_DIR / "backtest" / "figures"


def fig(name, caption, width=W):
    from PIL import Image as PI
    w, h = PI.open(FIG / name).size
    img = RLImage(str(FIG / name), width=width, height=width * h / w)
    return KeepTogether([img, Paragraph(caption, ParagraphStyle("cap", parent=small, textColor=colors.HexColor("#555555"),
                                                                   alignment=1, spaceBefore=2, spaceAfter=6))])


# ---------- 封面 ----------
s += [Spacer(1, 4), P("魚塭閉環第一版：新增功能說明", title),
      P("IoT 用在哪、AI 決策用在哪", sub), Spacer(1, 4),
      P("2026 全國 AI 專題創意競賽｜企業命題類 AI 應用組（銘祥科技）｜JNC-AIoT", small), Spacer(1, 8)]
s.append(table([
    ["項目", "內容"],
    ["對應 push", "commit <b>82a4e31</b>「JNC-AIoT：魚塭閉環第一版（IoT 感測→大數據→AI 分析→決策引擎→執行回饋）」"],
    ["日期", "2026-10-20，已推上 origin/main（github.com/jaylin0131/ai-competition-2026）"],
    ["規模", "69 個檔案，新增 3,138 行；新程式集中在 common/、state/、diagnose/、forecast/、decide/、backtest/、app/"],
    ["測試", "tests/test_pipeline.py 共 7 項，2026-10-20 重新執行全部通過"],
    ["場域", "這一版只做<b>魚塭（專家系統，pond）</b>；其他 6 個場域只有資料整理筆記（notes/eda/）"],
], [26 * mm, W - 26 * mm]))
s.append(Spacer(1, 6))
s.append(note("<b>一句話：</b>這一版把企業流程圖的五個階段串成一條可以實際跑的閉環。"
              "銘祥魚塭的歷史資料被<b>逐小時回放成即時 IoT 感測</b>，AI 先判斷探頭可不可信、再預測未來 6 小時的溶氧，"
              "決策引擎依「低溶氧機率」提前決定要不要開增氧機，輸出企業規定的 9 欄標準決策資料，最後模擬 SCADA／PLC 執行並回測成效。",
              TEAL, LIGHT))

s.append(P("主要成果（backtest/report.md，樣本外 7/15–9/28）", h2))
s.append(table([
    ["項目", "結果", "比較基準"],
    ["已知故障事件", "<b>9／9 偵測到</b>", "—"],
    ["合成故障 Recall", "<b>88%</b>（43 次注入）", "物理範圍檢查只抓得到掉 0、超範圍"],
    ["DO 預測 MAE（1／3／6 h）", "<b>0.162／0.193／0.219</b> mg/L", "持續法 0.180／0.214／0.247（改善約 10%）"],
    ["低溶氧提前預警（α = 0.3）", "<b>77% 事件、平均提前 4.9 小時</b>，每週誤報 0.7 次", "固定門檻：跌破才告警（提前 0 小時）"],
    ["低溶氧時數（工程估計）", "<b>133 小時</b>（比歷史少 54%）", "歷史 290、固定門檻 142"],
    ["用電", "<b>1,566 度</b>", "原始探頭門檻 1,766 度（少 11%）"],
    ["無效告警時數", "<b>9 小時</b>", "原始探頭門檻 286 小時"],
], [48 * mm, 66 * mm, 60 * mm]))

# ---------- 一、總覽 ----------
s.append(P("一、新增功能總覽（對應企業流程圖五個階段）", h1))
s.append(table([
    ["企業流程圖", "新增程式", "做什麼", "IoT／AI"],
    ["01 IoT 感測", "common/replay.py", "把銘祥 CSV 逐小時回放成即時感測；注入 5 種合成故障", "<b>IoT</b>"],
    ["02 大數據", "common/clean.py<br/>common/baseline.py", "補齊時間軸、判定斷線；各欄位各小時的歷史中位數與 MAD", "<b>IoT</b> 資料處理"],
    ["03 AI 分析", "state/pond.py", "三探頭互比算可信度、融合值、WQI、燈號、增氧機狀態", "IoT 設備健康＋規則"],
    ["", "diagnose/pond.py", "斷線、探頭失效／漂移、真實水質事件、設備異常、Isolation Forest", "<b>AI</b>＋規則"],
    ["", "forecast/pond.py", "DO 1–6 小時預測、低溶氧機率、超標時間、探頭剩餘可用時間", "<b>AI</b>"],
    ["04 決策引擎", "decide/engine.py<br/>decide/workorder.py", "9 欄標準決策資料、三級執行模式、工單派工備品能耗、LLM 白話（選用）", "<b>AI 決策</b>"],
    ["05 執行回饋", "backtest/closed_loop.py 等<br/>app/streamlit_app.py", "模擬 SCADA／PLC 執行、反事實回測、再學習 α、β；平台核准與執行紀錄", "IoT 執行端模擬＋AI 再學習"],
    ["串接", "common/pipeline.py", "PondPipeline.build().step(時間) 一次跑完五個階段", "—"],
    ["設定", "common/config.py<br/>decide/params.json", "全隊共用門檻；再學習後的 α、β 與增氧效果", "—"],
], [24 * mm, 40 * mm, 82 * mm, 28 * mm], style=tiny,
    extra=[("SPAN", (0, 3), (0, 5))]))

# ---------- 二、IoT ----------
s.append(PageBreak())
s.append(P("二、IoT 的使用在哪", h1))
s.append(note("<b>先說清楚：</b>依專案決定（HANDOFF 決定 1），本作品<b>不自建感測器或 ESP32 硬體</b>。"
              "IoT 的部分是「使用銘祥 IoT 平台收集的真實感測資料」，以回放器模擬即時上傳；"
              "感測器與設備的健康狀態由 AI 從資料中判斷；執行端的 SCADA／PLC 以軟體模擬。"))
s.append(P("2.1 用到的 IoT 感測資料（魚塭專家系統）", h2))
s.append(table([
    ["IoT 裝置", "欄位", "在哪裡用"],
    ["水質感測主機（三組探頭）", "DO1–3、pH1–3、ORP1–3、SC1–3", "三探頭互比算可信度與融合值；WQI；預測特徵"],
    ["溶氧探頭水溫", "DO1水溫", "WQI 水溫子指標；預測特徵"],
    ["電力量測（CPM 電表）", "CPM 系統總和功率、總用電度數", "<b>推斷增氧機有沒有在運轉</b>（&gt; 200 W＝運轉，約 760 W）；功率偏低＝設備異常；能耗計算"],
    ["微氣候站（OA4）", "溫度、濕度、大氣壓力、熱指數", "偵測氣象站凍結（12 小時以上不變）"],
], [42 * mm, 54 * mm, 78 * mm]))
s.append(P("2.2 IoT 在程式裡的位置", h2))
s.append(table([
    ["位置", "IoT 元素", "具體做法"],
    ["common/replay.py<br/>Replayer.stream()", "<b>模擬即時感測上傳</b>", "依時間一筆一筆送出資料，每次只給「當下以前 72 小時」的視窗，模組看不到未來，跟現場即時收資料的情況一樣"],
    ["common/replay.py<br/>inject_faults()", "<b>模擬現場感測故障</b>", "在乾淨期間注入 5 種故障：卡值（stuck）、漂移（drift）、跳點（spike）、掉 0（dropout）、整台斷線（offline），回傳正確答案供評估"],
    ["common/clean.py", "<b>通訊斷線判定</b>", "補齊每小時時間軸；缺漏的小時或整列全 0 判定為主機斷線，產生 offline 欄"],
    ["state/pond.py<br/>sensor_checks()", "<b>感測器健康度</b>", "每支探頭逐小時檢查：超出物理範圍、卡值、跳點、與另兩支中位數的偏離，扣分得到 0–100 可信度；設備健康度＝探頭平均可信度"],
    ["state/pond.py<br/>fused()", "<b>多感測器融合</b>", "只取可信度 ≥ 50 的探頭算中位數，壞掉的探頭自動被排除"],
    ["state/pond.py<br/>assess()", "<b>由電表推斷設備狀態</b>", "資料沒有增氧機開關欄位，用 CPM 功率 &gt; 200 W 判定運轉中"],
    ["diagnose/pond.py", "<b>IoT 設備診斷</b>", "offline（主機斷線）、sensor_fault（探頭失效）、sensor_drift（漂移需校正）、OA4 氣象站凍結、equipment_fault（增氧機運轉但功率 &lt; 650 W）"],
    ["forecast/pond.py<br/>probe_rul()", "<b>感測器預測維護</b>", "用探頭偏離量最近 72 小時的線性趨勢，外推何時超出容許差，得到剩餘可用時間與 48 小時內故障機率"],
    ["backtest/closed_loop.py", "<b>模擬 SCADA／PLC 執行端</b>", "依策略決定增氧機台數（0／1／2），用反事實公式估計執行後的 DO；無資料時 PLC 安全規則維持運轉"],
    ["app/streamlit_app.py", "<b>IoT 平台介面</b>", "側欄回放器（播放、前後一小時、跳到展示情境）；決策卡的「送 SCADA 執行」與執行紀錄"],
], [38 * mm, 34 * mm, 102 * mm], style=tiny))
s.append(Spacer(1, 4))
s.append(fig("sensor_trust.png", "圖 1　探頭可信度（state/pond.py）：故障或漂移的探頭可信度下降，融合時被自動排除", W * 0.92))

# ---------- 三、AI 決策 ----------
s.append(P("三、AI 決策的使用在哪", h1))
s.append(P("3.1 用到的 AI 模型與演算法", h2))
s.append(table([
    ["位置", "方法", "類型", "用途"],
    ["diagnose/pond.py<br/>IForest", "Isolation Forest（200 棵樹，contamination 1%），特徵為融合值偏離歷史同時段的 robust z", "<b>機器學習</b>（非監督）", "多變量異常：多個欄位同時偏離時告警，並列出偏離最大的兩個欄位"],
    ["forecast/pond.py<br/>DOForecaster", "梯度提升樹 GBDT：LightGBM；本機缺 libomp 時自動改用 scikit-learn HistGradientBoosting（本次回測用的是後者）", "<b>機器學習</b>（監督）", "預測 1–6 小時後的溶氧（預測「與現在的差」，絕對誤差損失、強正則化）"],
    ["forecast/pond.py", "校正期殘差分布", "統計", "把預測值轉成「6 小時內 DO &lt; 3.0 的機率」p_low，<b>這是決策的主要依據</b>"],
    ["forecast/pond.py<br/>walk_forward()", "滾動驗證（4 段：7/15、8/01、8/16、9/01 起）", "驗證方法", "每段只用之前的資料訓練，避免偷看未來"],
    ["forecast/pond.py<br/>probe_rul()", "線性趨勢外推＋logistic", "統計", "探頭剩餘可用時間與故障機率"],
    ["state/pond.py", "三探頭互比、加權 WQI", "規則", "可信度、融合值、燈號（不是機器學習，但決策要用）"],
    ["backtest/closed_loop.py", "網格搜尋 α、β", "<b>再學習</b>", "在 7/15–7/31 找成本最低的參數，8/01 之後驗證，寫回 decide/params.json"],
], [32 * mm, 62 * mm, 24 * mm, 56 * mm], style=tiny))

s.append(P("3.2 決策引擎 decide/engine.py：decide(state, diagnoses, forecast)", h2))
s.append(P("輸入狀態辨識、異常診斷、趨勢預測三個結果，依下列規則由上而下產生決策，再依優先級排序：", base))
s.append(Spacer(1, 3))
s.append(table([
    ["情境", "觸發條件", "決策", "執行模式"],
    ["A. 系統失效", "主機斷線，或三支 DO 探頭都不可信", "增氧機維持（或啟動）運轉直到資料恢復；派人檢查感測主機", "<b>Fallback</b>（PLC 安全連鎖）"],
    ["B. 危急", "融合 DO &lt; 2.5", "增氧機未開→立即啟動 3 小時；已開→啟動備用機或注水；暫停投餵", "自動執行／人工確認"],
    ["C. <b>預測性增氧</b>", "<b>p_low &gt; α</b>（6 小時內低溶氧機率），或 DO &lt; 3.0", "提前啟動增氧機 3 小時；已開則建議備用機並延後投餵", "<b>已驗證→自動執行</b>，否則人工確認"],
    ["D. 節能", "增氧機運轉、DO ≥ 4.5、p_low &lt; β、尖峰時段 9–21 時", "暫停增氧機 2 小時（節省約 1.52 度）", "人工確認"],
    ["E. 設備異常", "診斷到增氧機功率偏低（可信度 ≥ 0.5）", "派維修技師現場檢修，備品葉輪、軸承", "人工確認"],
    ["F. 感測器維護", "診斷到探頭失效或漂移（可信度 ≥ 0.5）", "清洗並校正／檢查或更換；DO 探頭 24 小時內、其他 3 天內", "人工確認"],
    ["G. 預防性維護", "探頭 48 小時內故障機率 ≥ 0.7", "在超出容許差前預防性校正", "人工確認"],
    ["（無事）", "以上都沒觸發", "維持現狀，下一小時重新評估", "自動執行"],
], [26 * mm, 50 * mm, 66 * mm, 32 * mm], style=tiny))
s.append(Spacer(1, 4))
s.append(note("<b>AI 決策的核心在情境 C：</b>一般 SCADA 是「DO 跌破門檻才開機」，這一版改成「預測 6 小時內跌破的機率超過 α 就提前開機」。"
              "α 由回測再學習決定：目前 decide/params.json 為 <b>α = 0.1、β = 0.02、validated = true</b>（驗證期成本 20,536，低於所有基準），"
              "所以預測性增氧被升級為<b>自動執行</b>。若驗證沒通過，同一決策會降為人工確認。", TEAL, LIGHT))

s.append(P("3.3 決策輸出：標準決策資料與工單", h2))
s += bl([
    "<b>9 欄標準決策資料</b>（企業規格）：設備、動作、時間、幅度、理由、預期效果、風險、人工確認、Fallback；另附類別（行動控制／管理優先）、執行模式、優先級、能耗、編號。",
    "<b>理由欄寫出依據</b>：例如「預計 3 小時後低於門檻；預測 1／3／6 小時 DO 為 …；3 支可信探頭一致」，讓人看得出 AI 為什麼這樣決定。",
    "<b>工單</b>（decide/workorder.py）：需要人處理的決策轉成工單，含優先級、派工對象、備品、能耗與電費（以每度 4 元估計）。",
    "<b>LLM 白話（選用）</b>：設定環境變數 JNC_LLM_MODEL 後，經本機 Ollama 把工單改寫成白話；<b>數字守門員</b>檢查 LLM 輸出的每個數字都要出現在原始決策中，否則退回範本。預設不啟用，判斷完全由規則與模型決定。",
    "<b>三個問題</b>（three_questions）：把結果濃縮成「現在發生什麼？接下來會怎樣？現在該做什麼？」顯示在平台最上方。",
])
s.append(Spacer(1, 4))
s.append(fig("forecast_example.png", "圖 2　溶氧 3 小時預測範例（樣本外）：綠線為 3 小時前的 AI 預測、虛線為持續法；同一模型也預測 1–6 小時，作為預測性增氧的依據", W * 0.92))

# ---------- 四、端到端 ----------
s.append(P("四、端到端流程：某一小時發生什麼事", h1))
s.append(P("common/pipeline.py 的 PondPipeline.step(時間) 依序執行（平台每切換一小時就跑一次）：", base))
s.append(Spacer(1, 3))
s.append(table([
    ["步驟", "程式", "輸入", "輸出"],
    ["1 取資料", "pipeline.step()", "當下以前 96 小時的清洗後資料", "時間視窗"],
    ["2 狀態辨識", "state()", "視窗", "WQI、燈號、融合 DO、各探頭可信度、增氧機狀態、是否斷線"],
    ["3 異常診斷", "diagnose()", "視窗＋逐小時診斷表", "診斷清單：類型、對象、原因、證據、可信度、已持續幾小時"],
    ["4 趨勢預測", "forecast()", "視窗＋該時段的滾動模型", "1–6 小時 DO、p_low、超標時間、探頭剩餘可用時間"],
    ["5 決策", "decide()", "前三項＋params.json", "依優先級排序的標準決策資料"],
    ["6 工單", "work_orders()", "決策", "工單（派工、備品、能耗、說明）"],
    ["7 回答三問", "three_questions()", "全部", "現在／接下來／該做什麼 三句話"],
], [24 * mm, 32 * mm, 52 * mm, 66 * mm], style=tiny))
s.append(Spacer(1, 4))
s.append(P("第一次啟動要訓練 4 段滾動模型（約 2 分鐘），結果存在 .cache/，之後直接讀快取。", small))
s.append(fig("closed_loop_example.png", "圖 3　閉環範例（backtest/closed_loop.py）：AI 決策提前開機後，模擬的 DO 與歷史實際的比較", W * 0.92))

# ---------- 五、平台 ----------
s.append(P("五、Streamlit 平台（app/streamlit_app.py）", h1))
s.append(table([
    ["區塊", "內容"],
    ["側欄：01 IoT 感測・資料回放", "回放時間拉桿、前後一小時、自動播放；5 個展示情境：預測性增氧（7/19 18:00）、危急低溶氧（7/20 03:00）、pH1 漂移＋DO2 劣化（8/30 14:00）、DO3 失效與氣象站凍結（9/20 06:00）、水質正常（9/10 13:00）；顯示目前 α、β 與是否已驗證"],
    ["頂部", "五階段色塊（各階段即時摘要）＋ 三個問題的回答"],
    ["分頁：決策與工單", "每筆決策卡顯示 9 欄；人工確認的決策有「核准／駁回」按鈕，其他有「送 SCADA 執行」；下方是工單表"],
    ["分頁：狀態辨識", "燈號、WQI、融合 DO、增氧機運轉與功率、各探頭可信度長條圖"],
    ["分頁：異常診斷", "依可信度排序的診斷卡（原因、證據、持續時間）；可信度 &lt; 0.5 只當資料品質提示"],
    ["分頁：趨勢預測", "低溶氧機率、預計超標時間、探頭故障機率；過去 48 小時＋未來 6 小時預測曲線與實際值；探頭剩餘可用時間表"],
    ["分頁：執行回饋", "核准或執行後的紀錄，比較「歷史實際」與「模擬執行後」3 小時後的 DO"],
    ["分頁：成效驗證", "顯示 backtest/report.md 重點與圖表"],
], [44 * mm, W - 44 * mm], style=tiny))
s.append(Spacer(1, 4))
s.append(P("啟動方式（在 JNC-AIoT 資料夾）：<font name='H'>.venv/bin/streamlit run app/streamlit_app.py</font>，瀏覽器開 http://localhost:8501。"
           "回測報告由 <font name='H'>.venv/bin/python scripts/run_backtest.py</font> 重新產生。", base))

# ---------- 六、成效 ----------
s.append(P("六、成效驗證（backtest/）", h1))
s.append(P("6.1 異常診斷", h2))
s += bl([
    "<b>已知事件 9／9 偵測到</b>：斷線 2 次、DO2／DO3／pH1／SC1 漂移、DO3 失效、OA4 氣象站凍結（事件來自 notes/eda/events.md 的資料整理，屬弱標籤）。",
    "<b>合成故障</b>：5 個隨機種子共 43 次注入，Recall 88%、類型正確率 100%、每週誤報 3.3 次；漂移最難（Recall 70%，延遲中位數 23 小時），掉 0 與斷線 100%。",
    "<b>Precision 只有 36%</b>，主因是 SC 探頭常有短暫跳動；因此可信度 &lt; 0.5 的診斷只當提示、不派工。",
])
s.append(P("6.2 溶氧預測與提前預警", h2))
s.append(table([
    ["α", "預警率", "平均提前", "每週誤報"],
    ["0.1", "92%", "5.8 小時", "2.1"],
    ["0.2", "82%", "5.4 小時", "0.8"],
    ["0.3", "77%", "4.9 小時", "0.7"],
    ["0.5", "54%", "4.9 小時", "0"],
], [30 * mm, 40 * mm, 40 * mm, 40 * mm]))
s.append(P("α 越小越早告警、誤報也越多；再學習以成本（低溶氧、危急時數與電費）選出 α = 0.1。", small))
s.append(P("6.3 閉環成效（工程估計：增氧效果 0.13 mg/L/h、衰減 0.73）", h2))
s.append(table([
    ["策略", "低溶氧時數", "危急時數", "用電（度）", "無效告警時數"],
    ["歷史實際", "290", "115", "1,324", "0"],
    ["固定門檻（原始探頭，一般 SCADA）", "150", "15", "1,766", "286"],
    ["固定門檻（AI 排除故障探頭後）", "142", "15", "1,569", "0"],
    ["<b>AI 決策</b>", "<b>133</b>", "<b>15</b>", "<b>1,566</b>", "<b>9</b>"],
], [62 * mm, 28 * mm, 26 * mm, 28 * mm, 30 * mm]))
s.append(Spacer(1, 4))
s.append(fig("tradeoff.png", "圖 4　用電與低溶氧時數的取捨（backtest/report.md）", W * 0.8))
s.append(note("<b>報告本身的解讀：</b>AI 最大的價值是「先判斷探頭可不可信」，避免一般 SCADA 讀到故障探頭的 0 值而一直誤開備用機與告警；"
              "預測讓告警提早約 5 小時。在同樣用電量下，AI 只比調好的固定門檻略好，因為這個池子的低溶氧是長時間緩慢發生，<b>報告明確寫不誇大這一點</b>。"))

# ---------- 七、限制 ----------
s.append(P("七、限制與待確認", h1))
s += bl([
    "<b>IoT 是回放不是即時連線</b>：資料來自銘祥提供的歷史 CSV；硬體與真正的 SCADA／PLC 串接不在這一版範圍。",
    "<b>沒有維修紀錄</b>（待問 Q1）：異常偵測只能用已知事件與合成故障評估。",
    "<b>增氧機台數、池子面積未知</b>（Q5）：閉環效果依工程估計；改用資料估計（0.0197 mg/L/h）時，各策略差距很小（低溶氧 267 vs 歷史 290 小時）。",
    "<b>備用增氧機、暫停投餵</b>在資料中沒有對應欄位，模擬時把備用機視為與主機同效果。",
    "<b>門檻</b>（DO 3.0、危急 2.5、充足 4.5）依此池資料分布訂定，物種與企業標準待確認；電價每度 4 元為估計。",
    "<b>預測模型</b>：本次回測用的是 HistGradientBoosting（本機缺 libomp 無法載入 LightGBM），兩者同為 GBDT。",
    "<b>只做魚塭</b>：河川、羊舍等擴充場域還沒有程式。",
])

# ---------- 八、檔案 ----------
s.append(P("八、新增與修改的檔案", h1))
s.append(table([
    ["類別", "檔案"],
    ["IoT 感測與資料", "common/replay.py、common/clean.py、common/baseline.py、common/events.py、common/config.py"],
    ["AI 分析", "state/pond.py、diagnose/pond.py、forecast/pond.py"],
    ["AI 決策", "decide/engine.py、decide/workorder.py、decide/params.json"],
    ["串接與平台", "common/pipeline.py、app/streamlit_app.py、../.claude/launch.json（平台預覽設定，port 8501）"],
    ["成效驗證", "backtest/closed_loop.py、backtest/detection.py、backtest/effect.py、backtest/report.md、backtest/figures/（4 張圖）、scripts/run_backtest.py"],
    ["資料整理", "notes/eda/（7 個場域各 1 頁＋圖、events.md 已知事件表）、scripts/build_eda_figures.py"],
    ["測試", "tests/test_pipeline.py：斷線標記、狀態介面、壞探頭被排除、回放器不偷看未來、注入故障可被偵測、決策 9 欄與執行模式、數字守門員"],
    ["文件", "HANDOFF.md、README.md、docs/architecture.md（第 4 節改為已實作的介面與程式對照）、docs/progress.md、各模組 README"],
], [30 * mm, W - 30 * mm], style=tiny))

doc.build(s)
print("ok", OUT)
