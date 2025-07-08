from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import logging

import database as db
from models import create_tables, Feedback

# Налаштування логування
logger = logging.getLogger(__name__)

# Стани для ConversationHandler
REGISTRATION_NAME, REGISTRATION_CITY, REGISTRATION_POSITION = range(3)
QUESTION_ANSWERING, FEEDBACK_CATEGORY, FEEDBACK = range(3, 6)
WAITING_FEEDBACK_TEXT = 6

# Callback data для кнопок
CALLBACK_OPTION_PREFIX = 'option_'
CALLBACK_NEXT_QUESTION = 'next_question'
CALLBACK_KNOWLEDGE_CATEGORY = 'knowledge_cat_'
CALLBACK_KNOWLEDGE_ITEM = 'knowledge_item_'
CALLBACK_FEEDBACK = 'feedback'
CALLBACK_STATISTICS = 'statistics'
CALLBACK_RANKING = 'ranking'
CALLBACK_MAIN_MENU = 'main_menu'
CALLBACK_TEST = 'test'
CALLBACK_KNOWLEDGE = 'knowledge'
CALLBACK_FEEDBACK_MENU = 'feedback_menu'


# Функції для команд бота
async def show_main_menu(update: Update, context: CallbackContext, message_text: str = None):
    """Показати головне меню з кнопками"""
    keyboard = [
        [InlineKeyboardButton("📝 Пройти тест", callback_data=CALLBACK_TEST)],
        [InlineKeyboardButton("📚 База знань", callback_data=CALLBACK_KNOWLEDGE)],
        [InlineKeyboardButton("📊 Статистика", callback_data=CALLBACK_STATISTICS)],
        [InlineKeyboardButton("💬 Зворотний зв'язок", callback_data=CALLBACK_FEEDBACK_MENU)],
        [InlineKeyboardButton("❓ Допомога", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_text is None:
        message_text = "🏠 <b>Головне меню</b>\n\nОбирай, що хочеш зробити:"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    elif hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )


async def start(update: Update, context: CallbackContext):
    """Обробник команди /start"""
    if not hasattr(update, 'message') or not update.message:
        return
        
    user = update.effective_user
    
    # Перевірка, чи зареєстрований користувач
    db_user = db.get_user_by_telegram_id(user.id)
    
    if db_user:
        welcome_message = f"Привіт, {db_user.first_name}! 👋\n\nКлас, що ти тут! Ти вже в нашій команді 😊"
        await show_main_menu(update, context, welcome_message)
    else:
        await update.message.reply_text(
            f"Привіт! 🤗\n\n"
            f"Супер, що ти вирішив приєднатися до нас! Давай знайомитися 😊\n\n"
            f"Напиши своє ім'я та прізвище:"
        )
        return REGISTRATION_NAME


async def register_name(update: Update, context: CallbackContext):
    """Обробник введення імені та прізвища"""
    if not hasattr(update, 'message') or not update.message:
        return ConversationHandler.END
        
    full_name = update.message.text.strip()
    name_parts = full_name.split()
    
    if len(name_parts) < 2:
        await update.message.reply_text(
            "Ой, здається ти забув прізвище! 😅\n\nНапиши, будь ласка, ім'я та прізвище разом (наприклад: Іван Петренко):"
        )
        return REGISTRATION_NAME
    
    # Збереження в контексті
    context.user_data['first_name'] = name_parts[0]
    context.user_data['last_name'] = ' '.join(name_parts[1:])
    
    # Отримання міст з бази даних
    cities = db.get_cities()
    
    if not cities:
        await update.message.reply_text(
            "Упс! 😔 Поки що немає доступних міст. Напиши адміністратору, він швидко все налаштує!"
        )
        return ConversationHandler.END
    
    # Створення клавіатури для вибору міста
    keyboard = []
    for city in cities:
        keyboard.append([InlineKeyboardButton(city.name, callback_data=f"city_{city.id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Чудово, {context.user_data['first_name']}! 🎉\n\nТепер обери своє місто:",
        reply_markup=reply_markup
    )
    return REGISTRATION_CITY


async def register_city(update: Update, context: CallbackContext):
    """Обробник вибору міста"""
    query = update.callback_query
    await query.answer()
    
    city_id = query.data.split('_')[1]
    
    # Отримання міста з бази даних
    cities = db.get_cities()
    selected_city = next((city for city in cities if str(city.id) == city_id), None)
    
    if not selected_city:
        await query.edit_message_text(
            "Ой, щось пішло не так з містом! 😅 Спробуй ще раз, будь ласка."
        )
        return REGISTRATION_CITY
    
    # Збереження в контексті
    context.user_data['city'] = selected_city.name
    
    # Отримання посад з бази даних
    positions = db.get_positions()
    
    if not positions:
        await query.edit_message_text(
            "Упс! 😔 Поки що немає доступних посад. Напиши адміністратору, він швидко все налаштує!"
        )
        return ConversationHandler.END
    
    # Створення клавіатури для вибору посади
    keyboard = []
    for position in positions:
        keyboard.append([InlineKeyboardButton(position.name, callback_data=f"position_{position.id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Супер! 👍 Тепер обери свою посаду:",
        reply_markup=reply_markup
    )
    return REGISTRATION_POSITION


async def register_position(update: Update, context: CallbackContext):
    """Обробник вибору посади"""
    query = update.callback_query
    await query.answer()
    
    position_id = query.data.split('_')[1]
    
    # Отримання посади з бази даних
    positions = db.get_positions()
    selected_position = next((position for position in positions if str(position.id) == position_id), None)
    
    if not selected_position:
        await query.edit_message_text(
            "Ой, щось пішло не так з посадою! 😅 Спробуй ще раз, будь ласка."
        )
        return REGISTRATION_POSITION
    
    # Збереження в контексті
    context.user_data['position'] = selected_position.name
    
    # Реєстрація користувача в базі даних
    try:
        user = db.register_user(
            telegram_id=query.from_user.id,
            first_name=context.user_data['first_name'],
            last_name=context.user_data['last_name'],
            city=context.user_data['city'],
            position=selected_position.name
        )
        
        # Показуємо головне меню після реєстрації
        registration_message = (
            f"Ура! {user.first_name}, ти тепер частина нашої команди! 🎉\n\n"
            f"Кожен день о 12:00 я буду надсилати тобі цікаві тести. "
            f"Перший тест отримаєш завтра! 📚\n\n"
            f"🏠 <b>Головне меню</b>\n\nОбирай, що хочеш зробити:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Пройти тест", callback_data=CALLBACK_TEST)],
            [InlineKeyboardButton("📚 База знань", callback_data=CALLBACK_KNOWLEDGE)],
            [InlineKeyboardButton("📊 Статистика", callback_data=CALLBACK_STATISTICS)],
            [InlineKeyboardButton("💬 Зворотний зв'язок", callback_data=CALLBACK_FEEDBACK_MENU)],
            [InlineKeyboardButton("❓ Допомога", callback_data="help")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            registration_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await query.edit_message_text(
            f"Ой, щось пішло не так! 😔 Спробуй ще раз трохи пізніше.\n"
            f"Помилка: {str(e)}"
        )
    
    return ConversationHandler.END


async def handle_main_menu(update: Update, context: CallbackContext):
    """Обробник кнопок головного меню"""
    query = update.callback_query
    await query.answer()
    
    if query.data == CALLBACK_TEST:
        await daily_test_button(update, context)
    elif query.data == CALLBACK_KNOWLEDGE:
        await knowledge_base_button(update, context)
    elif query.data == CALLBACK_STATISTICS:
        await statistics_button(update, context)
    elif query.data == CALLBACK_FEEDBACK_MENU:
        await feedback_button(update, context)
    elif query.data == CALLBACK_FEEDBACK:
        await feedback_button(update, context)
    elif query.data == "help":
        await help_button(update, context)
    elif query.data == CALLBACK_MAIN_MENU:
        await show_main_menu(update, context)


async def daily_test_button(update: Update, context: CallbackContext):
    """Обробник кнопки тесту"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Перевіряємо реєстрацію
    db_user = db.get_user_by_telegram_id(user_id)
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Викликаємо існуючу логіку тесту
    await daily_test_logic(update, context)


async def daily_test_logic(update: Update, context: CallbackContext):
    """Логіка проходження щоденного тесту"""
    from datetime import datetime, time
    import config
    
    # Визначаємо user_id залежно від типу update
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        user = update.callback_query.from_user
    else:
        user_id = update.message.from_user.id
        user = update.effective_user
    
    db_user = db.get_user_by_telegram_id(user_id)
    
    if not db_user:
        message_text = "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)
        return
    
    # Перевірка дедлайну (00:00 наступного дня)
    now = datetime.now()
    current_date = now.date()
    deadline_time = time(config.DEADLINE_HOUR, config.DEADLINE_MINUTE)
    
    # Якщо поточний час після опівночі (00:00), то дедлайн для вчорашнього дня вже минув
    if now.time() >= deadline_time and config.DEADLINE_HOUR == 0:
        # Перевіряємо, чи є незавершений тест з попереднього дня
        from datetime import timedelta
        from models import DailyTest
        session = db.get_session()
        try:
            yesterday = current_date - timedelta(days=1)
            yesterday_test = session.query(DailyTest).filter(
                DailyTest.user_id == db_user.id,
                DailyTest.date >= yesterday,
                DailyTest.date < current_date,
                DailyTest.is_completed == False
            ).first()
            
            if yesterday_test:
                # Позначаємо тест як неактивний (не зарахований)
                yesterday_test.is_completed = True
                yesterday_test.score = 0
                session.commit()
                
                message_text = (
                    "⏰ На жаль, час для проходження вчорашнього тесту вийшов (дедлайн: 00:00). "
                    "Тест не зарахований. Але не засмучуйся - сьогодні у тебе є новий шанс! 💪"
                )
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(message_text)
                elif hasattr(update, 'message') and update.message:
                    await update.message.reply_text(message_text)
        finally:
            session.close()
    
    # Генерація або отримання щоденного тесту
    try:
        daily_test = db.generate_daily_test(db_user.id)
        
        # Перевірка, чи тест вже завершено
        if daily_test.is_completed:
            test_results = db.get_test_results(daily_test.id)
            
            # Створюємо кнопку повернення до головного меню
            keyboard = [[InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                f"Ти вже молодець - пройшов сьогоднішній тест! ✅\n\n"
                f"Твій результат: {test_results['score']} з {test_results['total_questions']} правильних відповідей. Круто! 🎉"
            )
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
            elif hasattr(update, 'message') and update.message:
                await update.message.reply_text(message_text, reply_markup=reply_markup)
            return
        
        # Збереження ID тесту в контексті
        context.user_data['daily_test_id'] = daily_test.id
        context.user_data['current_question'] = 0
        
        # Відправка першого питання
        await send_test_question(update, context)
        
        return QUESTION_ANSWERING
    except Exception as e:
        message_text = (
            f"Ой, щось пішло не так з тестом! 😔 Спробуй ще раз трохи пізніше.\n"
            f"Помилка: {str(e)}"
        )
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)


async def daily_test(update: Update, context: CallbackContext):
    """Обробник команди /test для проходження щоденного тесту"""
    await daily_test_logic(update, context)


async def knowledge_base_button(update: Update, context: CallbackContext):
    """Обробник кнопки бази знань"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Перевіряємо реєстрацію
    db_user = db.get_user_by_telegram_id(user_id)
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Викликаємо існуючу логіку бази знань
    await knowledge_base_logic(update, context)


async def statistics_button(update: Update, context: CallbackContext):
    """Обробник кнопки статистики"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Перевіряємо реєстрацію
    db_user = db.get_user_by_telegram_id(user_id)
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Викликаємо існуючу логіку статистики
    await statistics_logic(update, context)


async def feedback_button(update: Update, context: CallbackContext):
    """Обробник кнопки зворотного зв'язку"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Перевіряємо реєстрацію
    db_user = db.get_user_by_telegram_id(user_id)
    if not db_user:
        await query.edit_message_text(
            "❌ Ви не зареєстровані в системі. Використовуйте /start для реєстрації."
        )
        return
    
    # Викликаємо існуючу логіку зворотного зв'язку
    await feedback_logic(update, context)


async def help_button(update: Update, context: CallbackContext):
    """Обробник кнопки допомоги"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "📋 <b>Довідка по боту</b>\n\n"
        "🔹 <b>Пройти тест</b> - щоденний тест, щоб перевірити свої знання 🧠\n"
        "🔹 <b>База знань</b> - тут знайдеш корисні матеріали 📚\n"
        "🔹 <b>Статистика</b> - подивися на свої результати та прогрес 📊\n"
        "🔹 <b>Зворотний зв'язок</b> - поділися думками або пропозиціями 💬\n\n"
        "Щоб повернутися до головного меню, просто натисни кнопку нижче! 😊"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def send_test_question(update: Update, context: CallbackContext):
    """Відправка питання тесту користувачу"""
    daily_test_id = context.user_data.get('daily_test_id')
    question_index = context.user_data.get('current_question', 0)
    
    # Отримання питання
    question_data = db.get_test_question(daily_test_id, question_index)
    if not question_data:
        message_text = "Ой, щось пішло не так з питанням! 😔 Спробуй ще раз трохи пізніше."
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)
        elif hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        return
    
    # Збереження ID результату тесту в контексті
    context.user_data['current_test_result_id'] = question_data['test_result_id']
    
    # Створення клавіатури з варіантами відповідей
    keyboard = []
    for option in question_data['options']:
        # Обмежуємо довжину тексту для комфортного читання
        display_text = option.text
        if len(display_text) > 25:
            display_text = display_text[:22] + "..."
        
        keyboard.append([InlineKeyboardButton(
            display_text, callback_data=f"{CALLBACK_OPTION_PREFIX}{option.id}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Відправка питання
    question = question_data['question']
    message_text = f"Питання {question_index + 1}/5:\n\n{question.text}"
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)


async def handle_answer(update: Update, context: CallbackContext):
    """Обробник відповіді на питання тесту"""
    query = update.callback_query
    await query.answer()
    
    # Отримання ID вибраного варіанту
    option_id = int(query.data.replace(CALLBACK_OPTION_PREFIX, ''))
    test_result_id = context.user_data.get('current_test_result_id')
    
    # Збереження відповіді
    try:
        answer_result = db.answer_question(test_result_id, option_id)
        
        # Відображення результату відповіді
        if answer_result['is_correct']:
            result_text = "✅ Супер! Правильно! "
        else:
            result_text = f"❌ Ой, не зовсім. {answer_result.get('explanation', '')}"
        
        # Перевірка, чи тест завершено
        if answer_result['test_completed']:
            # Отримання результатів тесту
            daily_test_id = context.user_data.get('daily_test_id')
            test_results = db.get_test_results(daily_test_id)
            
            # Створюємо кнопки для навігації після завершення тесту
            keyboard = [
                [InlineKeyboardButton("📚 База знань", callback_data=CALLBACK_KNOWLEDGE)],
                [InlineKeyboardButton("📊 Статистика", callback_data=CALLBACK_STATISTICS)],
                [InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"{result_text}\n\n"
                f"🎉 Ура! Ти завершив сьогоднішній тест!\n\n"
                f"Твій результат: {test_results['score']} з {test_results['total_questions']} правильних відповідей. Молодець! 👏",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        else:
            # Перехід до наступного питання
            keyboard = [[InlineKeyboardButton("Наступне питання", callback_data=CALLBACK_NEXT_QUESTION)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"{result_text}\n\nГотовий до наступного питання? Натискай! 🚀",
                reply_markup=reply_markup
            )
    except Exception as e:
        await query.edit_message_text(
            f"Ой, щось пішло не так з відповіддю! 😔 Спробуй ще раз трохи пізніше.\n"
            f"Помилка: {str(e)}"
        )
        return ConversationHandler.END


async def next_question(update: Update, context: CallbackContext):
    """Обробник переходу до наступного питання"""
    query = update.callback_query
    await query.answer()
    
    # Збільшення індексу поточного питання
    context.user_data['current_question'] = context.user_data.get('current_question', 0) + 1
    
    # Відправка наступного питання
    await send_test_question(update, context)


async def knowledge_base_logic(update: Update, context: CallbackContext):
    """Логіка роботи з базою знань"""
    # Визначаємо user_id залежно від типу update
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        user = update.callback_query.from_user
    else:
        user_id = update.message.from_user.id
        user = update.effective_user
    
    db_user = db.get_user_by_telegram_id(user_id)
    
    if not db_user:
        message_text = "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)
        return
    
    # Отримання категорій бази знань
    categories = db.get_knowledge_categories()
    
    if not categories:
        # Створюємо кнопку повернення до головного меню
        keyboard = [[InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "Ой, база знань поки що порожня! 📚 Але не переживай, скоро тут з'являться цікаві матеріали! 😊"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        return
    
    # Створення клавіатури з категоріями
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(
            category.name, callback_data=f"{CALLBACK_KNOWLEDGE_CATEGORY}{category.id}"
        )])
    
    # Додаємо кнопку повернення до головного меню
    keyboard.append([InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "📚 <b>База знань</b>\n\nОбирай категорію, яка тебе цікавить:"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif hasattr(update, 'message') and update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def handle_feedback_category(update: Update, context: CallbackContext):
    """Обробка вибору категорії зворотного зв'язку"""
    query = update.callback_query
    await query.answer()
    
    # Визначаємо категорію на основі callback_data
    category_map = {
        "feedback_tech": "Технічні питання",
        "feedback_content": "Питання про контент",
        "feedback_suggestions": "Пропозиції",
        "feedback_thanks": "Подяки",
        "feedback_other": "Інше"
    }
    
    selected_category = category_map.get(query.data, "Інше")
    
    # Зберігаємо категорію в контексті
    context.user_data['feedback_category'] = selected_category
    
    # Створюємо кнопку повернення
    keyboard = [[InlineKeyboardButton("🔙 Назад до категорій", callback_data=CALLBACK_FEEDBACK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"💬 <b>Зворотний зв'язок - {selected_category}</b>\n\n"
        "Напиши своє повідомлення! Я обов'язково передам його команді, і ми відповімо якнайшвидше. 😊\n\n"
        "Просто надішли текстове повідомлення."
    )
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    # Встановлюємо стан очікування тексту
    context.user_data['state'] = WAITING_FEEDBACK_TEXT


async def handle_feedback_text(update: Update, context: CallbackContext):
    """Обробка тексту зворотного зв'язку"""
    if context.user_data.get('state') != WAITING_FEEDBACK_TEXT:
        return
    
    user_id = update.message.from_user.id
    feedback_text = update.message.text
    feedback_category = context.user_data.get('feedback_category', 'Інше')
    
    # Перевіряємо, чи користувач зареєстрований
    db_user = db.get_user_by_telegram_id(user_id)
    if not db_user:
        await update.message.reply_text("Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!")
        return
    
    # Зберігаємо відгук в базі даних
    try:
        feedback = db.add_feedback(
            user_id=db_user.id,
            text=feedback_text,
            feedback_type=feedback_category
        )
        
        # Створюємо кнопку повернення до головного меню
        keyboard = [[InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Дякую за твій відгук у категорії '{feedback_category}'! 🙏\n\n"
            "Твоє повідомлення успішно надіслано і буде розглянуто найближчим часом. Ти супер! 😊",
            reply_markup=reply_markup
        )
        
        # Очищаємо стан
        context.user_data.pop('state', None)
        context.user_data.pop('feedback_category', None)
        
    except Exception as e:
        logger.error(f"Помилка при збереженні відгуку: {e}")
        await update.message.reply_text("Ой, щось пішло не так при збереженні твого відгуку! 😔 Спробуй ще раз.")


async def knowledge_base(update: Update, context: CallbackContext):
    """Обробник команди /knowledge для доступу до бази знань"""
    await knowledge_base_logic(update, context)


async def statistics_logic(update: Update, context: CallbackContext):
    """Логіка роботи зі статистикою"""
    # Визначаємо user_id залежно від типу update
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        user = update.callback_query.from_user
    else:
        user_id = update.message.from_user.id
        user = update.effective_user
    
    db_user = db.get_user_by_telegram_id(user_id)
    
    if not db_user:
        message_text = "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)
        return
    
    try:
        # Отримання статистики користувача
        stats = db.get_user_statistics(db_user.id)
        
        # Створюємо кнопки для додаткових опцій
        keyboard = [
            [InlineKeyboardButton("📈 Рейтинг", callback_data=CALLBACK_RANKING)],
            [InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            f"📊 <b>Твоя статистика</b>\n\n"
            f"👤 Ім'я: {db_user.first_name}\n"
            f"🏢 Місто: {db_user.city}\n"
            f"💼 Посада: {db_user.position}\n\n"
            f"📝 Пройдено тестів: {stats.get('tests_completed', 0)} 🎯\n"
            f"✅ Правильних відповідей: {stats.get('correct_answers', 0)}\n"
            f"❌ Неправильних відповідей: {stats.get('incorrect_answers', 0)}\n"
            f"📈 Середній бал: {stats.get('average_score', 0):.1f}% (так тримати!)\n"
            f"🔥 Поточна серія: {stats.get('current_streak', 0)} днів поспіль"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        # Створюємо кнопку повернення до головного меню
        keyboard = [[InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = f"Ой, щось пішло не так зі статистикою! 😔 Спробуй пізніше.\nПомилка: {str(e)}"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup)


async def feedback_logic(update: Update, context: CallbackContext):
    """Логіка роботи зі зворотним зв'язком"""
    # Визначаємо user_id залежно від типу update
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        user = update.callback_query.from_user
    else:
        user_id = update.message.from_user.id
        user = update.effective_user
    
    db_user = db.get_user_by_telegram_id(user_id)
    
    if not db_user:
        message_text = "Ви не зареєстровані в системі. Використайте команду /start для реєстрації."
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(message_text)
        return
    
    # Створення клавіатури з категоріями зворотного зв'язку
    keyboard = [
        [InlineKeyboardButton("🔧 Технічні питання", callback_data="feedback_tech")],
        [InlineKeyboardButton("📝 Питання про контент", callback_data="feedback_content")],
        [InlineKeyboardButton("💡 Пропозиції", callback_data="feedback_suggestions")],
        [InlineKeyboardButton("🙏 Подяки", callback_data="feedback_thanks")],
        [InlineKeyboardButton("❓ Інше", callback_data="feedback_other")],
        [InlineKeyboardButton("🏠 Головне меню", callback_data=CALLBACK_MAIN_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "💬 <b>Зворотний зв'язок</b>\n\n"
        "Обирай категорію свого повідомлення:"
    )
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif hasattr(update, 'message') and update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def knowledge_category(update: Update, context: CallbackContext):
    """Обробник вибору категорії бази знань"""
    query = update.callback_query
    await query.answer()
    
    # Отримання ID категорії
    category_id = int(query.data.replace(CALLBACK_KNOWLEDGE_CATEGORY, ''))
    
    # Отримання інформації про користувача для визначення його посади
    user = query.from_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Отримання елементів бази знань за категорією з урахуванням посади користувача
    items = db.get_knowledge_items_by_category(category_id, db_user.position)
    
    if not items:
        await query.edit_message_text(
            "У цій категорії поки що немає матеріалів для твоєї посади. Спробуй іншу категорію! 😊\n\n"
            "Використовуйте /knowledge для повернення до списку категорій."
        )
        return
    
    # Створення клавіатури з елементами
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(
            item.title, callback_data=f"{CALLBACK_KNOWLEDGE_ITEM}{item.id}"
        )])
    
    # Додавання кнопки повернення
    keyboard.append([InlineKeyboardButton("⬅️ Назад до категорій", callback_data="knowledge_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Обирай матеріал для перегляду:",
        reply_markup=reply_markup
    )


async def knowledge_item(update: Update, context: CallbackContext):
    """Обробник вибору елементу бази знань"""
    query = update.callback_query
    await query.answer()
    
    # Отримання ID елементу
    item_id = int(query.data.replace(CALLBACK_KNOWLEDGE_ITEM, ''))
    
    # Отримання інформації про користувача для визначення його посади
    user = query.from_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Отримання елементу бази знань з урахуванням посади користувача
    item = db.get_knowledge_item(item_id, db_user.position)
    
    if not item:
        await query.edit_message_text(
            "На жаль, не вдалося отримати матеріал або він не призначений для вашої посади. Спробуйте інший матеріал.\n\n"
            "Використовуйте /knowledge для повернення до списку категорій."
        )
        return
    
    # Створення клавіатури з кнопкою повернення
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"{CALLBACK_KNOWLEDGE_CATEGORY}{item.category_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Відправка вмісту елементу
    await query.edit_message_text(
        f"<b>{item.title}</b>\n\n{item.content}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def knowledge_back(update: Update, context: CallbackContext):
    """Обробник повернення до списку категорій"""
    query = update.callback_query
    await query.answer()
    
    # Повторний виклик функції knowledge_base
    await knowledge_base(update, context)


async def statistics(update: Update, context: CallbackContext):
    """Обробник команди /statistics для перегляду статистики"""
    if not hasattr(update, 'message') or not update.message:
        return
        
    user = update.effective_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Отримання статистики користувача
    stats = db.get_user_statistics(db_user.id)
    
    if not stats:
        await update.message.reply_text(
            "Ой, щось пішло не так зі статистикою! 😔 Спробуй ще раз пізніше."
        )
        return
    
    # Створення клавіатури
    keyboard = [[InlineKeyboardButton("Переглянути рейтинг", callback_data=CALLBACK_RANKING)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"🏆 Загальний рахунок: {stats['total_score']} балів\n"
        f"✅ Тестів пройдено: {stats['tests_completed']}\n"
        f"❌ Тестів пропущено: {stats['tests_missed']}\n"
        f"📈 Відсоток проходження: {stats['completion_rate']:.1f}%\n"
        f"🎯 Точність за останній тиждень: {stats['week_accuracy']:.1f}%\n\n"
        f"Використовуй кнопку нижче, щоб переглянути свій рейтинг серед інших користувачів! 🏆",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def ranking(update: Update, context: CallbackContext):
    """Обробник перегляду рейтингу користувачів"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Отримання рейтингу користувача
    ranking_data = db.get_user_ranking(db_user.id)
    
    if not ranking_data:
        await query.edit_message_text(
            "Ой, щось пішло не так з рейтингом! 😔 Спробуй ще раз пізніше."
        )
        return
    
    # Формування повідомлення з рейтингом
    message = f"🏆 <b>Рейтинг користувачів</b>\n\n"
    
    # Топ-10 користувачів
    for user_data in ranking_data['top_users']:
        if user_data['position'] == ranking_data['user_position']:
            message += f"<b>{user_data['position']}. {user_data['name']} - {user_data['score']} балів</b> (Ти)\n"
        else:
            message += f"{user_data['position']}. {user_data['name']} - {user_data['score']} балів\n"
    
    # Якщо користувач не в топ-10, додаємо його позицію окремо
    if ranking_data['user_position'] > 10:
        message += f"\n<b>{ranking_data['user_position']}. {db_user.first_name} {db_user.last_name} - {db_user.total_score} балів</b> (Ти)\n"
    
    message += f"\nВсього користувачів: {ranking_data['total_users']}"
    
    # Створення клавіатури з кнопкою повернення
    keyboard = [[InlineKeyboardButton("⬅️ Назад до статистики", callback_data=CALLBACK_STATISTICS)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def statistics_back(update: Update, context: CallbackContext):
    """Обробник повернення до статистики"""
    query = update.callback_query
    await query.answer()
    
    # Повторний виклик функції statistics
    await statistics(update, context)


async def feedback_command(update: Update, context: CallbackContext):
    """Обробник команди /feedback для надання зворотного зв'язку"""
    if not hasattr(update, 'message') or not update.message:
        return
        
    user = update.effective_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return
    
    # Створення клавіатури з категоріями зворотного зв'язку
    keyboard = [
        [InlineKeyboardButton("Технічні питання", callback_data="feedback_tech")],
        [InlineKeyboardButton("Питання про контент", callback_data="feedback_content")],
        [InlineKeyboardButton("Пропозиції", callback_data="feedback_suggestions")],
        [InlineKeyboardButton("Подяки", callback_data="feedback_thanks")],
        [InlineKeyboardButton("Інше", callback_data="feedback_other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Будь ласка, обирай категорію зворотного зв'язку:",
        reply_markup=reply_markup
    )
    return FEEDBACK_CATEGORY


async def select_feedback_category(update: Update, context: CallbackContext):
    """Обробник вибору категорії зворотного зв'язку"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await query.edit_message_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return ConversationHandler.END
    
    # Отримання обраної категорії
    category_data = query.data.split('_', 1)[1]
    categories = {
        'tech': 'Технічні питання',
        'content': 'Питання про контент',
        'suggestions': 'Пропозиції',
        'thanks': 'Подяки',
        'other': 'Інше'
    }
    
    category = categories.get(category_data, 'Інше')
    
    # Збереження категорії в контексті
    context.user_data['feedback_category'] = category
    
    await query.edit_message_text(
        f"Ти обрав категорію: {category}\n\nНапиши свій відгук або пропозицію:"
    )
    return FEEDBACK


async def handle_feedback(update: Update, context: CallbackContext):
    """Обробник отримання зворотного зв'язку"""
    if not hasattr(update, 'message') or not update.message:
        return ConversationHandler.END
        
    user = update.effective_user
    db_user = db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text(
            "Ой! 😅 Здається, ти ще не в нашій команді. Натисни /start, щоб приєднатися!"
        )
        return ConversationHandler.END
    
    feedback_text = update.message.text.strip()
    
    if not feedback_text:
        await update.message.reply_text(
            "Напиши свій відгук або пропозицію:"
        )
        return FEEDBACK
    
    # Отримання категорії з контексту
    feedback_category = context.user_data.get('feedback_category', 'Інше')
    
    # Збереження зворотного зв'язку
    try:
        db.add_feedback(db_user.id, feedback_text, feedback_type=feedback_category)
        
        await update.message.reply_text(
            f"Дякую за твій відгук у категорії '{feedback_category}'! 😊 Ми обов'язково врахуємо твою думку для покращення роботи бота.\n\n"
            "Використовуй /test для проходження щоденного тесту.\n"
            "Використовуй /knowledge для доступу до бази знань.\n"
            "Використовуй /statistics для перегляду твоєї статистики."
        )
    except Exception as e:
        await update.message.reply_text(
            f"Ой, щось пішло не так при збереженні відгуку! 😔 Спробуй ще раз пізніше.\n"
            f"Помилка: {str(e)}"
        )
    
    return ConversationHandler.END


async def help_command(update: Update, context: CallbackContext):
    """Обробник команди /help"""
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            "📚 <b>Довідка по командах бота</b>\n\n"
            "/start - Початок роботи з ботом та реєстрація\n"
            "/test - Проходження щоденного тесту\n"
            "/knowledge - Доступ до бази знань\n"
            "/statistics - Перегляд вашої статистики\n"
            "/feedback - Надання зворотного зв'язку\n"
            "/help - Показати цю довідку\n\n"
            "Якщо у вас виникли проблеми з використанням бота, зверніться до адміністратора.",
            parse_mode=ParseMode.HTML
        )


async def cancel(update: Update, context: CallbackContext):
    """Обробник скасування розмови"""
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            "Операцію скасовано. Використовуй /help для перегляду доступних команд."
        )
    return ConversationHandler.END


# Функція для ініціалізації бази даних
def init_database():
    """Ініціалізація бази даних"""
    try:
        create_tables()
        print("База даних успішно ініціалізована.")
    except Exception as e:
        print(f"Помилка при ініціалізації бази даних: {str(e)}")
        raise e