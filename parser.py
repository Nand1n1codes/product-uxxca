import re
from decimal import Decimal

def simple_parse(text):
    """
    Naive parser for short phrases like:
    - 'Paid 5000 rent'
    - 'Received ₹12,000 from Ramesh'

    Returns a dict: amount, debit_account, credit_account, narration

    Heuristics:
    - 'paid' -> debit Expense, credit Cash
    - 'received' -> debit Cash, credit Income
    - 'rent' -> Rent Expense
    - number extraction handles 12,000 and ₹12,000 and 12k
    """
    t = text.lower().strip()
    amt = None

    # match ₹12,000 or 12000 or 12,000.99
    m = re.search(r'\u20b9?\s*([0-9,]+(?:\.[0-9]+)?)', t)
    if m:
        amt = Decimal(m.group(1).replace(',', ''))
    else:
        m2 = re.search(r'(\d+(?:\.\d+)?)(k)\b', t)
        if m2:
            amt = Decimal(m2.group(1)) * 1000

    narration = text.strip()

    if 'paid' in t or 'paid to' in t or 'paid for' in t or 'paid:' in t:
        debit = 'Expense'
        credit = 'Cash'
    elif 'received' in t or 'got' in t or 'paid by' in t or 'received from' in t:
        debit = 'Cash'
        credit = 'Income'
    elif 'rent' in t:
        debit = 'Rent Expense'
        credit = 'Cash'
    else:
        debit = 'Expense'
        credit = 'Cash'

    return {
        'amount': float(amt) if amt is not None else None,
        'debit_account': debit,
        'credit_account': credit,
        'narration': narration
    }
