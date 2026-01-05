from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from config import DATABASE_URL

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True)
    username = Column(Text)
    full_name = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_premium = Column(Boolean, default=False)
    interaction_count = Column(Integer, default=0)

class UserSession(Base):
    __tablename__ = 'user_sessions'
    user_id = Column(BigInteger, primary_key=True) # One-to-One c users
    products = Column(Text)
    dialog_history = Column(JSON, default=[])
    state = Column(Text)
    generated_dishes = Column(JSON, default=[])
    available_categories = Column(JSON, default=[])
    current_dish = Column(Text)
    user_lang = Column(Text, default='ru')
    products_lang = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Настройка движка
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в .env")

# Supabase требует postgresql://, но asyncpg хочет postgresql+asyncpg://
# Фикс для совместимости, если строка начинается просто с postgres://
db_url = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
if not db_url.startswith("postgresql+asyncpg://"):
     db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)