import os
import logging
import pandas as pd
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text, or_
from sqlalchemy.orm import sessionmaker
import matplotlib.pyplot as plt
import io

import config
from models import Base, User, Category, Question, QuestionOption, DailyTest, TestResult, KnowledgeBaseItem, Feedback, City, Position

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Створення Flask додатку
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Налаштування Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Підключення до бази даних
engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)


# Модель адміністратора для Flask-Login
class Admin(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash


# Створення тестового адміністратора (в реальному проекті використовуйте базу даних)
admins = {
    1: Admin(1, 'admin', generate_password_hash('admin123'))
}


@login_manager.user_loader
def load_user(user_id):
    return admins.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Пошук адміністратора за ім'ям користувача
        admin = next((a for a in admins.values() if a.username == username), None)
        
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            return redirect(url_for('dashboard'))
        
        flash('Невірне ім\'я користувача або пароль', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    session = Session()
    try:
        # Статистика користувачів
        total_users = session.query(User).count()
        active_users = session.query(User).filter(User.last_activity >= datetime.now() - timedelta(days=7)).count()
        
        # Статистика тестів
        total_tests = session.query(DailyTest).count()
        completed_tests = session.query(DailyTest).filter(DailyTest.is_completed == True).count()
        
        # Статистика питань
        total_questions = session.query(Question).count()
        total_categories = session.query(Category).count()
        
        # Статистика бази знань
        total_kb_items = session.query(KnowledgeBaseItem).count()
        
        # Статистика зворотного зв'язку
        total_feedback = session.query(Feedback).count()
        unread_feedback = session.query(Feedback).filter(Feedback.is_read == False).count()
        
        # Статистика міст
        total_cities = session.query(City).count()
        
        # Статистика посад
        total_positions = session.query(Position).count()
        
        return render_template(
            'dashboard.html',
            total_users=total_users,
            active_users=active_users,
            total_tests=total_tests,
            completed_tests=completed_tests,
            total_questions=total_questions,
            total_categories=total_categories,
            total_kb_items=total_kb_items,
            total_feedback=total_feedback,
            unread_feedback=unread_feedback,
            total_cities=total_cities,
            total_positions=total_positions
        )
    finally:
        session.close()


@app.route('/users')
@login_required
def users():
    session = Session()
    try:
        users_list = session.query(User).all()
        return render_template('users.html', users=users_list)
    finally:
        session.close()


@app.route('/user/<int:user_id>')
@login_required
def user_details(user_id):
    session = Session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            flash('Користувача не знайдено', 'danger')
            return redirect(url_for('users'))
        
        # Отримання статистики користувача
        tests = session.query(DailyTest).filter(DailyTest.user_id == user_id).all()
        results = session.query(TestResult).filter(TestResult.user_id == user_id).all()
        
        # Обчислення статистики
        total_tests = len(tests)
        completed_tests = sum(1 for test in tests if test.is_completed)
        correct_answers = sum(result.is_correct for result in results)
        total_answers = len(results)
        accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        
        return render_template(
            'user_details.html',
            user=user,
            total_tests=total_tests,
            completed_tests=completed_tests,
            accuracy=accuracy
        )
    finally:
        session.close()


@app.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    session = Session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            flash('Користувача не знайдено', 'danger')
            return redirect(url_for('users'))
        
        # Видаляємо всі пов'язані дані перед видаленням користувача
        # Видаляємо результати тестів
        session.query(TestResult).filter(TestResult.user_id == user_id).delete()
        
        # Видаляємо щоденні тести
        session.query(DailyTest).filter(DailyTest.user_id == user_id).delete()
        
        # Видаляємо зворотний зв'язок
        session.query(Feedback).filter(Feedback.user_id == user_id).delete()
        
        # Видаляємо самого користувача
        session.delete(user)
        session.commit()
        flash('Користувача та всі пов\'язані дані успішно видалено', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні користувача: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('users'))


@app.route('/categories')
@login_required
def categories():
    session = Session()
    try:
        categories_list = session.query(Category).all()
        return render_template('categories.html', categories=categories_list)
    finally:
        session.close()


@app.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Назва категорії обов\'язкова', 'danger')
            return redirect(url_for('add_category'))
        
        session = Session()
        try:
            category = Category(name=name, description=description)
            session.add(category)
            session.commit()
            flash('Категорію успішно додано', 'success')
            return redirect(url_for('categories'))
        except Exception as e:
            session.rollback()
            flash(f'Помилка при додаванні категорії: {str(e)}', 'danger')
        finally:
            session.close()
    
    return render_template('add_category.html')


@app.route('/category/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    session = Session()
    try:
        category = session.query(Category).filter(Category.id == category_id).first()
        if not category:
            flash('Категорію не знайдено', 'danger')
            return redirect(url_for('categories'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash('Назва категорії обов\'язкова', 'danger')
                return redirect(url_for('edit_category', category_id=category_id))
            
            category.name = name
            category.description = description
            
            try:
                session.commit()
                flash('Категорію успішно оновлено', 'success')
                return redirect(url_for('categories'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при оновленні категорії: {str(e)}', 'danger')
        
        return render_template('edit_category.html', category=category)
    finally:
        session.close()


@app.route('/category/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    session = Session()
    try:
        category = session.query(Category).filter(Category.id == category_id).first()
        if not category:
            flash('Категорію не знайдено', 'danger')
            return redirect(url_for('categories'))
        
        # Перевірка, чи є питання в цій категорії
        questions_count = session.query(Question).filter(Question.category_id == category_id).count()
        if questions_count > 0:
            flash(f'Неможливо видалити категорію, оскільки вона містить {questions_count} питань', 'danger')
            return redirect(url_for('categories'))
        
        session.delete(category)
        session.commit()
        flash('Категорію успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні категорії: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('categories'))


@app.route('/cities')
@login_required
def cities():
    session = Session()
    try:
        cities_list = session.query(City).all()
        return render_template('cities.html', cities=cities_list)
    finally:
        session.close()


@app.route('/city/add', methods=['GET', 'POST'])
@login_required
def add_city():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Назва міста обов\'язкова', 'danger')
            return redirect(url_for('add_city'))
        
        session = Session()
        try:
            city = City(name=name, description=description)
            session.add(city)
            session.commit()
            flash('Місто успішно додано', 'success')
            return redirect(url_for('cities'))
        except Exception as e:
            session.rollback()
            flash(f'Помилка при додаванні міста: {str(e)}', 'danger')
        finally:
            session.close()
    
    return render_template('add_city.html')


@app.route('/city/edit/<int:city_id>', methods=['GET', 'POST'])
@login_required
def edit_city(city_id):
    session = Session()
    try:
        city = session.query(City).filter(City.id == city_id).first()
        if not city:
            flash('Місто не знайдено', 'danger')
            return redirect(url_for('cities'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash('Назва міста обов\'язкова', 'danger')
                return redirect(url_for('edit_city', city_id=city_id))
            
            city.name = name
            city.description = description
            
            try:
                session.commit()
                flash('Місто успішно оновлено', 'success')
                return redirect(url_for('cities'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при оновленні міста: {str(e)}', 'danger')
        
        return render_template('edit_city.html', city=city)
    finally:
        session.close()


@app.route('/city/delete/<int:city_id>', methods=['POST'])
@login_required
def delete_city(city_id):
    session = Session()
    try:
        city = session.query(City).filter(City.id == city_id).first()
        if not city:
            flash('Місто не знайдено', 'danger')
            return redirect(url_for('cities'))
        
        session.delete(city)
        session.commit()
        flash('Місто успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні міста: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('cities'))


@app.route('/questions')
@login_required
def questions():
    session = Session()
    try:
        # Отримання параметрів фільтрації
        category_id = request.args.get('category_id')
        position_required = request.args.get('position_required')
        search = request.args.get('search')
        
        # Базовий запит
        query = session.query(Question)
        
        # Застосування фільтрів
        if category_id:
            query = query.filter(Question.category_id == category_id)
        
        if position_required:
            query = query.filter(Question.position_required == position_required)
        
        if search:
            query = query.filter(Question.text.ilike(f'%{search}%'))
        
        questions_list = query.all()
        all_categories = session.query(Category).all()
        
        return render_template('questions.html', questions=questions_list, all_categories=all_categories)
    finally:
        session.close()


@app.route('/question/add', methods=['GET', 'POST'])
@login_required
def add_question():
    session = Session()
    try:
        categories_list = session.query(Category).all()
        
        if request.method == 'POST':
            text = request.form.get('text')
            category_id = request.form.get('category_id')
            
            if not text or not category_id:
                flash('Текст питання та категорія обов\'язкові', 'danger')
                return redirect(url_for('add_question'))
            
            # Отримання варіантів відповідей
            options = []
            for i in range(1, 5):  # Припускаємо, що у нас 4 варіанти відповіді
                option_text = request.form.get(f'option_{i}')
                is_correct = request.form.get(f'is_correct_{i}') == 'on'
                explanation = request.form.get(f'explanation_{i}', '')
                
                if option_text:
                    if len(option_text) > 25:
                        flash(f'Варіант відповіді {i} занадто довгий. Максимум 25 символів.', 'danger')
                        return redirect(url_for('add_question'))
                    options.append((option_text, is_correct, explanation))
            
            if len(options) < 2:
                flash('Питання повинно мати щонайменше 2 варіанти відповіді', 'danger')
                return redirect(url_for('add_question'))
            
            if not any(is_correct for _, is_correct, _ in options):
                flash('Питання повинно мати щонайменше 1 правильну відповідь', 'danger')
                return redirect(url_for('add_question'))
            
            try:
                # Отримання посади
                position_required = request.form.get('position_required')
                
                # Створення питання
                question = Question(
                    text=text,
                    category_id=category_id,
                    position_required=position_required
                )
                session.add(question)
                session.flush()  # Отримання ID питання
                
                # Створення варіантів відповідей
                for option_text, is_correct, explanation in options:
                    option = QuestionOption(
                        question_id=question.id,
                        text=option_text,
                        is_correct=is_correct,
                        explanation=explanation if explanation else None
                    )
                    session.add(option)
                
                session.commit()
                flash('Питання успішно додано', 'success')
                return redirect(url_for('questions'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при додаванні питання: {str(e)}', 'danger')
        
        return render_template('add_question.html', categories=categories_list)
    finally:
        session.close()


@app.route('/question/edit/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    session = Session()
    try:
        question = session.query(Question).filter(Question.id == question_id).first()
        if not question:
            flash('Питання не знайдено', 'danger')
            return redirect(url_for('questions'))
        
        categories_list = session.query(Category).all()
        options = session.query(QuestionOption).filter(QuestionOption.question_id == question_id).all()
        
        if request.method == 'POST':
            text = request.form.get('text')
            category_id = request.form.get('category_id')
            
            if not text or not category_id:
                flash('Текст питання та категорія обов\'язкові', 'danger')
                return redirect(url_for('edit_question', question_id=question_id))
            
            # Отримання посади
            position_required = request.form.get('position_required')
            
            # Оновлення питання
            question.text = text
            question.category_id = category_id
            question.position_required = position_required
            
            # Видалення старих варіантів відповідей
            for option in options:
                session.delete(option)
            
            # Отримання нових варіантів відповідей
            new_options = []
            for i in range(1, 5):  # Припускаємо, що у нас 4 варіанти відповіді
                option_text = request.form.get(f'option_{i}')
                is_correct = request.form.get(f'is_correct_{i}') == 'on'
                explanation = request.form.get(f'explanation_{i}', '')
                
                if option_text:
                    if len(option_text) > 25:
                        flash(f'Варіант відповіді {i} занадто довгий. Максимум 25 символів.', 'danger')
                        return redirect(url_for('edit_question', question_id=question_id))
                    new_options.append((option_text, is_correct, explanation))
            
            if len(new_options) < 2:
                flash('Питання повинно мати щонайменше 2 варіанти відповіді', 'danger')
                return redirect(url_for('edit_question', question_id=question_id))
            
            if not any(is_correct for _, is_correct, _ in new_options):
                flash('Питання повинно мати щонайменше 1 правильну відповідь', 'danger')
                return redirect(url_for('edit_question', question_id=question_id))
            
            try:
                # Створення нових варіантів відповідей
                for option_text, is_correct, explanation in new_options:
                    option = QuestionOption(
                        question_id=question.id,
                        text=option_text,
                        is_correct=is_correct,
                        explanation=explanation if explanation else None
                    )
                    session.add(option)
                
                session.commit()
                flash('Питання успішно оновлено', 'success')
                return redirect(url_for('questions'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при оновленні питання: {str(e)}', 'danger')
        
        return render_template('edit_question.html', question=question, categories=categories_list, options=options)
    finally:
        session.close()


@app.route('/question/delete/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    session = Session()
    try:
        question = session.query(Question).filter(Question.id == question_id).first()
        if not question:
            flash('Питання не знайдено', 'danger')
            return redirect(url_for('questions'))
        
        # Видалення варіантів відповідей
        options = session.query(QuestionOption).filter(QuestionOption.question_id == question_id).all()
        for option in options:
            session.delete(option)
        
        # Видалення питання
        session.delete(question)
        session.commit()
        flash('Питання успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні питання: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('questions'))


@app.route('/knowledge')
@login_required
def knowledge_base():
    session = Session()
    try:
        # Отримання параметрів фільтрації
        category_id = request.args.get('category_id')
        position_required = request.args.get('position_required')
        search = request.args.get('search')
        
        # Базовий запит
        query = session.query(KnowledgeBaseItem)
        
        # Застосування фільтрів
        if category_id:
            query = query.filter(KnowledgeBaseItem.category_id == category_id)
        
        if position_required:
            query = query.filter(KnowledgeBaseItem.position_required == position_required)
        
        if search:
            query = query.filter(or_(KnowledgeBaseItem.title.ilike(f'%{search}%'), 
                                   KnowledgeBaseItem.content.ilike(f'%{search}%')))
        
        knowledge_items = query.all()
        all_categories = session.query(Category).all()
        
        return render_template('knowledge_base.html', knowledge_items=knowledge_items, all_categories=all_categories)
    finally:
        session.close()


@app.route('/knowledge/add', methods=['GET', 'POST'])
@login_required
def add_knowledge_item():
    session = Session()
    try:
        categories_list = session.query(Category).all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            
            if not title or not content or not category_id:
                flash('Заголовок, вміст та категорія обов\'язкові', 'danger')
                return redirect(url_for('add_knowledge_item'))
            
            try:
                # Отримання посади
                position_required = request.form.get('position_required')
                
                item = KnowledgeBaseItem(
                    title=title,
                    content=content,
                    category_id=category_id,
                    position_required=position_required
                )
                session.add(item)
                session.commit()
                flash('Матеріал успішно додано', 'success')
                return redirect(url_for('knowledge_base'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при додаванні матеріалу: {str(e)}', 'danger')
        
        return render_template('add_knowledge_item.html', categories=categories_list)
    finally:
        session.close()


@app.route('/knowledge/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_knowledge_item(item_id):
    session = Session()
    try:
        item = session.query(KnowledgeBaseItem).filter(KnowledgeBaseItem.id == item_id).first()
        if not item:
            flash('Матеріал не знайдено', 'danger')
            return redirect(url_for('knowledge_base'))
        
        categories_list = session.query(Category).all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            
            if not title or not content or not category_id:
                flash('Заголовок, вміст та категорія обов\'язкові', 'danger')
                return redirect(url_for('edit_knowledge_item', item_id=item_id))
            
            try:
                # Отримання посади
                position_required = request.form.get('position_required')
                
                item.title = title
                item.content = content
                item.category_id = category_id
                item.position_required = position_required
                session.commit()
                flash('Матеріал успішно оновлено', 'success')
                return redirect(url_for('knowledge_base'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при оновленні матеріалу: {str(e)}', 'danger')
        
        return render_template('edit_knowledge_item.html', item=item, categories=categories_list)
    finally:
        session.close()


@app.route('/knowledge/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_knowledge_item(item_id):
    session = Session()
    try:
        item = session.query(KnowledgeBaseItem).filter(KnowledgeBaseItem.id == item_id).first()
        if not item:
            flash('Матеріал не знайдено', 'danger')
            return redirect(url_for('knowledge_base'))
        
        session.delete(item)
        session.commit()
        flash('Матеріал успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні матеріалу: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('knowledge_base'))


@app.route('/feedback')
@login_required
def feedback():
    session = Session()
    try:
        filter_type = request.args.get('filter', 'all')
        
        if filter_type == 'unread':
            feedback_list = session.query(Feedback).filter(Feedback.is_read == False).order_by(Feedback.created_at.desc()).all()
        elif filter_type == 'read':
            feedback_list = session.query(Feedback).filter(Feedback.is_read == True).order_by(Feedback.created_at.desc()).all()
        else:
            feedback_list = session.query(Feedback).order_by(Feedback.created_at.desc()).all()
        
        return render_template('feedback.html', feedback_items=feedback_list, filter=filter_type)
    finally:
        session.close()


@app.route('/feedback/mark_read/<int:feedback_id>', methods=['POST'])
@login_required
def mark_feedback_read(feedback_id):
    session = Session()
    try:
        feedback_item = session.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback_item:
            flash('Відгук не знайдено', 'danger')
            return redirect(url_for('feedback'))
        
        feedback_item.is_read = True
        session.commit()
        flash('Відгук позначено як прочитаний', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при оновленні відгуку: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('feedback'))


@app.route('/feedback/view/<int:feedback_id>')
@login_required
def view_feedback(feedback_id):
    session = Session()
    try:
        feedback_item = session.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback_item:
            flash('Відгук не знайдено', 'danger')
            return redirect(url_for('feedback'))
        
        # Позначаємо як прочитаний при перегляді
        if not feedback_item.is_read:
            feedback_item.is_read = True
            session.commit()
        
        return render_template('view_feedback.html', feedback=feedback_item)
    except Exception as e:
        session.rollback()
        flash(f'Помилка при завантаженні відгуку: {str(e)}', 'danger')
        return redirect(url_for('feedback'))
    finally:
        session.close()


@app.route('/feedback/delete/<int:feedback_id>', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    session = Session()
    try:
        feedback_item = session.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback_item:
            flash('Відгук не знайдено', 'danger')
            return redirect(url_for('feedback'))
        
        session.delete(feedback_item)
        session.commit()
        flash('Відгук успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні відгуку: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('feedback'))


@app.route('/reports')
@login_required
def reports():
    session = Session()
    try:
        all_categories = session.query(Category).all()
        return render_template('reports.html', all_categories=all_categories)
    finally:
        session.close()


@app.route('/reports/user_activity')
@login_required
def user_activity_report():
    session = Session()
    try:
        # Отримання даних про активність користувачів за останні 30 днів
        start_date = datetime.now() - timedelta(days=30)
        
        # SQL-запит для отримання кількості пройдених тестів за кожен день
        query = text("""
            SELECT DATE(date) as date, COUNT(*) as count
            FROM daily_tests
            WHERE date >= :start_date AND is_completed = TRUE
            GROUP BY DATE(date)
            ORDER BY date
        """)
        
        result = session.execute(query, {"start_date": start_date})
        dates = []
        counts = []
        
        for row in result:
            dates.append(row.date)
            counts.append(row.count)
        
        # Створення графіка
        plt.figure(figsize=(10, 6))
        plt.bar(dates, counts)
        plt.xlabel('Дата')
        plt.ylabel('Кількість пройдених тестів')
        plt.title('Активність користувачів за останні 30 днів')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Збереження графіка в байтовий потік
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png')
        img_bytes.seek(0)
        plt.close()
        
        return send_file(img_bytes, mimetype='image/png')
    finally:
        session.close()


@app.route('/reports/user_performance')
@login_required
def user_performance_report():
    session = Session()
    try:
        # Отримання даних про успішність користувачів
        query = text("""
            SELECT u.first_name || ' ' || u.last_name as name, 
                   COUNT(tr.id) as total_answers,
                   SUM(CASE WHEN tr.is_correct THEN 1 ELSE 0 END) as correct_answers
            FROM users u
            JOIN test_results tr ON u.id = tr.user_id
            GROUP BY u.id, u.first_name, u.last_name
            ORDER BY correct_answers DESC
            LIMIT 10
        """)
        
        result = session.execute(query)
        names = []
        accuracy = []
        
        for row in result:
            names.append(row.name)
            accuracy.append(row.correct_answers / row.total_answers * 100 if row.total_answers > 0 else 0)
        
        # Створення графіка
        plt.figure(figsize=(10, 6))
        plt.barh(names, accuracy)
        plt.xlabel('Точність відповідей (%)')
        plt.ylabel('Користувач')
        plt.title('Топ-10 користувачів за точністю відповідей')
        plt.tight_layout()
        
        # Збереження графіка в байтовий потік
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png')
        img_bytes.seek(0)
        plt.close()
        
        return send_file(img_bytes, mimetype='image/png')
    finally:
        session.close()


@app.route('/reports/category_difficulty')
@login_required
def category_difficulty_report():
    session = Session()
    try:
        # Отримання даних про складність категорій
        query = text("""
            SELECT c.name as category, 
                   COUNT(tr.id) as total_answers,
                   SUM(CASE WHEN tr.is_correct THEN 1 ELSE 0 END) as correct_answers
            FROM categories c
            JOIN questions q ON c.id = q.category_id
            JOIN test_results tr ON q.id = tr.question_id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        
        result = session.execute(query)
        categories = []
        difficulty = []
        
        for row in result:
            categories.append(row.category)
            # Складність = 100% - точність
            difficulty.append(100 - (row.correct_answers / row.total_answers * 100 if row.total_answers > 0 else 0))
        
        # Створення графіка
        plt.figure(figsize=(10, 6))
        plt.bar(categories, difficulty)
        plt.xlabel('Категорія')
        plt.ylabel('Складність (%)')
        plt.title('Складність категорій питань')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Збереження графіка в байтовий потік
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png')
        img_bytes.seek(0)
        plt.close()
        
        return send_file(img_bytes, mimetype='image/png')
    finally:
        session.close()


@app.route('/export/users')
@login_required
def export_users():
    session = Session()
    try:
        # Отримання даних користувачів
        users_data = session.query(User).all()
        
        # Створення DataFrame
        data = {
            'ID': [user.id for user in users_data],
            'Ім\'я': [user.first_name for user in users_data],
            'Прізвище': [user.last_name for user in users_data],
            'Місто': [user.city for user in users_data],
            'Посада': [user.position for user in users_data],
            'Telegram ID': [user.telegram_id for user in users_data],
            'Загальний рахунок': [user.total_score for user in users_data],
            'Дата реєстрації': [user.registration_date for user in users_data],
            'Остання активність': [user.last_activity for user in users_data]
        }
        
        df = pd.DataFrame(data)
        
        # Збереження в Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Користувачі', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    finally:
        session.close()


@app.route('/export/results')
@login_required
def export_results():
    session = Session()
    try:
        # Отримання результатів тестів
        query = text("""
            SELECT u.first_name || ' ' || u.last_name as user_name,
                   c.name as category,
                   q.text as question,
                   tr.is_correct,
                   tr.answered_at as created_at
            FROM test_results tr
            JOIN users u ON tr.user_id = u.id
            JOIN questions q ON tr.question_id = q.id
            JOIN categories c ON q.category_id = c.id
            ORDER BY tr.answered_at DESC
        """)
        
        result = session.execute(query)
        
        # Створення DataFrame
        data = {
            'Користувач': [],
            'Категорія': [],
            'Питання': [],
            'Правильна відповідь': [],
            'Дата': []
        }
        
        for row in result:
            data['Користувач'].append(row.user_name)
            data['Категорія'].append(row.category)
            data['Питання'].append(row.question)
            data['Правильна відповідь'].append('Так' if row.is_correct else 'Ні')
            data['Дата'].append(row.created_at)
            
        # Створення Excel-файлу
        df = pd.DataFrame(data)
        
        # Збереження в Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Результати тестів', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    finally:
        session.close()


@app.route('/reports/test_statistics')
@login_required
def test_statistics_report():
    session = Session()
    try:
        category_id = request.args.get('category_id')
        period = request.args.get('period', 'month')
        
        # Визначення періоду
        today = datetime.now()
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)  # За замовчуванням - місяць
        
        # Базовий запит
        query_base = """
            FROM test_results tr
            JOIN questions q ON tr.question_id = q.id
            JOIN categories c ON q.category_id = c.id
            WHERE tr.answered_at >= :start_date
        """
        
        # Додавання фільтра за категорією, якщо вказано
        if category_id and category_id.isdigit() and int(category_id) > 0:
            query_base += " AND c.id = :category_id"
            params = {"start_date": start_date, "category_id": int(category_id)}
        else:
            params = {"start_date": start_date}
        
        # Запит для загальної статистики
        query_total = text(f"""
            SELECT COUNT(*) as total_tests,
                   SUM(CASE WHEN tr.is_correct THEN 1 ELSE 0 END) as correct_answers
            {query_base}
        """)
        
        # Запит для статистики за категоріями
        query_categories = text(f"""
            SELECT c.name as category_name,
                   COUNT(*) as total_tests,
                   SUM(CASE WHEN tr.is_correct THEN 1 ELSE 0 END) as correct_answers
            {query_base}
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        
        # Виконання запитів
        result_total = session.execute(query_total, params).fetchone()
        result_categories = session.execute(query_categories, params).fetchall()
        
        # Підготовка даних для шаблону
        total_tests = result_total.total_tests if result_total.total_tests else 0
        correct_answers = result_total.correct_answers if result_total.correct_answers else 0
        incorrect_answers = total_tests - correct_answers
        
        # Розрахунок відсотків
        average_score = round((correct_answers / total_tests) * 100, 2) if total_tests > 0 else 0
        correct_percentage = round((correct_answers / total_tests) * 100, 2) if total_tests > 0 else 0
        incorrect_percentage = round((incorrect_answers / total_tests) * 100, 2) if total_tests > 0 else 0
        
        # Розподіл за складністю (умовно)
        difficulty = {
            "easy": round(total_tests * 0.3),  # 30% легкі
            "medium": round(total_tests * 0.5),  # 50% середні
            "hard": round(total_tests * 0.2)  # 20% складні
        }
        
        # Підготовка даних за категоріями
        categories_data = []
        for row in result_categories:
            cat_total = row.total_tests if row.total_tests else 0
            cat_correct = row.correct_answers if row.correct_answers else 0
            cat_incorrect = cat_total - cat_correct
            
            categories_data.append({
                "name": row.category_name,
                "total_tests": cat_total,
                "average_score": round((cat_correct / cat_total) * 100, 2) if cat_total > 0 else 0,
                "correct_answers": cat_correct,
                "incorrect_answers": cat_incorrect,
                "correct_percentage": round((cat_correct / cat_total) * 100, 2) if cat_total > 0 else 0,
                "incorrect_percentage": round((cat_incorrect / cat_total) * 100, 2) if cat_total > 0 else 0
            })
        
        # Формування даних для шаблону
        report_data = {
            "total_tests": total_tests,
            "average_score": average_score,
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "correct_percentage": correct_percentage,
            "incorrect_percentage": incorrect_percentage,
            "difficulty": difficulty,
            "categories": categories_data
        }
        
        # Отримання всіх категорій для фільтра
        all_categories = session.query(Category).all()
        
        return render_template('reports.html', 
                               report_data=report_data, 
                               report_type='test_statistics', 
                               report_title='Статистика тестування', 
                               all_categories=all_categories)
    finally:
        session.close()


@app.route('/reports/popular_questions')
@login_required
def popular_questions_report():
    session = Session()
    try:
        limit = request.args.get('limit', '10')
        sort = request.args.get('sort', 'views')
        
        # Перевірка параметрів
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        
        if sort not in ['views', 'correct', 'incorrect']:
            sort = 'views'
        
        # Формування запиту в залежності від сортування
        if sort == 'views':
            order_by = "views DESC"
        elif sort == 'correct':
            order_by = "correct_answers DESC"
        else:  # incorrect
            order_by = "incorrect_answers DESC"
        
        # Запит для отримання популярних питань
        query = text(f"""
            SELECT q.id, q.text, c.name as category,
                   COUNT(tr.id) as views,
                   SUM(CASE WHEN tr.is_correct THEN 1 ELSE 0 END) as correct_answers,
                   SUM(CASE WHEN NOT tr.is_correct THEN 1 ELSE 0 END) as incorrect_answers
            FROM questions q
            JOIN test_results tr ON q.id = tr.question_id
            JOIN categories c ON q.category_id = c.id
            GROUP BY q.id, q.text, c.name
            ORDER BY {order_by}
            LIMIT :limit
        """)
        
        result = session.execute(query, {"limit": limit})
        
        # Підготовка даних для шаблону
        questions_data = []
        chart_labels = []
        chart_data = []
        
        for row in result:
            total_answers = row.correct_answers + row.incorrect_answers
            correct_percentage = round((row.correct_answers / total_answers) * 100, 2) if total_answers > 0 else 0
            incorrect_percentage = round((row.incorrect_answers / total_answers) * 100, 2) if total_answers > 0 else 0
            
            # Розрахунок складності (100% - відсоток правильних відповідей)
            difficulty = round(100 - correct_percentage, 2)
            
            question_data = {
                "text": row.text,
                "category": row.category,
                "views": row.views,
                "correct_answers": row.correct_answers,
                "incorrect_answers": row.incorrect_answers,
                "correct_percentage": correct_percentage,
                "incorrect_percentage": incorrect_percentage,
                "difficulty": difficulty
            }
            
            questions_data.append(question_data)
            
            # Дані для графіка
            chart_labels.append(row.text[:30] + '...' if len(row.text) > 30 else row.text)
            if sort == 'views':
                chart_data.append(row.views)
            elif sort == 'correct':
                chart_data.append(row.correct_answers)
            else:  # incorrect
                chart_data.append(row.incorrect_answers)
        
        # Визначення підпису для графіка
        if sort == 'views':
            chart_label = 'Кількість переглядів'
        elif sort == 'correct':
            chart_label = 'Правильні відповіді'
        else:  # incorrect
            chart_label = 'Неправильні відповіді'
        
        # Формування даних для шаблону
        report_data = {
            "questions": questions_data,
            "chart_data": {
                "labels": chart_labels,
                "data": chart_data,
                "label": chart_label
            }
        }
        
        # Отримання всіх категорій для фільтра
        all_categories = session.query(Category).all()
        
        return render_template('reports.html', 
                               report_data=report_data, 
                               report_type='popular_questions', 
                               report_title='Популярні питання', 
                               all_categories=all_categories)
    finally:
        session.close()


@app.route('/reports/feedback_analysis')
@login_required
def feedback_analysis_report():
    session = Session()
    try:
        period = request.args.get('period', 'month')
        
        # Визначення періоду
        today = datetime.now()
        if period == 'week':
            start_date = today - timedelta(days=7)
            period_label = 'за тиждень'
        elif period == 'month':
            start_date = today - timedelta(days=30)
            period_label = 'за місяць'
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
            period_label = 'за квартал'
        elif period == 'year':
            start_date = today - timedelta(days=365)
            period_label = 'за рік'
        else:
            start_date = today - timedelta(days=30)
            period_label = 'за місяць'
        
        # Запит для отримання зворотного зв'язку за період
        feedback_list = session.query(Feedback).filter(Feedback.created_at >= start_date).order_by(Feedback.created_at.desc()).all()
        
        # Підготовка даних для шаблону
        total_feedback = len(feedback_list)
        read_feedback = sum(1 for f in feedback_list if f.is_read)
        unread_feedback = total_feedback - read_feedback
        
        # Розрахунок відсотків
        read_percentage = round((read_feedback / total_feedback) * 100, 2) if total_feedback > 0 else 0
        unread_percentage = round((unread_feedback / total_feedback) * 100, 2) if total_feedback > 0 else 0
        
        # Унікальні користувачі
        unique_users = len(set(f.user_id for f in feedback_list if f.user_id))
     
        # Розподіл за категоріями зворотного зв'язку
        feedback_categories = {
            'Технічні питання': 0,
            'Питання про контент': 0,
            'Пропозиції': 0,
            'Подяки': 0,
            'Інше': 0
        }
        
        # Підрахунок кількості відгуків за категоріями
        for f in feedback_list:
            category = f.feedback_type
            if category in feedback_categories:
                feedback_categories[category] += 1
            else:
                feedback_categories['Інше'] += 1
        
        # Формування даних для графіка
        topics = {
            "labels": list(feedback_categories.keys()),
            "data": list(feedback_categories.values())
        }
        
        # Динаміка зворотного зв'язку (реальні дати, але порожні дані)
        timeline_labels = [(today - timedelta(days=i)).strftime('%d.%m') for i in range(10, -1, -1)]
        timeline_data = [0] * len(timeline_labels)  # Ініціалізуємо нулями
        
        # Заповнюємо дані на основі реальних відгуків
        feedback_by_date = {}
        for f in feedback_list:
            date_str = f.created_at.strftime('%d.%m')
            if date_str in timeline_labels:
                index = timeline_labels.index(date_str)
                timeline_data[index] += 1
        
        timeline = {
            "labels": timeline_labels,
            "data": timeline_data
        }
        
        # Ключові слова (порожній список, буде заповнений реальними даними в майбутньому)
        keywords = []
        
        # Підготовка останніх відгуків для відображення
        recent_feedback = []
        for f in feedback_list[:10]:  # Обмеження до 10 останніх
            user = session.query(User).filter(User.id == f.user_id).first() if f.user_id else None
            user_name = f"{user.first_name} {user.last_name}" if user else "Невідомий"
            
            recent_feedback.append({
                "date": f.created_at.strftime('%d.%m.%Y %H:%M'),
                "user": user_name,
                "subject": f.feedback_type,
                "message": f.text[:100] + '...' if len(f.text) > 100 else f.text,
                "is_read": f.is_read
            })
        
        # Формування даних для шаблону
        report_data = {
            "period_start": start_date.strftime('%d.%m.%Y'),
            "period_end": today.strftime('%d.%m.%Y'),
            "total_feedback": total_feedback,
            "read_feedback": read_feedback,
            "unread_feedback": unread_feedback,
            "read_percentage": read_percentage,
            "unread_percentage": unread_percentage,
            "unique_users": unique_users,
            "topics": topics,
            "timeline": timeline,
            "keywords": keywords,
            "recent_feedback": recent_feedback
        }
        
        # Отримання всіх категорій для фільтра
        all_categories = session.query(Category).all()
        
        return render_template('reports.html', 
                               report_data=report_data, 
                               report_type='feedback_analysis', 
                               report_title=f'Аналіз зворотного зв\'язку {period_label}', 
                               all_categories=all_categories)
    finally:
        session.close()


# Маршрути для управління посадами
@app.route('/positions')
@login_required
def positions():
    session = Session()
    try:
        positions_list = session.query(Position).all()
        return render_template('positions.html', positions=positions_list)
    finally:
        session.close()


@app.route('/position/add', methods=['GET', 'POST'])
@login_required
def add_position():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Назва посади обов\'язкова', 'danger')
            return redirect(url_for('add_position'))
        
        session = Session()
        try:
            position = Position(name=name, description=description)
            session.add(position)
            session.commit()
            flash('Посаду успішно додано', 'success')
            return redirect(url_for('positions'))
        except Exception as e:
            session.rollback()
            flash(f'Помилка при додаванні посади: {str(e)}', 'danger')
        finally:
            session.close()
    
    return render_template('add_position.html')


@app.route('/position/edit/<int:position_id>', methods=['GET', 'POST'])
@login_required
def edit_position(position_id):
    session = Session()
    try:
        position = session.query(Position).filter(Position.id == position_id).first()
        if not position:
            flash('Посаду не знайдено', 'danger')
            return redirect(url_for('positions'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash('Назва посади обов\'язкова', 'danger')
                return redirect(url_for('edit_position', position_id=position_id))
            
            position.name = name
            position.description = description
            
            try:
                session.commit()
                flash('Посаду успішно оновлено', 'success')
                return redirect(url_for('positions'))
            except Exception as e:
                session.rollback()
                flash(f'Помилка при оновленні посади: {str(e)}', 'danger')
        
        return render_template('edit_position.html', position=position)
    finally:
        session.close()


@app.route('/position/delete/<int:position_id>', methods=['POST'])
@login_required
def delete_position(position_id):
    session = Session()
    try:
        position = session.query(Position).filter(Position.id == position_id).first()
        if not position:
            flash('Посаду не знайдено', 'danger')
            return redirect(url_for('positions'))
        
        # Перевірка, чи є користувачі з цією посадою
        users_count = session.query(User).filter(User.position == position.name).count()
        if users_count > 0:
            flash(f'Неможливо видалити посаду, оскільки її використовують {users_count} користувачів', 'danger')
            return redirect(url_for('positions'))
        
        # Перевірка, чи є питання, що вимагають цю посаду
        questions_count = session.query(Question).filter(Question.position_required == position.name).count()
        if questions_count > 0:
            flash(f'Неможливо видалити посаду, оскільки її вимагають {questions_count} питань', 'danger')
            return redirect(url_for('positions'))
        
        session.delete(position)
        session.commit()
        flash('Посаду успішно видалено', 'success')
    except Exception as e:
        session.rollback()
        flash(f'Помилка при видаленні посади: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('positions'))


if __name__ == '__main__':
    # Створення директорії для шаблонів
    os.makedirs('templates', exist_ok=True)
    
    # Ініціалізація бази даних
    from handlers import init_database
    init_database()
    
    # Запуск Flask додатку
    app.run(debug=True, host='0.0.0.0', port=5000)