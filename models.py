from sqlmodel import SQLModel, Field, create_engine
from datetime import date
from typing import Optional

# Using SQLite for zero-budget MVP. Change to Postgres for production.
DATABASE_URL = "sqlite:///./uxxca.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None

class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entry_date: date = Field(default_factory=date.today)
    debit_account: str
    credit_account: str
    amount: float
    narration: Optional[str] = None

def init_db():
    SQLModel.metadata.create_all(engine)
