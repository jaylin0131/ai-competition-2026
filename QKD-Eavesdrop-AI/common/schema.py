"""CSV 欄位與標籤的唯一定義（A 組與 B 組共用的介面）。

規格說明見 docs/csv-schema.md。要改這裡，必須三組都同意。
2026-10-11 依參賽進度分析報告改版：三類（normal/noise/eve）→ 七類診斷，一列＝一個「回合」。
"""

# 七類診斷：正常、三種良性通道劣化、三種已知攻擊
BENIGN_LABELS = ("fiber_aging", "pol_drift", "stray_light")
ATTACK_LABELS = ("intercept_resend", "pns", "blinding")
LABELS = ("normal",) + BENIGN_LABELS + ATTACK_LABELS

# 分兩階段：階段一（10/25）只有基本 BB84，階段二（11/8）加入誘騙態
STAGE1_LABELS = ("normal", "fiber_aging", "pol_drift", "intercept_resend")
STAGE2_LABELS = LABELS

ID_COLUMNS = ["round_id", "timestamp", "seed", "n_pulses"]

# 階段一：基本 BB84 就量得到的統計
STAGE1_FEATURES = [
    "gain_signal",      # 訊號態偵測率（n_detected / n_pulses）
    "sift_ratio",
    "qber",
    "qber_z",
    "qber_x",
    "err_var_window",
]

# 階段二：誘騙態才有的統計（PNS、致盲、雜散光只有這些看得到）
DECOY_FEATURES = [
    "gain_decoy",       # 誘騙態偵測率
    "gain_vacuum",      # 真空態偵測率（≈ 暗計數＋雜散光）
    "decoy_signal_ratio",  # gain_decoy / gain_signal，PNS 時會下降
    "qber_decoy",
]

FEATURE_COLUMNS = STAGE1_FEATURES + DECOY_FEATURES

# 只在儀表板顯示，不當特徵（決策 D6）
CHANNEL_COLUMNS = ["distance_km", "loss_db"]

LABEL_COLUMN = "label"

# 模擬時的「答案」，放進特徵會造成標籤洩漏，只能用於分段分析
FORBIDDEN_FEATURES = ["attack_ratio", "fault_severity", "faults", "noise_level"]

ALL_COLUMNS = ID_COLUMNS + FEATURE_COLUMNS + CHANNEL_COLUMNS + [LABEL_COLUMN] + FORBIDDEN_FEATURES


def is_attack(label: str) -> bool:
    """七類 → 是否為攻擊（用於和協定門檻法比較）。"""
    return label in ATTACK_LABELS


def check_no_leakage(feature_names: list[str]) -> None:
    """訓練前呼叫，確認沒有把答案欄位放進特徵。"""
    leaked = sorted(set(feature_names) & set(FORBIDDEN_FEATURES + [LABEL_COLUMN]))
    if leaked:
        raise ValueError(f"特徵中含有禁止欄位（標籤洩漏）：{leaked}")
