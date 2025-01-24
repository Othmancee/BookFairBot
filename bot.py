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
from halls.hall_manager import HallManager
from maps import MapManager
import cairosvg  # For converting SVG to PNG
import telegram
from favorites import FavoritesManager
from analytics import GA4Manager
import functools
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

# Environment setup
IS_PRODUCTION = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
GA4_DEBUG = os.getenv('GA4_DEBUG', 'false').lower() == 'true'

# Initialize managers
hall_manager = HallManager()
map_manager = MapManager()
favorites_manager = FavoritesManager()
ga4_manager = GA4Manager()  # Initialize without parameters

if not IS_PRODUCTION:
    logger.warning(
        "Running in development mode. GA4 events will be logged but not sent to GA4. "
        "Set RAILWAY_ENVIRONMENT=production to enable GA4 tracking."
    )

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
            # Get user_id if available
            user_id = None
            if args and isinstance(args[0], Update):
                user_id = str(args[0].effective_user.id) if args[0].effective_user else None
            
            if duration > 1.0:  # Log slow operations
                logger.warning(f"{func.__name__} took {duration:.2f} seconds")
                if user_id:
                    ga4_manager.track_performance(
                        user_id=user_id,
                        operation=func.__name__,
                        duration_ms=duration * 1000
                    )
    return wrapper

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user if possible."""
    error = context.error
    
    # Track error in GA4
    if isinstance(update, Update):
        user_id = str(update.effective_user.id) if update.effective_user else "unknown"
        ga4_manager.track_error(
            user_id=user_id,
            error_type=error.__class__.__name__,
            error_message=str(error)
        )
    
    # Handle old callback queries silently
    if isinstance(error, telegram.error.BadRequest) and "Query is too old" in str(error):
        return
    
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
        total_publishers = sum(len(hall_manager.get_hall_publishers(i)) for i in range(1, 6))
        intro_text = (
            "أكبر وأقدم معرض للكتاب في العالم العربي؛ ويقدم آلاف العناوين في مختلف المجالات؛ يجمع مئات دور النشر من مختلف أنحاء العالم \n"
            "📍 موقع المعرض: مركز مصر للمعارض الدولية \n"
            "🏛 عدد القاعات: 5 قاعات \n"
            f"📚 عدد دور النشر: {total_publishers} دار \n"
        )
        
        # Send logo with intro text as caption
        with open("assets/image.png", "rb") as photo:
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
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    # Track search with enhanced parameters
    results = hall_manager.search_publishers(text)
    ga4_manager.track_search(
        user_id=user_id,
        query=text,
        success=bool(results),
        results_count=len(results)
    )
    
    if not results:
        await update.message.reply_text(
            "عذراً، لم أجد أي دار نشر تطابق بحثك. حاول مرة أخرى باستخدام:\n"
            "• اسم الناشر بالعربية أو الإنجليزية\n"
            "• كود الجناح (مثال: A74)\n"
            "• رقم القاعة (مثال: قاعة 1)"
        )
        return

    # If we have multiple results, show them as a list
    if len(results) > 1:
        await show_search_results(update, results[:6])  # Limit to 6 results
    else:
        # Single result, show detailed info
        await handle_publisher_selection(update, context, results[0], is_callback=False)

async def show_search_results(update: Update, results: List[Dict]) -> None:
    """Show a list of search results with interactive buttons."""
    response = "*نتائج البحث:*\n\n"
    for i, pub in enumerate(results, 1):
        response += f"{i}. *{pub.get('nameAr', 'بدون اسم')}*\n"
        response += f"   🏷️ الكود: `{pub.get('code', 'غير متوفر')}`\n"
        response += f"   🏛 القاعة: {pub.get('hall', 'غير متوفر')}\n\n"
    
    response += "*اضغط على زر الناشر المطلوب لعرض التفاصيل* 👇"
    
    # Create keyboard with 2 buttons per row
    keyboard = []
    row = []
    for pub in results:
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
    
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_publisher_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    publisher: Dict,
    is_callback: bool = False
) -> None:
    """Handle when a user selects a publisher from the search list."""
    # Get publisher info with enhanced format
    info = hall_manager.format_publisher_info(publisher)
    
    # Get adjacent publishers
    hall_number = publisher['hall']
    section = publisher.get('section')
    if section:
        adjacent_pubs = hall_manager.get_adjacent_publishers(hall_number, section, publisher['code'])
        if adjacent_pubs:
            info += "\n\n*الأجنحة المجاورة:* 📍\n"
            for adj_pub in adjacent_pubs:
                info += f"• {adj_pub.get('nameAr', 'بدون اسم')} ({adj_pub.get('code', '??')})\n"
    
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


# ------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------
def create_home_button() -> List[List[InlineKeyboardButton]]:
    """Create a keyboard row with a home button."""
    return [[InlineKeyboardButton("عودة للقائمة الرئيسية", callback_data="start")]]

def create_nav_buttons(current: int, total: int) -> List[InlineKeyboardButton]:
    """Create navigation buttons for halls/sections."""
    nav_row = []
    if current > 1:
        nav_row.append(InlineKeyboardButton("◀️ السابق", callback_data=f"hall_{current - 1}"))
    if current < total:
        nav_row.append(InlineKeyboardButton("التالي ▶️", callback_data=f"hall_{current + 1}"))
    return nav_row

async def safe_delete_message(message: telegram.Message) -> None:
    """Safely delete a message, ignoring common errors."""
    try:
        await message.delete()
    except telegram.error.BadRequest:
        pass

async def safe_edit_message(query: telegram.CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None):
    """Safely edit or send a new message if the original is a photo/caption."""
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
            await safe_delete_message(query.message)
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            raise

async def track_feature_engagement(context: ContextTypes.DEFAULT_TYPE, user_id: str, new_feature: str) -> None:
    """Track feature engagement time and update context."""
    prev_feature = context.user_data.get('current_feature', 'start')
    
    # Track navigation between screens
    ga4_manager.track_navigation(
        user_id=user_id,
        from_screen=prev_feature,
        to_screen=new_feature
    )
    
    # Track feature usage
    if new_feature in ["search", "maps", "favorites", "events"]:
        ga4_manager.track_feature_use(
            user_id=user_id,
            feature=new_feature
        )
        context.user_data['current_feature'] = new_feature
        
        # Track engagement time
        if 'feature_start_time' in context.user_data:
            duration = time() - context.user_data['feature_start_time']
            ga4_manager.track_user_engagement(
                user_id=user_id,
                feature=prev_feature,
                engagement_time_msec=int(duration * 1000)
            )
        context.user_data['feature_start_time'] = time()


# ------------------------------------------------------------------------
# 4. CallbackQuery Handler
# ------------------------------------------------------------------------
@track_performance
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards."""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    await query.answer()
    
    # Track feature engagement
    await track_feature_engagement(context, user_id, query.data)
    
    try:
        # Track specific interactions first
        if query.data.startswith("hall_"):
            hall_number = int(query.data.split("_")[1])
            ga4_manager.track_map_interaction(
                user_id=user_id,
                hall_number=hall_number,
                action="view"
            )
        
        elif query.data.startswith("section_"):
            _, hall_number, section = query.data.split("_")
            ga4_manager.track_map_interaction(
                user_id=user_id,
                hall_number=int(hall_number),
                action="section_select",
                section=section
            )
        
        elif query.data.startswith("pub_"):
            code = query.data.replace("pub_", "")
            publisher = hall_manager.get_publisher_by_code(code)
            if publisher:
                ga4_manager.track_publisher_interaction(
                    user_id=user_id,
                    publisher_code=code,
                    action="view",
                    publisher_name=publisher.get('nameAr')
                )
        
        elif query.data.startswith("fav_"):
            code = query.data.replace("fav_", "")
            is_favorite = code in favorites_manager.get_user_favorites(int(user_id))
            action = "remove" if is_favorite else "add"
            ga4_manager.track_bookmark_action(
                user_id=user_id,
                publisher_code=code,
                action=action
            )
        
        # Handle the callbacks
        if query.data == "search":
            text = (
                "*البحث عن ناشر* 🔍\n\n"
                "اكتب اسم دار النشر أو رقم الجناح"
            )
            await safe_edit_message(query, text)
            
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
            
            await safe_delete_message(query.message)
            await query.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif query.data.startswith("pub_"):
            code = query.data.replace("pub_", "")
            publisher = hall_manager.get_publisher_by_code(code)
            if publisher:
                await handle_publisher_selection(update, context, publisher, is_callback=True)
            else:
                text = "عذراً، لم يتم العثور على الناشر"
                await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
            
        elif query.data.startswith("loc_"):
            # Show map with highlighted publisher
            _, hall_number, code = query.data.split("_")
            await handle_publisher_location(query, int(hall_number), code)
            
        elif query.data.startswith("hall_"):
            hall_number = int(query.data.split("_")[1])
            await handle_hall_map(query, hall_number)
            
        elif query.data.startswith("section_"):
            _, hall_number, section = query.data.split("_")
            await handle_section_view(query, int(hall_number), section)
            
        elif query.data == "categories":
            await handle_categories_view(query)
            
        elif query.data == "events":
            await handle_events_view(query)
            
        elif query.data == "favorites":
            await show_favorites(update, context)
            
        elif query.data.startswith("fav_"):
            code = query.data.replace("fav_", "")
            publisher = hall_manager.get_publisher_by_code(code)
            if publisher:
                await toggle_favorite(update, context, code)
                await handle_publisher_selection(update, context, publisher, is_callback=True)
            
        elif query.data == "about":
            await handle_about_view(query)
            
        elif query.data == "start":
            await safe_delete_message(query.message)
            await show_homepage(update, context)
            
        else:
            # Fallback for unhandled callback types
            text = "عذراً، حدث خطأ"
            await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
            
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        text = "عذراً، حدث خطأ"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))


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
# Handler Functions
# ------------------------------------------------------------------------
async def handle_hall_map(query: telegram.CallbackQuery, hall_number: int) -> None:
    """Handle displaying a hall map with sections and navigation."""
    hall_info = map_manager.get_hall_info(hall_number)
    if not hall_info:
        text = "عذراً، لا يمكن عرض الخريطة حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
        return
    
    publishers = hall_manager.get_hall_publishers(hall_number)
    svg_path = map_manager.save_hall_map(hall_number, publishers, highlight_code=None)
    if not svg_path:
        text = "عذراً، لا يمكن عرض الخريطة حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
        return
    
    try:
        png_path = svg_path.replace(".svg", ".png")
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        
        # Create section buttons
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
        
        # Add navigation buttons
        nav_row = create_nav_buttons(hall_number, 5)
        if nav_row:
            keyboard.append(nav_row)
        
        # Add home buttons
        keyboard.append([
            InlineKeyboardButton("عودة لقائمة القاعات", callback_data="maps"),
            InlineKeyboardButton("القائمة الرئيسية", callback_data="start")
        ])
        
        caption = (
            f"*خريطة {hall_info['name']}* 🗺\n"
            f"عدد الناشرين: {len(publishers)}"
        )
        
        await safe_delete_message(query.message)
        
        with open(png_path, "rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Cleanup temporary files
        os.remove(svg_path)
        os.remove(png_path)
        
    except Exception as e:
        logger.error(f"Error generating map: {e}")
        text = "عذراً، لا يمكن عرض الخريطة حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))

async def handle_section_view(query: telegram.CallbackQuery, hall_number: int, section: str) -> None:
    """Handle displaying publishers in a specific section."""
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
    
    await safe_delete_message(query.message)
    await query.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_categories_view(query: telegram.CallbackQuery) -> None:
    """Handle displaying publisher categories."""
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
    
    await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))

async def handle_events_view(query: telegram.CallbackQuery) -> None:
    """Handle displaying publisher events and offers."""
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
    
    await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))

async def handle_about_view(query: telegram.CallbackQuery) -> None:
    """Handle displaying about information."""
    total_publishers = sum(len(pubs) for pubs in hall_manager.halls.values())
    text = (
        "*معرض القاهرة الدولي للكتاب ٢٠٢٥* ℹ️\n\n"
        "أكبر وأقدم معرض كتاب في العالم العربي\n\n"
        f"• عدد دور النشر: {total_publishers}\n"
        "• عدد القاعات: 5\n"
        "• الموقع: مركز مصر للمعارض الدولية"
    )
    await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))

async def handle_publisher_location(query: telegram.CallbackQuery, hall_number: int, code: str) -> None:
    """Handle displaying a publisher's location on the hall map."""
    hall_info = map_manager.get_hall_info(hall_number)
    publisher = hall_manager.get_publisher_by_code(code)
    
    if not hall_info or not publisher:
        text = "عذراً، لا يمكن عرض الموقع حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
        return
    
    publishers = hall_manager.get_hall_publishers(hall_number)
    svg_path = map_manager.save_hall_map(hall_number, publishers, highlight_code=code)
    if not svg_path:
        text = "عذراً، لا يمكن عرض الموقع حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))
        return
    
    try:
        png_path = svg_path.replace(".svg", ".png")
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        
        keyboard = [
            [
                InlineKeyboardButton("↩️ عودة للناشر", callback_data=f"pub_{code}"),
                InlineKeyboardButton("📋 القائمة الرئيسية", callback_data="start")
            ]
        ]
        
        caption = (
            f"*موقع {publisher.get('nameAr', '')}*\n"
            f"الكود: `{code}` - قاعة {hall_number}"
        )
        
        await safe_delete_message(query.message)
        
        with open(png_path, "rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Cleanup temporary files
        os.remove(svg_path)
        os.remove(png_path)
        
    except Exception as e:
        logger.error(f"Error generating publisher map: {e}")
        text = "عذراً، لا يمكن عرض الموقع حالياً"
        await safe_edit_message(query, text, InlineKeyboardMarkup(create_home_button()))


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