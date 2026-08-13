import asyncio
import io
import logging
import re
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

from app.config import Settings
from app import db
from app.gemini import GeminiService
from app.keyboards import (
    main_menu, settings_menu, personality_menu, permissions_menu,
    permission_levels, voice_menu, language_menu, auto_delete_menu,
    PERSONALITIES, VOICES, FEATURES
)
from app.permissions import is_owner, is_admin, can_use

router = Router()
settings = None
ai = None
logger = logging.getLogger(__name__)

LANG_NAMES = {
    "id": "Indonesian", "en": "English", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "auto": "the detected language"
}

def setup_services(app_settings: Settings):
    global settings, ai
    settings = app_settings
    ai = GeminiService(app_settings)

def style_text(personality):
    return {
        "casual": "Gunakan gaya santai, natural, hangat, seperti anggota grup yang ramah.",
        "natural": "Gunakan gaya natural, jelas, ramah, tidak kaku. Ini gaya default.",
        "formal": "Gunakan gaya formal, sopan, dan profesional.",
        "humor": "Gunakan humor ringan bila cocok, tanpa mengganggu jawaban.",
        "professional": "Gunakan gaya profesional, terstruktur, dan akurat.",
        "short": "Jawab singkat dan langsung ke inti kecuali diminta detail.",
        "detail": "Jawab lengkap, terstruktur, dan beri contoh bila membantu.",
    }.get(personality, "Gunakan gaya natural, jelas, ramah, tidak kaku.")

async def safe_answer(message: Message, text: str, **kwargs):
    sent = await message.answer(text, **kwargs)
    await db.track_bot_message(message.chat.id, sent.message_id)
    group = await db.get_group(message.chat.id)
    if group.auto_delete_seconds > 0:
        asyncio.create_task(auto_delete(message.bot, message.chat.id, sent.message_id, group.auto_delete_seconds))
    return sent

async def auto_delete(bot, chat_id, message_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass
    await db.delete_tracked_bot_message(chat_id, message_id)

async def build_context(chat_id, reply=None):
    group = await db.get_group(chat_id)
    chunks = []
    if group.context_enabled:
        rows = await db.get_context(chat_id, settings.context_limit)
        if rows:
            chunks.append("RECENT GROUP CONTEXT:\n" + "\n".join(
                f"{r.username or r.user_id}: {r.text}" for r in rows
            ))
    if reply and group.reply_context_enabled:
        chunks.append("REPLIED MESSAGE:\n" + (reply.text or reply.caption or "[media]"))
    if group.memory_enabled and group.memory_context_enabled:
        mem = await db.get_memories(chat_id, settings.memory_limit)
        if mem:
            chunks.append("GROUP MEMORY:\n- " + "\n- ".join(m.content for m in mem))
    return "\n\n".join(chunks)

async def record_context(message: Message):
    if message.chat.type in ("group", "supergroup") and message.text:
        if not message.text.startswith("."):
            await db.add_context(
                message.chat.id, message.from_user.id,
                message.from_user.username or message.from_user.full_name,
                message.text, settings.context_limit
            )

@router.message(CommandStart())
async def start(message: Message):
    await db.get_group(message.chat.id)
    await message.answer(
        "🤖 <b>AI Group Bot</b>\n\nPilih fitur dari menu di bawah.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@router.message(F.text.startswith("."))
async def dot_commands(message: Message):
    parts = message.text.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    await record_context(message)

    if command in (".help", ".menu"):
        return await message.answer("🤖 Pilih fitur:", reply_markup=main_menu())
    if command == ".ai":
        return await do_ai(message, arg)
    if command in (".search", ".web"):
        return await do_search(message, arg)
    if command == ".image":
        return await do_image(message, arg)
    if command == ".vision":
        return await do_vision(message, arg)
    if command in (".translate", ".tr"):
        return await do_translate(message, arg)
    if command == ".translatefoto":
        return await do_photo_translate(message)
    if command == ".tts":
        return await do_tts(message, arg)
    if command == ".memory":
        return await do_memory(message, arg)
    if command == ".hapus":
        return await do_delete(message, arg)
    if command == ".gaya":
        if await is_owner(message.bot, message.chat.id, message.from_user.id):
            return await message.answer("🎭 Pilih gaya AI:", reply_markup=personality_menu())
        return await message.answer("🔒 Pengaturan ini hanya untuk owner.")
    if command == ".permission":
        if await is_owner(message.bot, message.chat.id, message.from_user.id):
            return await message.answer("🔐 Pilih fitur:", reply_markup=permissions_menu())
        return await message.answer("🔒 Pengaturan ini hanya untuk owner.")
    if command == ".settings":
        if await is_owner(message.bot, message.chat.id, message.from_user.id):
            return await message.answer("⚙️ Pengaturan grup:", reply_markup=settings_menu())
        return await message.answer("🔒 Pengaturan ini hanya untuk owner.")

async def do_ai(message, prompt):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "ai"):
        return await message.answer("🔒 AI Chat belum dibuka untuk akunmu.")
    if not prompt and message.reply_to_message:
        prompt = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not prompt:
        return await message.answer("Contoh: <code>.ai jelaskan blockchain</code>", parse_mode="HTML")

    group = await db.get_group(message.chat.id)
    ctx = await build_context(message.chat.id, message.reply_to_message)
    system = f"""Kamu adalah AI assistant di grup Telegram.
{style_text(group.personality)}
Ikuti topik yang sedang dibahas. Gunakan konteks hanya jika relevan.
Jangan mengarang fakta atau konteks yang tidak tersedia.
Jika pertanyaan membutuhkan informasi terkini, arahkan pengguna ke Web Search.
Jawab sesuai bahasa pengguna.
{ctx}"""
    try:
        result = await ai.generate_text(prompt, system)
        await safe_answer(message, result or "Maaf, saya belum bisa menjawab.")
    except Exception as e:
        logger.exception("AI error")
        await message.answer(f"⚠️ AI gagal memproses permintaan: {type(e).__name__}")

async def do_search(message, query):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "search"):
        return await message.answer("🔒 Web Search belum dibuka untuk akunmu.")
    if not query and message.reply_to_message:
        query = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not query:
        return await message.answer("Contoh: <code>.search berita teknologi terbaru</code>", parse_mode="HTML")
    group = await db.get_group(message.chat.id)
    try:
        result = await ai.generate_text(
            query,
            f"""Kamu adalah AI web-search assistant.
{style_text(group.personality)}
Gunakan Google Search grounding. Jawab berdasarkan hasil terbaru dan sertakan sumber/link bila tersedia.
Jangan mengarang sumber.""",
            use_search=True
        )
        await safe_answer(message, result or "Tidak ada hasil.")
    except Exception as e:
        logger.exception("Search error")
        await message.answer(f"⚠️ Web Search gagal: {type(e).__name__}")

async def do_image(message, prompt):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "image"):
        return await message.answer("🔒 Image Generator belum dibuka untuk akunmu.")
    if not prompt:
        return await message.answer("Contoh: <code>.image kota futuristik saat hujan</code>", parse_mode="HTML")
    try:
        data = await ai.generate_image(prompt)
        if not data:
            return await message.answer("⚠️ Model tidak mengembalikan gambar.")
        sent = await message.answer_photo(
            BufferedInputFile(data, filename="generated.png"),
            caption="🎨 <b>AI Image</b>",
            parse_mode="HTML"
        )
        await db.track_bot_message(message.chat.id, sent.message_id)
    except Exception as e:
        logger.exception("Image error")
        await message.answer(f"⚠️ Image Generator gagal: {type(e).__name__}")

async def download_photo(message: Message):
    if not message.photo:
        return None, None
    file = await message.bot.get_file(message.photo[-1].file_id)
    buf = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    return buf.getvalue(), "image/jpeg"

async def do_vision(message, prompt):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "vision"):
        return await message.answer("🔒 Vision belum dibuka untuk akunmu.")
    target = message.reply_to_message if message.reply_to_message else message
    data, mime = await download_photo(target)
    if not data:
        return await message.answer("Reply foto lalu gunakan <code>.vision</code>.", parse_mode="HTML")
    try:
        result = await ai.vision(data, mime, prompt or "Analisis gambar ini secara akurat dan ringkas.")
        await safe_answer(message, result or "Tidak ada hasil.")
    except Exception as e:
        logger.exception("Vision error")
        await message.answer(f"⚠️ Vision gagal: {type(e).__name__}")

async def do_photo_translate(message):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "photo_translate"):
        return await message.answer("🔒 Photo Translator belum dibuka untuk akunmu.")
    target = message.reply_to_message if message.reply_to_message else message
    data, mime = await download_photo(target)
    if not data:
        return await message.answer("Reply foto yang berisi teks lalu gunakan <code>.translatefoto</code>.", parse_mode="HTML")
    try:
        result = await ai.vision(
            data, mime,
            "Baca semua teks yang terlihat. Deteksi bahasa sumber. Terjemahkan seluruh teks ke Bahasa Indonesia. "
            "Pertahankan struktur seperlunya. Jangan mengarang teks yang tidak terlihat."
        )
        await safe_answer(message, "📸🌐 <b>Hasil terjemahan:</b>\n\n" + (result or "Tidak ada teks terdeteksi."), parse_mode="HTML")
    except Exception as e:
        logger.exception("Photo translate error")
        await message.answer(f"⚠️ Photo Translator gagal: {type(e).__name__}")

async def do_translate(message, arg):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "translate"):
        return await message.answer("🔒 Translator belum dibuka untuk akunmu.")

    target_lang = None
    text = arg
    if arg:
        first, *rest = arg.split(maxsplit=1)
        if first.lower() in LANG_NAMES:
            target_lang = LANG_NAMES[first.lower()]
            text = rest[0] if rest else ""
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not text:
        return await message.answer("Contoh: <code>.translate en Halo dunia</code> atau reply pesan lalu <code>.translate en</code>.", parse_mode="HTML")

    group = await db.get_group(message.chat.id)
    target_lang = target_lang or LANG_NAMES.get(group.default_language, "Indonesian")
    try:
        result = await ai.generate_text(
            text,
            f"Terjemahkan teks berikut ke {target_lang}. Hanya keluarkan hasil terjemahan, tanpa komentar."
        )
        await safe_answer(message, "🌐 " + result)
    except Exception as e:
        logger.exception("Translate error")
        await message.answer(f"⚠️ Translator gagal: {type(e).__name__}")

async def do_tts(message, text):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "tts"):
        return await message.answer("🔒 Text → Speech belum dibuka untuk akunmu.")
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not text:
        return await message.answer("Contoh: <code>.tts Halo semuanya</code>", parse_mode="HTML")
    voice = await db.get_user_voice(message.from_user.id)
    try:
        audio = await ai.tts(text, voice)
        sent = await message.answer_audio(BufferedInputFile(audio, filename="speech.wav"), title=f"TTS - {voice}")
        await db.track_bot_message(message.chat.id, sent.message_id)
    except Exception as e:
        logger.exception("TTS error")
        await message.answer(f"⚠️ Text → Speech gagal: {type(e).__name__}")

async def do_memory(message, arg):
    if not await can_use(message.bot, message.chat.id, message.from_user.id, "memory"):
        return await message.answer("🔒 Group Memory belum dibuka untuk akunmu.")
    if not await is_owner(message.bot, message.chat.id, message.from_user.id):
        return await message.answer("🔒 Pengelolaan Group Memory hanya untuk owner.")
    if arg.lower() == "clear":
        await db.clear_memories(message.chat.id)
        return await message.answer("🗑️ Group Memory sudah dihapus.")
    if arg.lower().startswith("tambah "):
        content = arg[7:].strip()
        if content:
            await db.add_memory(message.chat.id, content)
            return await message.answer("🧠 Memory disimpan.")
    memories = await db.get_memories(message.chat.id, settings.memory_limit)
    if not memories:
        return await message.answer("🧠 Belum ada memory.")
    text = "🧠 <b>Group Memory</b>\n\n" + "\n".join(f"• {m.content}" for m in memories)
    await message.answer(text, parse_mode="HTML")

async def do_delete(message, arg):
    if not message.reply_to_message and not arg:
        return await message.answer("Gunakan <code>.hapus</code> sebagai reply ke pesan bot, atau <code>.hapus 5</code>.", parse_mode="HTML")
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.answer("🔒 `.hapus` hanya untuk admin/owner.")

    if message.reply_to_message:
        target_id = message.reply_to_message.message_id
        try:
            await message.bot.delete_message(message.chat.id, target_id)
            await db.delete_tracked_bot_message(message.chat.id, target_id)
            await message.delete()
        except Exception:
            await message.answer("⚠️ Pesan tidak bisa dihapus. Pastikan bot punya izin Delete Messages.")
        return

    try:
        count = max(1, min(int(arg), 50))
    except ValueError:
        count = 1

    rows = await db.recent_bot_messages(message.chat.id, count)
    deleted = 0
    for row in rows:
        try:
            await message.bot.delete_message(message.chat.id, row.message_id)
            deleted += 1
        except Exception:
            pass
        await db.delete_tracked_bot_message(message.chat.id, row.message_id)
    try:
        await message.delete()
    except Exception:
        pass
    if deleted == 0:
        await message.answer("Tidak ada pesan bot yang bisa dihapus.")

@router.callback_query()
async def callbacks(call: CallbackQuery):
    data = call.data or ""
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if data == "menu:settings":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("⚙️ Pengaturan grup:", reply_markup=settings_menu())
        return await call.answer()

    if data == "menu:ai":
        return await call.answer("Gunakan .ai pertanyaan di chat.", show_alert=True)
    if data == "menu:search":
        return await call.answer("Gunakan .search pertanyaan.", show_alert=True)
    if data == "menu:image":
        return await call.answer("Gunakan .image prompt.", show_alert=True)
    if data == "menu:vision":
        return await call.answer("Reply foto lalu gunakan .vision.", show_alert=True)
    if data == "menu:translate":
        return await call.answer("Gunakan .translate id/en/... atau reply pesan.", show_alert=True)
    if data == "menu:photo_translate":
        return await call.answer("Reply foto lalu gunakan .translatefoto.", show_alert=True)
    if data == "menu:tts":
        await call.message.edit_text("🔊 Pilih suara untuk preferensi kamu:", reply_markup=voice_menu())
        return await call.answer()
    if data == "menu:memory":
        if not await can_use(call.bot, chat_id, user_id, "memory"):
            return await call.answer("Fitur belum diizinkan.", show_alert=True)
        memories = await db.get_memories(chat_id, settings.memory_limit)
        text = "🧠 <b>Group Memory</b>\n\n" + ("\n".join(f"• {m.content}" for m in memories) if memories else "Belum ada memory.")
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_menu())
        return await call.answer()

    if data == "set:personality":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("🎭 Pilih gaya AI:", reply_markup=personality_menu())
        return await call.answer()

    if data.startswith("personality:"):
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        value = data.split(":",1)[1]
        await db.update_group(chat_id, personality=value)
        await call.message.edit_text(f"✅ Gaya AI: {PERSONALITIES[value]}", reply_markup=settings_menu())
        return await call.answer()

    if data == "set:permissions":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("🔐 Pilih fitur yang aksesnya ingin diubah:", reply_markup=permissions_menu())
        return await call.answer()

    if data.startswith("permission:"):
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        feature = data.split(":",1)[1]
        await call.message.edit_text(f"🔐 Akses: {feature}", reply_markup=permission_levels(feature))
        return await call.answer()

    if data.startswith("level:"):
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        _, feature, level = data.split(":")
        await db.set_permission(chat_id, feature, level)
        await call.message.edit_text(
            f"✅ {feature} sekarang: {level}",
            reply_markup=permissions_menu()
        )
        return await call.answer()

    if data == "set:context":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        g = await db.get_group(chat_id)
        new = not g.context_enabled
        await db.update_group(chat_id, context_enabled=new)
        await call.message.edit_text(f"🧠 Context: {'ON' if new else 'OFF'}", reply_markup=settings_menu())
        return await call.answer()

    if data == "set:memory":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        g = await db.get_group(chat_id)
        new = not g.memory_enabled
        await db.update_group(chat_id, memory_enabled=new)
        await call.message.edit_text(f"🧠 Group Memory: {'ON' if new else 'OFF'}", reply_markup=settings_menu())
        return await call.answer()

    if data == "set:autodelete":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("🧹 Auto Delete:", reply_markup=auto_delete_menu())
        return await call.answer()

    if data.startswith("autodel:"):
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        seconds = int(data.split(":")[1])
        await db.update_group(chat_id, auto_delete_seconds=seconds)
        await call.message.edit_text(f"🧹 Auto Delete: {seconds}s" if seconds else "🧹 Auto Delete: OFF", reply_markup=settings_menu())
        return await call.answer()

    if data == "set:language":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("🌐 Pilih bahasa default:", reply_markup=language_menu())
        return await call.answer()

    if data.startswith("language:"):
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        value = data.split(":")[1]
        await db.update_group(chat_id, default_language=value)
        await call.message.edit_text(f"✅ Bahasa default: {value}", reply_markup=settings_menu())
        return await call.answer()

    if data.startswith("voice:"):
        voice = data.split(":",1)[1]
        if voice not in VOICES:
            return await call.answer("Voice tidak valid.", show_alert=True)
        await db.set_user_voice(user_id, voice)
        await call.answer(f"Voice disimpan: {VOICES[voice]}")
        return

    if data == "back:menu":
        await call.message.edit_text("🤖 Pilih fitur:", reply_markup=main_menu())
        return await call.answer()

    if data == "back:settings":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("⚙️ Pengaturan grup:", reply_markup=settings_menu())
        return await call.answer()

    if data == "back:permissions":
        if not await is_owner(call.bot, chat_id, user_id):
            return await call.answer("Hanya owner.", show_alert=True)
        await call.message.edit_text("🔐 Pilih fitur:", reply_markup=permissions_menu())
        return await call.answer()

    await call.answer()

@router.message(F.photo)
async def photo_handler(message: Message):
    await record_context(message)
    # No automatic reply/menu: avoids spam.
    # User can reply with .vision or .translatefoto.
    return

@router.message(F.voice | F.audio)
async def audio_handler(message: Message):
    await record_context(message)
    return

@router.message(F.text)
async def normal_text(message: Message):
    await record_context(message)
    # AI does NOT answer every group message automatically, preventing spam.
    return
