import os
import time
from sqlmodel import Session, create_engine, select, SQLModel
from app.config import settings

DATABASE_URL = os.getenv("DATABASE_URL", settings.SQLALCHEMY_DATABASE_URI)

engine = create_engine(DATABASE_URL)

def get_db():
    with Session(engine) as session:
        yield session

def init_db():
    # Retry logic for database connection
    max_retries = 5
    for i in range(max_retries):
        try:
            SQLModel.metadata.create_all(engine)
            break
        except Exception as e:
            if i == max_retries - 1:
                raise e
            print(f"Database not ready yet, retrying in 2s... ({i+1}/{max_retries})")
            time.sleep(2)
    
    from app.models import User
    from app.security import get_password_hash
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "admin@example.com")).first()
        if not user:
            user = User(
                email="admin@example.com",
                hashed_password=get_password_hash("password123"),
                full_name="Admin User",
                is_superuser=True
            )
            session.add(user)
            session.commit()
