#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from typing import Final, Dict, List
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import pytz
from halls import HallManager
from maps import MapManager
import cairosvg  # For converting SVG to PNG
import telegram
from favorites import FavoritesManager
from analytics import AnalyticsManager
import functools
import time
from time import time

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN: Final = os.getenv('BOT_TOKEN')

# Initialize managers
hall_manager = HallManager()
map_manager = MapManager()
favorites_manager = FavoritesManager()
analytics_manager = AnalyticsManager()

# Add performance monitoring decorator
def track_performance(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time() - start_time
            if duration > 1.0:  # Log slow operations
                logger.warning(f"{func.__name__} took {duration:.2f} seconds")
    return wrapper

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user if possible."""
    error = context.error
    
    # Track error
    analytics_manager.track_error()
    
    # Handle old callback queries silently
    if isinstance(error, telegram.error.BadRequest) and "Query is too old" in str(error):
        return  # Just ignore old callback queries

    # For other errors, log them and notify the user
    logger.error("Exception while handling an update:", exc_info=error)
    
    if isinstance(update, Update) and update.effective_message:
        error_message = "عذراً، حدث خطأ. الرجاء المحاولة مرة أخرى."
        await update.effective_message.reply_text(error_message)


# ------------------------------------------------------------------------
# 1. Helper function to show the *home page* (main menu)
# ------------------------------------------------------------------------
async def show_homepage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Displays the main (home) menu with the same text/buttons as /start.
    This function can be called from both a /start command or a callback query.
    """
    # Decide where to reply: if we have an Update from /start => update.message
    # if from a callback => update.callback_query.message
    target_message = update.message or update.callback_query.message
    
    # Show intro and logo only if this is a /start command (not a callback)
    if update.message:
        intro_text = (
            "أكبر وأقدم معرض للكتاب في العالم العربي؛ ويقدم آلاف العناوين في مختلف المجالات؛ يجمع مئات دور النشر من مختلف أنحاء العالم \n"
            "📍 موقع المعرض: مركز مصر للمعارض الدولية \n"
            "🏛 عدد القاعات: 5 قاعات \n"
            "📚 عدد دور النشر: {total_publishers} دار \n".format(
                total_publishers=sum(len(hall_manager.get_hall_publishers(i)) for i in range(1, 6))
            )
        )
        
        # Send logo with intro text as caption
        with open("image.png", "rb") as photo:
            await target_message.reply_photo(
                photo=photo,
                caption=intro_text,
                parse_mode=ParseMode.MARKDOWN
            )

    # Build the main menu keyboard
    keyboard = [
        [
            InlineKeyboardButton("🔍 البحث عن ناشر", callback_data="search"),
            InlineKeyboardButton("🗺 خريطة المعرض", callback_data="maps")
        ],
        [
            InlineKeyboardButton("⭐️ المفضلة", callback_data="favorites"),
            InlineKeyboardButton("📅 العروض", callback_data="events")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Main menu text
    text = (
        "مرحباً!* أنا «نديم»، بوت ذكي لمعرض القاهرة الدولي للكتاب 2025* \n\n"
        "سأساعدك في:\n"
        "🔍 البحث عن دور النشر والعناوين \n"
        "🗺 معرفة أماكن الأجنحة بدقة على خرائط المعرض \n"
        "⭐ حفظ مفضّلاتك والعودة إليها لاحقاً \n"
        "📝 اختر من القائمة أدناه أو اكتب اسم الناشر/رقم الجناح مباشرة \n\n"
        "-----------------------------------\n"
        "🌐 زوروا موقعنا: https://asfar.io/"
    )

    # Send the home page message as text
    await target_message.reply_text(
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# ------------------------------------------------------------------------
# 2. Command Handlers (/start, /help, etc.)
# ------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    The /start command simply shows the 'home page' using our shared function.
    """
    await show_homepage(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_text = (
        "*كيف يمكنني مساعدتك؟*\n\n"
        "الأوامر المتاحة:\n"
        "• /start - بدء البوت\n"
        "• /help - عرض المساعدة\n"
        "• /search - البحث عن ناشر\n"
        "• /maps - خريطة المعرض\n"
        "• /events - الفعاليات\n"
        "• /favorites - المفضلة\n\n"
        "يمكنك أيضاً كتابة اسم الناشر أو رقم الجناح مباشرة للبحث"
    )
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command."""
    search_text = (
        "*البحث عن ناشر* 🔍\n\n"
        "يمكنك البحث عن طريق:\n"
        "• اسم دار النشر (مثال: دار الشروق)\n"
        "• رقم الجناح (مثال: B29)\n"
        "• رقم القاعة (مثال: قاعة 1)\n\n"
        "اكتب ما تريد البحث عنه..."
    )
    await update.message.reply_text(
        search_text,
        parse_mode=ParseMode.MARKDOWN
    )


# ------------------------------------------------------------------------
# 3. General Message Handler (search logic, etc.)
# ------------------------------------------------------------------------
@track_performance
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages (likely publisher searches)."""
    start_time = time()
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Track user return
    analytics_manager.track_user_return(user_id)
    
    # Search for publishers
    results = hall_manager.search_publishers(text)
    
    # Track search with success indicator
    analytics_manager.track_search(user_id, text, success=bool(results))
    
    if not results:
        await update.message.reply_text(
            "عذراً، لم أجد أي دار نشر تطابق بحثك. حاول مرة أخرى باستخدام:\n"
            "• اسم الناشر بالعربية أو الإنجليزية\n"
            "• كود الجناح (مثال: A74)\n"
            "• رقم القاعة (مثال: قاعة 1)"
        )
        return
    
    # Track response time
    analytics_manager.track_response_time(time() - start_time)

    # If we have multiple results, show them as a list
    if len(results) > 1:
        response = "*نتائج البحث:*\n\n"
        for i, pub in enumerate(results[:6], 1):
            response += f"{i}. *{pub.get('nameAr', 'بدون اسم')}*\n"
            response += f"   🏷️ الكود: `{pub.get('code', 'غير متوفر')}`\n"
            response += f"   🏛 القاعة: {pub.get('hall', 'غير متوفر')}\n\n"
        
        # Add prompt for user action
        response += "*اضغط على زر الناشر المطلوب لعرض التفاصيل* 👇"
        
        # Create keyboard with 2 buttons per row
        keyboard = []
        row = []
        for pub in results[:6]:  # Limit to 6 results
            button = InlineKeyboardButton(
                f"{pub.get('code', '??')} - {pub.get('nameAr', 'بدون اسم')}",
                callback_data=f"pub_{pub.get('code', '')}"
            )
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        # Single result, show detailed info
        publisher = results[0]
        await handle_publisher_selection(update, context, publisher, is_callback=False)


async def handle_publisher_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    publisher: Dict,
    is_callback: bool = False
) -> None:
    """Handle when a user selects a publisher from the search list."""
    # Get publisher info with enhanced format
    info = hall_manager.format_publisher_info(publisher)
    
    # Check if publisher is in favorites
    user_id = update.effective_user.id
    is_favorite = publisher['code'] in favorites_manager.get_user_favorites(user_id)
    
    # Create navigation buttons
    keyboard = [
        [
            InlineKeyboardButton(
                "❌ إزالة من المفضلة" if is_favorite else "⭐️ أضف للمفضلة",
                callback_data=f"fav_{publisher['code']}"
            )
        ],
        [
            InlineKeyboardButton("📍 موقع الناشر", callback_data=f"loc_{publisher['hall']}_{publisher['code']}"),
            InlineKeyboardButton("📋 القائمة الرئيسية", callback_data="start")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        try:
            await update.callback_query.message.edit_text(
                text=info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except:
            await update.callback_query.message.reply_text(
                text=info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text=info,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


async def handle_search_result(update: Update, context: ContextTypes.DEFAULT_TYPE, publisher: Dict) -> None:
    """(Optional) Example function that might display a single search result."""
    info = hall_manager.format_publisher_info(publisher)
    keyboard = [
        [
            InlineKeyboardButton("📍 موقع الناشر", callback_data=f"loc_{publisher['hall']}_{publisher['code']}"),
            InlineKeyboardButton("📋 القائمة الرئيسية", callback_data="start")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# ------------------------------------------------------------------------
# 4. CallbackQuery Handler
# ------------------------------------------------------------------------
@track_performance
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards."""
    start_time = time()
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    # Track user return
    analytics_manager.track_user_return(user_id)
    
    # Get previous feature from context if available
    prev_feature = context.user_data.get('current_feature', 'start')
    
    # Track feature usage and navigation flow
    if query.data in ["search", "maps", "favorites", "events"]:
        analytics_manager.track_feature_use(query.data)
        analytics_manager.track_navigation_flow(user_id, prev_feature, query.data)
        context.user_data['current_feature'] = query.data
        
        # Track feature engagement time if we have previous time
        if 'feature_start_time' in context.user_data:
            duration = time() - context.user_data['feature_start_time']
            analytics_manager.track_feature_engagement(user_id, prev_feature, duration)
        
        context.user_data['feature_start_time'] = time()
    
    # Track hall views
    elif query.data.startswith("hall_"):
        hall_number = query.data.split("_")[1]
        analytics_manager.track_hall_view(hall_number)
    
    # Track publisher views
    elif query.data.startswith("pub_"):
        publisher_code = query.data.replace("pub_", "")
        analytics_manager.track_publisher_view(publisher_code)
    
    # Track favorite actions
    elif query.data.startswith("fav_"):
        code = query.data.replace("fav_", "")
        is_favorite = code in favorites_manager.get_user_favorites(user_id)
        analytics_manager.track_favorite_action("removed" if is_favorite else "added")
    
    # Track response time
    analytics_manager.track_response_time(time() - start_time)
    
    # Helper: safely edit or send new text if the original message is a photo/caption
    async def safe_edit_message(text: str, reply_markup: InlineKeyboardMarkup = None):
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except telegram.error.BadRequest as e:
            if "Message is not modified" in str(e):
                pass  # The text is identical
            elif ("Message to edit not found" in str(e)
                  or "There is no text in the message to edit" in str(e)):
                # The original message is probably media; delete & send a new one
                try:
                    await query.message.delete()
                except telegram.error.BadRequest:
                    pass
                await query.message.reply_text(
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                raise
    
    # --------------------------------------------------------------------
    # Callback data parsing
    # --------------------------------------------------------------------
    if query.data.startswith("pub_"):
        code = query.data.replace("pub_", "")
        publisher = hall_manager.get_publisher_by_code(code)
        if publisher:
            await handle_publisher_selection(update, context, publisher, is_callback=True)
        return
    
    elif query.data.startswith("loc_"):
        # Show map with highlighted publisher
        _, hall_number, code = query.data.split("_")
        hall_number = int(hall_number)
        hall_info = map_manager.get_hall_info(hall_number)
        
        if hall_info:
            publishers = hall_manager.get_hall_publishers(hall_number)
            publisher = hall_manager.get_publisher_by_code(code)
            
            svg_path = map_manager.save_hall_map(hall_number, publishers, highlight_code=code)
            if svg_path and publisher:
                try:
                    png_path = svg_path.replace(".svg", ".png")
                    cairosvg.svg2png(url=svg_path, write_to=png_path)
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("↩️ عودة لتفاصيل الناشر", callback_data=f"pub_{code}"),
                            InlineKeyboardButton("📋 القائمة الرئيسية", callback_data="start")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    caption = (
                        f"*موقع {publisher.get('nameAr', '')}*\n"
                        f"الكود: `{code}` - قاعة {hall_number}"
                    )
                    
                    try:
                        await query.message.delete()
                    except:
                        pass
                    
                    # Send new photo message
                    with open(png_path, "rb") as photo:
                        await query.message.reply_photo(
                            photo=photo,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=reply_markup
                        )
                    
                    os.remove(svg_path)
                    os.remove(png_path)
                    return
                except Exception as e:
                    print(f"Error generating map: {e}")
        
        # Fallback if we cannot show the map
        text = "عذراً، لا يمكن عرض الموقع حالياً"
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        await safe_edit_message(text, InlineKeyboardMarkup(keyboard))
        return
    
    elif query.data == "search":
        text = (
            "*البحث عن ناشر* 🔍\n\n"
            "اكتب اسم دار النشر أو رقم الجناح"
        )
        await safe_edit_message(text)
        return
    
    elif query.data == "maps":
        text = "*خريطة المعرض* 🗺\n\nاختر القاعة التي تريد عرض خريطتها:"
        keyboard = []
        row = []
        for hall_num in range(1, 6):
            row.append(InlineKeyboardButton(f"قاعة {hall_num}", callback_data=f"hall_{hall_num}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Often we delete the old message if it's media
        try:
            await query.message.delete()
        except:
            pass
        
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    elif query.data.startswith("hall_"):
        hall_number = int(query.data.split("_")[1])
        hall_info = map_manager.get_hall_info(hall_number)
        
        if hall_info:
            publishers = hall_manager.get_hall_publishers(hall_number)
            svg_path = map_manager.save_hall_map(hall_number, publishers, highlight_code=None)
            if svg_path:
                try:
                    png_path = svg_path.replace(".svg", ".png")
                    cairosvg.svg2png(url=svg_path, write_to=png_path)
                    
                    keyboard = []
                    row = []
                    for section in hall_info["sections"]:
                        section_pubs = hall_manager.get_section_publishers(hall_number, section)
                        row.append(InlineKeyboardButton(
                            f"قسم {section} ({len(section_pubs)})",
                            callback_data=f"section_{hall_number}_{section}"
                        ))
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    if row:
                        keyboard.append(row)
                    
                    nav_row = []
                    if hall_number > 1:
                        nav_row.append(InlineKeyboardButton(
                            "◀️ السابق",
                            callback_data=f"hall_{hall_number - 1}"
                        ))
                    if hall_number < 5:
                        nav_row.append(InlineKeyboardButton(
                            "التالي ▶️",
                            callback_data=f"hall_{hall_number + 1}"
                        ))
                    if nav_row:
                        keyboard.append(nav_row)
                    
                    keyboard.append([
                        InlineKeyboardButton("عودة لقائمة القاعات", callback_data="maps"),
                        InlineKeyboardButton("القائمة الرئيسية", callback_data="start")
                    ])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    caption = (
                        f"*خريطة {hall_info['name']}* 🗺\n"
                        f"عدد الناشرين: {len(publishers)}"
                    )
                    
                    try:
                        await query.message.delete()
                    except:
                        pass
                    
                    with open(png_path, "rb") as photo:
                        await query.message.reply_photo(
                            photo=photo,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=reply_markup
                        )
                    
                    os.remove(svg_path)
                    os.remove(png_path)
                    return
                except Exception as e:
                    print(f"Error generating map: {e}")
        
        # If we get here => fallback
        text = "عذراً، لا يمكن عرض الخريطة حالياً"
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    elif query.data.startswith("section_"):
        _, hall_number, section = query.data.split("_")
        hall_number = int(hall_number)
        
        publishers = hall_manager.get_section_publishers(hall_number, section)
        if publishers:
            text = f"*ناشرو قسم {section} - قاعة {hall_number}* 📍\n\n"
            for pub in publishers:
                text += f"• *{pub['nameAr']}*\n"
                text += f"  🏷 الكود: `{pub['code']}`\n\n"
        else:
            text = (
                f"*قسم {section} - قاعة {hall_number}* 📍\n\n"
                "لا يوجد ناشرين في هذا القسم حالياً"
            )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"عودة لخريطة قاعة {hall_number}",
                    callback_data=f"hall_{hall_number}"
                ),
                InlineKeyboardButton("القائمة الرئيسية", callback_data="start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.delete()
        except:
            pass
        
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    elif query.data == "categories":
        categories = {}
        for hall_publishers in hall_manager.halls.values():
            for pub in hall_publishers:
                if pub_categories := pub.get('categories', []):
                    for category in pub_categories:
                        categories[category] = categories.get(category, 0) + 1
        
        if categories:
            text = "*تصنيفات دور النشر* 📚\n\n"
            sorted_categories = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            for cat, count in sorted_categories:
                text += f"• {cat}: {count} ناشر\n"
        else:
            text = "*تصنيفات دور النشر* 📚\n\nلم يتم إضافة تصنيفات بعد"
        
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data == "events":
        all_offers = []
        for hall_publishers in hall_manager.halls.values():
            for pub in hall_publishers:
                if offers := pub.get("offers", []):
                    for offer in offers:
                        all_offers.append(f"• {offer} ({pub.get('nameAr', 'بدون اسم')})")
        
        if all_offers:
            text = "*عروض دور النشر* 💥\n\n" + "\n".join(all_offers)
        else:
            text = "*عروض دور النشر* 💥\n\nلم يتم إضافة عروض بعد"
        
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data == "favorites":
        await show_favorites(update, context)
        return
    
    elif query.data.startswith("fav_"):
        code = query.data.replace("fav_", "")
        publisher = hall_manager.get_publisher_by_code(code)
        if publisher:
            is_added = await toggle_favorite(update, context, code)
            await handle_publisher_selection(update, context, publisher, is_callback=True)
        return
    
    elif query.data == "about":
        total_publishers = sum(len(pubs) for pubs in hall_manager.halls.values())
        text = (
            "*معرض القاهرة الدولي للكتاب ٢٠٢٥* ℹ️\n\n"
            "أكبر وأقدم معرض كتاب في العالم العربي\n\n"
            f"• عدد دور النشر: {total_publishers}\n"
            "• عدد القاعات: 5\n"
            "• الموقع: مركز مصر للمعارض الدولية"
        )
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data == "start":
        # Always delete the old message if possible (in case it was media).
        try:
            await query.message.delete()
        except:
            pass
        # Show the same homepage as /start
        await show_homepage(update, context)
    
    else:
        # Fallback
        text = "عذراً، حدث خطأ"
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        await safe_edit_message(text, InlineKeyboardMarkup(keyboard))


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's favorite publishers."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    favorites = favorites_manager.get_user_favorites(user_id)
    
    if not favorites:
        keyboard = [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]
        await query.message.edit_text(
            "لا توجد لديك دور نشر في المفضلة بعد.\n"
            "يمكنك إضافة دور النشر للمفضلة عند البحث عنها! ⭐️",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = "*المفضلة* ⭐️\n\n"
    keyboard = []
    
    for pub_code in favorites:
        publisher = hall_manager.get_publisher_by_code(pub_code)
        if publisher:
            text += f"• {publisher['nameAr']} ({pub_code})\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📍 {publisher['nameAr']}",
                    callback_data=f"pub_{pub_code}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")])
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE, publisher_code: str) -> bool:
    """Add or remove a publisher from favorites."""
    user_id = update.effective_user.id
    return favorites_manager.toggle_favorite(user_id, publisher_code)


# ------------------------------------------------------------------------
# 5. Main entry point: create Application, add handlers, run bot
# ------------------------------------------------------------------------
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))

    # Message Handler (for user text)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback Query Handler (for inline keyboard buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Error Handler
    application.add_error_handler(error_handler)

    print("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()