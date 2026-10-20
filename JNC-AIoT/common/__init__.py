
import os as _os

# 4 核心筆電上 OpenMP 預設執行緒會互搶，訓練慢 5 倍以上
_os.environ.setdefault("OMP_NUM_THREADS", "2")
