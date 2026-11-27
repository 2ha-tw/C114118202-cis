import pandas as pd
import numpy as np

RANDOM_SEED = 42  # 固定 seed，任何隨機步驟都要用它，確保可重現（本腳本沒有隨機步驟）
np.random.seed(RANDOM_SEED)

# 全部先當字串讀進來，避免 pandas 自己把 NULL、n/a 這些值偷偷轉掉
df = pd.read_csv("credit-dirty.csv", dtype=str, keep_default_na=False)
n_raw = len(df)
print(f"處理前總列數：{n_raw}")

# ---------- 1. 整列重複：同一批資料被匯出兩次（Claire 說明）----------
dup_mask = df.duplicated(keep="first")
n_dup = int(dup_mask.sum())
df = df[~dup_mask].copy()
print(f"[排除] 整列完全重複：{n_dup} 筆（同一批資料重複匯出，保留第一筆）")

# ---------- 2. ID 空白：編號遺失，無法跟還款紀錄對帳 → 隔離 ----------
df["ID"] = df["ID"].str.strip()
no_id = df["ID"] == ""
quarantine = df[no_id].copy()
quarantine["quarantine_reason"] = "ID 空白：匯出時編號遺失，無法以 ID 與還款紀錄對帳"
quarantine.to_csv("credit-quarantine.csv", index=False)
df = df[~no_id].copy()
print(f"[隔離] ID 空白：{len(quarantine)} 筆 → 另存 credit-quarantine.csv，不會直接丟掉")

assert df["ID"].is_unique, "ID 仍有重複"

# ---------- 3. AGE：-1 是系統預設、unknown 是字跡無法辨識 → 設 NULL ----------
age = pd.to_numeric(df["AGE"].replace({"-1": "", "unknown": ""}), errors="coerce")
age = age.where(age.between(18, 100))
print(f"[設 NULL] AGE 沒有可用年齡：{int(age.isna().sum())} 筆")
df["AGE"] = age.astype("Int64")

# ---------- 4. MARITAL_STATUS：?? 與 NULL 是申請人拒答 → 設 NULL ----------
ms = df["MARITAL_STATUS"].str.strip().str.lower()
ms = ms.where(ms.isin(["single", "married", "divorced"]))
print(f"[設 NULL] MARITAL_STATUS 拒答：{int(ms.isna().sum())} 筆")
df["MARITAL_STATUS"] = ms

# ---------- 5. PAY_0：late 只知道有逾期、不知道幾個月 → 設 NULL ----------
pay = pd.to_numeric(df["PAY_0"].replace({"late": ""}), errors="coerce")
pay = pay.where(pay.between(-2, 9))
print(f"[設 NULL] PAY_0 為 late（逾期月數未知）：{int(pay.isna().sum())} 筆")
df["PAY_0"] = pay.astype("Int64")

# ---------- 6. BILL_AMT1：空白＝新戶尚未出帳 → 0；n/a＝同步失敗 → NULL ----------
bill_raw = df["BILL_AMT1"].str.strip()
n_new = int((bill_raw == "").sum())
n_na = int((bill_raw.str.lower() == "n/a").sum())
bill = pd.to_numeric(bill_raw.replace({"": "0", "n/a": "", "N/A": ""}), errors="coerce")
print(f"[轉換] BILL_AMT1 空白（新戶未出帳）→ 0：{n_new} 筆；n/a（金額存在但未知）→ NULL：{n_na} 筆")
df["BILL_AMT1"] = bill.round().astype("Int64")

# ---------- 7. signup_at：四種寫法統一成 ISO-8601 UTC ----------
def to_utc(s):
    s = s.strip()
    if s == "" or s == "not-a-date":
        return pd.NaT  # 舊系統欄位損毀，原始時間無法復原
    if "/" in s and len(s) == 10:
        # 01/02/2024 是 月/日/年，台北時間，只有日期 → 當天 00:00 台北時間
        return pd.to_datetime(s, format="%m/%d/%Y").tz_localize("Asia/Taipei").tz_convert("UTC")
    if s.count("/") == 2:
        # 2024/01/02 18:00+08:00
        return pd.to_datetime(s, format="%Y/%m/%d %H:%M%z").tz_convert("UTC")
    return pd.to_datetime(s, utc=True)

ts = df["signup_at"].map(to_utc)
print(f"[設 NULL] signup_at 為 not-a-date（欄位損毀）：{int(ts.isna().sum())} 筆")
df["signup_at"] = ts.map(lambda t: "" if pd.isna(t) else t.strftime("%Y-%m-%dT%H:%M:%SZ"))

# ---------- 8. default：目標變數，只檢查不改 ----------
df["default"] = df["default"].astype(int)
assert df["default"].isin([0, 1]).all()

# ---------- 9. LEAK_FUTURE_DEFAULT：結果期後回填，保留欄位但不得用於建模 ----------
df["LEAK_FUTURE_DEFAULT"] = df["LEAK_FUTURE_DEFAULT"].astype(int)
assert df["LEAK_FUTURE_DEFAULT"].isin([0, 1]).all()
print("[保留] LEAK_FUTURE_DEFAULT：結果期後才回填，申請當下拿不到；欄位保留，W14 建模時必須排除")

# ---------- 輸出與 missing_rate ----------
key = df[["ID", "PAY_0", "default"]]
missing_rows = int(key.isna().any(axis=1).sum())
missing_rate = missing_rows / len(df)
print(f"處理後總列數：{len(df)}")
print(f"被排除／隔離的列數：{n_raw - len(df)}（重複 {n_dup}、ID 空白 {len(quarantine)}）")
print(f"missing_rate：{missing_rows}/{len(df)} = {missing_rate:.2%}（ID、PAY_0、default 任一欄缺值的列數 ÷ 輸出列數）")

df.to_csv("credit-clean.csv", index=False)
