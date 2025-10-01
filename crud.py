from sqlmodel import Session, select
from models import engine, JournalEntry
from typing import List
from datetime import date

def create_entry(db: Session, entry: JournalEntry) -> JournalEntry:
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def list_entries(db: Session) -> List[JournalEntry]:
    stmt = select(JournalEntry).order_by(JournalEntry.entry_date)
    return db.exec(stmt).all()

def entries_between(db: Session, start: date, end: date):
    stmt = select(JournalEntry).where(JournalEntry.entry_date >= start, JournalEntry.entry_date <= end)
    return db.exec(stmt).all()
