import asyncio
import html
import random
import uuid
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from uuid import uuid4
import requests
from datetime import datetime
import pytz
from telethon.tl.functions.users import GetFullUserRequest
from telethon import Button, events
from telethon.tl.types import ChannelParticipantsAdmins
from deep_translator import GoogleTranslator
from telethon.tl.types import SendMessageTypingAction
from telethon import Button, TelegramClient, events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import (
    ChatBannedRights,
    ReactionEmoji,
    DocumentAttributeSticker,  # အသစ်ထည့်ထားသော Import
    DocumentAttributeAudio,    # အသစ်ထည့်ထားသော Import
)

# ==========================================
# CONFIGURATION & API SETTINGS
# ==========================================
API_ID = 33086718
API_HASH = "1d6aadd848b2f1bc61ee13a05b966640"
BOT_TOKEN = "8824327867:8834044402:AAEnHLN9JZUe73OVhQH51U-AAzi99qi2vgU"

OWNER_IDS = {8291459246}
OWNER_CHAT_ID = 8291459246
_BOT_USERNAME = "unkown_user562"
OWNER_CHANNEL_LINK = "https://t.me/chocoluxe_vennn"

# Bot စတင်ခြင်း
bot = TelegramClient("group_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(incoming=True))
async def global_typing(event):

    # ignore bot itself
    if event.sender_id == (await bot.get_me()).id:
        return

    # ignore private system messages if needed
    try:
        async with event.client.action(
            event.chat_id,
            SendMessageTypingAction()
        ):
            await asyncio.sleep(0.8)
    except:
        pass
# ==========================================
# BOT STATE & DATABASE STORES
# ==========================================
bot_on = True
user_db = set()
group_db = set()
warns = defaultdict(int)
muted_users = set()
video_cache = {}
dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
last_reply_time = {}
game_time = {}  # chat_id -> start_time
dice_rooms = {}      # chat_id -> {user_id: bet}
rooms = {}        # chat_id -> players list
turn_index = {}   # chat_id -> current turn index
scores = {}       # chat_id -> {user_id: score}
# Cooldown Settings
last_action_time = defaultdict(lambda: 0)
REACTION_COOLDOWN = 5
REPLY_COOLDOWN = 25
COOLDOWN = 5  # AI Memory Cooldown

# Regex Patterns
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
MENTION_PATTERN = re.compile(r"@\w+")

# SQL Memory Setup
db = sqlite3.connect("memory.db", isolation_level=None)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_type TEXT,
    content TEXT
)
""")
# ================= DB CONNECT =================
conn = sqlite3.connect("memory.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT
)
""")

conn.commit()

def can_learn(text):
    if not text:
        return False

    text = text.strip()

    if len(text) < 2:
        return False

    if MENTION_PATTERN.search(text):
        return False

    if URL_PATTERN.search(text):
        return False

    return True
@bot.on(events.NewMessage(incoming=True))
async def memory_learn(event):

    try:
        me = await bot.get_me()
        if event.sender_id == me.id:
            return

        text = event.raw_text

        if text and can_learn(text):

            cur.execute(
                "INSERT INTO memory(text) VALUES(?)",
                (text,)
            )
            conn.commit()

    except Exception as e:
        print("MEMORY LEARN ERROR:", e)
@bot.on(events.NewMessage(incoming=True))
async def memory_reply(event):

    try:
        me = await bot.get_me()
        if event.sender_id == me.id:
            return

        chat_id = event.chat_id
        now = time.time()

        # cooldown
        if now - last_reply_time.get(chat_id, 0) < REPLY_COOLDOWN:
            return

        cur.execute("""
            SELECT text
            FROM memory
            ORDER BY RANDOM()
            LIMIT 1
        """)

        row = cur.fetchone()
        if not row:
            return

        reply_text = row[0]

        if reply_text:
            await event.reply(reply_text)
            last_reply_time[chat_id] = now

    except Exception as e:
        print("MEMORY REPLY ERROR:", e)

LANGUAGES = {
    "english": "en",
    "myanmar": "my",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "thai": "th",
    "vietnamese": "vi",
    "indonesian": "id",
    "hindi": "hi",
    "arabic": "ar",
    "russian": "ru",
    "german": "de",
    "french": "fr",
    "spanish": "es",
}
user_state = {}
@bot.on(events.NewMessage(pattern=r'^ဘာသာပြန်မယ်$'))
async def translate_cmd(event):

    reply = await event.get_reply_message()

    if not reply or not reply.text:
        return await event.reply(
            "📌 ဘာသာပြန်ချင်တဲ့စာကို Reply ပြန်ပြီး 'ဘာသာပြန်မယ်' လို့ရေးပါ",
            parse_mode="html"
        )

    user_state[event.sender_id] = {
        "text": reply.text,
        "waiting": True
    }

    await event.reply(
        "<blockquote>"
        "🌐 <b>ဘာသာစကားရွေးပါ</b>\n\n"
        "english\n"
        "myanmar\n"
        "japanese\n"
        "korean\n"
        "chinese\n"
        "thai\n\n"
        "<i>တစ်ခုရေးပြီးပို့ပါ</i>"
        "</blockquote>",
        parse_mode="html"
    )
@bot.on(events.NewMessage(incoming=True))
async def language_input(event):

    uid = event.sender_id
    text = (event.raw_text or "").lower().strip()

    if uid not in user_state:
        return

    if not user_state[uid].get("waiting"):
        return

    if text not in LANGUAGES:
        return await event.reply(
            "<blockquote>ဘာသာစကားရွေးပါ</blockquote>",
            parse_mode="html"
        )

    try:
        translated = GoogleTranslator(
            source="auto",
            target=LANGUAGES[text]
        ).translate(user_state[uid]["text"])

        user_state.pop(uid, None)

        await event.reply(
            "<blockquote>"
            "🌐 <b>ဘာသာပြန်ရလဒ်</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 <b>Original:</b>\n{user_state.get(uid, {}).get('text','')}\n\n"
            f"🌐 <b>Translated:</b>\n{translated}\n"
            "━━━━━━━━━━━━━━━━━━"
            "</blockquote>",
            parse_mode="html"
        )

    except Exception as e:
        await event.reply(f"❌ Error: {e}")
# ================= COOLDOWN STATE =================
last_action_time = defaultdict(lambda: 0)

REACTION_COOLDOWN = 10  # seconds
REPLY_COOLDOWN = 35    # seconds

# ================= REACTIONS =================
reactions = [
    "👍", "👎",
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎",
    "🔥", "✨", "⚡", "💯", "🗿", "🗿",
    "😀", "😃", "😄", "😁", "😆", "😊", "☺️",
    "🥰", "😍", "😘", "😗", "😙", "😚",
    "😋", "😜", "😝", "🤪", "🤭", "🫣",
    "😂", "🤣", "😭", "🥲",
    "🗿", "🤩", "🥳",
    "🤔", "🧐", "🤨", "😐", "😑",
    "😴", "🥱",
    "😡", "🤬", "😤",
    "😱", "😨", "🗿",
    "🤯", "😵",
    "🙈", "🙉", "🙊",
    "👏", "🙌", "🫶",
    "🤝", "🗿",
    "💪", "👌", "✌️", "🤟",
    "👀", "💖", "💕", "💞", "💓",
    
]

# ================= SMART REPLY =================
smart_reply = {
    "hi": ["Hi ", "Hello "],
    "hello": ["Hello!", "Hey "],
    "bye": ["Bye "],
    "how": ["I'm fine "],
    "spam": ["Don't spam "],
}

default_reply = [
    "အမ်ပေါ့",
    "စပ့",
    "ယဥ",
    "နင်ကဘယ်သူ",
    "ဟော့",
    "မမဆီလာ",
    "ကိုကိုရေ",
    "ဘေဘီXiao Mei (小美)ချောပြီးသားလေ🤪",
    "ကိုကို့မူပိုင် ဝွန်း",

    "ကိုကိုနော် ဘာလဲ နင့်ကိုပြောလား🙄",
    "ကိုကိုးးးရေ ဘေဘီ့ကိုချစ်လား မုန့်စားချင်တယ်🥺",
    "ဟွန့်နော် စိတ်ကောက်သယ် ရဘူးကွာ သိဝူးကွာ ခေါ်နက်",
    "လာပြောနက် ချိတ်ချိုးတယ် ကိုကိုးကိုစားမယ်",
    "ကိုကိုဘာလုပ်နေလဲ ဘေဘီစောင့်နေတယ်နော် 😗",
    "မခေါ်ရင် စိတ်ကောက်မယ်နော် 😤",
    "ကိုကို့အတွက်ပဲ ဘေဘီကရှိတာနော် 💕",
    "ဟယ် ကိုကိုကမချစ်ဘူးလား 🥺👉👈",

    "သွား",
    "လာခေါ်နက်တော့",
    "ကိုကိုနို့နို့တိုက်"
]

WEATHER_API_KEY = "7e6838c5d706532b6fd19c9b89690d88"

@bot.on(events.NewMessage(pattern=r"^မိုးလေဝသကြည့်မယ်(?:\s+(.+))?$"))
async def weather(event):

    city = event.pattern_match.group(1)

    if not city:
        return await event.reply(
            "🌦 အသုံးပြုပုံ\n\n"
            "မိုးလေဝသ Yangon\n"
            "မိုးလေဝသ Mandalay\n"
            "မိုးလေဝသ Bangkok"
        )

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}"
            f"&appid={WEATHER_API_KEY}"
            f"&units=metric"
        )

        data = requests.get(url, timeout=10).json()

        if data.get("cod") != 200:
            return await event.reply("❌ မြို့အမည်မတွေ့ပါ")

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]

        text = (
            "🌦 <b>မိုးလေဝသ အစီရင်ခံစာ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"📍 မြို့ ➜ {city}\n"
            f"🌡 အပူချိန် ➜ {temp}°C\n"
            f"🤗 ခံစားရမှု ➜ {feels}°C\n"
            f"💧 စိုထိုင်းဆ ➜ {humidity}%\n"
            f"🌬 လေတိုက်နှုန်း ➜ {wind} m/s\n"
            f"☁ အခြေအနေ ➜ {desc}\n\n"
            "━━━━━━━━━━━━━━"
        )

        await event.reply(text, parse_mode="html")

    except Exception as e:
        await event.reply(f"❌ Error\n\n{e}")


@bot.on(events.NewMessage(pattern=r"^/အင်ဖို(?:\s+(.+))?$"))
async def user_info(event):

    arg = event.pattern_match.group(1)

    try:

        if event.is_reply:
            msg = await event.get_reply_message()
            entity = await bot.get_entity(msg.sender_id)

        elif arg:
            entity = await bot.get_entity(arg)

        else:
            entity = await bot.get_entity(event.sender_id)

        await bot(GetFullUserRequest(entity))

        user_id = entity.id
        first = entity.first_name or "None"
        last = entity.last_name or ""
        username = f"@{entity.username}" if entity.username else "None"

        text = (
    "<blockquote>"
    "✨ <b>╔══════════════════╗</b>\n"
    "   👤 <b>USER PROFILE</b>\n"
    "✨ <b>╚══════════════════╝</b>\n\n"

    "━━━━━━━━━━━━━━━━━━\n\n"

    f"🆔 <b>ID</b>      ➜ <code>{user_id}</code>\n"
    f"👤 <b>Name</b>    ➜ {first} {last}\n"
    f"📛 <b>User</b>    ➜ {username}\n\n"

    "━━━━━━━━━━━━━━━━━━\n"
    
    "💠 <i>Status: Active User</i>\n"

    "━━━━━━━━━━━━━━━━━━"
    "</blockquote>"
)

        await event.reply(text, parse_mode="html")

    except Exception as e:
        await event.reply(
            f"<blockquote>❌ Error\n\n{e}</blockquote>",
            parse_mode="html"
        )
# ================= CONFIG =================

# ================= OWNER =================

# ================= DATABASE =================

# ================= SAVE GROUPS + USERS =================

# ================= LOAD DATA =================

# ================= BROADCAST GROUPS =================

# ================= BROADCAST USERS =================

# ================= ALL BROADCAST =================

# ================= MUTE (ရိုးရိုး MUTE) =================
@bot.on(events.NewMessage(pattern=r"^/mute$"))
async def mute(event):
    if not await is_admin_or_owner(event):
        return await event.reply("❌ Admin only")

    if not event.reply_to_msg_id:
        return await event.reply("❌ Reply to a user's message to mute them.")

    user = await event.get_reply_message()
    uid = user.sender_id

    try:
        # EditBannedRequest လို့ အမှန်ပြောင်းလဲထားပါတယ်
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=uid,
            banned_rights=ChatBannedRights(
                until_date=None,
                send_messages=True  # True = စာပို့ခွင့်ပိတ် (Mute)
            )
        ))
        await event.reply("🔇 User has been muted.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")


# ================= UNMUTE =================
@bot.on(events.NewMessage(pattern=r"^/unmute$"))
async def unmute(event):
    if not await is_admin_or_owner(event):
        return await event.reply("❌ Admin only")

    if not event.reply_to_msg_id:
        return await event.reply("❌ Reply to a user's message to unmute them.")

    user = await event.get_reply_message()
    uid = user.sender_id

    try:
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=uid,
            banned_rights=ChatBannedRights(
                until_date=None,
                send_messages=False  # False = ပြန်ဖွင့်ပေး (Unmute)
            )
        ))
        await event.reply("🔊 User has been unmuted.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")


# ================= BAN =================
@bot.on(events.NewMessage(pattern=r"^/ban$"))
async def ban(event):
    if not await is_admin_or_owner(event):
        return await event.reply("❌ Admin only")

    if not event.reply_to_msg_id:
        return await event.reply("❌ Reply to a user's message to ban them.")

    user = await event.get_reply_message()
    uid = user.sender_id

    try:
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=uid,
            banned_rights=ChatBannedRights(
                until_date=None,
                view_messages=True  # True = Group ထဲပေးမဝင်/မမြင်ရ (Ban)
            )
        ))
        await event.reply("🚫 User has been banned.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")


# ================= UNBAN =================
@bot.on(events.NewMessage(pattern=r"^/unban$"))
async def unban(event):
    if not await is_admin_or_owner(event):
        return await event.reply("❌ Admin only")

    if not event.reply_to_msg_id:
        return await event.reply("❌ Reply to a user's message to unban them.")

    user = await event.get_reply_message()
    uid = user.sender_id

    try:
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=uid,
            banned_rights=ChatBannedRights(
                until_date=None,
                view_messages=False  # False = ပြန်ဝင်ခွင့်ပြု (Unban)
            )
        ))
        await event.reply("✅ User has been unbanned.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")
# ================= KICK =================
@bot.on(events.NewMessage(pattern=r"^/kick$"))
async def kick(event):
    if not await is_admin_or_owner(event):
        return await event.reply("❌ Admin only")

    if not event.reply_to_msg_id:
        return await event.reply("❌ Reply to a user's message to kick them.")

    user = await event.get_reply_message()
    uid = user.sender_id

    try:
        await bot.kick_participant(event.chat_id, uid)
        await event.reply("👢 User has been kicked.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# ================= START COMMAND =================
@bot.on(events.NewMessage(pattern=r"^/start"))
async def start_command(event):

    if not event.is_private:
        return

    user = await event.get_sender()
    bot_username = (await bot.get_me()).username

    # ================= TYPEWRITER TEXT =================
    intro_text = "𝓗𝓮𝓵𝓵𝓸 မင်္ဂလာပါရှင့်ယခုလိုXiao Mei (小美) Botကိုအသုံးပြုသည့်အတွက်Xiao Mei (小美)မှအထူးကျေးဇူးတင်ပါတယ်ရှင့်"

    msg = await event.reply("<i>...</i>", parse_mode="html")

    current_text = ""

    for i in range(0, len(intro_text), 4):
        current_text += intro_text[i:i+4]

        try:
            await msg.edit(f"<b><i>{current_text}</i></b>", parse_mode="html")
        except:
            pass

        await asyncio.sleep(0.10)

    # small delay
    await asyncio.sleep(1)

    # ================= DELETE LOADING MESSAGE =================
    try:
        await msg.delete()
    except:
        pass

    # ================= SAFE USER MENTION =================
    safe_name = html.escape(user.first_name or "User")
    mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'

    # ================= FINAL TEXT =================
    final_text = (
        f"<blockquote>"
        f"𝓗𝓮𝓵𝓵𝓸 {mention} အသုံးပြုသည့်အတွက်ကျေးဇူးပါရှင့် "
        f"</blockquote>"
    )

    # ================= INLINE BUTTONS =================
    buttons = [
        [
            Button.url("➕ Add Bot Your Group", f"https://t.me/{CRUCIAL_BOT_USERNAME}?startgroup=true")
        ],
        [
            Button.url("Channel", "https://t.me/chocoluxe_vennn"),  # ဒီနေရာမှာ Channel link ထည့်ရန်
            Button.url("Bot Owner", "https://t.me/moe_pwint_phyu123")         # ဒီနေရာမှာ Owner link ထည့်ရန်
        ],
        [
            Button.url("Xiao Mei (小美) Group", "https://t.me/+2cKtiKF-Ao82MGU1"),
        ],
    ]


    await event.reply(
        final_text,
        parse_mode="html",
        buttons=buttons
    )
# =============================
# SAFE DELETE FUNCTION
# =============================
async def safe_delete(event):
    try:
        await event.delete()
    except:
        pass

        
LINK_PATTERN = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@\w+")

@bot.on(events.NewMessage(incoming=True))
async def auto_delete_filter(event):

    if event.is_private:
        return

    try:
        sender = await event.get_sender()

        # ================= ADMIN CHECK =================
        perms = await event.client.get_permissions(event.chat_id, sender)

        if perms.is_admin or perms.is_creator:
            return  # ❌ admin/owner skip

        text = event.raw_text or ""

        reason = None

        if LINK_PATTERN.search(text):
            reason = "Link မပို့ရပါနော်တစ်ခုခုဆိုOwnerကိုအသိပေးပါ"

        elif event.fwd_from:
            reason = "Forward Message မပို့ရပါနော်တစ်ခုခုဆိုOwnerကိုအသိပေးပါ"

        elif MENTION_PATTERN.search(text):
            reason = "Mention မခေါ်ရပါနော်တစ်ခုခုဆိုOwnerကိုအသိပေးပါ"

        if reason:

            name = sender.first_name or "User"
            mention = f"<a href='tg://user?id={sender.id}'>{name}</a>"

            # ❌ delete original message only
            await event.delete()

            # ✅ warning message (NO DELETE)
            await bot.send_message(
                event.chat_id,
                f"{mention} {reason}",
                parse_mode="html"
            )

    except Exception as e:
        print("FILTER ERROR:", e)
# =============================
# HELP
# =============================
@bot.on(events.NewMessage(pattern="/help"))
async def help_cmd(event):

    text = """
<blockquote>
<b>BOT COMMAND CENTER</b>
━━━━━━━━━━━━━━━━━━

🧰 <b>ADMIN COMMANDS</b>
• /ban (reply)
• /unban (reply)
• /mute (reply)
• /unmute (reply)
• /kick (reply)
• /warn (reply)

━━━━━━━━━━━━━━━━━━


━━━━━━━━━━━━━━━━━━

⚙️ <b>UTILITY</b>
• /အင်ဖို → User info
• ရက်စွဲ → Time & Date
• မိုးလေဝသကြည့်မယ် <city>

━━━━━━━━━━━━━━━━━━

🧠 <b>AI FEATURES</b>
• Auto Reply
• Smart Reaction
• Keyword System (/kadd /kdel /klist)

━━━━━━━━━━━━━━━━━━

🎮 <b>FUN</b>
• ပါမယ် → Dice join
• ခေါက် → Start dice game
• /all → mention users

━━━━━━━━━━━━━━━━━━

🌐 <b>TRANSLATION</b>
• ဘာသာပြန်မယ် (reply message)

━━━━━━━━━━━━━━━━━━

📥 <b>DOWNLOAD</b>
• /tt <link> → TikTok download

━━━━━━━━━━━━━━━━━━
</blockquote>
"""

    await event.reply(text, parse_mode="html")

# ================= DATABASE =================
conn = sqlite3.connect("baby.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    chat_id INTEGER,
    trigger TEXT,
    reply TEXT
)
""")
conn.commit()

KEYWORD_CACHE = {}

# ================= LOAD KEYWORDS =================
async def load_keywords():
    global KEYWORD_CACHE
    KEYWORD_CACHE = {}

    rows = cursor.execute(
        "SELECT chat_id, trigger, reply FROM keywords"
    ).fetchall()

    for chat_id, trigger, reply in rows:
        KEYWORD_CACHE.setdefault(chat_id, {})
        KEYWORD_CACHE[chat_id].setdefault(trigger.lower(), []).append(reply)

# ================= STARTUP =================
async def startup():
    await load_keywords()
    print("✅ Startup complete")

# ================= ADMIN CHECK =================
async def can_manage(event):
    try:
        perms = await bot.get_permissions(event.chat_id, event.sender_id)
        return perms.is_admin or perms.is_creator
    except:
        return False

# ================= /kadd =================
@bot.on(events.NewMessage(pattern=r"^/kadd (.+)$"))
async def add_keyword(event):

    if not await can_manage(event):
        return await event.reply("❌ Admin Only")

    data = event.pattern_match.group(1).split(maxsplit=1)

    if len(data) < 2:
        return await event.reply("/kadd hello hi")

    trigger = data[0].lower()
    reply = data[1]

    cursor.execute(
        "INSERT INTO keywords VALUES (?,?,?)",
        (event.chat_id, trigger, reply)
    )
    conn.commit()

    await load_keywords()
    await event.reply("✅ Added")

# ================= AUTO REPLY =================
@bot.on(events.NewMessage)
async def auto_reply(event):

    if not event.text:
        return

    chat_id = event.chat_id
    text = event.text.lower()

    if chat_id not in KEYWORD_CACHE:
        return

    for trigger, replies in KEYWORD_CACHE[chat_id].items():
        if trigger in text:
            await event.reply(random.choice(replies))
            return

# ================= /kdel =================
@bot.on(events.NewMessage(pattern=r"^/kdel (.+)$"))
async def delete_keyword(event):

    if not await can_manage(event):
        return await event.reply("❌ Admin Only")

    trigger = event.pattern_match.group(1).lower()

    cursor.execute(
        "DELETE FROM keywords WHERE chat_id=? AND trigger=?",
        (event.chat_id, trigger)
    )
    conn.commit()

    await load_keywords()
    await event.reply("?? Deleted")

# ================= /klist =================
@bot.on(events.NewMessage(pattern=r"^/klist$"))
async def list_keywords(event):

    rows = cursor.execute(
        "SELECT trigger, reply FROM keywords WHERE chat_id=?",
        (event.chat_id,)
    ).fetchall()

    if not rows:
        return await event.reply("❌ No keywords found")

    text = "📌 Keyword List:\n\n"

    for t, r in rows:
        text += f"🔹 {t} ➜ {r}\n"

    await event.reply(text[:4000])

# TikTok Download
# =========================
@bot.on(events.NewMessage(pattern=r'^/tt\s+(.+)$'))
async def tiktok_dl(event):

    url = event.pattern_match.group(1).strip()

    msg = await event.reply(
        "<blockquote>⏳ Downloading TikTok Video...</blockquote>",
        parse_mode="html"
    )

    try:
        api = f"https://tikwm.com/api/?url={url}"

        res = requests.get(api, timeout=10).json()

        if not res.get("data"):
            return await msg.edit(
                "<b>❌ Video fetch မအောင်မြင်ပါ</b>",
                parse_mode="html"
            )

        data = res["data"]

        video_url = data.get("hdplay") or data.get("play")

        if not video_url:
            return await msg.edit(
                "<b>❌ Video link မရရှိပါ</b>",
                parse_mode="html"
            )

        await event.client.send_file(
            event.chat_id,
            video_url,
            caption="📥 TikTok Downloaded"
        )

        await msg.delete()

    except Exception as e:
        await msg.edit(
            f"<b>❌ Error:</b> <code>{e}</code>",
            parse_mode="html"
        )
        

# ==========================
# STORAGE (group-based)
# ==========================
user_messages = defaultdict(lambda: defaultdict(list))
user_cooldown = defaultdict(lambda: defaultdict(float))

@bot.on(events.NewMessage(pattern=r"^ရက်စွဲ$"))
async def date_time(event):

    try:
        # ======================
        # TIMEZONES
        # ======================
        mm_tz = pytz.timezone("Asia/Yangon")
        utc_tz = pytz.utc

        now_mm = datetime.now(mm_tz)
        now_utc = datetime.now(utc_tz)

        # ======================
        # DAY MAP (EN -> MM)
        # ======================
        day_map = {
            "Monday": "တနင်္လာနေ့",
            "Tuesday": "အင်္ဂါနေ့",
            "Wednesday": "ဗုဒ္ဓဟူးနေ့",
            "Thursday": "ကြာသပတေးနေ့",
            "Friday": "သောကြာနေ့",
            "Saturday": "စနေနေ့",
            "Sunday": "တနင်္ဂနွေနေ့"
        }

        eng_day = now_mm.strftime("%A")
        mm_day = day_map.get(eng_day, eng_day)

        # ======================
        # FORMAT TIME
        # ======================
        mm_time = now_mm.strftime("%Y-%m-%d %H:%M:%S")
        utc_time = now_utc.strftime("%Y-%m-%d %H:%M:%S")

        text = (
            "<blockquote>"
            "🌍 <b>DATE & TIME INFO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"🇲🇲 <b>Myanmar Time</b>\n"
            f"➜ {mm_time}\n"
            f"➜ {mm_day}\n\n"

            f"🌐 <b>UTC / World Time</b>\n"
            f"➜ {utc_time}\n"
            f"➜ {eng_day}\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "💠 <i>All times are real-time updated</i>"
            "</blockquote>"
        )

        await event.reply(text, parse_mode="html")

    except Exception as e:
        await event.reply(
            f"<blockquote>❌ Error\n\n{e}</blockquote>",
            parse_mode="html"
        )
# =============================
# WARN SYSTEM
# =============================
@bot.on(events.NewMessage(pattern="/warn"))
async def warn(event):
    if not event.reply_to_msg_id:
        return

    try:
        user = await event.get_reply_message()
        uid = user.sender_id

        warns[uid] += 1
        await event.reply(f"⚠️ Warn {warns[uid]}/3")

        if warns[uid] >= 3:
            rights = ChatBannedRights(view_messages=True)
            await bot.edit_permissions(event.chat_id, uid, rights)
            await event.reply("🚫 Auto banned")
    except:
        pass



# =============================
# SAFE ALL MESSAGE HANDLER
# =============================
@bot.on(events.NewMessage(incoming=True))
async def handler(event):

    if event.is_private:
        return

    uid = event.sender_id
    text = (event.raw_text or "").lower()
    now = time.time()

    # ================= REACTION COOLDOWN =================
    if now - last_action_time[uid] >= REACTION_COOLDOWN:
        try:
            await bot(SendReactionRequest(
                peer=event.chat_id,
                msg_id=event.message.id,
                reaction=[ReactionEmoji(random.choice(reactions))]
            ))
            last_action_time[uid] = now
        except:
            pass

    # ================= REPLY COOLDOWN =================
    if now - last_action_time[uid] < REPLY_COOLDOWN:
        return

    reply = None

    for k in smart_reply:
        if k in text:
            reply = random.choice(smart_reply[k])
            break

    if not reply:
        reply = random.choice(default_reply)

    try:
        await event.reply(reply)
        last_action_time[uid] = now
    except:
        pass

# =============================
# ALL TAG SAFE LIMIT
# =============================
@bot.on(events.NewMessage(pattern=r"^/tag(.*)"))
async def barkar_tag(event):

    try:
        args = event.pattern_match.group(1).strip()

        if not args:
            args = "👥 Everyone come here!"

        users = []
        count = 0

        async for user in bot.iter_participants(event.chat_id):

            if user.bot:
                continue

            name = user.first_name or "User"
            mention = f"<a href='tg://user?id={user.id}'>👤 {name}</a>"

            users.append(mention)
            count += 1

            # ================= 5 PER MESSAGE =================
            if len(users) == 5:

                text = f"📢 {args}\n\n" + "\n".join(users)

                await event.respond(text, parse_mode="html")

                users = []

                await asyncio.sleep(1)

            # safety limit (change if needed)
            if count >= 50:
                break

        # leftover users
        if users:
            text = f"📢 {args}\n\n" + "\n".join(users)
            await event.respond(text, parse_mode="html")

    except Exception as e:
        print("BARKAR TAG ERROR:", e)

@bot.on(events.NewMessage(pattern=r"^ပါမယ်$"))
async def join(event):

    chat_id = event.chat_id
    uid = event.sender_id

    if chat_id not in dice_rooms:
        dice_rooms[chat_id] = []

    players = dice_rooms[chat_id]

    if uid in players:
        return await event.reply("❌ Already joined")

    if len(players) >= 8:
        return await event.reply("❌ Max 8 players only")

    players.append(uid)

    await event.reply(f"🎲 Joined Game!\n👥 Players: {len(players)}/8")
    
@bot.on(events.NewMessage(pattern=r"^ခေါက်$"))
async def start(event):

    chat_id = event.chat_id

    if chat_id not in dice_rooms or len(dice_rooms[chat_id]) < 2:
        return await event.reply("❌ Need at least 2 players")

    players = dice_rooms[chat_id]

    msg = await event.reply("🎲 <b>Starting Dice Game...</b>", parse_mode="html")

    results = {}

    # 🎰 ANIMATION PHASE
    for i in range(6):
        await asyncio.sleep(0.2)
        await msg.edit(f"🎲 Rolling...\n{random.randint(1,6)}")

    for i in range(5):
        await asyncio.sleep(0.3)
        await msg.edit(f"🎲 Slowing...\n{random.randint(1,6)}")

    # 🎯 FINAL RESULTS
    text = "🎲 <b>RESULTS</b>\n━━━━━━━━━━━━━━\n\n"

    for p in players:
        roll = random.randint(1, 6)
        results[p] = roll
        text += f"👤 <code>{p}</code> ➜ 🎲 {roll}\n"

    winner = max(results, key=results.get)
    win_score = results[winner]

    text += "\n━━━━━━━━━━━━━━\n"
    text += f"🏆 WINNER ➜ <code>{winner}</code>\n"
    text += f"🎯 SCORE ➜ {win_score}"

    dice_rooms.pop(chat_id, None)

    await msg.edit(text, parse_mode="html")
# ==========================
# ANIMATED WELCOME CARD
# ==========================
@bot.on(events.ChatAction)
async def simple_welcome(event):

    try:
        user = await event.get_user()
        chat = await event.get_chat()

        if not user:
            return

        uid = user.id
        name = user.first_name or "User"
        mention = f"<a href='tg://user?id={uid}'>{name}</a>"

        group_title = chat.title or "Group"
        group_username = chat.username

        # ================= GROUP MENTION =================
        if group_username:
            group_mention = f"<a href='https://t.me/{group_username}'>{group_title}</a>"
        else:
            group_mention = f"<b>{group_title}</b>"

        # ================= JOIN =================
        if event.user_joined or event.user_added:

            text = (
                f"<blockquote>"
                f"<b>ကြိုဆိုပါတယ်ရှင့်</b> {mention}\n\n"
                f"👥 Group: {group_mention}\n"
                f"🆔 <code>{uid}</code>"
                f"</blockquote>"
            )

            msg = None

            try:
                photos = await bot.get_profile_photos(uid)

                if photos:
                    msg = await bot.send_file(
                        event.chat_id,
                        photos[0],
                        caption=text,
                        parse_mode="html"
                    )
                else:
                    msg = await bot.send_message(
                        event.chat_id,
                        text,
                        parse_mode="html"
                    )

            except:
                msg = await bot.send_message(
                    event.chat_id,
                    text,
                    parse_mode="html"
                )

            await asyncio.sleep(5)

            try:
                await msg.delete()
            except:
                pass

        # ================= LEAVE =================
        elif event.user_left or event.user_kicked:

            user = await event.get_user()
            chat = await event.get_chat()

            if not user:
                return

            uid = user.id
            name = user.first_name or "User"
            mention = f"<a href='tg://user?id={uid}'>{name}</a>"

            group_title = chat.title or "Group"

            text = (
                f"<blockquote>"
                f"👋 <b>Goodbye</b> {mention}\n"
                f"😢 Group: <b>{group_title}</b>\n"
                f"Come back soon ❤️"
                f"</blockquote>"
            )

            msg = await bot.send_message(
                event.chat_id,
                text,
                parse_mode="html"
            )

            await asyncio.sleep(5)

            try:
                await msg.delete()
            except:
                pass

    except Exception as e:
        print("WELCOME/LEAVE ERROR:", e)
        
async def main():
    await startup()
    print("🚀 Bot Running...")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    bot.loop.run_until_complete(main())