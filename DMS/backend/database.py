from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import config
from sqlalchemy.exc import OperationalError
import time

DATABASE_URL = config.SQLALCHEMY_DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    max_retries = 3
    retry_count = 0
    db = None
    while retry_count < max_retries:
        try:
            db = SessionLocal()
            yield db
            break
        except OperationalError:
            retry_count += 1
            time.sleep(2)
            if retry_count == max_retries:
                raise
        finally:
            if db:
                db.close()