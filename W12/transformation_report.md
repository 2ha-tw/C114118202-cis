## 轉換摘要 － 對應評分：reproducibility

（以下數字都是執行 `python clean_credit_data.py` 印出來的結果。）

- 處理前總列數：219　處理後總列數：190
- 被排除／隔離的列數：29　原因：17 筆是整列完全重複（同一批資料匯出兩次，保留第一筆）；12 筆 ID 空白（匯出時編號遺失，無法跟還款紀錄對帳），隔離另存到 credit-quarantine.csv，沒有直接丟掉
- 做了哪些轉換（逐步寫，至少三個步驟或三個欄位各自的處理）：
  1. 刪掉 17 筆整列重複，再把 12 筆 ID 空白的列隔離到 credit-quarantine.csv，確認剩下的 ID 都不重複
  2. AGE：-1、unknown、空白共 141 筆設成 NULL，其餘轉成整數（都在 18–100）
  3. MARITAL_STATUS：??、NULL 共 80 筆設成 NULL，其餘統一成 single／married／divorced
  4. PAY_0：late 共 31 筆設成 NULL，其餘轉成整數（都在 -2～9）
  5. BILL_AMT1：空白（新戶未出帳）68 筆補 0；n/a（同步失敗）59 筆設成 NULL；轉成整數
  6. signup_at：三種日期寫法統一轉成 ISO-8601 UTC，not-a-date 共 50 筆設成 NULL
  7. default、LEAK_FUTURE_DEFAULT：檢查都是 0／1，不改動
- missing_rate：16.32%（31／190）（門檻 < 20%；計算方式與範圍：依 QA 工程師說明，以 ID、PAY_0、default 三欄中任一欄缺值的列數 ÷ 輸出檔總列數；被整列排除或隔離的列不算在分母。31 筆全部來自 PAY_0 的 late）
- random seed：42（固定值，確保重跑結果一致）

我把腳本連續跑兩次，兩次輸出的 credit-clean.csv 完全一樣（MD5 相同）。腳本只讀本機的 credit-dirty.csv，不連網。
