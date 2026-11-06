"""Task 1-2: net product purchases, preserve unmatched refunds, portable paths.

Copy to customer_segmentation/preprocessing/data_preprocessor.py.
RFM: R/F use Quantity > 0; M sums ALL TotalAmount, including negative refunds.
"""
from collections import defaultdict
from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "datasets" / "raw" / "Online Retail.xlsx"
PROCESSED_DIR = ROOT / "datasets" / "processed"
COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
           "UnitPrice", "CustomerID", "Country"]
# Explicit business policy: merchandise only, excluding fees, manual adjustments,
# discounts, samples and gift vouchers. Keep actual alphanumeric SKUs (e.g. PADS).
NON_PRODUCT_CODES = {"POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE",
                     "B", "C2", "CRUK", "D", "S"}
MONEY_SCALE = 10000  # Match the DECIMAL(...,4) precision in database.sql.


def prepare_transactions(raw):
    missing = set(COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing input columns: {sorted(missing)}")
    df = raw[COLUMNS].copy()
    df["SourceRow"] = np.arange(len(df)) + 2  # Original Excel row, including header.
    steps = []
    rejected = []

    def retain(mask, reason):
        nonlocal df
        before = len(df)
        bad = df.loc[~mask].copy()
        bad["Reason"] = reason
        rejected.append(bad)
        df = df.loc[mask].copy()
        steps.append({"Step": reason, "Before": before,
                      "Removed": before - len(df), "After": len(df)})

    retain(~df.duplicated(subset=COLUMNS), "exact_duplicate")
    for c in ("InvoiceNo", "StockCode", "Description", "Country"):
        df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    # Numeric IDs read from some Excel files appear as '12345.0'.
    for c in ("InvoiceNo", "StockCode"):
        df[c] = df[c].str.replace(r"^(\d+)\.0$", r"\1", regex=True)
    df["StockCode"] = df["StockCode"].str.upper()
    df["InvoiceNo"] = df["InvoiceNo"].str.upper()
    for c in ("Quantity", "UnitPrice", "CustomerID"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    retain(df["InvoiceDate"].notna(), "invalid_date")
    customer = df["CustomerID"]
    retain(np.isfinite(customer) & customer.gt(0) & customer.mod(1).eq(0),
           "missing_or_invalid_customer")
    retain(df["InvoiceNo"].notna() & df["StockCode"].notna(), "missing_invoice_or_stock")
    non_product = (df["StockCode"].isin(NON_PRODUCT_CODES)
                   | df["StockCode"].str.startswith("GIFT_", na=False))
    retain(~non_product, "non_product_code")
    quantity = df["Quantity"]
    retain(np.isfinite(quantity) & quantity.ne(0) & quantity.mod(1).eq(0),
           "invalid_or_zero_quantity")
    retain(np.isfinite(df["UnitPrice"]) & df["UnitPrice"].gt(0), "invalid_unit_price")
    # A cancellation with positive quantity is inconsistent: do not guess its sign.
    retain(~(df["InvoiceNo"].str.startswith("C") & df["Quantity"].gt(0)),
           "cancellation_with_positive_quantity")
    df["CustomerID"] = df["CustomerID"].astype("int64")
    df["Quantity"] = df["Quantity"].astype("int64")
    scaled_price = df["UnitPrice"] * MONEY_SCALE
    if not np.allclose(scaled_price, np.rint(scaled_price), rtol=0, atol=0.000001):
        raise ValueError("UnitPrice has more than four decimal places; review precision.")
    df["PriceUnits"] = np.rint(scaled_price).astype("int64")
    df["AmountUnits"] = df["Quantity"] * df["PriceUnits"]
    df["TotalAmount"] = df["AmountUnits"] / MONEY_SCALE
    return df, pd.DataFrame(steps), pd.concat(rejected, ignore_index=True)


def net_returns(transactions):
    """LIFO by (customer, SKU, exact price), using earlier purchases only.

    InvoiceNo of a credit note is NOT an original invoice reference. Matching is
    an explicit allocation rule, not a claim to know the actual original invoice.
    Unmatched quantity stays negative so that net spend is never overstated.
    """
    df = transactions.sort_values(["InvoiceDate", "SourceRow"], kind="stable").reset_index(drop=True)
    remaining = df["Quantity"].to_numpy(copy=True)
    purchases = defaultdict(list)
    links = []
    for i, row in enumerate(df.itertuples(index=False)):
        key = (row.CustomerID, row.StockCode, row.PriceUnits)
        if row.Quantity > 0:
            purchases[key].append(i)
            continue
        need = -int(row.Quantity)
        stack = purchases[key]
        while need and stack:
            j = stack[-1]
            used = min(need, int(remaining[j]))
            remaining[j] -= used
            need -= used
            links.append({"ReturnSourceRow": int(row.SourceRow),
                          "PurchaseSourceRow": int(df.at[j, "SourceRow"]),
                          "ReturnInvoice": row.InvoiceNo,
                          "PurchaseInvoice": df.at[j, "InvoiceNo"],
                          "CustomerID": int(row.CustomerID), "StockCode": row.StockCode,
                          "MatchedQuantity": used,
                          "MatchedAmount": used * int(row.PriceUnits) / MONEY_SCALE})
            if remaining[j] == 0:
                stack.pop()
        remaining[i] = -need
    df["Quantity"] = remaining
    df["AmountUnits"] = df["Quantity"] * df["PriceUnits"]
    df["TotalAmount"] = df["AmountUnits"] / MONEY_SCALE
    net = df.loc[df["Quantity"].ne(0)].copy()
    # Check exact customer totals in integer money units; matching must conserve money.
    before = transactions.groupby("CustomerID")["AmountUnits"].sum()
    after = net.groupby("CustomerID")["AmountUnits"].sum().reindex(before.index, fill_value=0)
    if not before.eq(after).all():
        raise AssertionError("Return allocation changed customer net spend.")
    link_columns = ["ReturnSourceRow", "PurchaseSourceRow", "ReturnInvoice",
                    "PurchaseInvoice", "CustomerID", "StockCode", "MatchedQuantity", "MatchedAmount"]
    return net, pd.DataFrame(links, columns=link_columns)


def customer_summary(transactions, net):
    """Net spend includes every valid product refund, even if unmatched."""
    summary = transactions.groupby("CustomerID")["AmountUnits"].sum().to_frame("NetUnits")
    retained = net.loc[net["Quantity"].gt(0)]
    g = retained.groupby("CustomerID")
    summary = summary.join(g["InvoiceNo"].nunique().rename("Frequency"))
    summary = summary.join(g["InvoiceDate"].max().rename("LastPurchase"))
    summary["Frequency"] = summary["Frequency"].fillna(0).astype("int64")
    summary["NetMonetary"] = summary.pop("NetUnits") / MONEY_SCALE
    # Customers fully refunded or with net debt are not active purchasing RFM cases.
    summary["RFMEligible"] = summary["NetMonetary"].gt(0) & summary["Frequency"].gt(0)
    return summary.reset_index()


def main():
    if not RAW_PATH.is_file():
        raise FileNotFoundError(f"Input file not found: {RAW_PATH}")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print("[1/6] Dang doc Excel goc (541.909 dong), vui long cho...", flush=True)
    raw = pd.read_excel(RAW_PATH)
    print(f"Da doc {len(raw):,} dong.", flush=True)
    print("[2/6] Dang lam sach va loc ma hang...", flush=True)
    valid, steps, rejected = prepare_transactions(raw)
    print("[3/6] Dang doi chieu mua va hoan hang...", flush=True)
    net, links = net_returns(valid)
    print("[4/6] Dang tinh tong tien rong theo khach...", flush=True)
    summary = customer_summary(valid, net)
    clean = net[COLUMNS + ["TotalAmount"]]
    print(f"[5/6] Dang ghi Excel {len(clean):,} dong. Buoc nay co the mat vai phut...", flush=True)
    clean.to_excel(PROCESSED_DIR / "Online Retail_cleaned.xlsx", index=False)
    print("Da ghi xong Excel. [6/6] Dang xuat cac bang doi chieu CSV...", flush=True)
    # Retain source-row trace and excluded records separately from the clean dataset.
    valid[COLUMNS + ["SourceRow", "TotalAmount"]].to_csv(
        PROCESSED_DIR / "transactions_ledger.csv", index=False, encoding="utf-8-sig")
    net.loc[net["Quantity"].lt(0), COLUMNS + ["SourceRow", "TotalAmount"]].to_csv(
        PROCESSED_DIR / "unmatched_returns.csv", index=False, encoding="utf-8-sig")
    rejected.to_csv(PROCESSED_DIR / "rejected_rows.csv", index=False, encoding="utf-8-sig")
    links.to_csv(PROCESSED_DIR / "return_matches.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(PROCESSED_DIR / "customer_net_summary.csv", index=False, encoding="utf-8-sig")
    steps.to_csv(PROCESSED_DIR / "cleaning_steps.csv", index=False, encoding="utf-8-sig")
    comparison = pd.DataFrame({
        "Metric": ["Rows", "Columns", "Customers", "Exact duplicate rows",
                   "Missing CustomerID", "Cancellation rows", "Negative quantity rows",
                   "Zero quantity rows", "Nonpositive price rows", "Missing Description",
                   "TotalAmount (GBP)", "RFM eligible customers"],
        "Before": [len(raw), len(raw.columns), raw["CustomerID"].nunique(),
                   raw.duplicated().sum(), raw["CustomerID"].isna().sum(),
                   raw["InvoiceNo"].astype(str).str.upper().str.startswith("C").sum(),
                   raw["Quantity"].lt(0).sum(), raw["Quantity"].eq(0).sum(),
                   raw["UnitPrice"].le(0).sum(), raw["Description"].isna().sum(),
                   (raw["Quantity"] * raw["UnitPrice"]).sum(), None],
        "After": [len(clean), len(clean.columns), clean["CustomerID"].nunique(),
                  clean.duplicated().sum(), clean["CustomerID"].isna().sum(),
                  clean["InvoiceNo"].str.startswith("C").sum(), clean["Quantity"].lt(0).sum(),
                  clean["Quantity"].eq(0).sum(), clean["UnitPrice"].le(0).sum(),
                  clean["Description"].isna().sum(), clean["TotalAmount"].sum(),
                  int(summary["RFMEligible"].sum())]})
    comparison.to_csv(PROCESSED_DIR / "cleaning_comparison.csv", index=False, encoding="utf-8-sig")
    totals = {"raw_rows": len(raw), "valid_product_ledger_rows": len(valid),
              "cleaned_rows": len(clean), "cleaned_customers": int(clean.CustomerID.nunique()),
              "net_product_revenue": int(valid.AmountUnits.sum()) / MONEY_SCALE,
              "unmatched_return_rows": int(clean.Quantity.lt(0).sum()),
              "unmatched_return_amount": float(-clean.loc[clean.Quantity.lt(0), "TotalAmount"].sum()),
              "rfm_eligible_customers": int(summary.RFMEligible.sum())}
    (PROCESSED_DIR / "cleaning_summary.json").write_text(
        json.dumps(totals, indent=2), encoding="utf-8")
    print(comparison.to_string(index=False))
    print(json.dumps(totals, indent=2))
    print(f"HOAN TAT! Saved to: {PROCESSED_DIR}", flush=True)
    print("IMPORTANT: R/F use positive purchases only; M includes negative unmatched refunds.")


if __name__ == "__main__":
    main()
