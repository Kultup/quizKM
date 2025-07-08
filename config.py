import os
from dotenv import load_dotenv

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Конфігурація бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Конфігурація бази даних
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot_database.db')

# Налаштування часу розсилки (за замовчуванням 10:00)
DEFAULT_NOTIFICATION_HOUR = int(os.getenv('DEFAULT_NOTIFICATION_HOUR', 10))
DEFAULT_NOTIFICATION_MINUTE = int(os.getenv('DEFAULT_NOTIFICATION_MINUTE', 0))

# Час розсилки щоденних тестів (формат HH:MM)
DAILY_TEST_TIME = f"{DEFAULT_NOTIFICATION_HOUR:02d}:{DEFAULT_NOTIFICATION_MINUTE:02d}"

# Налаштування дедлайну (за замовчуванням 00:00 наступного дня)
DEADLINE_HOUR = int(os.getenv('DEADLINE_HOUR', 0))
DEADLINE_MINUTE = int(os.getenv('DEADLINE_MINUTE', 0))

# Кількість питань у щоденному тесті
QUESTIONS_PER_DAY = int(os.getenv('QUESTIONS_PER_DAY', 5))

# Час нагадування (за N годин до дедлайну)
REMINDER_HOURS_BEFORE_DEADLINE = int(os.getenv('REMINDER_HOURS_BEFORE_DEADLINE', 3))

# Час відправки нагадувань (формат HH:MM, за замовчуванням 18:00)
REMINDER_TIME = os.getenv('REMINDER_TIME', '18:00')

# Налаштування для Flask адмін-панелі
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_change_in_production')
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Налаштування для адміністратора
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Налаштування логування
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Часовий пояс
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Kiev')

# Налаштування для рейтингової системи
POINTS_PER_CORRECT_ANSWER = int(os.getenv('POINTS_PER_CORRECT_ANSWER', 10))  # Кількість балів за правильну відповідь

# Налаштування для бази знань
KNOWLEDGE_BASE_ITEMS_PER_PAGE = int(os.getenv('KNOWLEDGE_BASE_ITEMS_PER_PAGE', 5))  # Кількість елементів на сторінці бази знань