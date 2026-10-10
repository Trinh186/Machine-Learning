
import pandas as pd
import numpy as np

# ============================================================
# 1. DOC DU LIEU
# ============================================================

df = pd.read_excel("Online Retail.xlsx")

so_dong_goc = len(df)
so_cot_goc = len(df.columns)
so_khach_hang_goc = df["CustomerID"].nunique()

print("=" * 65)
print("1. THONG KE TONG QUAN DATASET BAN DAU")
print("=" * 65)

print(f"So dong: {len(df):,}")
print(f"So cot: {len(df.columns)}")
print(f"So khach hang: {df['CustomerID'].nunique():,}")
print(f"Thoi gian bat dau: {df['InvoiceDate'].min()}")
print(f"Thoi gian ket thuc: {df['InvoiceDate'].max()}")

print("\nDanh sach thuoc tinh:")
print(df.columns.tolist())

print("\n5 dong dau tien:")
print(df.head().to_string(index=False))

print("\nKieu du lieu ban dau:")
print(df.dtypes)

print("\nGia tri thieu theo cot:")
print(df.isna().sum().to_string())


# ============================================================
# 2. KHAO SAT CHAT LUONG DU LIEU GOC
# ============================================================

df["InvoiceNo"] = df["InvoiceNo"].astype("string")
duplicate_goc = int(df.duplicated().sum())
customerid_thieu_goc = int(df["CustomerID"].isna().sum())
description_thieu_goc = int(df["Description"].isna().sum())
hoa_don_huy_goc = int(
    df["InvoiceNo"].str.startswith("C", na=False).sum()
)
quantity_am_goc = int((df["Quantity"] < 0).sum())
quantity_bang_0_goc = int((df["Quantity"] == 0).sum())
quantity_khong_hop_le_goc = int((df["Quantity"] <= 0).sum())
unitprice_bang_0_goc = int((df["UnitPrice"] == 0).sum())
unitprice_am_goc = int((df["UnitPrice"] < 0).sum())
unitprice_khong_hop_le_goc = int((df["UnitPrice"] <= 0).sum())
print("\n" + "=" * 65)
print("2. KHAO SAT CHAT LUONG DU LIEU GOC")
print("=" * 65)
print(f"Dong trung lap hoan toan: {duplicate_goc:,}")
print(f"CustomerID bi thieu: {customerid_thieu_goc:,}")
print(f"Description bi thieu: {description_thieu_goc:,}")
print(f"InvoiceNo bat dau bang C: {hoa_don_huy_goc:,}")
print(f"Quantity < 0 (giao dich hoan tra): {quantity_am_goc:,}")
print(f"Quantity = 0: {quantity_bang_0_goc:,}")
print(f"Quantity <= 0: {quantity_khong_hop_le_goc:,}")
print(f"UnitPrice = 0: {unitprice_bang_0_goc:,}")
print(f"UnitPrice < 0: {unitprice_am_goc:,}")
print(f"UnitPrice <= 0: {unitprice_khong_hop_le_goc:,}")


# ============================================================
# 3. XU LY DONG TRUNG LAP
# ============================================================

truoc = len(df)
df = df.drop_duplicates().copy()
sau = len(df)

print("\n" + "=" * 65)
print("3. XU LY DONG TRUNG LAP")
print("=" * 65)

print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")
print(f"Dong trung lap con lai: {df.duplicated().sum():,}")


# ============================================================
# 4. CHUAN HOA KIEU DU LIEU
# ============================================================

df["InvoiceNo"] = df["InvoiceNo"].astype("string")
df["StockCode"] = df["StockCode"].astype("string")
df["Description"] = df["Description"].astype("string")
df["Country"] = df["Country"].astype("string")
df["Quantity"] = pd.to_numeric(
    df["Quantity"], errors="coerce"
)
df["UnitPrice"] = pd.to_numeric(
    df["UnitPrice"], errors="coerce"
)
df["CustomerID"] = pd.to_numeric(
    df["CustomerID"], errors="coerce"
)
df["InvoiceDate"] = pd.to_datetime(
    df["InvoiceDate"], errors="coerce"
)
# Loai cac dong khong co ngay giao dich hop le
truoc = len(df)
df = df.dropna(subset=["InvoiceDate"]).copy()
sau = len(df)
print("\n" + "=" * 65)
print("4. KIEM TRA NGAY GIAO DICH")
print("=" * 65)
print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")


# ============================================================
# 5. XU LY CUSTOMERID BI THIEU
# ============================================================

truoc = len(df)
df = df.dropna(subset=["CustomerID"]).copy()
sau = len(df)

print("\n" + "=" * 65)
print("5. XU LY CUSTOMERID BI THIEU")
print("=" * 65)

print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")
print(f"CustomerID thieu con lai: {df['CustomerID'].isna().sum():,}")


# ============================================================
# 6. XU LY HOA DON BI HUY
# ============================================================

truoc = len(df)

df = df[
    ~df["InvoiceNo"].str.startswith("C", na=False)
].copy()

sau = len(df)

print("\n" + "=" * 65)
print("6. XU LY HOA DON BI HUY")
print("=" * 65)

print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")
print(
    "Hoa don bat dau bang C con lai: "
    f"{df['InvoiceNo'].str.startswith('C', na=False).sum():,}"
)


# ============================================================
# 7. XU LY QUANTITY VA GIAO DICH HOAN TRA
# ============================================================

print("\n" + "=" * 65)
print("7. KIEM TRA QUANTITY")
print("=" * 65)

print(f"Quantity < 0: {(df['Quantity'] < 0).sum():,}")
print(f"Quantity = 0: {(df['Quantity'] == 0).sum():,}")
print(f"Quantity <= 0: {(df['Quantity'] <= 0).sum():,}")

truoc = len(df)

df = df[
    df["Quantity"].notna()
    & (df["Quantity"] > 0)
].copy()

sau = len(df)

print("\nKet qua xu ly Quantity:")
print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")
print(f"Quantity <= 0 con lai: {(df['Quantity'] <= 0).sum():,}")


# ============================================================
# 8. XU LY UNITPRICE KHONG HOP LE
# ============================================================

print("\n" + "=" * 65)
print("8. KIEM TRA UNITPRICE")
print("=" * 65)

print(f"UnitPrice = 0: {(df['UnitPrice'] == 0).sum():,}")
print(f"UnitPrice < 0: {(df['UnitPrice'] < 0).sum():,}")
print(f"UnitPrice <= 0: {(df['UnitPrice'] <= 0).sum():,}")

truoc = len(df)

df = df[
    df["UnitPrice"].notna()
    & (df["UnitPrice"] > 0)
].copy()

sau = len(df)

print("\nKet qua xu ly UnitPrice:")
print(f"So dong truoc xu ly: {truoc:,}")
print(f"So dong da loai: {truoc - sau:,}")
print(f"So dong sau xu ly: {sau:,}")
print(f"UnitPrice <= 0 con lai: {(df['UnitPrice'] <= 0).sum():,}")


# ============================================================
# 9. CHUAN HOA KIEU DU LIEU SAU CLEANING
# ============================================================

df["Quantity"] = df["Quantity"].astype("int64")
df["UnitPrice"] = df["UnitPrice"].astype("float64")
df["CustomerID"] = df["CustomerID"].astype("int64")

print("\n" + "=" * 65)
print("9. KIEU DU LIEU SAU CHUAN HOA")
print("=" * 65)

print(df.dtypes)


# ============================================================
# 10. TINH TOTALAMOUNT
# ============================================================

df["TotalAmount"] = df["Quantity"] * df["UnitPrice"]

print("\n" + "=" * 65)
print("10. TINH TOTALAMOUNT")
print("=" * 65)

print("Cong thuc: TotalAmount = Quantity * UnitPrice")

print(
    df[
        [
            "InvoiceNo",
            "StockCode",
            "Quantity",
            "UnitPrice",
            "TotalAmount"
        ]
    ].head().to_string(index=False)
)


# ============================================================
# 11. KIEM TRA CUOI CUNG
# ============================================================

print("\n" + "=" * 65)
print("11. KIEM TRA DATASET SAU CLEANING")
print("=" * 65)
print(f"So dong: {len(df):,}")
print(f"So cot: {len(df.columns)}")
print(f"So khach hang: {df['CustomerID'].nunique():,}")
print(f"Dong trung lap con lai: {df.duplicated().sum():,}")
print(f"CustomerID thieu: {df['CustomerID'].isna().sum():,}")
print(
    "Hoa don bi huy con lai: "
    f"{df['InvoiceNo'].str.startswith('C', na=False).sum():,}"
)
print(f"Quantity <= 0: {(df['Quantity'] <= 0).sum():,}")
print(f"UnitPrice <= 0: {(df['UnitPrice'] <= 0).sum():,}")
print(f"InvoiceDate thieu: {df['InvoiceDate'].isna().sum():,}")
print(f"TotalAmount thieu: {df['TotalAmount'].isna().sum():,}")
print("\nGia tri thieu theo cot:")
print(df.isna().sum().to_string())
print("\nKhoang thoi gian giao dich:")
print(f"Tu: {df['InvoiceDate'].min()}")
print(f"Den: {df['InvoiceDate'].max()}")


# ============================================================
# 12. SO SANH TRUOC VA SAU CLEANING
# ============================================================

bang_so_sanh = pd.DataFrame({
    "Chi tieu": [
        "So dong",
        "So cot",
        "So khach hang",
        "Dong trung lap",
        "CustomerID thieu",
        "Hoa don bi huy",
        "Quantity <= 0",
        "UnitPrice <= 0",
        "Description thieu"
    ],
    "Truoc cleaning": [
        so_dong_goc,
        so_cot_goc,
        so_khach_hang_goc,
        duplicate_goc,
        customerid_thieu_goc,
        hoa_don_huy_goc,
        quantity_khong_hop_le_goc,
        unitprice_khong_hop_le_goc,
        description_thieu_goc
    ],
    "Sau cleaning": [
        len(df),
        len(df.columns),
        df["CustomerID"].nunique(),
        int(df.duplicated().sum()),
        int(df["CustomerID"].isna().sum()),
        int(df["InvoiceNo"].str.startswith("C", na=False).sum()),
        int((df["Quantity"] <= 0).sum()),
        int((df["UnitPrice"] <= 0).sum()),
        int(df["Description"].isna().sum())
    ]
})

print("\n" + "=" * 65)
print("12. BANG SO SANH TRUOC VA SAU CLEANING")
print("=" * 65)

print(bang_so_sanh.to_string(index=False))


# ============================================================
# 13. XUAT FILE DU LIEU SAU TIEN XU LY
# ============================================================

df.to_excel("Online Retail_cleaned.xlsx", index=False)

print("\n" + "=" * 65)
print("13. HOAN TAT")
print("=" * 65)

print("Da xuat file: Online Retail_cleaned.xlsx")
print(f"So dong cuoi cung: {len(df):,}")
print(f"So cot cuoi cung: {len(df.columns)}")
