from aiogram import Bot
from app.db import get_permission

async def is_owner(bot: Bot, chat_id: int, user_id: int):
    # Global bot owner: works in private chats and every group.
    if user_id == getattr(bot, "_app_owner_id", None):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == "creator"
    except Exception:
        return False

async def is_admin(bot: Bot, chat_id: int, user_id: int):
    if await is_owner(bot, chat_id, user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except Exception:
        return False

async def can_use(bot: Bot, chat_id: int, user_id: int, feature: str):
    # Global owner always has access, regardless of per-group permission.
    if await is_owner(bot, chat_id, user_id):
        return True
    if chat_id > 0:
        return False
    level = await get_permission(chat_id, feature)
    if level == "all":
        return True
    if level == "admin":
        return await is_admin(bot, chat_id, user_id)
    return False
