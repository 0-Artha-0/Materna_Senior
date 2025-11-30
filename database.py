from sqlmodel import SQLModel, create_engine
from sqlalchemy import event

# Define where your SQLite database file lives
# creates materna.db in current working directory
DATABASE_URL = "sqlite:///materna.db"

# create_engine is your DB connection
# echo=True shows SQL in console
engine = create_engine(DATABASE_URL, echo=True)

# Enforce foreign keys on SQLite


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Function to initialize database and create tables


def init_db():
    SQLModel.metadata.create_all(engine)
