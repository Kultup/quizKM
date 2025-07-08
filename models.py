from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

from config import DATABASE_URL

# Створення з'єднання з базою даних
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
    """Модель користувача"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    total_score = Column(Integer, default=0)
    tests_completed = Column(Integer, default=0)
    tests_missed = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.now)

    # Зв'язки з іншими таблицями
    test_results = relationship('TestResult', back_populates='user')
    feedback = relationship('Feedback', back_populates='user')

    def __repr__(self):
        return f"<User(id={self.id}, name={self.first_name} {self.last_name}, position={self.position})>"


class City(Base):
    """Модель міста"""
    __tablename__ = 'cities'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<City(id={self.id}, name={self.name})>"


class Category(Base):
    """Модель категорії питань"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Зв'язки з іншими таблицями
    questions = relationship('Question', back_populates='category')
    knowledge_base_items = relationship('KnowledgeBaseItem', back_populates='category')

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Question(Base):
    """Модель питання"""
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    difficulty = Column(Integer, default=1)  # Рівень складності від 1 до 5
    is_active = Column(Boolean, default=True)
    position_required = Column(String(100), nullable=True)  # Посада, для якої призначене питання

    # Зв'язки з іншими таблицями
    category = relationship('Category', back_populates='questions')
    options = relationship('QuestionOption', back_populates='question')
    test_results = relationship('TestResult', back_populates='question')

    def __repr__(self):
        return f"<Question(id={self.id}, category_id={self.category_id})>"


class QuestionOption(Base):
    """Модель варіанту відповіді на питання"""
    __tablename__ = 'question_options'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    explanation = Column(Text, nullable=True)  # Пояснення, якщо відповідь неправильна

    # Зв'язки з іншими таблицями
    question = relationship('Question', back_populates='options')

    def __repr__(self):
        return f"<QuestionOption(id={self.id}, question_id={self.question_id}, is_correct={self.is_correct})>"


class DailyTest(Base):
    """Модель щоденного тесту"""
    __tablename__ = 'daily_tests'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, default=datetime.now)
    is_completed = Column(Boolean, default=False)
    score = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)

    # Зв'язки з іншими таблицями
    user = relationship('User')
    test_results = relationship('TestResult', back_populates='daily_test')

    def __repr__(self):
        return f"<DailyTest(id={self.id}, user_id={self.user_id}, date={self.date}, is_completed={self.is_completed})>"


class TestResult(Base):
    """Модель результату відповіді на питання"""
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    daily_test_id = Column(Integer, ForeignKey('daily_tests.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    question_index = Column(Integer, nullable=False, default=0)  # Порядок питання в тесті
    selected_option_id = Column(Integer, ForeignKey('question_options.id'), nullable=True)
    is_correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, nullable=True)

    # Зв'язки з іншими таблицями
    daily_test = relationship('DailyTest', back_populates='test_results')
    user = relationship('User', back_populates='test_results')
    question = relationship('Question', back_populates='test_results')
    selected_option = relationship('QuestionOption')

    def __repr__(self):
        return f"<TestResult(id={self.id}, user_id={self.user_id}, question_id={self.question_id}, is_correct={self.is_correct})>"


class KnowledgeBaseItem(Base):
    """Модель елементу бази знань"""
    __tablename__ = 'knowledge_base'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    position_required = Column(String(100), nullable=True)  # Посада, для якої призначений матеріал
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Зв'язки з іншими таблицями
    category = relationship('Category', back_populates='knowledge_base_items')

    def __repr__(self):
        return f"<KnowledgeBaseItem(id={self.id}, title={self.title}, category_id={self.category_id})>"


class Feedback(Base):
    """Модель зворотного зв'язку"""
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    rating = Column(Float, nullable=True)  # Оцінка від 1 до 5
    created_at = Column(DateTime, default=datetime.now)
    feedback_type = Column(String(50), nullable=False)  # Тип зворотного зв'язку (навчання, меню, тощо)
    is_read = Column(Boolean, default=False)  # Чи прочитано зворотній зв'язок

    # Зв'язки з іншими таблицями
    user = relationship('User', back_populates='feedback')

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, rating={self.rating})>"


class Position(Base):
    """Модель посади"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Position(id={self.id}, name={self.name})>"


# Створення всіх таблиць в базі даних
def create_tables():
    Base.metadata.create_all(engine)


# Функція для отримання сесії бази даних
def get_session():
    return Session()