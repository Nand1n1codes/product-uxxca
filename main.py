from fastapi import FastAPI, HTTPException, Depends, Header, Response
from sqlmodel import Session
from models import init_db, engine, JournalEntry
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from crud import create_entry, list_entries, entries_between
from parser import simple_parse
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --------- CONFIG ---------
API_KEYS = {"botpress": "DEV_KEY_123"}  # change this before public deploy
# --------------------------

app = FastAPI(title="UXXCA MVP Backend Expanded", version="0.2")

init_db()

class EntryIn(BaseModel):
    entry_date: Optional[date] = None
    debit_account: str
    credit_account: str
    amount: float
    narration: Optional[str] = None

class EntryOut(BaseModel):
    id: int
    entry_date: date
    debit_account: str
    credit_account: str
    amount: float
    narration: Optional[str]

def get_session():
    with Session(engine) as session:
        yield session

def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key not in API_KEYS.values():
        raise HTTPException(status_code=401, detail='Invalid or missing API Key')

# --- Parsing endpoint (Bot -> parse user message) ---
@app.post('/parse')
def parse_text(payload: dict, api_key: Optional[str] = Depends(require_api_key)):
    text = payload.get('text') if payload else ''
    if not text:
        raise HTTPException(status_code=400, detail='Text required')
    parsed = simple_parse(text)
    return parsed

# --- Create a journal entry ---
@app.post('/entries', response_model=EntryOut)
def create_journal_entry(payload: EntryIn, db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    entry = JournalEntry(
        entry_date = payload.entry_date or date.today(),
        debit_account = payload.debit_account,
        credit_account = payload.credit_account,
        amount = payload.amount,
        narration = payload.narration
    )
    created = create_entry(db, entry)
    return created

# --- List entries ---
@app.get('/entries', response_model=List[EntryOut])
def get_entries(db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    entries = list_entries(db)
    return entries

# --- Simple P&L report (naive heuristics for MVP) ---
@app.get('/reports/pnl')
def profit_and_loss(start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    s = start or date(1970,1,1)
    e = end or date.today()
    entries = entries_between(db, s, e)
    revenue = 0.0
    expenses = 0.0
    for en in entries:
        da = en.debit_account.lower() if en.debit_account else ''
        ca = en.credit_account.lower() if en.credit_account else ''
        amt = en.amount
        if 'income' in da or 'sales' in da or 'income' in ca or 'sales' in ca:
            revenue += amt
        elif 'rent' in da or 'expense' in da or 'salary' in da or 'wages' in da:
            expenses += amt
        else:
            expenses += amt
    return {"start": str(s), "end": str(e), "revenue": revenue, "expenses": expenses, "profit": revenue - expenses}

# --- Simple Balance Sheet (naive) ---
@app.get('/reports/balance-sheet')
def balance_sheet(db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    rows = list_entries(db)
    assets = {}
    liabilities = {}
    for r in rows:
        d = r.debit_account; c = r.credit_account; amt = r.amount
        assets[d] = assets.get(d,0) + amt
        liabilities[c] = liabilities.get(c,0) + amt
    return {"assets": assets, "liabilities": liabilities}

# --- Export as Excel ---
@app.get('/export/excel')
def export_excel(start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    s = start or date(1970,1,1)
    e = end or date.today()
    entries = entries_between(db, s, e)
    data = [dict(id=en.id, date=str(en.entry_date), debit=en.debit_account, credit=en.credit_account, amount=en.amount, narration=en.narration) for en in entries]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='JournalEntries')
    output.seek(0)
    return Response(content=output.read(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": f"attachment; filename=uxxca_entries_{s}_{e}.xlsx"})

# --- Export as PDF ---
@app.get('/export/pdf')
def export_pdf(start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_session), api_key: Optional[str] = Depends(require_api_key)):
    s = start or date(1970,1,1)
    e = end or date.today()
    entries = entries_between(db, s, e)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont('Helvetica-Bold', 12)
    c.drawString(40, y, f'UXXCA Journal Entries {s} to {e}')
    y -= 30
    c.setFont('Helvetica', 10)
    for en in entries:
        text = f"{en.entry_date} | Dr: {en.debit_account} | Cr: {en.credit_account} | ₹{en.amount} | {en.narration or ''}"
        c.drawString(40, y, text[:120])
        y -= 16
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    buffer.seek(0)
    return Response(content=buffer.read(), media_type='application/pdf', headers={"Content-Disposition": f"attachment; filename=uxxca_entries_{s}_{e}.pdf"})
