import os

from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session

load_dotenv()  # local dev: reads .env at repo root

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://hannibal:hannibal@localhost:5432/hannibal",
)

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session