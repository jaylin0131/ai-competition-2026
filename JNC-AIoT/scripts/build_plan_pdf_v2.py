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
    c.drawString(18 * mm, 10 * mm, "2026 全國 AI 專題創意競賽｜企業命題 AI 應用組｜銘祥科技 AI 分析與 6 人分工規劃（v2）")
    c.drawRightString(192 * mm, 10 * mm, f"{d.page}")
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.2)
    c.line(18 * mm, 285 * mm, 192 * mm, 285 * mm)
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm,
                      title="銘祥科技命題 AI 分析與 6 人分工規劃 v2", author="參賽團隊")
doc.addPageTemplates([PageTemplate(frames=[Frame(18 * mm, 16 * mm, 174 * mm, 265 * mm, id="f")],
                                   onPage=on_page)])
W = 174 * mm
s = []

mono2 = ParagraphStyle("m2", parent=base, fontSize=8, leading=11.5)
tiny = ParagraphStyle("tiny", parent=small, fontSize=7.8, leading=11)

# ---------- 封面 ----------
s += [Spacer(1, 4), P("銘祥科技「AIoT 預測維護與異常診斷」", title),
      P("AI 分析方向與 6 人分工規劃（v2：依企業命題頁重新整理）", sub), Spacer(1, 4),
      P("2026 全國 AI 專題創意競賽｜企業命題類 AI 應用組", small), Spacer(1, 8)]
s.append(note("<b>這一版改了什麼：</b>企業命題頁寫明「IoT 大數據收集 → 銘祥企業提供」、「AI 往下做數據分析、辨識、預測、診斷 → 參賽團隊執行」。"
              "所以本版<b>不再自建感測器、ESP32、繼電器等硬體</b>，6 個人全部投入 AI 分析與決策。"
              "企業流程圖裡的「執行」由 SCADA／PLC 或人工負責，我們用<b>軟體模擬執行和歷史資料回測</b>來完成「結果回傳與成效驗證」這一段。",
              TEAL, LIGHT))
s.append(Spacer(1, 6))
s.append(table([
    ["項目", "內容"],
    ["報名截止", "<b>2026/12/01（二）23:59:59</b>；隊內截止 <b>11/28（六）</b>"],
    ["初賽", "<b>12/11（五）</b>，看作品說明書加線上展示"],
    ["決賽", "<b>12/19（六）</b>，國立臺南大學中山館現場展示並頒獎，至少 1 名隊員到場"],
    ["企業獎勵", "實習或工讀名額 2–3 位以上，時薪 210 元以上或月薪 38,000 元以上"],
    ["紅線", "禁用中國或中資的模型與工具（DeepSeek、Qwen 及其微調版）；作品不得已商品化；簡報、海報、影片不露出校名、系所、指導老師"],
], [28 * mm, W - 28 * mm]))

# ---------- 一、企業命題重點 ----------
s.append(P("一、企業命題重點（官網與流程圖整理）", h1))
s.append(table([
    ["分工", "內容", "誰負責"],
    ["1. 資料", "IoT 智慧感測大數據：感測器數據、設備數據、環境氣象數據、維修紀錄（7 個 CSV）", "<b>銘祥提供</b>"],
    ["2. AI", "數據分析、辨識、預測、診斷，回答三個問題，把資料轉成「可執行的決策」", "<b>參賽團隊</b>"],
], [22 * mm, 120 * mm, 32 * mm]))
s.append(P("企業流程圖：決策閉環", h2))
s.append(table([
    ["步驟", "企業圖中的說明", "我們怎麼做"],
    ["01 IoT 感測", "水質、設備、環境，取得現場即時事實", "企業提供（我們用 CSV 回放模擬即時資料）"],
    ["02 大數據", "清洗、儲存、關聯，建立歷史基準", "P2 資料工程"],
    ["03 AI 分析", "異常偵測、預測，診斷可能原因（辨識、預測、診斷）", "P3 狀態辨識、P4 異常診斷、P5 趨勢預測"],
    ["04 決策引擎", "結合規則與風險，選擇最佳行動（目標、規則、風險、成本）", "P6 決策引擎"],
    ["決策結果", "做什麼、何時做、做多少", "P6 輸出標準決策資料"],
    ["05 執行回饋", "人工／SCADA／PLC 執行，結果回傳與成效驗證，再學習", "軟體模擬執行＋歷史資料回測（P6、P5）"],
], [26 * mm, 76 * mm, 72 * mm]))
s.append(P("企業要的 AI 決策輸出（圖中「JNC 的 AI 決策輸出」）", h2))
s.append(table([
    ["輸出", "企業列出的內容", "回答哪個問題", "負責人"],
    ["狀態辨識", "WQI／GI、燈號、感測器可信度", "現在發生什麼？", "P3"],
    ["異常診斷", "可能原因、判斷證據、診斷可信度", "現在發生什麼？", "P4"],
    ["趨勢預測", "超標時間、設備故障機率", "接下來會怎樣？", "P5"],
    ["行動控制", "設備、動作、時間、幅度", "現在該做什麼？", "P6"],
    ["管理優先", "工單、派工、備品與能耗", "現在該做什麼？", "P6"],
], [24 * mm, 70 * mm, 40 * mm, 40 * mm]))
s.append(Spacer(1, 4))
s.append(table([
    ["企業規定的格式與原則", "內容"],
    ["標準決策資料（每筆決策都要有）", "設備／動作／時間／幅度／理由／預期效果／風險／人工確認／Fallback"],
    ["安全控制原則", "AI 提出決策 → SCADA 呈現、告警與管理流程 → PLC 保留安全連鎖與緊急控制"],
    ["執行模式分級", "低風險且已驗證：可自動執行｜高風險操作：人工確認｜系統失效：Fallback 安全規則"],
], [52 * mm, 122 * mm]))
s.append(Spacer(1, 4))
s.append(note("<b>這張圖等於企業給的規格書。</b>作品的輸出欄位、說明書章節、demo 畫面都直接對應這五項輸出和「標準決策資料」，評審和企業一看就知道我們有照命題做。"
              "<br/>「GI」在圖中沒有說明，建議寫信問主辦單位或企業它代表什麼指標。"))

# ---------- 二、資料盤點 ----------
s.append(P("二、資料盤點（實際讀取 7 個 CSV 確認）", h1))
s.append(table([
    ["資料集", "期間／筆數", "實際欄位", "可以做什麼", "定位"],
    ["專家系統（魚塭）", "6/1–9/28<br/>2,698 筆", "pH、ORP、SC、DO 各三支探頭；DO1 水溫；溫濕度、氣壓、熱指數、熱危害等級；風速風向；水位；用電（電壓、電流、功率、功因、頻率、度數）共 35 欄",
     "水質燈號、三探頭可信度、DO 預測、低氧預警、用電判斷增氧設備有沒有開與有沒有效", "<b>核心</b>"],
    ["三爺宮溪（河川站）", "1/1–5/1<br/>2,881 筆", "太陽能電壓／電流、充電電流、電池電量、電池電壓；pH、EC、DO、DO 飽和度、水溫及各探頭斜率",
     "污染事件 vs 感測器異常（DO 有負值、EC 有 0）、電池耗盡預測、探頭斜率判斷校正需求", "擴充"],
    ["羊舍", "7/8–8/13<br/>871 筆", "帆布、遮陽的張／收狀態；4 個編號致動器（07、08、04、03）；溫濕度、CO2、NH3、CH4、雨量、風速風向；成羊區、仔羊區 THI；成羊區加開／減開",
     "THI 熱緊迫預測、風扇與帆布建議。<b>有實際操作紀錄</b>，可以比對 AI 建議和現場實際操作", "擴充"],
    ["育成北側", "6/1–8/31<br/>387 筆", "空品＋設備健康：訊號強度、運轉時間、開機次數、送電時間、電池電壓、電壓、4G 訊號（CSQ）",
     "設備健康診斷：斷線、異常重開機、通訊品質劣化、故障機率", "加分"],
    ["育成一廠、東北角", "6/1–8/31<br/>2,204／2,026 筆", "風速風向、溫濕度、PM2.5、PM10、HCHO、CO、TVOC", "空品燈號、超標時間預測", "加分"],
    ["工地微氣候", "1/1–4/4<br/>2,219 筆", "風速風向、溫濕度、熱指數、危害等級、PM2.5、PM10、噪音", "工地熱危害、粉塵、噪音超標預警", "加分"],
], [26 * mm, 22 * mm, 56 * mm, 56 * mm, 14 * mm], style=tiny))
s.append(Spacer(1, 4))
s += bl([
    "所有檔案都是 <b>UTF-16、Tab 分隔、每小時一筆</b>；工地微氣候前 2 列不是資料，要跳過；育成北側的日期和小時有補零（2026/06/01、08），格式和其他檔不同。",
    "<b>7 個檔案裡都沒有獨立的「維修紀錄」欄位</b>，但企業命題寫了會提供，建議寫信問主辦單位（aittc.nutn@gmail.com）能不能補。有的話可以做真正的故障預測。",
    "專家系統<b>沒有增氧機開關欄位</b>，要從「CPM 系統總和功率」的跳升推斷設備什麼時候開。",
], small_b := ParagraphStyle("sb", parent=bullet, fontSize=8.8, leading=13))

# ---------- 三、作品定位 ----------
s.append(P("三、作品定位", h1))
s.append(table([
    ["項目", "內容"],
    ["作品名稱（暫定）", "<b>AIoT 決策大腦</b>：多場域預測維護與異常診斷平台（核心場域：魚塭守門員）"],
    ["一句話賣點", "同一套 AI 決策引擎，讀進銘祥的感測資料，就能告訴現場「現在怎麼了、接下來會怎樣、現在該做什麼」，並照企業的標準決策格式輸出。"],
    ["範圍", "<b>必做：</b>專家系統（魚塭）完整做完五項輸出與回測<br/>"
             "<b>建議：</b>三爺宮溪、羊舍，證明「換場域只要換設定檔」，對應銘祥的模組化架構<br/>"
             "<b>加分：</b>育成北側設備健康、三個空品站的燈號與超標預測"],
    ["成品形式", "① Streamlit 網頁平台（含資料回放、五項輸出卡片、人工確認按鈕、回測報告）<br/>"
                 "② 標準決策資料的 JSON 輸出，方便企業接到 SCADA<br/>③ 作品說明書與 3 分鐘影片"],
], [30 * mm, W - 30 * mm]))

# ---------- 四、系統架構 ----------
s.append(P("四、系統架構（純軟體）", h1))
layers = [
    ["層", "內容", "負責人"],
    ["資料層", "讀檔、清洗、時間對齊、資料字典、歷史基準（各時段正常範圍）、CSV 回放模擬器", "P2"],
    ["分析層", "狀態辨識（P3）｜異常診斷（P4）｜趨勢預測（P5）", "P3、P4、P5"],
    ["決策層", "目標、規則、風險、成本 → 選擇行動 → 標準決策資料 → 執行模式分級", "P6"],
    ["呈現層", "Streamlit 平台：即時燈號、診斷卡、預測曲線、決策卡、工單清單；LLM 把決策寫成白話", "P2、P6"],
    ["驗證層", "模擬執行與歷史回測：照 AI 建議做 vs 不做，低溶氧時數、能耗、誤報差多少 → 回饋調整門檻", "P6、P5"],
]
lc = ["#D9EAD3", "#CFE2F3", "#FCE5CD", "#D9D2E9", "#F4CCCC"]
s.append(table(layers, [22 * mm, 120 * mm, 32 * mm],
               extra=[("BACKGROUND", (0, i + 1), (0, i + 1), colors.HexColor(c)) for i, c in enumerate(lc)]))

# ---------- 五、五項輸出 × 場域 ----------
s.append(P("五、五項 AI 輸出在各場域的具體做法", h1))
s.append(table([
    ["輸出", "魚塭（專家系統，核心）", "河川站（三爺宮溪）", "羊舍", "設備健康（育成北側）"],
    ["狀態辨識", "自訂水質指標（DO、pH、水溫）＋綠黃橘紅燈號；三支探頭一致性算感測器可信度",
     "水質燈號；DO 負值、EC 為 0 判定為不可信", "THI 熱緊迫分級燈號", "設備狀態燈號（訊號、電壓）"],
    ["異常診斷", "單支異常 → 探頭故障或漂移；三支同步 → 真實水質事件；耗電但 DO 不回升 → 增氧設備異常；附證據與可信度",
     "污染事件 vs 感測器異常；斜率變化 → 需要校正", "NH3、CO2 異常；致動器狀態與環境不符", "斷線、異常重開機、4G 劣化"],
    ["趨勢預測", "1／3／6 小時後 DO、pH；<b>預估幾小時後 DO 跌破門檻</b>", "未來 24–72 小時電池電量、何時斷電", "未來數小時 THI", "未來 24 小時斷線或故障機率"],
    ["行動控制", "開哪台增氧設備、何時開、開多久", "降低回傳頻率省電、派員換電池", "開幾台風扇、帆布張或收", "遠端重啟、派員檢修"],
    ["管理優先", "校正、檢修工單排序；增氧能耗估算", "巡檢與換電池排程", "與實際操作紀錄比對", "備品與派工優先序"],
], [18 * mm, 52 * mm, 36 * mm, 34 * mm, 34 * mm], style=tiny))

# ---------- 六、6 人分工 ----------
s.append(PageBreak())
s.append(P("六、6 人分工", h1))
s.append(table([
    ["代號", "角色", "對應企業輸出", "建議人選"],
    ["P1", "隊長／專案經理＋文件展示", "整份作品對齊企業需求", "最有時間、最會溝通、文筆好的人"],
    ["P2", "資料工程＋平台整合", "02 大數據、平台", "通訊系（資料管線、平台）"],
    ["P3", "狀態辨識＋感測器可信度", "狀態辨識", "對水質、環境指標有興趣的人"],
    ["P4", "異常診斷", "異常診斷", "電機系（用電、電池、設備）"],
    ["P5", "趨勢預測", "趨勢預測", "數學、程式較強的人"],
    ["P6", "決策引擎＋管理優先＋成效驗證", "行動控制、管理優先、05 執行回饋", "智慧自動化系（控制邏輯）"],
], [14 * mm, 52 * mm, 50 * mm, 58 * mm]))
s.append(Spacer(1, 3))
s.append(P("三個科系在純軟體架構裡仍各有主場：電機負責用電與電池的設備診斷、通訊負責資料管線與設備通訊健康、自動化負責決策與控制邏輯。這就是「跨域整合與團隊協作」的證據。", small))

s += person("P1", "隊長／專案經理＋文件展示", [
    ("負責", "進度管理、每週會議與紀錄、報名文件、與老師和主辦單位聯絡（含詢問維修紀錄與 GI 定義）、作品說明書總編、3 分鐘影片、簡報海報（匿名版）、Q&amp;A 題庫"),
    ("交付物", ["<b>企業需求對照表</b>：企業圖上每一項（五項輸出、標準決策資料、安全分級）對應到我們哪個功能、哪張截圖",
                "每週進度表與會議紀錄（每次 5 行以內）", "作品說明書、3 分鐘影片、決賽簡報與海報", "10 題 Q&amp;A 題庫，每人負責回答自己那一層"]),
    ("前期", "10 月協助做三個空品站的資料初探，自己也要懂技術，答得出評審的問題"),
])
s += person("P2", "資料工程＋平台整合（02 大數據）", [
    ("負責", "所有人共用的資料基礎與最後的平台"),
    ("交付物", ["共用讀檔函式 load_jnc()：處理 UTF-16、Tab 分隔、工地微氣候跳過 2 列、育成北側日期格式、欄名縮短、合併日期與小時",
                "<b>資料字典</b>：7 個資料集每個欄位的意義、單位、合理範圍、缺值比例",
                "<b>歷史基準</b>：各欄位在不同時段（日夜、週）的正常範圍，給 P3、P4 當比較基礎",
                "時間軸補齊與缺漏標記（缺漏可能代表斷線）",
                "CSV 回放模擬器：依時間順序把資料一筆一筆送進系統，可加速、可注入異常",
                "<b>Streamlit 平台</b>：整合 P3–P6 的輸出，做成燈號、診斷卡、預測曲線、決策卡、工單清單、回測頁面"]),
    ("工具", "pandas、Streamlit、Plotly"),
    ("成果數字", "資料品質報告（缺值、不合理值比例）、平台處理一筆資料到產生決策的時間"),
])
s += person("P3", "狀態辨識＋感測器可信度（現在發生什麼）", [
    ("交付物", ["<b>物理規則檢查</b>：DO &lt; 0、pH 為 0 或不在 0–14、EC 為 0 等不可能值",
                "<b>水質指標與燈號</b>：用 DO、pH、水溫自訂魚塭水質指標（WQI），分綠黃橘紅四級，門檻依文獻並寫明出處",
                "<b>感測器可信度分數</b>：三支探頭彼此差異（spread）、與歷史基準的偏離、斜率變化，算出每支探頭 0–100 的可信度",
                "擴充：羊舍 THI 熱緊迫分級、空品站燈號"]),
    ("工具", "pandas、numpy"),
    ("基準", "只看單支探頭即時值的固定門檻"),
    ("成果數字", "對合成故障（P4 注入）的感測器可信度判別準確率、燈號與實際低氧時段的一致率"),
])
s += person("P4", "異常診斷（現在發生什麼＋為什麼）", [
    ("交付物", ["<b>異常偵測</b>：Isolation Forest 找出可疑時段",
                "<b>原因分類</b>：感測器故障、感測器漂移、真實水質事件、增氧設備異常、斷線、供電不足",
                "<b>判斷證據</b>：每個診斷附上依據，例如「pH3 與另兩支相差 0.6 以上、持續 6 小時」",
                "<b>診斷可信度</b>：依證據數量和一致性給分",
                "<b>用電分析</b>：從系統總和功率跳升推斷增氧設備開機時間，比對開機後 DO 是否回升；耗電但沒效果就判定設備異常",
                "<b>合成異常注入工具</b>：漂移、卡值、突跳、斷線四種，給全隊做評估",
                "擴充：三爺宮溪太陽能與電池異常、育成北側重開機與 4G 劣化"]),
    ("工具", "scikit-learn"),
    ("基準", "固定門檻告警"),
    ("成果數字", "合成異常的 Precision、Recall；原因分類正確率；誤報減少比例"),
])
s += person("P5", "趨勢預測（接下來會怎樣）", [
    ("交付物", ["特徵工程：lag 1、2、3、6、12、24 小時、時段（DO 有日夜週期）、水溫、氣溫、功率",
                "LightGBM 預測 1／3／6 小時後的 DO 與 pH。<b>依時間先後切分</b>：前 80% 訓練、後 20% 測試",
                "<b>超標時間預測</b>：預估「還有幾小時 DO 會跌破門檻」，這是企業圖上明列的輸出",
                "<b>設備故障機率</b>：三爺宮溪電池 24–72 小時電量與斷電時間；育成北側斷線機率",
                "擴充：羊舍 THI、空品超標時間",
                "協助 P6 回測：提供回測期間的預測值"]),
    ("工具", "LightGBM、scikit-learn"),
    ("基準", "persistence（假設下一刻跟現在一樣）"),
    ("成果數字", "MAE、RMSE（mg/L）與基準比較、平均提早預警時數、預測曲線對照圖"),
])
s += person("P6", "決策引擎＋管理優先＋成效驗證（現在該做什麼）", [
    ("交付物", ["<b>決策引擎</b>：依企業圖的「目標、規則、風險、成本」設計。例如目標是 DO 不低於門檻，成本是增氧耗電，風險是誤判造成魚群缺氧",
                "<b>標準決策資料</b>：每筆決策輸出設備、動作、時間、幅度、理由、預期效果、風險、人工確認、Fallback 九個欄位",
                "<b>執行模式分級</b>：低風險且已驗證 → 自動執行；高風險 → 平台跳出人工確認；資料失效 → Fallback 安全規則（例如感測器可信度太低時維持增氧設備運轉）",
                "<b>管理優先</b>：校正、檢修工單排序與派工建議，估算增氧能耗",
                "<b>LLM 說明層</b>：把決策寫成現場人員看得懂的工單。LLM 只負責寫成人話，判斷由規則和模型決定",
                "<b>成效驗證（回測）</b>：在歷史資料上模擬「照 AI 建議做」與「不做」或「固定門檻控制」，比較低溶氧時數、能耗、誤報次數"]),
    ("工具", "Python；LLM 用 Gemma 4、Gemma-3-TAIDE-12b、Granite 4.0、Ministral 3 等非中資模型，或 Gemini、OpenAI、Claude API；Breeze 2（含 InternViT）與 TAIDE-R1（含 DeepSeek 權重）不可用，清單見 architecture.md 第 7 節"),
    ("基準", "不採取行動、固定門檻控制"),
    ("成果數字", "低溶氧時數減少比例、提早行動時數、增氧能耗變化、需人工確認的比例"),
])

# ---------- 七、介面約定 ----------
s.append(PageBreak())
s.append(P("七、模組介面約定（第一週就要定好）", h1))
s.append(P("每個模組都是一個 Python 函式，輸入一段時間的資料，輸出固定格式的 JSON。誰的模組還沒好，其他人就先用假資料測試。", base))
s.append(Spacer(1, 4))
s.append(table([
    ["模組", "負責人", "輸出範例"],
    ["state()", "P3", P('{"ts":"2026-07-15T02:00", "site":"pond1", "wqi":62, "light":"orange", "sensor_trust":{"pH1":95,"pH2":93,"pH3":41}}', mono)],
    ["diagnose()", "P4", P('{"ts":..., "type":"sensor_drift", "target":"pH3", "evidence":["與另兩支相差0.6以上","持續6小時"], "confidence":0.86}', mono)],
    ["forecast()", "P5", P('{"ts":..., "target":"DO1", "h1":3.0, "h3":2.6, "h6":2.4, "hours_to_threshold":3, "fail_prob":null}', mono)],
    ["decide()", "P6", P("見下方「標準決策資料」", mono)],
], [24 * mm, 16 * mm, 134 * mm]))
s.append(P("標準決策資料範例（依企業圖的九個欄位）", h2))
s.append(table([[P(
    '{<br/>&nbsp;&nbsp;"設備": "1 號增氧機",<br/>&nbsp;&nbsp;"動作": "啟動",<br/>&nbsp;&nbsp;"時間": "立即，持續 2 小時",<br/>'
    '&nbsp;&nbsp;"幅度": "全速",<br/>&nbsp;&nbsp;"理由": "預測 3 小時後 DO 降至 2.6 mg/L，低於門檻；三支探頭同步下降，判定為真實水質事件（可信度 0.9）",<br/>'
    '&nbsp;&nbsp;"預期效果": "2 小時內 DO 回升至 4 mg/L 以上",<br/>&nbsp;&nbsp;"風險": "中（夜間水溫 29.6°C，耗氧加快）",<br/>'
    '&nbsp;&nbsp;"人工確認": false,<br/>&nbsp;&nbsp;"Fallback": "若 DO 資料中斷超過 1 小時，維持增氧機運轉並通知值班人員"<br/>}', mono2)]],
    [W], header=False, extra=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7F9"))]))
s.append(Spacer(1, 4))
s.append(P("<b>GitHub 資料夾建議：</b>data/、common/（load_jnc、資料字典）、state/、diagnose/、forecast/、decide/、backtest/、app/（Streamlit）、docs/。每人主要改自己的資料夾，commit 紀錄就是團隊協作的證據。", base))

# ---------- 八、成果數字 ----------
s.append(P("八、說明書第一頁要放的成果數字", h1))
s.append(table([
    ["數字", "負責人", "比較基準"],
    ["預測誤差（DO 的 MAE，mg/L）與平均提早預警時數", "P5", "persistence"],
    ["合成異常的 Precision／Recall、原因分類正確率", "P4", "固定門檻"],
    ["感測器可信度判別準確率", "P3", "只看即時值"],
    ["回測：低溶氧時數減少比例、增氧能耗變化", "P6", "不採取行動、固定門檻控制"],
], [92 * mm, 24 * mm, 58 * mm]))
s.append(Spacer(1, 4))
s.append(note("評審最常問：「你的 AI 比不用 AI 好多少？」每個功能都要配一個最簡單的基準。數字一定要是真的跑出來的，不要寫預估值。"))

# ---------- 九、時程 ----------
s.append(P("九、每人時程", h1))
sched = [
    ["週次", "P1 隊長", "P2 資料平台", "P3 狀態", "P4 診斷", "P5 預測", "P6 決策"],
    ["10/09–10/21", "組隊、範本、寄信問維修紀錄與 GI", "<b>load_jnc、資料字典</b>", "專家系統資料初探、物理規則", "三爺宮溪、育成北側資料初探", "專家系統 DO 資料初探、persistence 基準", "羊舍資料初探、決策規則草稿"],
    ["10/22–11/04", "說明書架構、需求對照表", "歷史基準、回放模擬器", "WQI 燈號、可信度第一版", "合成異常工具、Isolation Forest", "LightGBM 第一版", "標準決策資料格式、規則第一版"],
    ["<b>10/31 檢查點</b>", "檢查進度", "全員能用共用函式讀資料", "有燈號", "有異常偵測數字", "有 MAE", "能輸出決策 JSON"],
    ["11/05–11/15", "會議紀錄、影片素材", "Streamlit 平台串起全部模組", "擴充羊舍 THI", "原因分類、用電分析", "超標時間、電池預測", "執行分級、LLM 工單、回測"],
    ["<b>11/15 全員整合</b>", "<b>平台從回放到決策卡全線可跑，錄第一支 demo 影片（全員）</b>", "", "", "", "", ""],
    ["11/16–11/28", "<b>說明書定稿、影片、11/28 報名</b>", "寫資料章節", "寫狀態章節", "寫診斷章節", "寫預測章節", "寫決策與回測章節"],
    ["12/02–12/10", "線上展示演練", "平台穩定性、備援錄影", "修 bug", "修 bug", "修 bug", "修 bug"],
    ["12/12–12/18", "海報、簡報、彩排", "現場筆電與網路", "彩排 Q&amp;A", "彩排 Q&amp;A", "彩排 Q&amp;A", "彩排 Q&amp;A"],
]
s.append(table(sched, [24 * mm] + [25 * mm] * 6, style=tiny,
               extra=[("SPAN", (1, 5), (-1, 5)), ("BACKGROUND", (0, 3), (-1, 3), NOTE_BG),
                      ("BACKGROUND", (0, 5), (-1, 5), NOTE_BG)]))
s.append(Spacer(1, 3))
s.append(P("期中考大概在 11 月上中旬，考試週只排輕量工作，例如寫說明書草稿、整理圖表。", small))

# ---------- 十、demo ----------
s.append(P("十、決賽 demo 流程（所有人都要上場）", h1))
s.append(table([
    ["步驟", "負責人", "平台上看到什麼"],
    ["1", "P2", "回放 7 月某一晚的魚塭資料，燈號從綠開始"],
    ["2", "P4", "注入「pH3 漂移」→ 診斷卡顯示感測器漂移、證據與可信度"],
    ["3", "P3", "pH3 可信度降到 41，系統改用另兩支探頭判斷，燈號不亂跳"],
    ["4", "P5", "DO 開始下降 → 預測顯示「約 3 小時後跌破門檻」"],
    ["5", "P6", "決策卡依標準決策資料輸出：啟動 1 號增氧機 2 小時；高風險情境跳出人工確認按鈕"],
    ["6", "P6", "LLM 產生的工單出現在工單清單，並排出優先順序"],
    ["7", "P6、P5", "切到回測頁：整段期間照 AI 建議做，低溶氧時數減少多少"],
    ["8", "P1", "收尾：企業需求對照表、換場域只要換設定檔（切到羊舍或河川站）"],
], [16 * mm, 22 * mm, 136 * mm]))

# ---------- 十一、提醒 ----------
s.append(P("十一、提醒與常見地雷", h1))
s += bl([
    "<b>硬體改為選配：</b>企業命題的執行端是 SCADA／PLC 或人工，我們不必自建感測器。決賽的「完整性」用能實際運作的平台、回放和回測來證明。若最後有餘力，再加一個小型實機展示即可，不要排在主線上。",
    "<b>時間序列不能隨機切分：</b>一律前 80% 訓練、後 20% 測試，並在說明書寫明。",
    "<b>先做完魚塭一個場域，再擴充：</b>10/31 魚塭五項輸出都要有第一版，擴充場域排在 11/05 以後。",
    "<b>資料期間短：</b>羊舍只有約 36 天、育成北側 387 筆，承認限制並用簡單模型，避免過擬合。",
    "<b>中資模型：</b>下載任何模型前檢查 model card 的 base model。",
    "<b>匿名：</b>簡報、海報、影片一律不出現校名、系所、指導老師。",
    "<b>備援：</b>決賽準備錄影版 demo，存在筆電和隨身碟，網路出狀況時立即切換。",
])

doc.build(s)
print("ok", OUT)
