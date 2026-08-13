from aiogram import Bot
from app.db import get_permission

async def is_owner(bot: Bot, chat_id: int, user_id: int):
    """Global owner check. Only OWNER_ID is the bot owner."""
    return user_id == getattr(bot, "_app_owner_id", None)

async def is_admin(bot: Bot, chat_id: int, user_id: int):
    if await is_owner(bot, chat_id, user_id):
        return True
    if chat_id > 0:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except Exception:
        return False

async def can_use(bot: Bot, chat_id: int, user_id: int, feature: str):
    if await is_owner(bot, chat_id, user_id):
        return True
    if chat_id > 0:
        return False
    level = await get_permission(chat_id, feature)
    if level == "all":
        # "all" means Admin + Member (everyone in the group).
        return True
    if level == "admin":
        return await is_admin(bot, chat_id, user_id)
    return False
