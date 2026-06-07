# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import time
from werkzeug.utils import secure_filename
from flask import flash
from datetime import datetime
from flask_mail import Mail, Message
from datetime import timezone, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

# ===== НАСТРОЙКА БАЗЫ ДАННЫХ =====
import urllib.parse
import os

# Определяем, где запущено приложение
if os.environ.get('DB_HOST') or os.environ.get('MYSQL_HOST'):
    # Настройки для Timeweb (встроенная БД)
    MYSQL_HOST = os.environ.get('DB_HOST', os.environ.get('MYSQL_HOST', 'localhost'))
    MYSQL_USER = os.environ.get('DB_USER', os.environ.get('MYSQL_USER', 'root'))
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', os.environ.get('MYSQL_PASSWORD', ''))
    MYSQL_DB = os.environ.get('DB_NAME', os.environ.get('MYSQL_DB', 'app_db'))
    
    password_encoded = urllib.parse.quote_plus(MYSQL_PASSWORD)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{password_encoded}@{MYSQL_HOST}/{MYSQL_DB}?charset=utf8mb4'
    print(f"✅ Подключение к MySQL: {MYSQL_HOST}/{MYSQL_DB}")
else:
    # Локальная разработка — SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "shop.db")}'
    print("✅ Подключение к SQLite")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ===== НАСТРОЙКИ EMAIL =====
app.config['MAIL_SERVER'] = 'smtp.timeweb.ru'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'zakaz@autoinomarki76.ru'
app.config['MAIL_PASSWORD'] = 'XbW@i5Wa>upt1A'
app.config['MAIL_DEFAULT_SENDER'] = 'zakaz@autoinomarki76.ru'

app.config['MAIL_TIMEOUT'] = 30
app.config['MAIL_MAX_EMAILS'] = None

mail = Mail(app)

db = SQLAlchemy(app)

# ===== МОДЕЛИ БАЗЫ ДАННЫХ =====
class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), nullable=False)
    car_info = db.Column(db.String(200), nullable=False)
    parts_needed = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class HitProduct(db.Model):
    __tablename__ = 'hit_products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price_old = db.Column(db.String(50), nullable=False)
    discount = db.Column(db.String(10), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)
    sort_order = db.Column(db.Integer, default=0)

class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

# ===== АДМИН-ДАННЫЕ =====
ADMIN_USERNAME = 'autoinomarki'
ADMIN_PASSWORD = '030189'

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_setting(key, default=''):
    setting = SiteSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

def set_setting(key, value):
    setting = SiteSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = SiteSetting(key=key, value=value)
        db.session.add(setting)
    db.session.commit()

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== МАРШРУТЫ =====
@app.route('/')
def index():
    hit_products = HitProduct.query.order_by(HitProduct.sort_order).all()
    
    shop_title = get_setting('shop_title', 'Магазин автозапчастей в Ярославле')
    shop_subtitle = get_setting('shop_subtitle', 'Продаем запчасти с 2007 года. Более 30 000 позиций в наличии на складе')
    logo_filename = get_setting('logo_filename', '')
    logo_width = get_setting('logo_width', '150')
    logo_alignment = get_setting('logo_alignment', 'center')    
    phone_number = get_setting('phone_number', '+7 (4852) 28-24-28')
    phone_icon_filename = get_setting('phone_icon_filename', '')
    phone_icon_width = get_setting('phone_icon_width', '24')
    shop_address = get_setting('shop_address', 'г. Ярославль, Ленинградский проспект 47')
    work_hours = get_setting('work_hours', 'ПН–ПТ 10:00–18:30 | Сб 10:00–15:00')
    show_map = get_setting('show_map', 'yes')
    show_hit_block = get_setting('show_hit_block', 'yes')
    hit_block_title = get_setting('hit_block_title', 'ХИТ продаж')
    show_hit_fire = get_setting('show_hit_fire', 'yes')
    form_title = get_setting('form_title', 'Задайте вопрос - менеджер свяжется с Вами')
    
    return render_template('index.html', 
                         hit_products=hit_products,
                         hit_block_title=hit_block_title,
                         shop_title=shop_title, 
                         shop_subtitle=shop_subtitle, 
                         logo_filename=logo_filename, 
                         logo_width=logo_width,
                         logo_alignment=logo_alignment,
                         phone_number=phone_number,
                         phone_icon_filename=phone_icon_filename,
                         phone_icon_width=phone_icon_width,
                         shop_address=shop_address,
                         work_hours=work_hours,
                         show_map=show_map,
                         show_hit_fire=show_hit_fire,
                         show_hit_block=show_hit_block,
                         form_title=form_title)

@app.route('/request', methods=['POST'])
def add_request():
    phone = request.form['phone']
    car_info = request.form['car_info']
    parts_needed = request.form['parts_needed']
    new_request = Request(phone=phone, car_info=car_info, parts_needed=parts_needed)
    db.session.add(new_request)
    db.session.commit()
    
    if get_setting('send_email_notifications', 'yes') == 'yes':
        manager_email = get_setting('manager_email', '')
        if manager_email:
            try:
                recipients = [manager_email]
                extra_email = get_setting('manager_email_extra', '')
                if extra_email:
                    recipients.append(extra_email)
                
                msg = Message(
                    subject='🔔 Новая заявка с сайта',
                    recipients=recipients
                )
                
                msg.body = f'''
Новая заявка от клиента!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 Телефон: {phone}
🚗 Марка авто / VIN: {car_info}
📋 Нужные запчасти: {parts_needed}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Московское время (UTC+3)
moscow_tz = timezone(timedelta(hours=3))
moscow_time = datetime.now(moscow_tz)
Время заявки: {moscow_time.strftime('%d.%m.%Y %H:%M')}
                
                try:
                    mail.send(msg)
                    print(f"✅ Email отправлен на {recipients}")
                except Exception as mail_error:
                    print(f"❌ Ошибка при отправке email: {mail_error}")
                    # Не прерываем выполнение, просто логируем ошибку
            except Exception as e:
                print(f"Ошибка отправки email: {e}")
    
    flash('Спасибо, мы свяжемся с Вами!', 'success')
    return redirect(url_for('index'))

# ===== АДМИН-ПАНЕЛЬ =====
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin/login.html', error='Неверный логин или пароль')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@admin_required
def admin_dashboard():
    hit_count = HitProduct.query.count()
    requests_count = Request.query.count()
    return render_template('admin/dashboard.html', hit_count=hit_count, requests_count=requests_count)

# ===== ОБРАБОТКА ЗАЯВОК =====
@app.route('/admin/request/delete/<int:id>')
@admin_required
def delete_request(id):
    request_to_delete = Request.query.get_or_404(id)
    db.session.delete(request_to_delete)
    db.session.commit()
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/delete-all')
@admin_required
def delete_all_requests():
    confirm = request.args.get('confirm', 'no')
    if confirm == 'yes':
        Request.query.delete()
        db.session.commit()
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests')
@admin_required
def admin_requests():
    requests_list = Request.query.all()
    return render_template('admin/requests.html', requests=requests_list)

# ===== УПРАВЛЕНИЕ ТОВАРАМИ =====
@app.route('/admin/hit-products')
@admin_required
def admin_hit_products():
    hit_products = HitProduct.query.order_by(HitProduct.sort_order).all()
    return render_template('admin/hit_products.html', hit_products=hit_products)

@app.route('/admin/hit-product/add', methods=['GET', 'POST'])
@admin_required
def add_hit_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price_old = request.form.get('price_old')
        discount = request.form.get('discount')
        sort_order = request.form.get('sort_order', 0)
        
        image_filename = None
        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            if '.' in image_file.filename:
                ext = image_file.filename.rsplit('.', 1)[1].lower()
            else:
                ext = 'png'
            new_filename = f"hit_{int(time.time())}.{ext}"
            image_file.save(os.path.join('static', new_filename))
            image_filename = new_filename
        
        hit_product = HitProduct(
            name=name,
            price_old=price_old,
            discount=discount,
            image_filename=image_filename,
            sort_order=int(sort_order)
        )
        db.session.add(hit_product)
        db.session.commit()
        return redirect(url_for('admin_hit_products'))
    
    return render_template('admin/hit_product_form.html', product=None)

@app.route('/admin/hit-product/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_hit_product(id):
    product = HitProduct.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price_old = request.form.get('price_old')
        product.discount = request.form.get('discount')
        product.sort_order = int(request.form.get('sort_order', 0))
        
        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            if product.image_filename:
                old_path = os.path.join('static', product.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            if '.' in image_file.filename:
                ext = image_file.filename.rsplit('.', 1)[1].lower()
            else:
                ext = 'png'
            new_filename = f"hit_{int(time.time())}.{ext}"
            image_file.save(os.path.join('static', new_filename))
            product.image_filename = new_filename
        
        db.session.commit()
        return redirect(url_for('admin_hit_products'))
    
    return render_template('admin/hit_product_form.html', product=product)

@app.route('/admin/hit-product/delete/<int:id>')
@admin_required
def delete_hit_product(id):
    product = HitProduct.query.get_or_404(id)
    if product.image_filename:
        old_path = os.path.join('static', product.image_filename)
        if os.path.exists(old_path):
            os.remove(old_path)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_hit_products'))

# ===== НАСТРОЙКИ =====
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    UPLOAD_FOLDER = 'static'
    
    saved = False
    
    if request.method == 'POST':
        set_setting('shop_title', request.form.get('shop_title', ''))
        set_setting('shop_subtitle', request.form.get('shop_subtitle', ''))
        set_setting('phone_number', request.form.get('phone_number', ''))
        set_setting('show_hit_block', request.form.get('show_hit_block', 'no'))
        set_setting('hit_block_title', request.form.get('hit_block_title', 'ХИТ продаж'))
        set_setting('show_hit_fire', request.form.get('show_hit_fire', 'yes'))
        set_setting('shop_address', request.form.get('shop_address', ''))
        set_setting('work_hours', request.form.get('work_hours', ''))
        set_setting('show_map', request.form.get('show_map', 'no'))
        
        logo_width = request.form.get('logo_width', '150')
        set_setting('logo_width', logo_width)
        
        phone_icon_width = request.form.get('phone_icon_width', '24')
        set_setting('phone_icon_width', phone_icon_width)
        
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename and allowed_file(logo_file.filename):
            old_logo = get_setting('logo_filename', '')
            if old_logo:
                old_path = os.path.join(UPLOAD_FOLDER, old_logo)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            if '.' in logo_file.filename:
                ext = logo_file.filename.rsplit('.', 1)[1].lower()
            else:
                ext = 'png'
            new_filename = f"logo_{int(time.time())}.{ext}"
            logo_file.save(os.path.join(UPLOAD_FOLDER, new_filename))
            set_setting('logo_filename', new_filename)
        
        phone_icon_file = request.files.get('phone_icon')
        if phone_icon_file and phone_icon_file.filename and allowed_file(phone_icon_file.filename):
            old_icon = get_setting('phone_icon_filename', '')
            if old_icon:
                old_path = os.path.join(UPLOAD_FOLDER, old_icon)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            if '.' in phone_icon_file.filename:
                ext = phone_icon_file.filename.rsplit('.', 1)[1].lower()
            else:
                ext = 'png'
            new_filename = f"phone_icon_{int(time.time())}.{ext}"
            phone_icon_file.save(os.path.join(UPLOAD_FOLDER, new_filename))
            set_setting('phone_icon_filename', new_filename)
        
        if request.form.get('delete_phone_icon') == 'yes':
            old_icon = get_setting('phone_icon_filename', '')
            if old_icon:
                old_path = os.path.join(UPLOAD_FOLDER, old_icon)
                if os.path.exists(old_path):
                    os.remove(old_path)
                set_setting('phone_icon_filename', '')
        
        set_setting('logo_alignment', request.form.get('logo_alignment', 'center'))

        if request.form.get('delete_logo') == 'yes':
            old_logo = get_setting('logo_filename', '')
            if old_logo:
                old_path = os.path.join(UPLOAD_FOLDER, old_logo)
                if os.path.exists(old_path):
                    os.remove(old_path)
                set_setting('logo_filename', '')

        set_setting('form_title', request.form.get('form_title', 'Задайте вопрос - менеджер свяжется с Вами'))
        set_setting('manager_email', request.form.get('manager_email', ''))
        set_setting('manager_email_extra', request.form.get('manager_email_extra', ''))
        set_setting('send_email_notifications', request.form.get('send_email_notifications', 'yes'))
        
        saved = True
        
    shop_title = get_setting('shop_title', 'Магазин автозапчастей в Ярославле')
    shop_subtitle = get_setting('shop_subtitle', 'Продаем запчасти с 2007 года. Более 30 000 позиций в наличии на складе')
    logo_filename = get_setting('logo_filename', '')
    logo_width = get_setting('logo_width', '150')
    phone_number = get_setting('phone_number', '+7 (4852) 28-24-28')
    phone_icon_filename = get_setting('phone_icon_filename', '')
    phone_icon_width = get_setting('phone_icon_width', '24')
    shop_address = get_setting('shop_address', 'г. Ярославль, Ленинградский проспект 47')
    work_hours = get_setting('work_hours', 'ПН–ПТ 10:00–18:30 | Сб 10:00–15:00')
    show_map = get_setting('show_map', 'yes')
    show_hit_block = get_setting('show_hit_block', 'yes')
    hit_block_title = get_setting('hit_block_title', 'ХИТ продаж')
    show_hit_fire = get_setting('show_hit_fire', 'yes')
    logo_alignment = get_setting('logo_alignment', 'center')
    form_title = get_setting('form_title', 'Задайте вопрос - менеджер свяжется с Вами')
    manager_email = get_setting('manager_email', '')
    manager_email_extra = get_setting('manager_email_extra', '')
    send_email_notifications = get_setting('send_email_notifications', 'yes')

    return render_template('admin/settings.html', 
                         shop_title=shop_title, 
                         shop_subtitle=shop_subtitle,
                         logo_filename=logo_filename,
                         logo_width=logo_width,
                         phone_number=phone_number,
                         phone_icon_filename=phone_icon_filename,
                         phone_icon_width=phone_icon_width,
                         shop_address=shop_address,
                         work_hours=work_hours,
                         show_map=show_map,
                         show_hit_block=show_hit_block,
                         hit_block_title=hit_block_title,
                         logo_alignment=logo_alignment,
                         show_hit_fire=show_hit_fire,
                         form_title=form_title,
                         manager_email=manager_email,
                         manager_email_extra=manager_email_extra,
                         send_email_notifications=send_email_notifications,
                         saved=saved)

# ===== AJAX-ЗАГРУЗКА РАЗДЕЛОВ АДМИНКИ =====
@app.route('/admin/ajax/hit-products')
@admin_required
def ajax_hit_products():
    hit_products = HitProduct.query.order_by(HitProduct.sort_order).all()
    return render_template('admin/ajax_hit_products.html', hit_products=hit_products)

@app.route('/admin/ajax/requests')
@admin_required
def ajax_requests():
    requests_list = Request.query.all()
    return render_template('admin/ajax_requests.html', requests=requests_list)

@app.route('/admin/ajax/settings')
@admin_required
def ajax_settings():
    shop_title = get_setting('shop_title', 'Магазин автозапчастей в Ярославле')
    shop_subtitle = get_setting('shop_subtitle', 'Продаем запчасти с 2007 года. Более 30 000 позиций в наличии на складе')
    logo_filename = get_setting('logo_filename', '')
    logo_width = get_setting('logo_width', '150')
    logo_alignment = get_setting('logo_alignment', 'center')
    phone_number = get_setting('phone_number', '+7 (4852) 28-24-28')
    phone_icon_filename = get_setting('phone_icon_filename', '')
    phone_icon_width = get_setting('phone_icon_width', '24')
    shop_address = get_setting('shop_address', 'г. Ярославль, Ленинградский проспект 47')
    work_hours = get_setting('work_hours', 'ПН–ПТ 10:00–18:30 | Сб 10:00–15:00')
    show_map = get_setting('show_map', 'yes')
    show_hit_block = get_setting('show_hit_block', 'yes')
    hit_block_title = get_setting('hit_block_title', 'ХИТ продаж')
    show_hit_fire = get_setting('show_hit_fire', 'yes')
    form_title = get_setting('form_title', 'Задайте вопрос - менеджер свяжется с Вами')
    manager_email = get_setting('manager_email', '')
    manager_email_extra = get_setting('manager_email_extra', '')
    send_email_notifications = get_setting('send_email_notifications', 'yes')
    
    return render_template('admin/ajax_settings.html', 
                         shop_title=shop_title, 
                         shop_subtitle=shop_subtitle,
                         logo_filename=logo_filename,
                         logo_width=logo_width,
                         logo_alignment=logo_alignment,
                         phone_number=phone_number,
                         phone_icon_filename=phone_icon_filename,
                         phone_icon_width=phone_icon_width,
                         shop_address=shop_address,
                         work_hours=work_hours,
                         show_map=show_map,
                         show_hit_block=show_hit_block,
                         hit_block_title=hit_block_title,
                         show_hit_fire=show_hit_fire,
                         form_title=form_title,
                         manager_email=manager_email,
                         manager_email_extra=manager_email_extra,
                         send_email_notifications=send_email_notifications)

@app.route('/admin/ajax/settings', methods=['POST'])
@admin_required
def ajax_settings_post():
    UPLOAD_FOLDER = 'static'
    
    set_setting('shop_title', request.form.get('shop_title', ''))
    set_setting('shop_subtitle', request.form.get('shop_subtitle', ''))
    set_setting('phone_number', request.form.get('phone_number', ''))
    set_setting('show_hit_block', request.form.get('show_hit_block', 'no'))
    set_setting('hit_block_title', request.form.get('hit_block_title', 'ХИТ продаж'))
    set_setting('show_hit_fire', request.form.get('show_hit_fire', 'yes'))
    set_setting('shop_address', request.form.get('shop_address', ''))
    set_setting('work_hours', request.form.get('work_hours', ''))
    set_setting('show_map', request.form.get('show_map', 'no'))
    
    logo_width = request.form.get('logo_width', '150')
    set_setting('logo_width', logo_width)
    
    phone_icon_width = request.form.get('phone_icon_width', '24')
    set_setting('phone_icon_width', phone_icon_width)
    
    set_setting('logo_alignment', request.form.get('logo_alignment', 'center'))
    set_setting('form_title', request.form.get('form_title', 'Задайте вопрос - менеджер свяжется с Вами'))
    set_setting('manager_email', request.form.get('manager_email', ''))
    set_setting('manager_email_extra', request.form.get('manager_email_extra', ''))
    set_setting('send_email_notifications', request.form.get('send_email_notifications', 'yes'))
    
    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename and allowed_file(logo_file.filename):
        old_logo = get_setting('logo_filename', '')
        if old_logo:
            old_path = os.path.join(UPLOAD_FOLDER, old_logo)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        if '.' in logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[1].lower()
        else:
            ext = 'png'
        new_filename = f"logo_{int(time.time())}.{ext}"
        logo_file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        set_setting('logo_filename', new_filename)
    
    phone_icon_file = request.files.get('phone_icon')
    if phone_icon_file and phone_icon_file.filename and allowed_file(phone_icon_file.filename):
        old_icon = get_setting('phone_icon_filename', '')
        if old_icon:
            old_path = os.path.join(UPLOAD_FOLDER, old_icon)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        if '.' in phone_icon_file.filename:
            ext = phone_icon_file.filename.rsplit('.', 1)[1].lower()
        else:
            ext = 'png'
        new_filename = f"phone_icon_{int(time.time())}.{ext}"
        phone_icon_file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        set_setting('phone_icon_filename', new_filename)
    
    if request.form.get('delete_phone_icon') == 'yes':
        old_icon = get_setting('phone_icon_filename', '')
        if old_icon:
            old_path = os.path.join(UPLOAD_FOLDER, old_icon)
            if os.path.exists(old_path):
                os.remove(old_path)
            set_setting('phone_icon_filename', '')
    
    if request.form.get('delete_logo') == 'yes':
        old_logo = get_setting('logo_filename', '')
        if old_logo:
            old_path = os.path.join(UPLOAD_FOLDER, old_logo)
            if os.path.exists(old_path):
                os.remove(old_path)
            set_setting('logo_filename', '')
    
    return jsonify(success=True)

# Создаём таблицы при запуске (для Gunicorn на сервере)
with app.app_context():
    try:
        db.create_all()
        print("✅ Таблицы базы данных созданы/проверены")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")

if __name__ == '__main__':
    app.run(debug=True)
