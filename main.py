from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from io import BytesIO
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(title="UXXCA MVP Backend", version="1.0")

API_KEY = "DEV_KEY_123"
entries_db = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_api_key(request: Request, x_api_key: str = None):
    key = request.headers.get("X-API-Key") or x_api_key
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


# -------------------------
# Entries
# -------------------------
@app.post("/entries")
async def add_entry(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)
    data = await req.json()
    entry = {
        "id": len(entries_db) + 1,
        "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "debit_account": data.get("debit_account"),
        "credit_account": data.get("credit_account"),
        "amount": data.get("amount"),
        "narration": data.get("narration"),
    }
    entries_db.append(entry)
    return entry


@app.get("/entries")
async def get_entries(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)
    return entries_db


from fastapi.responses import Response

# --- Improved P&L (text output, more robust matching) ---
@app.get("/reports/pnl")
async def get_pnl(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)

    # normalize and sum
    revenue = 0.0
    expenses = 0.0

    rev_keywords = ("income", "sales", "revenue")
    exp_keywords = ("expense", "rent", "salary", "wages", "cost", "purchase", "utility", "utilities")

    for e in entries_db:
        debit = (e.get("debit_account") or "").lower()
        credit = (e.get("credit_account") or "").lower()
        amt = float(e.get("amount") or 0)

        # treat anything matching revenue keywords in either side as revenue
        if any(k in debit for k in rev_keywords) or any(k in credit for k in rev_keywords):
            revenue += amt
        # treat anything matching expense keywords in debit as expense
        elif any(k in debit for k in exp_keywords) or any(k in credit for k in exp_keywords):
            expenses += amt
        else:
            # fallback: if debit looks like an expense-like name, count as expense
            if any(k in debit for k in exp_keywords):
                expenses += amt
            else:
                # conservative fallback: treat debits as expenses (helps catch plain 'Expense')
                if debit:
                    expenses += amt

    net_profit = revenue - expenses

    report = (
        "Profit & Loss Statement\n"
        "-----------------------\n"
        f"Revenue: ₹{revenue}\n"
        f"Expenses: ₹{expenses}\n"
        "-----------------------\n"
        f"Net Profit: ₹{net_profit}\n"
    )

    return Response(content=report, media_type="text/plain")


# --- Improved Balance Sheet (text output, aggregate balances per account) ---
@app.get("/reports/balance-sheet")
async def get_balance_sheet(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)

    # Build ledger-like balances: debit adds, credit subtracts
    balances = {}
    for e in entries_db:
        debit = e.get("debit_account") or "Unknown"
        credit = e.get("credit_account") or "Unknown"
        amt = float(e.get("amount") or 0)

        balances[debit] = balances.get(debit, 0.0) + amt
        balances[credit] = balances.get(credit, 0.0) - amt

    # Separate positive balances (assets/expenses) vs negative (liabilities/equity)
    assets_list = []
    liabilities_list = []
    total_assets = 0.0
    total_liabilities = 0.0
    for acct, bal in balances.items():
        if bal > 0:
            assets_list.append(f"{acct}: ₹{bal}")
            total_assets += bal
        elif bal < 0:
            liabilities_list.append(f"{acct}: ₹{abs(bal)}")
            total_liabilities += abs(bal)

    report = "Balance Sheet\n-------------\n"
    report += "Assets:\n" + (("\n".join(assets_list)) if assets_list else "- None") + "\n\n"
    report += "Liabilities & Equity:\n" + (("\n".join(liabilities_list)) if liabilities_list else "- None") + "\n\n"
    report += f"Total Assets: ₹{total_assets}\n"
    report += f"Total Liabilities & Equity: ₹{total_liabilities}\n"

    return Response(content=report, media_type="text/plain")



# -------------------------
# Export Excel (readable)
# -------------------------
@app.get("/export/excel")
async def export_excel(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)
    if not entries_db:
        raise HTTPException(status_code=404, detail="No entries to export")

    # Create a simple readable DataFrame
    df = pd.DataFrame(entries_db)
    df = df[["entry_date", "debit_account", "credit_account", "amount", "narration"]]
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="JournalEntries")
    output.seek(0)

    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=uxxca_entries.xlsx"},
    )


# -------------------------
# Export PDF (readable)
# -------------------------
@app.get("/export/pdf")
async def export_pdf(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)
    if not entries_db:
        raise HTTPException(status_code=404, detail="No entries to export")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "UXXCA Journal Entries")
    y -= 30
    c.setFont("Helvetica", 10)

    for en in entries_db:
        text = f"{en['entry_date']} | Dr: {en['debit_account']} | Cr: {en['credit_account']} | ₹{en['amount']} | {en.get('narration','')}"
        c.drawString(40, y, text[:120])
        y -= 16
        if y < 40:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 10)

    c.save()
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=uxxca_entries.pdf"},
    )
import re

@app.post("/parse")
async def parse_text(req: Request, x_api_key: str = None):
    check_api_key(req, x_api_key)
    data = await req.json()
    text = data.get("text", "").lower()

    # Naive parsing
    amount = None
    m = re.search(r'(\d+)', text)
    if m:
        amount = float(m.group(1))

    if "rent" in text:
        debit = "Rent Expense"
        credit = "Cash"
    elif "paid" in text:
        debit = "Expense"
        credit = "Cash"
    elif "received" in text:
        debit = "Cash"
        credit = "Income"
    else:
        debit = "Expense"
        credit = "Cash"

    return {
        "amount": amount,
        "debit_account": debit,
        "credit_account": credit,
        "narration": data.get("text")
    }
