from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

FEATURES = [
    ("ai", "💬 AI Chat"),
    ("assistant", "🧠 Group Assistant"),
    ("memory", "🧠 Group Memory"),
    ("search", "🔎 Web Search"),
    ("vision", "🖼️ Vision"),
    ("image", "🎨 Image Generator"),
    ("tts", "🔊 Text → Speech"),
    ("translate", "🌐 Translator"),
    ("photo_translate", "📸 Photo Translator"),
]

PERSONALITIES = {
    "casual": "😎 Santai",
    "natural": "🙂 Natural",
    "formal": "👔 Formal",
    "humor": "😂 Humoris",
    "professional": "🧠 Profesional",
    "short": "⚡ Singkat",
    "detail": "📚 Detail",
}

VOICES = {
    "Kore": "👩 Kore",
    "Aoede": "👩 Aoede",
    "Leda": "👩 Leda",
    "Puck": "👨 Puck",
    "Charon": "👨 Charon",
    "Orus": "👨 Orus",
}

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 AI Chat", callback_data="menu:ai"),
         InlineKeyboardButton(text="🔎 Web Search", callback_data="menu:search")],
        [InlineKeyboardButton(text="🖼️ Vision", callback_data="menu:vision"),
         InlineKeyboardButton(text="🎨 Image", callback_data="menu:image")],
        [InlineKeyboardButton(text="🌐 Translator", callback_data="menu:translate"),
         InlineKeyboardButton(text="📸 Photo Translate", callback_data="menu:photo_translate")],
        [InlineKeyboardButton(text="🔊 Text → Speech", callback_data="menu:tts")],
        [InlineKeyboardButton(text="🧠 Group Memory", callback_data="menu:memory")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="menu:settings")],
    ])

def settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 AI Personality", callback_data="set:personality")],
        [InlineKeyboardButton(text="🧠 Context", callback_data="set:context"),
         InlineKeyboardButton(text="🧠 Memory", callback_data="set:memory")],
        [InlineKeyboardButton(text="🔐 Permissions", callback_data="set:permissions")],
        [InlineKeyboardButton(text="🧹 Auto Delete", callback_data="set:autodelete")],
        [InlineKeyboardButton(text="🌐 Default Language", callback_data="set:language")],
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="back:menu")],
    ])

def personality_menu():
    rows = [[InlineKeyboardButton(text=v, callback_data=f"personality:{k}")] for k,v in PERSONALITIES.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Settings", callback_data="back:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def permissions_menu():
    rows = [[InlineKeyboardButton(text=label, callback_data=f"permission:{key}")]
            for key, label in FEATURES]
    rows.append([InlineKeyboardButton(text="⬅️ Settings", callback_data="back:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def permission_levels(feature):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Owner Only", callback_data=f"level:{feature}:owner")],
        [InlineKeyboardButton(text="🛡️ Admin Only", callback_data=f"level:{feature}:admin")],
        [InlineKeyboardButton(text="👥 All Members", callback_data=f"level:{feature}:all")],
        [InlineKeyboardButton(text="⬅️ Permissions", callback_data="set:permissions")],
    ])

def voice_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩 Kore", callback_data="voice:Kore"),
         InlineKeyboardButton(text="👨 Puck", callback_data="voice:Puck")],
        [InlineKeyboardButton(text="👩 Aoede", callback_data="voice:Aoede"),
         InlineKeyboardButton(text="👨 Charon", callback_data="voice:Charon")],
        [InlineKeyboardButton(text="👩 Leda", callback_data="voice:Leda"),
         InlineKeyboardButton(text="👨 Orus", callback_data="voice:Orus")],
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="back:menu")],
    ])

def language_menu():
    langs = [
        ("id","🇮🇩 Indonesia"), ("en","🇬🇧 English"),
        ("ja","🇯🇵 Japanese"), ("ko","🇰🇷 Korean"),
        ("zh","🇨🇳 Chinese"), ("ar","🇸🇦 Arabic"),
        ("auto","🌍 Auto Detect"),
    ]
    rows = []
    for i in range(0, len(langs), 2):
        rows.append([InlineKeyboardButton(text=x[1], callback_data=f"language:{x[0]}")
                     for x in langs[i:i+2]])
    rows.append([InlineKeyboardButton(text="⬅️ Settings", callback_data="back:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def auto_delete_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="OFF", callback_data="autodel:0")],
        [InlineKeyboardButton(text="1 menit", callback_data="autodel:60"),
         InlineKeyboardButton(text="5 menit", callback_data="autodel:300")],
        [InlineKeyboardButton(text="10 menit", callback_data="autodel:600"),
         InlineKeyboardButton(text="30 menit", callback_data="autodel:1800")],
        [InlineKeyboardButton(text="1 jam", callback_data="autodel:3600")],
        [InlineKeyboardButton(text="⬅️ Settings", callback_data="back:settings")],
    ])
