Below is a complete reference implementation in Python using python-telegram-bot. It incorporates all the core features we discussed—from a rich welcome menu, fuzzy or partial search with “did you mean” suggestions, hall maps, About section, neighbor stands, plus placeholders for categories, events, favorites, and even a minimal approach to handle voice messages.

Use this as a solid foundation to deploy quickly (for tomorrow’s exhibition) while still having room to expand. The steps below walk you through exactly how to set it up and maintain it.

1. Environment & Project Setup
	1.	Python Installation
Make sure you have Python 3.7+ installed.
	2.	Install Dependencies

pip install python-telegram-bot==13.14

Why this version? Version 13.x is stable and widely used. If you prefer the new v20+ release, you can adapt the code accordingly.

	3.	Obtain Bot Token
	•	Talk to @BotFather on Telegram.
	•	Create a new bot, note down the token (123456:ABC-DEF...).
	4.	File Structure (example)

bookfair_bot/
├── bot.py
├── publishers.json
└── requirements.txt


	5.	publishers.json Example
Make sure it’s valid JSON. We’ll assume a structure like:

{
  "publishers": [
    {
      "code": "A74",
      "nameAr": "دار النهضة العربية للنشر والتوزيع",
      "nameEn": "Dar Al-Nahda",
      "hall": 1,
      "section": "A",
      "position": { "x": 20, "y": 10 },
      "category": "Cultural",
      "events": []  // e.g. ["2025-01-24 12:00 Book Signing"]
    },
    {
      "code": "B29",
      "nameAr": "دار الشروق للنشر",
      "nameEn": "Dar Al-Shorouk",
      "hall": 1,
      "section": "B",
      "position": { "x": 15, "y": 5 },
      "category": "General",
      "events": []
    }
    // ...
  ]
}

	•	code: Booth code (ex: B29).
	•	nameAr: Arabic name.
	•	nameEn: English name (if available).
	•	hall: Which hall (1 to 5).
	•	section: A label or letter block (A, B, C…).
	•	position: (Optional) coordinates if you want advanced map usage.
	•	category: e.g., “Children”, “Education”, “Religious”, “General”, etc.
	•	events: a list of events or signings.

2. Full Code: bot.py

Below is a single-file bot that you can run immediately:

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ParseMode
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)
from difflib import get_close_matches
import re
import os

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ LOAD DATA ============
with open("publishers.json", "r", encoding="utf-8") as f:
    data = json.load(f)

PUBLISHERS = data["publishers"]

# Build quick lookups for code => publisher, name => publisher
CODE_INDEX = {}
NAME_AR_INDEX = {}
NAME_EN_INDEX = {}

for pub in PUBLISHERS:
    code_lower = pub["code"].lower()
    CODE_INDEX[code_lower] = pub

    # You might want to store full name with spaces removed for partial matching
    name_ar_key = re.sub(r"\s+", "", pub["nameAr"].lower())
    name_en_key = re.sub(r"\s+", "", pub["nameEn"].lower())
    NAME_AR_INDEX[name_ar_key] = pub
    NAME_EN_INDEX[name_en_key] = pub

# For easy code-based neighbor lookups, we create a dictionary:
# e.g. "B29" => neighbors are "B28", "B30" if they exist
def get_neighbors(booth_code):
    """
    Basic neighbor logic: If code = B29, parse letter = B, num=29,
    check for B28, B30 in CODE_INDEX.
    """
    match = re.match(r"([A-Za-z]+)(\d+)", booth_code)
    if not match:
        return []

    letter = match.group(1)
    num = int(match.group(2))

    possible_neighbors = []
    for offset in [-1, 1]:
        neighbor_code = f"{letter}{num + offset}"
        if neighbor_code.lower() in CODE_INDEX:
            pub = CODE_INDEX[neighbor_code.lower()]
            possible_neighbors.append(pub["code"] + " " + pub["nameAr"])
    return possible_neighbors

# =========== GLOBAL STATE FOR FAVORITES (OPTIONAL) ===========
# We'll store user favorites in memory. For production, consider a DB.
user_favorites = {}  # user_favorites[chat_id] = set_of_codes

# =========== MAIN HANDLERS ===========

def start(update: Update, context: CallbackContext):
    """
    /start command:
    - Show welcome message with inline buttons (Search, Maps, About, etc.)
    """
    chat_id = update.effective_chat.id

    keyboard = [
        [
            InlineKeyboardButton("🔍 ابحث عن ناشر", switch_inline_query_current_chat=""),
            InlineKeyboardButton("🗺 خرائط القاعات", callback_data="show_maps")
        ],
        [
            InlineKeyboardButton("ℹ️ عن أسفار", callback_data="about_asfar"),
            InlineKeyboardButton("📆 فعاليات", callback_data="show_events")
        ],
        [
            InlineKeyboardButton("🗂 التصنيفات", callback_data="show_categories"),
            InlineKeyboardButton("⭐️ مفضلتي", callback_data="show_favorites")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "مرحباً بك في *دليل أسفار* لمعرض القاهرة الدولي للكتاب ٢٠٢٥ 📚\n"
        "يمكنك كتابة اسم الناشر أو رقم الجناح مباشرة للبحث.\n\n"
        "اختر أحد الخيارات أدناه:"
    )

    context.bot.send_photo(
        chat_id=chat_id,
        photo="https://via.placeholder.com/300x150?text=Asfar+Logo",  # Replace with your actual image or file_id
        caption=welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


def callback_handler(update: Update, context: CallbackContext):
    """
    Handles all InlineKeyboard callback_data.
    """
    query = update.callback_query
    data = query.data

    if data == "show_maps":
        hall_maps(update, context, from_callback=True)

    elif data.startswith("map_"):
        # e.g. map_1, map_2, etc.
        hall_num = data.split("_")[1]
        send_map(update, context, hall_num)

    elif data == "about_asfar":
        about_asfar(update, context, from_callback=True)

    elif data == "show_events":
        show_events(update, context, from_callback=True)

    elif data == "show_categories":
        show_categories(update, context, from_callback=True)

    elif data.startswith("cat_"):
        # e.g. cat_Children => show pubs in that category
        cat_name = data.split("_", 1)[1]
        list_by_category(update, context, cat_name)

    elif data == "back_to_menu":
        start(update, context)

    elif data == "show_favorites":
        show_favorites(update, context, from_callback=True)

    query.answer()


def text_message_handler(update: Update, context: CallbackContext):
    """
    Any text message not a command -> treat as search query.
    We'll handle:
    - Exact code search (B29)
    - Name (Arabic/English) partial search
    - Fuzzy matching "did you mean?"
    - "قاعة 1" to list all in hall 1
    """
    chat_id = update.effective_chat.id
    text_input = update.message.text.strip()

    # 1. Check if user wrote "قاعة X"
    if text_input.startswith("قاعة"):
        # extract hall number
        match = re.search(r"(\d+)", text_input)
        if match:
            hall_num = int(match.group(1))
            pubs_in_hall = [p for p in PUBLISHERS if p["hall"] == hall_num]
            if pubs_in_hall:
                msg = f"**وجدت {len(pubs_in_hall)} ناشر في قاعة {hall_num}:**\n"
                for p in pubs_in_hall[:15]:  # show first 15 to avoid flooding
                    msg += f"- {p['code']} {p['nameAr']}\n"
                msg += "\n...(قد يكون هناك المزيد)\n"
                update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                update.message.reply_text("لم أجد ناشرين في هذه القاعة.")
            return

    # 2. Attempt direct code match
    # Remove spaces, to handle something like " B29 "
    text_lower = re.sub(r"\s+", "", text_input.lower())
    if text_lower in CODE_INDEX:
        pub = CODE_INDEX[text_lower]
        respond_with_publisher_info(pub, update, context)
        return

    # 3. Partial search by name (Arabic or English)
    # We'll get close matches from our index keys
    name_ar_keys = list(NAME_AR_INDEX.keys())
    name_en_keys = list(NAME_EN_INDEX.keys())

    # Combine them (some duplicates might exist but rarely an issue)
    combined_keys = list(set(name_ar_keys + name_en_keys))

    # difflib fuzzy matching
    potential = get_close_matches(text_lower, combined_keys, n=5, cutoff=0.5)
    # If we have direct partial matches containing the query:
    exact_matches = []
    for k in combined_keys:
        if text_lower in k:
            exact_matches.append(k)

    matched_pubs = []
    # Start with exact substring matches
    for k in exact_matches:
        if k in NAME_AR_INDEX:
            matched_pubs.append(NAME_AR_INDEX[k])
        if k in NAME_EN_INDEX:
            matched_pubs.append(NAME_EN_INDEX[k])

    # Then add fuzzy matches
    for k in potential:
        if k in NAME_AR_INDEX:
            matched_pubs.append(NAME_AR_INDEX[k])
        if k in NAME_EN_INDEX:
            matched_pubs.append(NAME_EN_INDEX[k])

    # Filter duplicates
    matched_pubs_unique = []
    seen_codes = set()
    for mp in matched_pubs:
        c = mp["code"]
        if c not in seen_codes:
            matched_pubs_unique.append(mp)
            seen_codes.add(c)

    if not matched_pubs_unique:
        # No results? Let's do a final "did you mean" approach if we found anything in difflib
        if potential:
            # Typically we’d show them as a suggestion
            suggestions = [f"- {NAME_AR_INDEX[k]['nameAr']}" for k in potential if k in NAME_AR_INDEX]
            if not suggestions:
                suggestions = [f"- {NAME_EN_INDEX[k]['nameEn']}" for k in potential if k in NAME_EN_INDEX]
            suggestion_text = "\n".join(suggestions)
            update.message.reply_text(
                f"عذراً لم أجد تطابق.\nربما تقصد:\n{suggestion_text}"
            )
        else:
            update.message.reply_text(
                "عذراً، لم أجد نتائج.\n\n"
                "تأكد من كتابة الاسم بالعربية بدقة أو رقم الجناح مثل B29.\n"
                "أو ابحث بـ 'قاعة 1' الخ..."
            )
        return

    # Show top results
    for pub in matched_pubs_unique[:5]:  # limit to 5
        respond_with_publisher_info(pub, update, context)


def respond_with_publisher_info(pub, update, context):
    """
    Format and send the publisher info:
    - Name
    - Hall + code
    - Neighbors
    - Buttons to add to favorites, etc.
    """
    chat_id = update.effective_chat.id
    name_ar = pub["nameAr"]
    code = pub["code"]
    hall = pub["hall"]

    # Get neighbors
    neighbors = get_neighbors(code)
    neighbor_text = "\n".join([f"• {n}" for n in neighbors]) if neighbors else "لا يوجد مجاورين"

    text = (
        f"*{name_ar}*\n"
        f"الموقع: قاعة {hall} - جناح {code}\n\n"
        f"الناشرون المجاورون:\n{neighbor_text}\n\n"
        "مقدم من أسفار | asfar.io | @asfarbooks"
    )

    # Inline buttons to add to favorites, see map, etc.
    keyboard = [
        [
            InlineKeyboardButton("⭐️ أضف للمفضلة", callback_data=f"fav_{code}"),
            InlineKeyboardButton("عرض خريطة القاعة", callback_data=f"map_{hall}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# =========== MAPS FEATURE ===========

def hall_maps(update: Update, context: CallbackContext, from_callback=False):
    """
    Show a menu of hall maps: 1..5, plus back button.
    """
    if from_callback:
        query = update.callback_query
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    keyboard = [
        [
            InlineKeyboardButton("قاعة 1", callback_data="map_1"),
            InlineKeyboardButton("قاعة 2", callback_data="map_2"),
            InlineKeyboardButton("قاعة 3", callback_data="map_3")
        ],
        [
            InlineKeyboardButton("قاعة 4", callback_data="map_4"),
            InlineKeyboardButton("قاعة 5", callback_data="map_5")
        ],
        [
            InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")
        ]
    ]
    text = "اختر القاعة لعرض الخريطة:"
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )


def send_map(update: Update, context: CallbackContext, hall_num):
    """
    Send a static map image for the given hall number.
    """
    query = update.callback_query
    chat_id = query.message.chat_id

    map_urls = {
        "1": "https://via.placeholder.com/500x300?text=Hall+1+Map",
        "2": "https://via.placeholder.com/500x300?text=Hall+2+Map",
        "3": "https://via.placeholder.com/500x300?text=Hall+3+Map",
        "4": "https://via.placeholder.com/500x300?text=Hall+4+Map",
        "5": "https://via.placeholder.com/500x300?text=Hall+5+Map",
    }

    photo_url = map_urls.get(hall_num, "")
    if not photo_url:
        context.bot.send_message(chat_id=chat_id, text="لا تتوفر خريطة لهذه القاعة.")
        return

    caption_text = (
        f"خريطة قاعة {hall_num}\n"
        "يمكنك كتابة اسم الناشر أو رقم الجناح للبحث عن موقعه."
    )

    context.bot.send_photo(
        chat_id=chat_id,
        photo=photo_url,
        caption=caption_text
    )


# =========== ABOUT FEATURE ===========

def about_asfar(update: Update, context: CallbackContext, from_callback=False):
    """
    Show an About card with brand info.
    """
    if from_callback:
        query = update.callback_query
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    about_text = (
        "*أسفار - منصة الكتب العربية*\n\n"
        "نقدم لكم دليل معرض القاهرة الدولي للكتاب ٢٠٢٥.\n"
        "اكتشف أفضل الكتب العربية من مختلف الناشرين.\n"
        "\n"
        "للمزيد:\n"
        "🔗 [asfar.io](https://asfar.io)\n"
        "📱 [@asfarbooks](https://t.me/asfarbooks)\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("زيارة Asfar.io", url="https://asfar.io"),
            InlineKeyboardButton("تابعنا على تيليجرام", url="https://t.me/asfarbooks")
        ],
        [
            InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_photo(
        chat_id=chat_id,
        photo="https://via.placeholder.com/400x200?text=Asfar+Brand",
        caption=about_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# =========== EVENTS FEATURE ===========

def show_events(update: Update, context: CallbackContext, from_callback=False):
    """
    Shows upcoming events or signings from the data, if any.
    """
    if from_callback:
        query = update.callback_query
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    # Example: gather all events from publishers
    all_events = []
    for p in PUBLISHERS:
        if p.get("events"):
            for e in p["events"]:
                all_events.append((p["nameAr"], e))

    if not all_events:
        context.bot.send_message(
            chat_id=chat_id,
            text="لا توجد فعاليات مسجلة حالياً."
        )
        return

    # Otherwise list them
    msg = "*الفعاليات القادمة:*\n"
    for name, e in all_events[:10]:  # limit for brevity
        msg += f"- {name}: {e}\n"
    msg += "\n(قد توجد فعاليات أخرى غير مسجلة في النظام)"

    keyboard = [
        [InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# =========== CATEGORIES FEATURE ===========

def show_categories(update: Update, context: CallbackContext, from_callback=False):
    """
    Display a list of categories from the data.
    """
    if from_callback:
        query = update.callback_query
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    # Gather unique categories
    cats = set()
    for p in PUBLISHERS:
        cat = p.get("category", "Other")
        cats.add(cat)

    # Build inline buttons
    keyboard = []
    row = []
    for cat in sorted(cats):
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Add a back button
    keyboard.append([InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=chat_id,
        text="اختر التصنيف لاستعراض الناشرين:",
        reply_markup=reply_markup
    )


def list_by_category(update: Update, context: CallbackContext, cat_name):
    """
    Show publishers that match a specific category.
    """
    query = update.callback_query
    chat_id = query.message.chat_id

    matched = [p for p in PUBLISHERS if p.get("category", "").lower() == cat_name.lower()]
    if not matched:
        context.bot.send_message(chat_id=chat_id, text="لا يوجد ناشرون في هذا التصنيف.")
        return

    msg = f"*الناشرون في تصنيف {cat_name}:*\n\n"
    for p in matched[:20]:
        msg += f"- {p['code']} {p['nameAr']}\n"
    if len(matched) > 20:
        msg += "\n(تم إظهار أول 20 فقط)"

    keyboard = [
        [InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# =========== FAVORITES FEATURE ===========

def show_favorites(update: Update, context: CallbackContext, from_callback=False):
    """
    Lists user's saved favorites.
    """
    if from_callback:
        query = update.callback_query
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    favs = user_favorites.get(chat_id, set())
    if not favs:
        context.bot.send_message(chat_id=chat_id, text="قائمة المفضلة فارغة.")
        return

    msg = "*مفضلتي:*\n"
    for code in favs:
        pub = CODE_INDEX.get(code.lower())
        if pub:
            msg += f"- {pub['code']} {pub['nameAr']}\n"

    keyboard = [
        [
            InlineKeyboardButton("مسح المفضلة", callback_data="clear_favs"),
            InlineKeyboardButton("عودة للقائمة", callback_data="back_to_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# We can intercept the "fav_" or "clear_favs" callback in callback_handler if we want
def advanced_callback_handler(update: Update, context: CallbackContext):
    """
    Additional callback handler for favorites or other advanced data.
    """
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat_id

    if data.startswith("fav_"):
        code = data.split("_", 1)[1]
        if chat_id not in user_favorites:
            user_favorites[chat_id] = set()
        user_favorites[chat_id].add(code.lower())
        query.answer("تمت الإضافة للمفضلة!")
    elif data == "clear_favs":
        user_favorites[chat_id] = set()
        query.answer("تم مسح المفضلة.")
        show_favorites(update, context, from_callback=True)

    else:
        # If we didn't handle it here, pass it on
        return

    # No further action needed if we handled it
    return


# =========== VOICE MESSAGE (OPTIONAL) ===========
def voice_message_handler(update: Update, context: CallbackContext):
    """
    Placeholder for voice input. 
    In reality, you'd need to download the voice file, send it to a speech-to-text API,
    then handle the recognized text. For demonstration, we just respond with a placeholder.
    """
    chat_id = update.effective_chat.id
    update.message.reply_text(
        "تلقيت رسالة صوتية. في الإصدار المستقبلي سنقوم بتحويلها لنص تلقائياً."
    )
    # If you want to do more:
    # 1. file_id = update.message.voice.file_id
    # 2. file = context.bot.getFile(file_id)
    # 3. file.download('voice.oga')
    # 4. Use an STT service to convert, then search.


# =========== MAIN ENTRY POINT ===========

def main():
    TOKEN = os.environ.get("BOT_TOKEN", "<PUT_YOUR_TOKEN_HERE>")
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("maps", hall_maps))
    dp.add_handler(CommandHandler("about", about_asfar))
    # Optionally: dp.add_handler(CommandHandler("events", show_events))
    # Optionally: dp.add_handler(CommandHandler("categories", show_categories))

    # Callback handler for inline buttons
    dp.add_handler(CallbackQueryHandler(advanced_callback_handler, pattern=r"^(fav_|clear_favs)"))
    dp.add_handler(CallbackQueryHandler(callback_handler))

    # Text messages -> search
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))

    # Voice messages -> placeholder
    dp.add_handler(MessageHandler(Filters.voice, voice_message_handler))

    # Start the bot
    updater.start_polling()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == "__main__":
    main()

3. Explanation of Key Sections
	1.	Data Loading & Indexes
	•	We load publishers.json once and build quick lookups (CODE_INDEX, NAME_AR_INDEX, NAME_EN_INDEX).
	•	This makes searching by code or partial name faster and simpler.
	2.	Start Command
	•	Sends a welcome photo & inline keyboard with options (Search, Maps, About, etc.).
	3.	Callback Handling
	•	We have callback_handler for the main menu items (show_maps, about_asfar, show_events, etc.).
	•	A second advanced_callback_handler specifically for “favorites” logic.
	•	This separation helps keep the logic clean.
	4.	Text Search
	•	If the message text is not a command, we treat it as a search.
	•	We handle “قاعة X” to list all publishers in that hall.
	•	Then try direct booth code match (B29, A74, etc.).
	•	If that fails, we do a partial/fuzzy match using Python’s built-in difflib (get_close_matches).
	•	If still no matches, we show “did you mean…” suggestions or an error message.
	5.	Neighbors
	•	A small function get_neighbors(booth_code) that tries to find B28/B30 if the code is B29. This is purely an example logic.
	6.	Hall Maps
	•	Tapping “🗺 خرائط القاعات” triggers an inline keyboard to choose from Hall 1..5.
	•	send_map sends back the appropriate static image URL or file ID.
	7.	About
	•	A static message showing brand info and links.
	8.	Events
	•	Gathers all events from the JSON. If none exist, display “No events.” Otherwise lists them.
	9.	Categories
	•	Gathers unique categories from all publishers, shows them as inline buttons. Tapping a category displays matching publishers.
	10.	Favorites

	•	Very simple approach: a global user_favorites dictionary mapping chat_id -> set_of_codes.
	•	Users can add a favorite by tapping “⭐️ أضف للمفضلة” in the search result.
	•	They can view or clear favorites in the “⭐️ مفضلتي” menu.

	11.	Voice Messages

	•	Currently a placeholder. We note how you could integrate a speech-to-text API in the future.

	12.	Logging & Debugging

	•	Python logging is set up at the start, which helps debug any issues.

4. Deployment (Quick Instructions)
	1.	Local Deployment
	•	Put your bot token in code: TOKEN = "123456:ABCDEF..." or set environment variable BOT_TOKEN.
	•	Run:

python bot.py


	•	The bot should start polling. Check logs for “Bot is running…”

	2.	Server / VPS
	•	Copy your files to a cloud VPS (e.g., DigitalOcean, AWS Lightsail, etc.).
	•	Make sure Python and dependencies are installed.
	•	Run python bot.py in a screen or tmux session so it keeps running.
	3.	Webhook (Optional)
	•	If you prefer webhooks, you’ll need an HTTPS endpoint.
	•	Since you’re in a rush, polling is simpler and reliable enough.

5. Final Check & Launch
	•	Test all flows:
	•	/start
	•	Searching: booth code, partial Arabic name, full Arabic name, “قاعة X”
	•	Maps
	•	About
	•	Favorites
	•	Categories & events (if data is present)
	•	Announce your bot: share the t.me/YourBotName link or create a QR code displayed at your booth.

Done!