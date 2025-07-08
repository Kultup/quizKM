from datetime import datetime, timedelta
import random
import logging
from sqlalchemy import func
from models import (
    get_session, User, Category, Question, QuestionOption, 
    DailyTest, TestResult, KnowledgeBaseItem, Feedback, City, Position
)
from config import QUESTIONS_PER_DAY

# Налаштування логування
logger = logging.getLogger(__name__)


# Функції для роботи з користувачами
def register_user(telegram_id, first_name, last_name, city, position):
    """Реєстрація нового користувача"""
    session = get_session()
    try:
        # Перевірка, чи існує користувач
        existing_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if existing_user:
            # Оновлення даних існуючого користувача
            existing_user.first_name = first_name
            existing_user.last_name = last_name
            existing_user.city = city
            existing_user.position = position
            existing_user.is_active = True
            session.commit()
            # Створюємо копію об'єкта перед закриттям сесії
            user_copy = User(
                id=existing_user.id,
                telegram_id=existing_user.telegram_id,
                first_name=existing_user.first_name,
                last_name=existing_user.last_name,
                city=existing_user.city,
                position=existing_user.position,
                registration_date=existing_user.registration_date,
                is_active=existing_user.is_active,
                is_admin=existing_user.is_admin,
                total_score=existing_user.total_score,
                tests_completed=existing_user.tests_completed,
                tests_missed=existing_user.tests_missed,
                last_activity=existing_user.last_activity
            )
            return user_copy
        
        # Створення нового користувача
        new_user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            city=city,
            position=position
        )
        session.add(new_user)
        session.commit()
        # Створюємо копію об'єкта перед закриттям сесії
        user_copy = User(
            id=new_user.id,
            telegram_id=new_user.telegram_id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            city=new_user.city,
            position=new_user.position,
            registration_date=new_user.registration_date,
            is_active=new_user.is_active,
            is_admin=new_user.is_admin,
            total_score=new_user.total_score,
            tests_completed=new_user.tests_completed,
            tests_missed=new_user.tests_missed,
            last_activity=new_user.last_activity
        )
        return user_copy
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_user_by_telegram_id(telegram_id):
    """Отримання користувача за Telegram ID"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            # Створюємо копію об'єкта перед закриттям сесії
            user_copy = User(
                id=user.id,
                telegram_id=user.telegram_id,
                first_name=user.first_name,
                last_name=user.last_name,
                city=user.city,
                position=user.position,
                registration_date=user.registration_date,
                is_active=user.is_active,
                is_admin=user.is_admin,
                total_score=user.total_score,
                tests_completed=user.tests_completed,
                tests_missed=user.tests_missed,
                last_activity=user.last_activity
            )
            return user_copy
        return None
    finally:
        session.close()


def get_user_statistics(user_id):
    """Отримання статистики користувача"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Загальна статистика відповідей
        all_results = session.query(TestResult).filter(
            TestResult.user_id == user_id,
            TestResult.answered_at.isnot(None)
        ).all()
        
        correct_answers = sum(1 for result in all_results if result.is_correct)
        incorrect_answers = len(all_results) - correct_answers
        average_score = (correct_answers / len(all_results) * 100) if all_results else 0
        
        # Поточна серія (streak) - кількість днів поспіль з пройденими тестами
        current_streak = 0
        current_date = datetime.now().date()
        
        # Перевіряємо кожен день назад, поки знаходимо пройдені тести
        check_date = current_date
        while True:
            daily_test = session.query(DailyTest).filter(
                DailyTest.user_id == user_id,
                func.date(DailyTest.date) == check_date,
                DailyTest.is_completed == True
            ).first()
            
            if daily_test:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        # Загальна статистика
        total_tests = user.tests_completed + user.tests_missed
        completion_rate = (user.tests_completed / total_tests * 100) if total_tests > 0 else 0
        
        # Статистика за останній тиждень
        week_ago = datetime.now() - timedelta(days=7)
        week_results = session.query(TestResult).join(DailyTest).filter(
            TestResult.user_id == user_id,
            DailyTest.date >= week_ago
        ).all()
        
        week_correct = sum(1 for result in week_results if result.is_correct)
        week_total = len(week_results)
        week_accuracy = (week_correct / week_total * 100) if week_total > 0 else 0
        
        return {
            'total_score': user.total_score,
            'tests_completed': user.tests_completed,
            'tests_missed': user.tests_missed,
            'completion_rate': completion_rate,
            'week_accuracy': week_accuracy,
            'correct_answers': correct_answers,
            'incorrect_answers': incorrect_answers,
            'average_score': average_score,
            'current_streak': current_streak
        }
    finally:
        session.close()


def get_user_ranking(user_id):
    """Отримання рейтингу користувача серед інших"""
    session = get_session()
    try:
        # Отримання всіх користувачів, відсортованих за балами
        users = session.query(User).filter(User.is_active == True).order_by(User.total_score.desc()).all()
        
        # Знаходження позиції користувача
        user_position = next((i + 1 for i, u in enumerate(users) if u.id == user_id), None)
        
        # Отримання топ-10 користувачів
        top_users = users[:10]
        
        return {
            'user_position': user_position,
            'total_users': len(users),
            'top_users': [{
                'position': i + 1,
                'name': f"{user.first_name} {user.last_name}",
                'score': user.total_score
            } for i, user in enumerate(top_users)]
        }
    finally:
        session.close()


# Функції для роботи з питаннями та тестами
def generate_daily_test(user_id):
    """Генерація щоденного тесту для користувача з урахуванням його посади"""
    session = get_session()
    try:
        # Перевірка, чи вже є тест на сьогодні
        today = datetime.now().date()
        existing_test = session.query(DailyTest).filter(
            DailyTest.user_id == user_id,
            func.date(DailyTest.date) == today
        ).first()
        
        if existing_test:
            return existing_test
        
        # Отримання інформації про користувача для визначення його посади
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"Користувача з ID {user_id} не знайдено")
        
        # Створення нового тесту
        new_test = DailyTest(user_id=user_id)
        session.add(new_test)
        session.flush()  # Отримання ID нового тесту
        
        # Отримання категорій
        categories = session.query(Category).all()
        if not categories:
            raise ValueError("Немає доступних категорій питань")
        
        # Отримання всіх питань, які користувач вже проходив раніше (виключаючи сьогоднішні тести)
        used_question_results = session.query(TestResult.question_id).join(
            DailyTest, TestResult.daily_test_id == DailyTest.id
        ).filter(
            TestResult.user_id == user_id,
            func.date(DailyTest.date) != today  # Виключаємо сьогоднішні тести
        ).distinct().all()
        
        used_questions = [row[0] for row in used_question_results]
        logger.info(f"Користувач {user_id} вже проходив {len(used_questions)} питань (виключаючи сьогоднішні): {used_questions}")
        
        # Вибір випадкових питань з різних категорій з урахуванням посади та виключенням вже пройдених
        selected_questions = []
        logger.info(f"Початок вибору питань для користувача {user_id}, посада: {user.position}")
        
        for _ in range(QUESTIONS_PER_DAY):
            # Вибір випадкової категорії
            category = random.choice(categories)
            logger.info(f"Вибрана категорія: {category.name}")
            
            # Отримання питань з цієї категорії, які відповідають посаді користувача або не мають обмежень за посадою
            # та виключаємо питання, які користувач вже проходив
            available_questions = session.query(Question).filter(
                Question.category_id == category.id,
                Question.is_active == True,
                ~Question.id.in_([q.id for q in selected_questions]),
                ~Question.id.in_(used_questions),
                ((Question.position_required == user.position) | (Question.position_required == None))
            ).all()
            
            logger.info(f"Знайдено {len(available_questions)} доступних питань у категорії {category.name} (виключаючи вже пройдені)")
            
            if available_questions:
                selected_question = random.choice(available_questions)
                selected_questions.append(selected_question)
                logger.info(f"Вибране питання ID: {selected_question.id}")
        
        # Якщо не вдалося вибрати достатньо питань з різних категорій,
        # доповнюємо випадковими питаннями, які відповідають посаді або не мають обмежень
        # та виключаємо вже пройдені питання
        if len(selected_questions) < QUESTIONS_PER_DAY:
            remaining_questions = session.query(Question).filter(
                Question.is_active == True,
                ~Question.id.in_([q.id for q in selected_questions]),
                ~Question.id.in_(used_questions),
                ((Question.position_required == user.position) | (Question.position_required == None))
            ).order_by(func.random()).limit(QUESTIONS_PER_DAY - len(selected_questions)).all()
            
            selected_questions.extend(remaining_questions)
            logger.info(f"Додано {len(remaining_questions)} питань для посади (виключаючи вже пройдені)")
        
        # Якщо все ще недостатньо питань, доповнюємо будь-якими активними питаннями (виключаючи вже пройдені)
        if len(selected_questions) < QUESTIONS_PER_DAY:
            logger.warning(f"Недостатньо питань для посади {user.position}, додаємо загальні питання (виключаючи вже пройдені)")
            any_remaining_questions = session.query(Question).filter(
                Question.is_active == True,
                ~Question.id.in_([q.id for q in selected_questions]),
                ~Question.id.in_(used_questions)
            ).order_by(func.random()).limit(QUESTIONS_PER_DAY - len(selected_questions)).all()
            
            selected_questions.extend(any_remaining_questions)
            logger.info(f"Додано {len(any_remaining_questions)} загальних питань (виключаючи вже пройдені)")
        
        # Якщо все ще недостатньо питань навіть після виключення вже пройдених,
        # то повертаємо вже пройдені питання (це означає, що користувач пройшов всі доступні питання)
        if len(selected_questions) < QUESTIONS_PER_DAY:
            logger.warning(f"Користувач {user_id} пройшов всі нові доступні питання, повертаємо вже пройдені")
            fallback_questions = session.query(Question).filter(
                Question.is_active == True,
                ~Question.id.in_([q.id for q in selected_questions]),
                Question.id.in_(used_questions),  # Тепер беремо саме вже пройдені питання
                ((Question.position_required == user.position) | (Question.position_required == None))
            ).order_by(func.random()).limit(QUESTIONS_PER_DAY - len(selected_questions)).all()
            
            selected_questions.extend(fallback_questions)
            logger.info(f"Додано {len(fallback_questions)} вже пройдених питань як резерв")
        
        # Створення записів TestResult для кожного питання
        logger.info(f"Створення {len(selected_questions)} TestResult записів")
        for i, question in enumerate(selected_questions):
            test_result = TestResult(
                daily_test_id=new_test.id,
                user_id=user_id,
                question_id=question.id,
                question_index=i
            )
            session.add(test_result)
            logger.info(f"Створено TestResult: daily_test_id={new_test.id}, question_id={question.id}, index={i}")
        
        session.commit()
        logger.info(f"Щоденний тест успішно створено для користувача {user_id}, ID тесту: {new_test.id}")
        
        # Створюємо копію об'єкта перед закриттям сесії
        test_copy = DailyTest(
            id=new_test.id,
            user_id=new_test.user_id,
            date=new_test.date,
            is_completed=new_test.is_completed,
            score=new_test.score,
            completed_at=new_test.completed_at
        )
        return test_copy
    except Exception as e:
        session.rollback()
        logger.error(f"Помилка при генерації тесту для користувача {user_id}: {str(e)}")
        raise e
    finally:
        session.close()


def get_test_question(daily_test_id, question_index):
    """Отримання питання за індексом з щоденного тесту"""
    session = get_session()
    try:
        logger.info(f"Отримання питання для тесту {daily_test_id}, індекс {question_index}")
        
        # Отримання результату тесту за індексом
        test_result = session.query(TestResult).filter(
            TestResult.daily_test_id == daily_test_id,
            TestResult.question_index == question_index
        ).first()
        
        if not test_result:
            logger.warning(f"Результат тесту з індексом {question_index} для тесту {daily_test_id} не знайдено")
            return None
        
        logger.info(f"Знайдено результат тесту з індексом {question_index}")
        logger.info(f"Отримання питання з ID {test_result.question_id}")
        
        question = session.query(Question).filter(Question.id == test_result.question_id).first()
        if not question:
            logger.error(f"Питання з ID {test_result.question_id} не знайдено")
            return None
            
        options = session.query(QuestionOption).filter(QuestionOption.question_id == question.id).all()
        if not options:
            logger.error(f"Варіанти відповідей для питання {question.id} не знайдено")
            return None
            
        logger.info(f"Знайдено {len(options)} варіантів відповідей")
        
        # Створюємо копії об'єктів перед закриттям сесії
        question_copy = Question(
            id=question.id,
            category_id=question.category_id,
            text=question.text,
            difficulty=question.difficulty,
            position_required=question.position_required
        )
        
        options_copy = []
        for option in options:
            option_copy = QuestionOption(
                id=option.id,
                question_id=option.question_id,
                text=option.text,
                is_correct=option.is_correct,
                explanation=option.explanation
            )
            options_copy.append(option_copy)
        
        return {
            'test_result_id': test_result.id,
            'question': question_copy,
            'options': options_copy
        }
    finally:
        session.close()


def answer_question(test_result_id, option_id):
    """Збереження відповіді користувача на питання"""
    session = get_session()
    try:
        # Отримання результату тесту
        test_result = session.query(TestResult).filter(TestResult.id == test_result_id).first()
        if not test_result:
            return None
        
        # Отримання вибраного варіанту
        option = session.query(QuestionOption).filter(QuestionOption.id == option_id).first()
        if not option:
            return None
        
        # Збереження відповіді
        test_result.selected_option_id = option_id
        test_result.is_correct = option.is_correct
        test_result.answered_at = datetime.now()
        
        # Оновлення щоденного тесту
        daily_test = session.query(DailyTest).filter(DailyTest.id == test_result.daily_test_id).first()
        
        # Перевірка, чи всі питання відповідені
        all_answered = session.query(TestResult).filter(
            TestResult.daily_test_id == daily_test.id,
            TestResult.answered_at == None
        ).count() == 0
        
        if all_answered:
            daily_test.is_completed = True
            daily_test.completed_at = datetime.now()
            
            # Підрахунок балів
            correct_answers = session.query(TestResult).filter(
                TestResult.daily_test_id == daily_test.id,
                TestResult.is_correct == True
            ).count()
            
            daily_test.score = correct_answers
            
            # Оновлення статистики користувача
            user = session.query(User).filter(User.id == daily_test.user_id).first()
            user.total_score += correct_answers
            user.tests_completed += 1
        
        session.commit()
        
        return {
            'is_correct': option.is_correct,
            'explanation': option.explanation if not option.is_correct else None,
            'test_completed': daily_test.is_completed if daily_test else False
        }
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_test_results(daily_test_id):
    """Отримання результатів тесту"""
    session = get_session()
    try:
        # Отримання щоденного тесту
        daily_test = session.query(DailyTest).filter(DailyTest.id == daily_test_id).first()
        if not daily_test:
            return None
        
        # Отримання результатів
        results = session.query(TestResult).filter(TestResult.daily_test_id == daily_test_id).all()
        
        # Формування детальної інформації
        detailed_results = []
        for result in results:
            question = session.query(Question).filter(Question.id == result.question_id).first()
            selected_option = session.query(QuestionOption).filter(
                QuestionOption.id == result.selected_option_id
            ).first() if result.selected_option_id else None
            
            correct_option = session.query(QuestionOption).filter(
                QuestionOption.question_id == question.id,
                QuestionOption.is_correct == True
            ).first()
            
            detailed_results.append({
                'question_text': question.text,
                'selected_option': selected_option.text if selected_option else None,
                'correct_option': correct_option.text,
                'is_correct': result.is_correct,
                'explanation': selected_option.explanation if selected_option and not result.is_correct else None
            })
        
        return {
            'score': daily_test.score,
            'total_questions': len(results),
            'completed_at': daily_test.completed_at,
            'detailed_results': detailed_results
        }
    finally:
        session.close()


def generate_daily_test_for_all_users():
    """Генерація щоденних тестів для всіх активних користувачів з урахуванням їх посади"""
    session = get_session()
    try:
        # Отримання всіх активних користувачів
        active_users = session.query(User).filter(User.is_active == True).all()
        
        # Список користувачів, для яких створено тести
        users_with_tests = []
        
        for user in active_users:
            try:
                # Створення тесту для користувача з урахуванням його посади
                daily_test = generate_daily_test(user.id)
                if daily_test:
                    users_with_tests.append((user.id, user.telegram_id))
            except Exception as e:
                logger.error(f"Помилка при створенні тесту для користувача {user.id}: {str(e)}")
        
        return users_with_tests
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def send_reminder_to_users():
    """Відправка нагадувань користувачам, які не пройшли щоденний тест"""
    session = get_session()
    try:
        # Отримання сьогоднішньої дати
        today = datetime.now().date()
        
        # Отримання користувачів, які мають непройдені тести на сьогодні
        users_to_remind = []
        
        # Отримання всіх активних користувачів
        active_users = session.query(User).filter(User.is_active == True).all()
        
        for user in active_users:
            # Перевірка, чи є у користувача тест на сьогодні
            daily_test = session.query(DailyTest).filter(
                DailyTest.user_id == user.id,
                func.date(DailyTest.date) == today,
                DailyTest.is_completed == False
            ).first()
            
            if daily_test:
                users_to_remind.append(user.telegram_id)
        
        return users_to_remind
    except Exception as e:
        logger.error(f"Помилка при відправці нагадувань: {str(e)}")
        session.rollback()
        raise e
    finally:
        session.close()


# Функції для роботи з базою знань
def get_knowledge_categories():
    """Отримання всіх категорій бази знань"""
    session = get_session()
    try:
        categories = session.query(Category).all()
        # Створюємо копії об'єктів перед закриттям сесії
        categories_copy = []
        for category in categories:
            category_copy = Category(
                id=category.id,
                name=category.name,
                description=category.description
            )
            categories_copy.append(category_copy)
        return categories_copy
    finally:
        session.close()


def get_knowledge_items_by_category(category_id, user_position=None):
    """Отримання елементів бази знань за категорією з урахуванням посади користувача"""
    session = get_session()
    try:
        # Базовий запит для отримання елементів за категорією
        query = session.query(KnowledgeBaseItem).filter(
            KnowledgeBaseItem.category_id == category_id
        )
        
        # Якщо вказана посада користувача, фільтруємо елементи за посадою
        if user_position:
            query = query.filter(
                ((KnowledgeBaseItem.position_required == user_position) | (KnowledgeBaseItem.position_required == None))
            )
        
        items = query.all()
        
        # Створюємо копії об'єктів перед закриттям сесії
        items_copy = []
        for item in items:
            item_copy = KnowledgeBaseItem(
                id=item.id,
                category_id=item.category_id,
                title=item.title,
                content=item.content,
                position_required=item.position_required,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            items_copy.append(item_copy)
        return items_copy
    except Exception as e:
        logger.error(f"Помилка при отриманні елементів бази знань за категорією {category_id}: {str(e)}")
        return []
    finally:
        session.close()


def get_knowledge_item(item_id, user_position=None):
    """Отримання конкретного елементу бази знань з урахуванням посади користувача"""
    session = get_session()
    try:
        # Отримання елементу за ID
        item = session.query(KnowledgeBaseItem).filter(KnowledgeBaseItem.id == item_id).first()
        
        # Перевірка, чи елемент доступний для посади користувача
        if item and user_position and item.position_required and item.position_required != user_position:
            logger.warning(f"Користувач з посадою {user_position} намагається отримати доступ до елементу {item_id}, призначеного для посади {item.position_required}")
            return None
        
        if item:
            # Створюємо копію об'єкта перед закриттям сесії
            item_copy = KnowledgeBaseItem(
                id=item.id,
                category_id=item.category_id,
                title=item.title,
                content=item.content,
                position_required=item.position_required,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            return item_copy
        return None
    except Exception as e:
        logger.error(f"Помилка при отриманні елементу бази знань {item_id}: {str(e)}")
        return None
    finally:
        session.close()


# Функції для роботи з містами
def get_cities():
    """Отримання всіх міст"""
    session = get_session()
    try:
        cities = session.query(City).all()
        # Створюємо копії об'єктів перед закриттям сесії
        cities_copy = []
        for city in cities:
            city_copy = City(
                id=city.id,
                name=city.name,
                description=city.description
            )
            cities_copy.append(city_copy)
        return cities_copy
    finally:
        session.close()


# Функції для роботи з посадами
def get_positions():
    """Отримання всіх посад"""
    session = get_session()
    try:
        positions = session.query(Position).all()
        # Створюємо копії об'єктів перед закриттям сесії
        positions_copy = []
        for position in positions:
            position_copy = Position(
                id=position.id,
                name=position.name,
                description=position.description
            )
            positions_copy.append(position_copy)
        return positions_copy
    finally:
        session.close()


# Функції для роботи зі зворотним зв'язком
def add_feedback(user_id, text, rating=None, feedback_type='general'):
    """Додавання зворотного зв'язку від користувача"""
    session = get_session()
    try:
        feedback = Feedback(
            user_id=user_id,
            text=text,
            rating=rating,
            feedback_type=feedback_type
        )
        session.add(feedback)
        session.commit()
        
        # Створюємо копію об'єкта перед закриттям сесії
        feedback_copy = Feedback(
            id=feedback.id,
            user_id=feedback.user_id,
            text=feedback.text,
            rating=feedback.rating,
            feedback_type=feedback.feedback_type,
            created_at=feedback.created_at
        )
        return feedback_copy
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()