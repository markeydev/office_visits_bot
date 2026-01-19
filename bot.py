"""
Telegram бот для отслеживания посещений офиса
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

from database import Database
from calendar_data import is_working_day, format_date_ru, get_work_week_dates
from report_generator import ReportGenerator


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация
db = Database()
report_gen = ReportGenerator(db)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я помогу тебе отслеживать посещения офиса.

📌 <b>Основные команды:</b>
/today - Отметить сегодня
/week - Статус текущей недели
/report - Сформировать отчет

<b>Требования:</b>
Необходимо посещать офис минимум 1 раз в рабочую неделю.

Используй кнопки меню для быстрого доступа к функциям.
    """
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Был в офисе сегодня", callback_data="mark_today_office"),
            InlineKeyboardButton("🏠 Работал удаленно", callback_data="mark_today_home")
        ],
        [
            InlineKeyboardButton("📊 Текущая неделя", callback_data="show_week"),
            InlineKeyboardButton("📈 Отчет за месяц", callback_data="show_report")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /today"""
    today = datetime.now()
    
    if not is_working_day(today):
        await update.message.reply_text(
            f"📅 {format_date_ru(today)}\n\n"
            "Сегодня выходной день, отметка не требуется. 😊"
        )
        return
    
    keyboard = [
        [
            InlineKeyboardButton("🏢 Был в офисе", callback_data="mark_today_office"),
            InlineKeyboardButton("🏠 Работал удаленно", callback_data="mark_today_home")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверяем, есть ли уже отметка
    visit = db.get_visit(update.effective_user.id, today)
    
    status_text = ""
    if visit:
        status = "в офисе 🏢" if visit['was_in_office'] else "работал удаленно 🏠"
        status_text = f"\n<b>Текущий статус:</b> {status}"
    
    await update.message.reply_text(
        f"📅 <b>{format_date_ru(today)}</b>\n\n"
        f"Где ты сегодня работаешь?{status_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /week"""
    user_id = update.effective_user.id
    status = report_gen.get_current_week_status(user_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ Отметить сегодня", callback_data="mark_today_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        status,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /report"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Текущий месяц", callback_data="report_current"),
            InlineKeyboardButton("📅 Предыдущий месяц", callback_data="report_previous")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выбери период для отчета:",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    today = datetime.now()
    
    # Отметка сегодняшнего дня
    if query.data == "mark_today_office":
        if not is_working_day(today):
            await query.edit_message_text("Сегодня выходной день, отметка не требуется. 😊")
            return
        
        db.mark_visit(user_id, today, True)
        await query.edit_message_text(
            f"✅ Отлично! Отметил, что ты был в офисе.\n\n"
            f"📅 {format_date_ru(today)}\n"
            f"🏢 <b>В офисе</b>",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "mark_today_home":
        if not is_working_day(today):
            await query.edit_message_text("Сегодня выходной день, отметка не требуется. 😊")
            return
        
        db.mark_visit(user_id, today, False)
        await query.edit_message_text(
            f"✅ Записал! Сегодня удаленная работа.\n\n"
            f"📅 {format_date_ru(today)}\n"
            f"🏠 <b>Работа из дома</b>",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "mark_today_menu":
        keyboard = [
            [
                InlineKeyboardButton("🏢 Был в офисе", callback_data="mark_today_office"),
                InlineKeyboardButton("🏠 Работал удаленно", callback_data="mark_today_home")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📅 <b>{format_date_ru(today)}</b>\n\nГде ты сегодня работаешь?",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    # Показать неделю
    elif query.data == "show_week":
        status = report_gen.get_current_week_status(user_id)
        keyboard = [
            [InlineKeyboardButton("✅ Отметить сегодня", callback_data="mark_today_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            status,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    # Отчеты
    elif query.data in ["show_report", "report_current"]:
        await query.edit_message_text("⏳ Генерирую отчет...")
        
        # Текстовый отчет
        text_report = report_gen.generate_text_report(user_id, today.year, today.month)
        
        # Графический отчет
        try:
            image_report = report_gen.generate_image_report(user_id, today.year, today.month)
            await query.message.reply_photo(
                photo=image_report,
                caption="📊 Визуальный отчет о посещениях офиса"
            )
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
        
        await query.message.reply_text(text_report, parse_mode=ParseMode.HTML)
        await query.message.delete()
    
    elif query.data == "report_previous":
        await query.edit_message_text("⏳ Генерирую отчет...")
        
        # Предыдущий месяц
        if today.month == 1:
            prev_month = 12
            prev_year = today.year - 1
        else:
            prev_month = today.month - 1
            prev_year = today.year
        
        # Текстовый отчет
        text_report = report_gen.generate_text_report(user_id, prev_year, prev_month)
        
        # Графический отчет
        try:
            image_report = report_gen.generate_image_report(user_id, prev_year, prev_month)
            await query.message.reply_photo(
                photo=image_report,
                caption="📊 Визуальный отчет о посещениях офиса"
            )
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
        
        await query.message.reply_text(text_report, parse_mode=ParseMode.HTML)
        await query.message.delete()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуй еще раз или обратись к администратору."
        )


def main():
    """Запуск бота"""
    # Загружаем переменные из .env
    load_dotenv()
    # Получаем токен из переменной окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не указан TELEGRAM_BOT_TOKEN в переменных окружения")
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("week", week_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
