# 原始資料來源

銘祥科技於企業命題頁提供的 7 個 CSV，2026-10-11 下載。**本資料夾的檔案請勿修改**；整理後的版本在 `data/processed/`，由 `scripts/prepare_data.py` 產生。

- 命題頁：https://phpweb4.nutn.edu.tw/ilt/wordpress/?page_id=4359
- 下載位址前綴：`https://phpweb4.nutn.edu.tw/ilt/wordpress/wp-content/uploads/2026/09/`
- 格式：UTF-16 LE、Tab 分隔、CRLF、每小時一筆；工地微氣候標題列前有 2 列（HH、HI）不是資料
- 用途：僅供本競賽使用，請勿公開散布原始資料

| 檔名 | 程式代號 | 大小 | SHA-256 |
|---|---|---|---|
| Data2026-06-01專家系統.csv | `pond` | 977,094 | `41613bb84dcdb060f62302667a3b1b904d9bb7b6c962e01f957f1c1e8238e258` |
| Data2026-01-01-三爺宮溪.csv | `river` | 397,048 | `a8c3ca443df5b4d7e796e6802aa25979053bcc60bf05ed27f296804325944822` |
| Data2026-06-01-羊舍.csv | `goat` | 203,748 | `cf66af8897eb5a711bf6943baa7a149fa88915c329ef03f2dc92aff37a9c8961` |
| Data2026-06-01-育成北側.csv | `yucheng_north` | 62,442 | `27f7ee6b2e61767e5344fbf8f2256fafe42e6f03ed7448600eb0f6b7d43a0155` |
| Data2026-06-01-育成一廠.csv | `yucheng1` | 240,810 | `70070fad19dd1fd4b838ba35cec5d0949e2bb72de77107ab87795330a056f94f` |
| Data2026-06-01-東北角.csv | `northeast` | 190,080 | `6c9724e11fcdc917cbbf2ec8b334b4bd0b26cf8edb56160d4967358ad520bf2d` |
| Data2026-01-01-工地微氣候.csv | `construction` | 215,436 | `365e2a1398b0f4a3f61fc9267aaf5e746c6929610645adb3b1c74547ce9146e4` |

確認檔案沒被改過：

```bash
shasum -a 256 data/raw/*.csv
```
