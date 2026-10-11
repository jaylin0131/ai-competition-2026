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
    c.drawString(18 * mm, 10 * mm, "2026 全國 AI 專題創意競賽｜企業命題 AI 應用組｜銘祥科技 6 人分工規劃")
    c.drawRightString(192 * mm, 10 * mm, f"{d.page}")
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.2)
    c.line(18 * mm, 285 * mm, 192 * mm, 285 * mm)
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm,
                      title="銘祥科技命題 6 人分工規劃", author="參賽團隊")
doc.addPageTemplates([PageTemplate(frames=[Frame(18 * mm, 16 * mm, 174 * mm, 265 * mm, id="f")],
                                   onPage=on_page)])
W = 174 * mm
s = []

# ---------- 封面區 ----------
s += [Spacer(1, 4), P("銘祥科技「AIoT 預測維護與異常診斷」", title),
      P("作品方向、技術內容與 6 人分工規劃", sub), Spacer(1, 4),
      P("2026 全國 AI 專題創意競賽｜企業命題類 AI 應用組", small), Spacer(1, 8)]
s.append(table([
    ["項目", "內容"],
    ["報名截止", "<b>2026/12/01（二）23:59:59</b>；隊內截止 <b>11/28（六）</b>"],
    ["初賽", "<b>12/11（五）</b>，看作品說明書加線上展示（上課日，要先排好誰上線）"],
    ["決賽", "<b>12/19（六）</b>，國立臺南大學中山館現場展示並頒獎，至少 1 名隊員到場"],
    ["企業獎勵", "實習或工讀名額 2–3 位以上，時薪 210 元以上或月薪 38,000 元以上"],
    ["紅線", "禁用中國或中資的模型與工具（DeepSeek、Qwen 及其微調版）；作品不得已商品化；"
             "簡報、海報、影片不露出校名、系所、指導老師"],
], [28 * mm, W - 28 * mm]))
s.append(Spacer(1, 6))
s.append(note("<b>資料來源：</b>《2026 全國 AI 專題創意競賽參賽攻略手冊》、大會官網與銘祥科技企業命題頁。"
              "規則若與主辦單位最新公告不同，一律以官網為準。<br/>"
              "<b>要向主辦單位確認：</b>企業說會提供「維修紀錄」，但目前 7 個 CSV 看起來沒有獨立的維修紀錄檔；"
              "官網也沒有公布各評分項目的配分比例。聯絡信箱：aittc.nutn@gmail.com"))

# ---------- 一、作品定位 ----------
s.append(P("一、作品定位", h1))
s.append(table([
    ["項目", "內容"],
    ["作品名稱", "<b>魚塭守門員</b>，養殖水質預警與增氧決策系統"],
    ["主要資料", "專家系統.csv：魚塭三組探頭（pH、ORP、SC、DO）、水溫、微氣候、水位、設備用電，共 2,698 筆、35 欄"],
    ["加分擴充", "把同一套流程套到三爺宮溪或羊舍資料上，展示「換場域只要換設定檔」"],
    ["一句話賣點", "不只告訴你魚塭要缺氧了，還會幫你開增氧機，並告訴你哪支探頭該校正。"],
], [28 * mm, W - 28 * mm]))
s.append(Spacer(1, 6))
s.append(P("企業期待：透過 AI 把 IoT 大數據轉換成「可執行的決策」。作品要回答三個問題，只做到預測不夠，"
           "<b>「行動」才是加分關鍵</b>。", base))
s.append(Spacer(1, 4))
s.append(table([
    ["企業的三個問題", "我們要做的功能", "程度"],
    ["<b>現在發生什麼？</b>", "物理規則檢查，加上 Isolation Forest 異常偵測", "必做"],
    ["", "<b>異常診斷分類</b>：只有單支探頭異常 → 感測器問題；三支一起變 → 水質真的變差", "必做（核心亮點）"],
    ["", "設備異常：增氧機有耗電但 DO 沒回升", "加分"],
    ["<b>接下來會怎樣？</b>", "用 LightGBM 預測 1、3、6 小時後的 DO 與 pH", "必做"],
    ["", "提前預警，例如「預估 X 小時後 DO 跌破門檻」", "必做"],
    ["<b>現在該做什麼？</b>", "規則層決策，例如開哪台增氧機、開多久", "必做"],
    ["", "用<b>預測值</b>觸發決策，取得提前量", "必做"],
    ["", "用 LLM 把判斷結果寫成工單和推播訊息（只能用非中資模型）", "加分"],
    ["", "實體閉環：繼電器啟動打氣馬達，結果再回饋給系統", "必做（決賽重點）"],
], [32 * mm, 110 * mm, 32 * mm],
    extra=[("SPAN", (0, 1), (0, 3)), ("SPAN", (0, 4), (0, 5)), ("SPAN", (0, 6), (0, 9)),
           ("BACKGROUND", (0, 1), (-1, -1), colors.white)]))

# ---------- 二、系統架構 ----------
s.append(P("二、系統架構（每層對應負責人）", h1))
layers = [
    ["層", "內容", "負責人"],
    ["感測層", "CSV 資料回放器＋真實水溫、TDS 感測器（ESP32）；回放時可注入異常做示範", "P2 電機"],
    ["通訊層", "Wi-Fi → MQTT（Mosquitto）→ 時序資料庫（InfluxDB）→ 推播", "P3 通訊"],
    ["AI 層", "資料清理 → 異常偵測與診斷（P5）→ 預測（P6）", "P5、P6"],
    ["決策層", "規則表＋預測觸發 → LLM 寫工單（P6）", "P4 自動化"],
    ["行動層", "繼電器 → 打氣馬達｜儀表板｜LINE 或 Telegram 推播", "P4、P3"],
    ["閉環回饋", "馬達啟動後 DO 有沒有回升 → 回到 AI 層判斷", "P4"],
]
layer_colors = ["#D9EAD3", "#CFE2F3", "#FCE5CD", "#F4CCCC", "#D9D2E9", "#EEEEEE"]
s.append(table(layers, [24 * mm, 118 * mm, 32 * mm],
               extra=[("BACKGROUND", (0, i + 1), (0, i + 1), colors.HexColor(c)) for i, c in enumerate(layer_colors)]))
s.append(Spacer(1, 6))
s.append(note("<b>為什麼要有資料回放器？</b>真實的 DO 感測器很貴，大一團隊不必買。寫一支程式把銘祥的 CSV 依時間順序一筆一筆送進 MQTT，"
              "假裝是現場即時資料，再接便宜的水溫或 TDS 感測器做實機展示。這樣決賽就能看到「資料即時流進來 → AI 即時判斷 → 馬達即時動作」。",
              TEAL, LIGHT))

# ---------- 三、6 人分工 ----------
s.append(P("三、6 人分工", h1))
s.append(table([
    ["代號", "角色", "建議人選", "一句話職責"],
    ["P1", "隊長／專案經理，兼文件總編", "最有時間、最會溝通的人", "進度、報名、說明書、影片、海報與簡報"],
    ["P2", "感測與電力", "電機系", "硬體、感測器、用電分析、異常注入"],
    ["P3", "資料管線與雲端", "通訊系", "回放器、MQTT、資料庫、儀表板、推播"],
    ["P4", "決策引擎與控制", "智慧自動化系", "規則表、繼電器閉環、實機模型、決策模擬"],
    ["P5", "AI（一）：清理與異常診斷", "資料或程式較強者", "現在發生什麼"],
    ["P6", "AI（二）：預測與 LLM 工單", "資料或程式較強者", "接下來會怎樣、寫成人話"],
], [14 * mm, 52 * mm, 40 * mm, 68 * mm]))

s += person("P1", "隊長／專案經理，兼文件總編", [
    ("負責", "報名與文件、進度表、每週會議與紀錄、聯絡老師和主辦單位、作品說明書總編、海報與簡報（匿名版）、影片腳本和剪輯"),
    ("交付物", ["每週進度表與會議紀錄（每次 5 行以內）", "說明書，依大會範本", "3 分鐘影片",
                "決賽海報和簡報", "10 題 Q&amp;A 題庫"]),
    ("工具", "Google 雲端、HackMD、Canva 或 Figma、剪輯軟體"),
    ("備註", "11/15 以前的空檔協助 P5 做 7 個資料集的資料初探（每個 1 頁）。這樣自己也懂技術，答得出評審的問題。"),
])
s += person("P2", "電機：感測與電力", [
    ("負責", "硬體與感測器、資料回放器的 ESP32 端、用電資料分析"),
    ("交付物", ["ESP32 讀 DS18B20 水溫和 TDS（或 pH）模組，每 N 秒上傳到 MQTT",
                "感測器校正紀錄，例如 pH 用校正液",
                "<b>用電分析：</b>從專家系統的電壓、電流、功率欄位判斷增氧機什麼時候開；分析開機後 DO 有沒有回升，找出「耗電卻沒效果」的時段，標成設備異常",
                "資料回放器裡的<b>異常注入功能</b>，例如讓某支探頭突然漂移，用來做現場示範"]),
    ("工具", "Arduino IDE 或 MicroPython、pandas"),
    ("成果數字", "偵測到幾次增氧機運轉事件、設備異常事件數"),
])
s += person("P3", "通訊：資料管線與雲端", [
    ("負責", "資料回放器的 Python 端、MQTT、資料庫、推播、儀表板"),
    ("交付物", ["資料回放器：把 CSV 依時間順序丟進 MQTT，可加速播放（例如 1 秒代表 1 小時）",
                "Mosquitto broker 和 InfluxDB",
                "儀表板（Streamlit 或 Grafana）：顯示即時數值、預測曲線、異常標記、決策紀錄，警示時變色",
                "手機推播（LINE Messaging API 或 Telegram Bot；LINE Notify 已停止服務）",
                "斷線處理：ESP32 本地保留門檻控制，恢復連線後補傳"]),
    ("工具", "Python paho-mqtt、Node-RED（可選）、Streamlit"),
    ("成果數字", "端到端延遲（從資料進來到推播送達幾秒）、斷線補傳成功率"),
])
s += person("P4", "智慧自動化：決策引擎與控制", [
    ("負責", "決策規則表、控制邏輯、實機模型"),
    ("交付物", ["<b>決策規則表</b>，例如：<br/>"
                "‧ 預測 3 小時後 DO 低於門檻，且增氧機目前未運轉 → 啟動 1 號增氧機 2 小時<br/>"
                "‧ 只有單支探頭異常 → 產生校正工單，不啟動增氧機<br/>"
                "‧ 三支探頭一起變差 → 啟動增氧機，並發出橘色或紅色警報<br/>"
                "‧ 增氧機運轉 1 小時後 DO 仍沒回升 → 產生設備檢修工單",
                "警報分級（綠、黃、橘、紅）和冷卻時間，避免一直重複推播",
                "繼電器加打氣馬達的控制，以及閉環回饋（動作後確認數值變化）",
                "實機模型組裝：水族箱或收納盒、感測器、馬達",
                "<b>決策模擬：</b>拿歷史資料模擬「照系統建議操作」和「不採取行動」，比較低溶氧時數差多少"]),
    ("工具", "Python、ESP32 控制繼電器、Node-RED（可選）"),
    ("成果數字", "低溶氧時數減少百分比、誤報次數／週"),
])
s += person("P5", "AI（一）：資料清理與異常診斷（現在發生什麼）", [
    ("交付物", ["共用的讀檔函式 load_jnc()：處理 UTF-16、Tab 分隔、工地微氣候要跳過前 2 列、欄名縮短、合併日期和小時，給全隊共用",
                "<b>物理規則檢查：</b>DO &lt; 0、pH 等於 0 或不在 0–14、EC 等於 0、時間軸缺漏（判定為斷線）",
                "<b>三探頭交叉比對：</b>計算三支 pH 和 DO 的差異（spread），找出漂移的是哪一支",
                "Isolation Forest 異常偵測",
                "<b>診斷分類器</b>，把異常分成：感測器故障、感測器漂移、真實水質事件、斷線",
                "<b>評估：</b>用 P2 注入的合成異常計算 Precision 和 Recall，再人工抽查真實異常"]),
    ("工具", "pandas、scikit-learn"),
    ("基準", "和「固定門檻告警」比較"),
    ("成果數字", "感測器異常辨識率、Precision、Recall、誤報減少多少"),
])
s += person("P6", "AI（二）：預測與 LLM 工單（接下來會怎樣）", [
    ("交付物", ["特徵工程：lag 1、2、3、6、12、24 小時，時段（DO 有日夜週期），水溫，氣溫，系統功率",
                "LightGBM 預測 1、3、6 小時後的 DO 和 pH。<b>訓練和測試要依時間先後切分</b>，前 80% 訓練、後 20% 測試",
                "預警評估：平均提早幾小時預警",
                "<b>LLM 說明層：</b>輸入決策結果和判斷依據，輸出工單和推播文字。LLM 只負責寫成人話，判斷由規則和模型決定",
                "<b>加分：</b>把同一套流程套到三爺宮溪或羊舍資料，用設定檔切換場域"]),
    ("工具", "LightGBM；LLM 用 Ollama 跑 Gemma、Llama、Phi、TAIDE、Breeze，或呼叫 Gemini、OpenAI、Claude 的 API。"
             "下載模型前要檢查 base model 不是 Qwen 系列"),
    ("基準", "persistence（假設下一刻跟現在一樣）"),
    ("成果數字", "MAE、RMSE（mg/L）、預測曲線和實際曲線的對照圖、平均提早預警時數"),
])

# ---------- 四、介面約定 ----------
s.append(PageBreak())
s.append(P("四、介面約定（第一週就要定好）", h1))
s.append(P("6 個人要能同時開發，先把資料格式定下來。誰的模組還沒好，其他人就先用假資料測試。", base))
s.append(Spacer(1, 4))
s.append(table([
    ["MQTT topic", "發送者 → 接收者", "JSON 內容（範例）"],
    ["jnc/pond1/sensor", "P2、P3 回放器 → P5、P6",
     P('{"ts":"2026-07-01T02:00", "pH1":7.8, "pH2":7.9, "pH3":7.2, "DO1":3.1, ..., "power":1520}', mono)],
    ["jnc/pond1/anomaly", "P5 → P4", P('{"ts":..., "type":"sensor_drift", "sensor":"pH3", "score":0.87}', mono)],
    ["jnc/pond1/forecast", "P6 → P4、P3", P('{"ts":..., "target":"DO1", "h1":3.0, "h3":2.6, "h6":2.4}', mono)],
    ["jnc/pond1/decision", "P4 → P3、P6",
     P('{"ts":..., "level":"orange", "actions":["aerator1_on_2h","calibrate_pH3"], "reasons":[...]}', mono)],
    ["jnc/pond1/actuator", "P4 → ESP32", P('{"aerator1":"on"}', mono)],
    ["jnc/pond1/notify", "P6（LLM 文字）→ P3 推播", P('{"title":"A池溶氧偏低風險", "body":"..."}', mono)],
], [34 * mm, 38 * mm, 102 * mm]))
s.append(Spacer(1, 6))
s.append(P("<b>GitHub 資料夾建議：</b>data/、common/（load_jnc）、replay/、anomaly/、forecast/、decision/、dashboard/、firmware/、docs/。"
           "每人主要改自己的資料夾，大家的 commit 紀錄就是「團隊協作」的證據。", base))

# ---------- 五、時程 ----------
s.append(P("五、每人時程", h1))
sched = [
    ["週次", "P1 隊長", "P2 電機", "P3 通訊", "P4 自動化", "P5 異常", "P6 預測"],
    ["10/08–10/21", "組隊、下載範本、進度表", "2 個資料集的資料初探、列出零件清單", "2 個資料集的資料初探、定 MQTT 規格",
     "1 個資料集的資料初探、規則表草稿", "<b>load_jnc 共用函式</b>、專家系統的資料初探", "1 個資料集的資料初探、建立預測基準"],
    ["10/22–11/04", "說明書架構、匿名版模板", "零件到貨後單獨測試、用電分析", "回放器和 broker 上線",
     "規則表第一版、繼電器測試", "物理規則、Isolation Forest 第一版", "LightGBM 第一版和 MAE"],
    ["<b>10/31 檢查點</b>", "檢查各組進度", "感測器可以讀值", "回放的資料能流到資料庫",
     "繼電器能被 MQTT 控制", "有異常偵測數字", "有預測數字"],
    ["11/05–11/15", "會議紀錄、拍攝素材", "異常注入、組裝實機", "儀表板、推播",
     "決策引擎串上預測和異常", "診斷分類、Precision/Recall", "預警時數、LLM 工單"],
    ["<b>11/15 全員實體整合</b>", "<b>閉環打通，錄第一支 demo 影片（全員）</b>", "", "", "", "", ""],
    ["11/16–11/28", "<b>說明書定稿、影片剪輯、11/28 報名</b>", "寫說明書的硬體章節", "寫通訊章節",
     "寫決策章節和模擬結果", "寫異常章節和比較表", "寫預測章節、加分場域"],
    ["12/02–12/10", "線上展示演練、Q&amp;A", "穩定性和備品", "備援錄影 demo", "修 bug", "修 bug", "修 bug"],
    ["12/12–12/18", "海報、簡報、打包清單", "硬體打包", "確認網路熱點", "實機彩排", "彩排 Q&amp;A", "彩排 Q&amp;A"],
]
cw = [24 * mm] + [25 * mm] * 6
s.append(table(sched, cw, style=ParagraphStyle("tiny", parent=small, fontSize=7.8, leading=11),
               extra=[("SPAN", (1, 5), (-1, 5)), ("BACKGROUND", (0, 3), (-1, 3), NOTE_BG),
                      ("BACKGROUND", (0, 5), (-1, 5), NOTE_BG)]))
s.append(Spacer(1, 4))
s.append(P("期中考大概在 11 月上中旬，剛好壓在開發期，考試週只排輕量工作，例如寫說明書草稿、整理圖表。", small))

# ---------- 六、成果數字 ----------
s.append(PageBreak())
s.append(P("六、說明書第一頁要放的成果數字", h1))
s.append(table([
    ["數字", "負責人", "比較基準"],
    ["預測誤差（DO 的 MAE，單位 mg/L）", "P6", "persistence"],
    ["平均提早預警時數", "P6 + P4", "只看即時值的告警"],
    ["感測器異常辨識率（Precision / Recall）", "P5", "固定門檻"],
    ["低溶氧時數減少百分比", "P4", "不採取行動"],
], [90 * mm, 30 * mm, 54 * mm]))
s.append(Spacer(1, 6))
s.append(note("評審最常問：「你的 AI 比不用 AI 好多少？」每個功能都要配一個最簡單的基準，再展示我們的方法好了多少百分比。"
              "這些數字一定要是真的跑出來的，不要寫預估值。"))

# ---------- 七、決賽 demo ----------
s.append(P("七、決賽 demo 流程（所有人都要上場）", h1))
s.append(table([
    ["步驟", "負責人", "內容"],
    ["1", "P3", "啟動回放，儀表板開始跑資料"],
    ["2", "P2", "現場注入「pH3 漂移」"],
    ["3", "P5", "說明系統判斷為感測器問題，所以只開校正工單，不開增氧機"],
    ["4", "P2", "再注入三支探頭一起下降的情況"],
    ["5", "P6", "說明預測顯示「3 小時後 DO 將跌破門檻」"],
    ["6", "P4", "說明決策引擎啟動，繼電器打開、打氣馬達轉動"],
    ["7", "P3", "手機收到 LLM 寫的工單"],
    ["8", "P1", "收尾：比較表和對企業的效益"],
], [16 * mm, 22 * mm, 136 * mm]))

# ---------- 八、實機零件 ----------
s.append(P("八、實機展示零件（參考）", h1))
s.append(table([
    ["零件", "用途", "參考價格"],
    ["ESP32 開發板 ×2", "一片接感測器、一片控制繼電器（或一片包辦）", "約 $200–350／片"],
    ["DS18B20 防水水溫探頭", "真實水溫量測", "約 $100"],
    ["TDS 或 pH 類比模組", "真實水質量測（pH 模組需校正液）", "約 $300–900"],
    ["繼電器模組＋水族打氣馬達", "「增氧機」的縮小版，AI 判斷後自動啟動", "約 $300"],
    ["小水族箱或透明收納盒", "魚塭模型", "約 $200"],
    ["筆電或樹莓派", "MQTT broker、AI 模型、儀表板", "現有設備"],
], [50 * mm, 90 * mm, 34 * mm]))
s.append(P("價格為大約範圍，以實際購買為準；採購前先問指導老師實驗室是否已有零件。", small))

# ---------- 九、技術提醒 ----------
s.append(P("九、技術提醒與常見地雷", h1))
s += bl([
    "<b>讀檔：</b>銘祥的 CSV 是 Excel 匯出的 UTF-16 編碼、Tab 分隔檔，要用 pd.read_csv(path, sep=\"\\t\", encoding=\"utf-16\")；工地微氣候要跳過前 2 列。",
    "<b>時間序列不能隨機切分：</b>一律前 80% 訓練、後 20% 測試，並在說明書寫明。",
    "<b>題目不要太大：</b>先把專家系統一個場域、一條閉環做完整，再談擴充。",
    "<b>11/15 一定要有能動的 demo</b>，哪怕很陽春。",
    "<b>中資模型：</b>下載任何模型前檢查 model card 的 base model。",
    "<b>匿名：</b>簡報、海報、影片一律使用匿名版本。",
    "<b>備援：</b>決賽帶備品（ESP32、杜邦線、延長線、熱點）和備援影片，現場可立即切換。",
    "<b>LLM 會不會亂講：</b>LLM 只負責寫成人話，判斷由規則和模型決定，輸出附判斷依據。",
])

doc.build(s)
print("ok", OUT)
