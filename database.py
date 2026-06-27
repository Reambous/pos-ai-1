import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Muat variabel dari file .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartpos.db")

# connect_args={"check_same_thread": False} khusus diperlukan oleh SQLite
# agar bisa diakses oleh banyak proses async di FastAPI secara aman.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Membuat pabrik sesi (session factory) untuk interaksi data (Query, Insert, Update)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Kelas dasar (Base Class) yang akan diwarisi oleh semua model tabel kita
Base = declarative_base()

# Fungsi bantuan (Dependency) untuk mendapatkan instance database di FastAPI nanti


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
