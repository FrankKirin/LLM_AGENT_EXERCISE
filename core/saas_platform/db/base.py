from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

class DBSettings():
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_store.db"
    DB_ECHO: bool = False

db_settings = DBSettings()

class Base(MappedAsDataclass, DeclarativeBase):
    pass