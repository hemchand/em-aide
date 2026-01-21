# app/api/deps.py
from app.db import get_db  # adjust to your project
from sqlalchemy.orm import Session
from fastapi import Depends

DbDep = Session
def db_dep(db: Session = Depends(get_db)) -> Session:
    return db
