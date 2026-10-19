from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import parametres

moteur = create_engine(parametres().database_url, pool_pre_ping=True)
SessionLocale = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def session_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()
