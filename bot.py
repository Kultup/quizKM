import os
import logging
import schedule
import time
import threading
import asyncio
import sys
import psutil
from datetime import datetime, timedelta
from warnings import filterwarnings

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram.warnings import PTBUserWarning
from telegram.error import Conflict, NetworkError, TelegramError

# Ігнорування попереджень про CallbackQueryHandler в ConversationHandler
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

import config
import handlers
from database import generate_daily_test_for_all_users, send_reminder_to_users

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_scheduler():
    """Функція для запуску планувальника в окремому потоці"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Перевірка кожну хвилину


async def send_daily_tests():
    """Функція для розсилки щоденних тестів"""
    logger.info("Розсилка щоденних тестів...")
    try:
        # Генерація щоденних тестів для всіх користувачів
        users_with_tests = generate_daily_test_for_all_users()
        
        # Відправка повідомлень користувачам
        bot = Bot(token=config.TELEGRAM_TOKEN)
        for user_id, telegram_id in users_with_tests:
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text="Привіт! 🌟 Твій щоденний тест вже чекає на тебе! Готовий перевірити свої знання? Натискай /test! 🚀"
                )
                logger.info(f"Тест відправлено користувачу {telegram_id}")
            except Exception as e:
                logger.error(f"Помилка при відправці тесту користувачу {telegram_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Помилка при розсилці щоденних тестів: {str(e)}")


async def send_reminders():
    """Функція для відправки нагадувань про непройдені тести"""
    logger.info("Відправка нагадувань...")
    try:
        # Отримання користувачів, які не пройшли тест
        users_to_remind = send_reminder_to_users()
        
        # Відправка нагадувань
        bot = Bot(token=config.TELEGRAM_TOKEN)
        for telegram_id in users_to_remind:
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text="Гей! 👋 Не забувай про сьогоднішній тест! Ще є час показати, на що ти здатний! 💪 Жми /test!"
                )
                logger.info(f"Нагадування відправлено користувачу {telegram_id}")
            except Exception as e:
                logger.error(f"Помилка при відправці нагадування користувачу {telegram_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Помилка при відправці нагадувань: {str(e)}")


def setup_scheduler():
    """Налаштування планувальника завдань"""
    # Розсилка щоденних тестів о 12:00
    schedule.every().day.at(config.DAILY_TEST_TIME).do(lambda: asyncio.run(send_daily_tests()))
    
    # Відправка нагадувань о 18:00
    schedule.every().day.at(config.REMINDER_TIME).do(lambda: asyncio.run(send_reminders()))
    
    # Запуск планувальника в окремому потоці
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logger.info("Планувальник завдань запущено")


def is_bot_already_running():
    """Перевірка, чи вже запущений екземпляр бота"""
    current_process = psutil.Process(os.getpid())
    current_process_name = current_process.name()
    
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        # Пропускаємо поточний процес
        if process.info['pid'] == current_process.pid:
            continue
        
        # Перевіряємо, чи це Python процес
        if process.info['name'] == current_process_name:
            try:
                cmdline = process.info['cmdline']
                if cmdline and len(cmdline) > 1 and 'bot.py' in cmdline[-1]:
                    logger.warning(f"Знайдено інший екземпляр бота (PID: {process.info['pid']})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    return False


async def error_handler(update, context):
    """Обробник помилок для бота"""
    try:
        raise context.error
    except Conflict:
        logger.error("Конфлікт: інший екземпляр бота вже запущено. Завершення роботи...")
        # Завершуємо роботу програми
        sys.exit(1)
    except NetworkError:
        logger.error("Помилка мережі. Спробуй пізніше.")
    except TelegramError as e:
        logger.error(f"Помилка Telegram API: {e}")
    except Exception as e:
        logger.error(f"Невідома помилка: {e}")


def main():
    """Головна функція для запуску бота"""
    # Перевірка, чи вже запущений екземпляр бота
    if is_bot_already_running():
        logger.error("Інший екземпляр бота вже запущено. Завершення роботи...")
        sys.exit(1)
    
    # Ініціалізація бази даних
    handlers.init_database()
    
    # Створення додатку
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Реєстрація обробника помилок
    application.add_error_handler(error_handler)
    
    # Реєстрація обробників команд
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("knowledge", handlers.knowledge_base))
    application.add_handler(CommandHandler("statistics", handlers.statistics))
    
    # Обробник для тестів
    application.add_handler(CommandHandler("test", handlers.daily_test))
    
    # Обробник для реєстрації
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handlers.start)],
        states={
            handlers.REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.register_name)],
            handlers.REGISTRATION_CITY: [CallbackQueryHandler(handlers.register_city, pattern=r'^city_')],
            handlers.REGISTRATION_POSITION: [CallbackQueryHandler(handlers.register_position, pattern=r'^position_')],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)]
    )
    application.add_handler(registration_handler)
    
    # Обробник для зворотного зв'язку
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", handlers.feedback_command)],
        states={
            handlers.FEEDBACK_CATEGORY: [CallbackQueryHandler(handlers.select_feedback_category, pattern=r'^feedback_')],
            handlers.FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_feedback)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)]
    )
    application.add_handler(feedback_handler)
    
    # Обробники для відповідей на тести
    application.add_handler(CallbackQueryHandler(handlers.handle_answer, pattern=f"^{handlers.CALLBACK_OPTION_PREFIX}"))
    application.add_handler(CallbackQueryHandler(handlers.next_question, pattern=f"^{handlers.CALLBACK_NEXT_QUESTION}$"))
    
    # Обробники для бази знань
    application.add_handler(CallbackQueryHandler(handlers.knowledge_category, pattern=f"^{handlers.CALLBACK_KNOWLEDGE_CATEGORY}"))
    application.add_handler(CallbackQueryHandler(handlers.knowledge_item, pattern=f"^{handlers.CALLBACK_KNOWLEDGE_ITEM}"))
    application.add_handler(CallbackQueryHandler(handlers.knowledge_back, pattern=r'^knowledge_back$'))
    
    # Обробники для статистики та рейтингу
    application.add_handler(CallbackQueryHandler(handlers.ranking, pattern=f"^{handlers.CALLBACK_RANKING}$"))
    application.add_handler(CallbackQueryHandler(handlers.statistics_back, pattern=f"^statistics_back$"))
    
    # Обробники для категорій зворотного зв'язку
    application.add_handler(CallbackQueryHandler(handlers.handle_feedback_category, pattern=r'^feedback_(tech|content|suggestions|thanks|other)$'))
    
    # Обробник для тексту зворотного зв'язку
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_feedback_text))
    
    # Обробник для головного меню
    application.add_handler(CallbackQueryHandler(handlers.handle_main_menu, pattern=r'^(test|knowledge|statistics|feedback_menu|feedback|help|main_menu)$'))
    
    # Налаштування планувальника
    setup_scheduler()
    
    try:
        # Запуск бота
        logger.info("Запуск бота...")
        application.run_polling()
        logger.info("Бот запущено")
    except Conflict:
        logger.error("Конфлікт: інший екземпляр бота вже запущено. Завершення роботи...")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()