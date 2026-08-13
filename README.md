# Telegram AI Group Bot — Railway

Bot Telegram AI untuk grup dengan:
- AI Chat natural
- Context-aware / topic-aware
- AI Group Assistant
- Group Memory
- Gemini Web Search grounding
- AI Vision
- AI Image Generator
- Text-to-Speech dengan pilihan suara pria/wanita
- Translator
- Photo Translator
- Inline Keyboard
- Dot commands (`.ai`, `.search`, dll.)
- Reply-based action tanpa menu otomatis
- `.hapus`
- Auto-delete pesan bot
- Permission per fitur: Owner / Admin / All Members
- Pengaturan personality per grup

## Model

AI utama:
`gemini-3.1-flash-lite`

Image:
`gemini-3.1-flash-image`

TTS:
`gemini-3.1-flash-tts-preview`

Semua memakai `GEMINI_API_KEY` yang sama.

## Railway

1. Tambahkan service PostgreSQL pada project Railway.
2. Deploy repository bot.
3. Isi variables pada service bot:
   - `TELEGRAM_BOT_TOKEN`
   - `GEMINI_API_KEY`
   - `DATABASE_URL` — URL PostgreSQL Railway.
4. Model variables boleh dibiarkan default.

Railway PostgreSQL menyediakan `DATABASE_URL` dan variabel koneksi PostgreSQL secara otomatis.

Railway akan menjalankan:
`python main.py`

## Penting

Bot harus menjadi admin grup bila ingin `.hapus` dan penghapusan otomatis bekerja secara konsisten.

Default semua fitur = Owner Only.

Untuk membuka fitur:
Settings -> Permissions -> pilih fitur -> Owner/Admin/All.

## Commands

`.ai pertanyaan`
`.search pertanyaan`
`.image prompt`
`.vision` (reply foto)
`.translate en teks`
`.translate id` (reply pesan)
`.translatefoto` (reply foto)
`.tts teks`
`.memory`
`.memory tambah isi`
`.memory clear`
`.gaya`
`.permission`
`.settings`
`.hapus` (reply pesan bot)
`.hapus 5`
`.help`

## Catatan TTS

Suara yang disediakan:
- Kore / Aoede / Leda = suara wanita
- Puck / Charon / Orus = suara pria

Nama voice mengikuti daftar voice Gemini TTS. Jika suatu voice tidak tersedia pada akun/model saat ini, bot akan mengembalikan error API secara aman tanpa mematikan proses bot.
