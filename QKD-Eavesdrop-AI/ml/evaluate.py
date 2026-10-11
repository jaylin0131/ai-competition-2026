"""評估與出圖（B 組，任務 B3、B5）。圖存到 reports/，直接放進作品說明書。

必出：
1. 七類混淆矩陣（重點：攻擊被判成良性故障的格子）
2. 同誤報率（10%、5%、2%）下各攻擊的偵測率：協定門檻 vs 物理規則表 vs 決策樹 vs 梯度提升
3. 依 attack_ratio 分段的偵測率曲線
4. 留一攻擊驗證：訓練時拿掉一種攻擊，看能否當成異常抓到
5. SHAP 特徵重要度、決策樹圖、max_depth vs. 訓練／驗證準確率
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("B3：評估工具")


if __name__ == "__main__":
    main()
