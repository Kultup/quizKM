FROM python:3.9-slim

# Встановлення робочої директорії
WORKDIR /app

# Копіювання файлів залежностей
COPY requirements.txt .

# Встановлення залежностей
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання всіх файлів проекту
COPY . .

# Створення директорії для бази даних
RUN mkdir -p /app/data

# Встановлення змінних оточення
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///data/bot_database.db \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000

# Відкриття порту для адміністративної панелі
EXPOSE 5000

# Запуск бота та адміністративної панелі
CMD ["python", "bot.py"]