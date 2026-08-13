from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, select, desc, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import Settings

class Base(DeclarativeBase):
    pass

class GroupSettings(Base):
    __tablename__ = "group_settings"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    personality: Mapped[str] = mapped_column(String(30), default="natural")
    default_language: Mapped[str] = mapped_column(String(20), default="auto")
    context_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reply_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_response_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    memory_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_memory: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_delete_seconds: Mapped[int] = mapped_column(Integer, default=0)

class Permission(Base):
    __tablename__ = "permissions"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    feature: Mapped[str] = mapped_column(String(40), primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="owner")

class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ContextMessage(Base):
    __tablename__ = "context_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tts_voice: Mapped[str] = mapped_column(String(50), default="Kore")

class BotMessage(Base):
    __tablename__ = "bot_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

_engine = None
_session = None
_app_settings = None

def init_db(app_settings: Settings):
    global _engine, _session, _app_settings
    _app_settings = app_settings
    _engine = create_async_engine(app_settings.database_url, pool_pre_ping=True)
    _session = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

async def create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_group(chat_id: int):
    async with _session() as s:
        obj = await s.get(GroupSettings, chat_id)
        if obj is None:
            obj = GroupSettings(chat_id=chat_id)
            s.add(obj)
            await s.commit()
        return obj

async def update_group(chat_id: int, **values):
    async with _session() as s:
        obj = await s.get(GroupSettings, chat_id)
        if obj is None:
            obj = GroupSettings(chat_id=chat_id)
            s.add(obj)
        for key, value in values.items():
            setattr(obj, key, value)
        await s.commit()
        return obj

async def get_permission(chat_id: int, feature: str) -> str:
    async with _session() as s:
        obj = await s.get(Permission, {"chat_id": chat_id, "feature": feature})
        return obj.level if obj else "owner"

async def set_permission(chat_id: int, feature: str, level: str):
    async with _session() as s:
        obj = await s.get(Permission, {"chat_id": chat_id, "feature": feature})
        if obj is None:
            s.add(Permission(chat_id=chat_id, feature=feature, level=level))
        else:
            obj.level = level
        await s.commit()

async def add_context(chat_id, user_id, username, text, limit):
    if not text:
        return
    async with _session() as s:
        s.add(ContextMessage(
            chat_id=chat_id, user_id=user_id,
            username=(username or "")[:255], text=text[:5000]
        ))
        await s.commit()

        ids = (await s.execute(
            select(ContextMessage.id)
            .where(ContextMessage.chat_id == chat_id)
            .order_by(desc(ContextMessage.id))
            .offset(limit)
        )).scalars().all()
        if ids:
            await s.execute(delete(ContextMessage).where(ContextMessage.id.in_(ids)))
            await s.commit()

async def get_context(chat_id, limit):
    async with _session() as s:
        rows = (await s.execute(
            select(ContextMessage)
            .where(ContextMessage.chat_id == chat_id)
            .order_by(desc(ContextMessage.id))
            .limit(limit)
        )).scalars().all()
        return list(reversed(rows))

async def add_memory(chat_id, content):
    async with _session() as s:
        s.add(Memory(chat_id=chat_id, content=content[:5000]))
        await s.commit()

async def get_memories(chat_id, limit):
    async with _session() as s:
        return (await s.execute(
            select(Memory)
            .where(Memory.chat_id == chat_id)
            .order_by(desc(Memory.id))
            .limit(limit)
        )).scalars().all()

async def clear_memories(chat_id):
    async with _session() as s:
        await s.execute(delete(Memory).where(Memory.chat_id == chat_id))
        await s.commit()

async def set_user_voice(user_id, voice):
    async with _session() as s:
        obj = await s.get(UserPreference, user_id)
        if obj is None:
            s.add(UserPreference(user_id=user_id, tts_voice=voice))
        else:
            obj.tts_voice = voice
        await s.commit()

async def get_user_voice(user_id):
    async with _session() as s:
        obj = await s.get(UserPreference, user_id)
        return obj.tts_voice if obj else "Kore"

async def track_bot_message(chat_id, message_id):
    async with _session() as s:
        s.add(BotMessage(chat_id=chat_id, message_id=message_id))
        await s.commit()

async def recent_bot_messages(chat_id, limit):
    async with _session() as s:
        return (await s.execute(
            select(BotMessage)
            .where(BotMessage.chat_id == chat_id)
            .order_by(desc(BotMessage.id))
            .limit(limit)
        )).scalars().all()

async def delete_tracked_bot_message(chat_id, message_id):
    async with _session() as s:
        await s.execute(delete(BotMessage).where(
            BotMessage.chat_id == chat_id,
            BotMessage.message_id == message_id
        ))
        await s.commit()
