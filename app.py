from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from utils.database import db, UserInfo, HouseInfo, HouseRecommend, HouseAppointment, UserBehavior, HouseReview, HouseImage
from utils.recommender import HouseRecommender
from utils.admin_utils import admin_required
import json
from datetime import datetime, timedelta
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect


UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 在 app.py 文件开头附近添加北京区域映射
BEIJING_DISTRICTS = {
    '北京市': ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '石景山区', '通州区', '昌平区',
               '大兴区', '顺义区', '房山区', '门头沟区', '怀柔区', '密云区', '延庆区', '平谷区'],
    '北京': ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '石景山区', '通州区', '昌平区',
             '大兴区', '顺义区', '房山区', '门头沟区', '怀柔区', '密云区', '延庆区', '平谷区']
}

# 初始化扩展
db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面'

# 初始化推荐系统
recommender = HouseRecommender()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def record_user_behavior(behavior_type, target_type=None):
    """记录用户行为的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 执行原函数
            result = f(*args, **kwargs)

            # 记录用户行为
            if current_user.is_authenticated:
                behavior = UserBehavior(
                    user_id=current_user.id,
                    behavior_type=behavior_type,
                    target_type=target_type,
                    ip_address=request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
                    user_agent=request.headers.get('User-Agent', '')
                )

                # 根据行为类型设置额外信息
                if behavior_type == 'view' and 'house_id' in kwargs:
                    behavior.target_id = kwargs['house_id']
                elif behavior_type == 'search':
                    behavior.extra_data = request.args.get('keyword', '')  # 修改为 extra_data

                db.session.add(behavior)
                db.session.commit()

            return result
        return decorated_function
    return decorator


@login_manager.user_loader
def load_user(user_id):
    return UserInfo.query.get(int(user_id))


@app.before_request
def setup_recommender():
    """在第一个请求前初始化推荐系统"""
    if not hasattr(app, 'first_request_done'):
        with app.app_context():
            houses = HouseInfo.query.all()
            recommender.train(houses)
        app.first_request_done = True


@app.context_processor
def inject_user():
    """向所有模板注入当前用户信息"""
    return dict(current_user=current_user)


@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """上传用户头像"""
    if 'avatar' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('profile'))

    file = request.files['avatar']

    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('profile'))

    if file and allowed_file(file.filename):
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        # 添加用户ID避免文件名冲突
        name, ext = os.path.splitext(filename)
        filename = f"user_{current_user.id}_avatar{ext}"

        # 确保上传目录存在
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars')
        os.makedirs(upload_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # 更新数据库中的头像路径（保存相对路径）
        current_user.avatar_url = f"static/img/avatars/{filename}"
        db.session.commit()

        flash('头像上传成功')
    else:
        flash('只允许上传 PNG, JPG, JPEG, GIF 格式的文件')

    return redirect(url_for('profile'))


# ========== 用户认证路由 ==========
def login_required_with_redirect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        addr = request.form.get('addr', '').strip()

        # 验证输入
        if not username or not email or not password:
            flash('请填写所有必填字段')
            return render_template('register.html')

        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('register.html')

        if len(password) < 6:
            flash('密码长度至少为6位')
            return render_template('register.html')

        # 检查用户是否已存在
        if UserInfo.query.filter_by(name=username).first():
            flash('用户名已存在')
            return render_template('register.html')

        if UserInfo.query.filter_by(email=email).first():
            flash('邮箱已被注册')
            return render_template('register.html')

        # 创建新用户
        new_user = UserInfo(
            name=username,
            email=email,
            addr=addr
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('注册成功，请登录')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = UserInfo.query.filter_by(name=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('用户名或密码错误')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功退出登录')
    return redirect(url_for('login'))  # 修改为跳转到登录页面


# 添加密码找回相关路由
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """忘记密码"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email:
            flash('请输入邮箱地址')
            return render_template('forgot_password.html')

        user = UserInfo.query.filter_by(email=email).first()

        if user:
            # 生成重置令牌
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # 发送重置邮件（这里只是模拟，实际项目中需要配置邮件服务器）
            try:
                # 模拟发送邮件
                reset_link = url_for('reset_password', token=reset_token, _external=True)
                # 在实际应用中，这里应该发送真实的邮件
                flash('密码重置链接已发送到您的邮箱，请查收')
            except Exception as e:
                flash('邮件发送失败，请稍后再试')
        else:
            # 为了安全，即使邮箱不存在也显示相同信息
            flash('密码重置链接已发送到您的邮箱，请查收')

        return render_template('forgot_password.html')

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """重置密码"""
    # 查找具有该令牌且未过期的用户
    user = UserInfo.query.filter(
        UserInfo.reset_token == token,
        UserInfo.reset_token_expires > datetime.utcnow()
    ).first()

    if not user:
        flash('密码重置链接无效或已过期')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not password or len(password) < 6:
            flash('密码长度至少为6位')
            return render_template('reset_password.html', token=token)

        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('reset_password.html', token=token)

        # 更新密码
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()

        flash('密码重置成功，请使用新密码登录')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 验证旧密码
        if not current_user.check_password(old_password):
            flash('当前密码错误')
            return render_template('change_password.html')

        # 验证新密码
        if len(new_password) < 6:
            flash('新密码长度至少为6位')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('两次输入的新密码不一致')
            return render_template('change_password.html')

        # 更新密码
        current_user.set_password(new_password)
        db.session.commit()
        flash('密码修改成功')
        return redirect(url_for('profile'))

    return render_template('change_password.html')


# 在 app.py 中修改 profile 路由
@app.route('/profile')
@login_required
def profile():
    """用户个人资料"""
    collected_ids = current_user.get_collected_houses()
    collected_houses = HouseInfo.query.filter(HouseInfo.id.in_(collected_ids)).all() if collected_ids else []

    seen_ids = current_user.get_seen_houses()[:10]  # 最近10个浏览记录
    seen_houses = HouseInfo.query.filter(HouseInfo.id.in_(seen_ids)).all() if seen_ids else []

    # 获取用户的预约记录，同时加载关联的房源信息
    appointments = db.session.query(HouseAppointment) \
        .join(HouseInfo, HouseAppointment.house_id == HouseInfo.id) \
        .filter(HouseAppointment.user_id == current_user.id) \
        .order_by(HouseAppointment.created_at.desc()) \
        .all()

    return render_template('profile.html',
                           collected_houses=collected_houses,
                           seen_houses=seen_houses,
                           appointments=appointments)


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """更新用户资料"""
    email = request.form.get('email', '').strip()
    addr = request.form.get('addr', '').strip()

    # 检查邮箱是否已被其他用户使用
    existing_user = UserInfo.query.filter(UserInfo.email == email, UserInfo.id != current_user.id).first()
    if existing_user:
        flash('邮箱已被其他用户使用')
        return redirect(url_for('profile'))

    current_user.email = email
    current_user.addr = addr

    db.session.commit()
    flash('个人资料更新成功')
    return redirect(url_for('profile'))


# ========== 房源相关路由 ==========
@app.route('/')
def index():
    """首页 - 显示热门房源和新上房源"""
    # 热门房源（浏览量高）
    popular_houses = HouseInfo.query.filter_by(is_available=True) \
        .order_by(HouseInfo.page_views.desc()) \
        .limit(8).all()

    # 最新房源
    new_houses = HouseInfo.query.filter_by(is_available=True) \
        .order_by(HouseInfo.publish_time.desc()) \
        .limit(8).all()

    return render_template('index.html',
                           popular_houses=popular_houses,
                           new_houses=new_houses)


@app.route('/search')
@record_user_behavior('search', 'house')
def search():
    # 获取搜索参数
    keyword = request.args.get('keyword', '').strip()
    region = request.args.get('region', '')
    rent_type = request.args.get('rent_type', '')
    rooms = request.args.get('rooms', '')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    sort = request.args.get('sort', 'default')

    # 构建查询基础
    query = HouseInfo.query.filter_by(is_available=True)

    # 处理区域搜索 - 添加北京特殊处理
    if region in BEIJING_DISTRICTS:
        # 如果选择的是北京市或北京，搜索所有北京下属区域
        regions_to_search = BEIJING_DISTRICTS[region]
        query = query.filter(HouseInfo.region.in_(regions_to_search))
    elif region:
        # 正常的单区域搜索
        query = query.filter(HouseInfo.region.like(f'%{region}%'))

    if rent_type:
        query = query.filter(HouseInfo.rent_type == rent_type)
    if rooms:
        query = query.filter(HouseInfo.rooms == rooms)
    if min_price:
        try:
            query = query.filter(HouseInfo.price >= int(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            query = query.filter(HouseInfo.price <= int(max_price))
        except ValueError:
            pass
    if keyword:
        query = query.filter(HouseInfo.title.contains(keyword))

    # 添加排序逻辑
    if sort == 'price_asc':
        query = query.order_by(HouseInfo.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(HouseInfo.price.desc())
    elif sort == 'views':
        query = query.order_by(HouseInfo.page_views.desc())
    else:
        query = query.order_by(HouseInfo.publish_time.desc())

    houses = query.limit(100).all()

    # 获取所有区域用于筛选
    regions = db.session.query(HouseInfo.region).distinct().all()
    regions = [r[0] for r in regions if r[0]]

    return render_template('search.html',
                           houses=houses,
                           keyword=keyword,
                           region=region,
                           rent_type=rent_type,
                           min_price=min_price,
                           max_price=max_price,
                           rooms=rooms,
                           regions=regions,
                           sort=sort)

@app.route('/detail/<int:house_id>')
@record_user_behavior('view', 'house')
def detail(house_id):
    """房源详情页"""
    house = HouseInfo.query.get_or_404(house_id)

    if not house.is_available:
        flash('该房源已下架')
        return redirect(url_for('index'))

    # 增加浏览量
    house.page_views = (house.page_views or 0) + 1

    # 记录用户浏览历史
    if current_user.is_authenticated:
        seen_ids = current_user.get_seen_houses()
        if house_id not in seen_ids:
            seen_ids.insert(0, house_id)
            # 只保留最近20个浏览记录
            current_user.seen_id = ','.join(str(x) for x in seen_ids[:20])
            db.session.commit()

    db.session.commit()

    # 获取相似房源推荐
    similar_houses_ids = recommender.recommend_similar_houses(house_id, 6)
    similar_houses = HouseInfo.query.filter(
        HouseInfo.id.in_(similar_houses_ids),
        HouseInfo.is_available == True
    ).all() if similar_houses_ids else []

    # 处理设施信息
    facilities = []
    if house.facilities:
        facilities = [f.strip() for f in house.facilities.split(',') if f.strip()]

    return render_template('detail.html',
                           house=house,
                           similar_houses=similar_houses,
                           facilities=facilities)

@app.route('/recommend')
@login_required
def recommend():
    """个性化推荐"""
    # 获取用户浏览历史
    seen_ids = current_user.get_seen_houses()

    # 获取推荐房源ID
    recommended_ids = recommender.recommend_for_user(current_user.id, seen_ids, 12)

    if recommended_ids:
        recommended_houses = HouseInfo.query.filter(
            HouseInfo.id.in_(recommended_ids),
            HouseInfo.is_available == True
        ).all()

        # 如果推荐数量不足，用热门房源补充
        if len(recommended_houses) < 8:
            popular_ids = recommender.get_popular_houses(12 - len(recommended_houses))
            popular_houses = HouseInfo.query.filter(
                HouseInfo.id.in_(popular_ids),
                HouseInfo.is_available == True
            ).all()
            recommended_houses.extend(popular_houses)
    else:
        # 如果没有个性化推荐，返回热门房源
        recommended_houses = HouseInfo.query.filter_by(is_available=True) \
            .order_by(HouseInfo.page_views.desc()) \
            .limit(12).all()

    return render_template('recommend.html', houses=recommended_houses)


@app.route('/house/<int:house_id>/review', methods=['POST'])
@login_required
def add_review(house_id):
    """添加房源评价"""
    house = HouseInfo.query.get_or_404(house_id)

    if not house.is_available:
        flash('该房源已下架，无法评价')
        return redirect(url_for('detail', house_id=house_id))

    # 检查用户是否已经评价过该房源
    existing_review = HouseReview.query.filter_by(
        house_id=house_id,
        user_id=current_user.id
    ).first()

    if existing_review:
        flash('您已经评价过该房源')
        return redirect(url_for('detail', house_id=house_id))

    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash('请选择有效的评分（1-5星）')
        return redirect(url_for('detail', house_id=house_id))

    # 创建评价
    review = HouseReview(
        house_id=house_id,
        user_id=current_user.id,
        rating=rating,
        comment=comment
    )

    db.session.add(review)
    db.session.commit()

    flash('评价成功，感谢您的反馈！')
    return redirect(url_for('detail', house_id=house_id))


@app.route('/house/<int:house_id>/reviews')
def house_reviews(house_id):
    """获取房源评价列表"""
    house = HouseInfo.query.get_or_404(house_id)

    page = request.args.get('page', 1, type=int)
    per_page = 10

    reviews = HouseReview.query.filter_by(house_id=house_id)\
        .order_by(HouseReview.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 返回JSON格式数据用于AJAX请求
        return jsonify({
            'reviews': [review.to_dict() for review in reviews.items],
            'total': reviews.total,
            'pages': reviews.pages,
            'current_page': reviews.page
        })

    return render_template('house_reviews.html', house=house, reviews=reviews)


# ========== 用户交互功能 ==========

@app.route('/collect/<int:house_id>')
@login_required
@record_user_behavior('collect', 'house')
def collect_house(house_id):
    """收藏房源"""
    house = HouseInfo.query.get_or_404(house_id)

    if not house.is_available:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '房源已下架'}), 400
        flash('该房源已下架，无法收藏')
        return redirect(request.referrer or url_for('index'))

    collect_ids = current_user.get_collected_houses()

    if house_id not in collect_ids:
        collect_ids.insert(0, house_id)
        current_user.collect_id = ','.join(str(x) for x in collect_ids[:50])  # 只保留最近50个收藏
        db.session.commit()
        flash('收藏成功')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'collected'})
    else:
        # 取消收藏
        collect_ids.remove(house_id)
        current_user.collect_id = ','.join(str(x) for x in collect_ids)
        db.session.commit()
        flash('已取消收藏')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'uncollected'})

    return redirect(request.referrer or url_for('index'))

@app.route('/appointment/<int:house_id>', methods=['GET', 'POST'])
@login_required
def make_appointment(house_id):
    """预约看房"""
    house = HouseInfo.query.get_or_404(house_id)

    if not house.is_available:
        flash('该房源已下架，无法预约看房')
        return redirect(url_for('index'))

    if request.method == 'POST':
        appointment_date_str = request.form.get('appointment_date')
        appointment_time_str = request.form.get('appointment_time')
        message = request.form.get('message', '').strip()

        try:
            # 合并日期和时间
            appointment_datetime_str = f"{appointment_date_str} {appointment_time_str}"
            appointment_datetime = datetime.strptime(appointment_datetime_str, '%Y-%m-%d %H:%M')

            # 检查预约时间是否在未来
            if appointment_datetime <= datetime.now():
                flash('预约时间必须是将来的时间')
                return render_template('appointment.html', house=house)

            # 创建预约记录
            appointment = HouseAppointment(
                user_id=current_user.id,
                house_id=house_id,
                appointment_date=appointment_datetime,
                message=message
            )

            db.session.add(appointment)
            db.session.commit()

            flash('预约看房成功，房东会尽快联系您确认')
            return redirect(url_for('detail', house_id=house_id))

        except ValueError:
            flash('请选择有效的预约时间')

    # 默认预约时间为明天上午10点
    default_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_time = '10:00'

    return render_template('appointment.html',
                           house=house,
                           default_date=default_date,
                           default_time=default_time)


@app.route('/cancel_appointment/<int:appointment_id>')
@login_required
def cancel_appointment(appointment_id):
    """取消预约"""
    appointment = HouseAppointment.query.get_or_404(appointment_id)

    # 检查权限
    if appointment.user_id != current_user.id and not current_user.is_admin:
        flash('无权操作')
        return redirect(url_for('profile'))

    appointment.status = 'cancelled'
    db.session.commit()

    flash('预约已取消')
    return redirect(url_for('profile'))


# ========== API接口 ==========

@app.route('/api/houses')
def api_houses():
    """房源数据API接口"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    houses = HouseInfo.query.filter_by(is_available=True) \
        .order_by(HouseInfo.publish_time.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    result = {
        'houses': [house.to_dict() for house in houses.items],
        'total': houses.total,
        'page': page,
        'per_page': per_page,
        'pages': houses.pages
    }

    return jsonify(result)


@app.route('/api/search_suggest')
def api_search_suggest():
    """搜索建议API"""
    keyword = request.args.get('q', '').strip()

    if not keyword or len(keyword) < 2:
        return jsonify([])

    # 搜索标题中包含关键词的房源
    houses = HouseInfo.query.filter(
        HouseInfo.title.like(f'%{keyword}%'),
        HouseInfo.is_available == True
    ).limit(10).all()

    suggestions = [{'title': house.title, 'id': house.id} for house in houses]

    return jsonify(suggestions)


# ========== 管理员功能 ==========
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """管理员仪表盘"""
    # 统计信息
    total_users = UserInfo.query.count()
    total_houses = HouseInfo.query.count()
    available_houses = HouseInfo.query.filter_by(is_available=True).count()
    pending_houses = HouseInfo.query.filter_by(is_available=False).count()
    # 修改为只统计非取消状态的预约
    total_appointments = HouseAppointment.query.filter(HouseAppointment.status != 'cancelled').count()

    # 新增统计信息
    total_reviews = HouseReview.query.count()
    avg_rating = db.session.query(db.func.avg(HouseReview.rating)).scalar() or 0

    # 用户行为统计
    total_behaviors = UserBehavior.query.count()
    today_behaviors = UserBehavior.query.filter(
        UserBehavior.created_at >= datetime.utcnow().date()
    ).count()

    # 热门搜索词
    search_behaviors = UserBehavior.query.filter_by(behavior_type='search')\
        .filter(UserBehavior.extra_data.isnot(None))\
        .filter(UserBehavior.extra_data != '')\
        .all()

    # 统计搜索词频率
    from collections import Counter
    search_keywords = [b.extra_data for b in search_behaviors if b.extra_data]
    keyword_counter = Counter(search_keywords)
    popular_keywords = keyword_counter.most_common(10)
    # 最新注册用户
    recent_users = UserInfo.query.order_by(UserInfo.created_at.desc()).limit(5).all()

    # 最新房源
    recent_houses = HouseInfo.query.order_by(HouseInfo.created_at.desc()).limit(5).all()

    # 最近预约
    recent_appointments = HouseAppointment.query.order_by(HouseAppointment.created_at.desc()).limit(5).all()

    # 用户增长趋势（最近7天）
    week_ago = datetime.utcnow() - timedelta(days=7)
    user_growth_data = db.session.query(
        db.func.date(UserInfo.created_at).label('date'),
        db.func.count(UserInfo.id).label('count')
    ).filter(UserInfo.created_at >= week_ago)\
     .group_by(db.func.date(UserInfo.created_at))\
     .order_by(db.func.date(UserInfo.created_at)).all()

    # 房源发布趋势（最近7天）
    house_growth_data = db.session.query(
        db.func.date(HouseInfo.created_at).label('date'),
        db.func.count(HouseInfo.id).label('count')
    ).filter(HouseInfo.created_at >= week_ago)\
     .group_by(db.func.date(HouseInfo.created_at))\
     .order_by(db.func.date(HouseInfo.created_at)).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_houses=total_houses,
                           available_houses=available_houses,
                           pending_houses=pending_houses,
                           total_appointments=total_appointments,
                           total_reviews=total_reviews,
                           avg_rating=round(avg_rating, 1),
                           total_behaviors=total_behaviors,
                           today_behaviors=today_behaviors,
                           popular_keywords=popular_keywords,
                           recent_users=recent_users,
                           recent_houses=recent_houses,
                           recent_appointments=recent_appointments,
                           user_growth_data=user_growth_data,
                           house_growth_data=house_growth_data)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """用户管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示10条记录

    # 获取搜索参数
    keyword = request.args.get('keyword', '').strip()
    role = request.args.get('role', '').strip()

    # 构建查询
    query = UserInfo.query

    # 应用搜索条件
    if keyword:
        query = query.filter(
            db.or_(
                UserInfo.name.like(f'%{keyword}%'),
                UserInfo.email.like(f'%{keyword}%')
            )
        )

    # 应用角色筛选
    if role == 'admin':
        query = query.filter(UserInfo.is_admin == True)
    elif role == 'landlord':
        query = query.filter(UserInfo.is_landlord == True, UserInfo.is_admin == False)
    elif role == 'user':
        query = query.filter(UserInfo.is_admin == False, UserInfo.is_landlord == False)

    # 排序和分页
    users = query.order_by(UserInfo.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return render_template('admin/users.html', users=users)


@app.route('/admin/houses')
@login_required
@admin_required
def admin_houses():
    """房源管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示10条记录

    # 获取搜索参数
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()
    region = request.args.get('region', '').strip()

    # 构建查询
    query = HouseInfo.query

    # 应用搜索条件
    if keyword:
        query = query.filter(
            db.or_(
                HouseInfo.title.like(f'%{keyword}%'),
                HouseInfo.address.like(f'%{keyword}%')
            )
        )

    # 应用状态筛选
    if status == 'available':
        query = query.filter(HouseInfo.is_available == True)
    elif status == 'pending':
        query = query.filter(HouseInfo.is_available == False)

    # 应用区域筛选
    if region:
        query = query.filter(HouseInfo.region == region)

    # 排序和分页
    houses = query.order_by(HouseInfo.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return render_template('admin/houses.html', houses=houses)

@app.route('/admin/add_house', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_house():
    """管理员添加房源"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        rooms = request.form.get('rooms', '').strip()
        area = request.form.get('area', '').strip()
        price = request.form.get('price', '').strip()
        direction = request.form.get('direction', '').strip()
        rent_type = request.form.get('rent_type', '').strip()
        region = request.form.get('region', '').strip()
        block = request.form.get('block', '').strip()
        address = request.form.get('address', '').strip()
        traffic = request.form.get('traffic', '').strip()
        facilities = request.form.get('facilities', '').strip()
        highlights = request.form.get('highlights', '').strip()
        matching = request.form.get('matching', '').strip()
        travel = request.form.get('travel', '').strip()
        landlord = request.form.get('landlord', '').strip()
        phone_num = request.form.get('phone_num', '').strip()
        house_num = request.form.get('house_num', '').strip()

        # 验证必填字段
        if not title or not price or not region or not address:
            flash('请填写必填字段（标题、价格、区域、地址）')
            return render_template('admin/add_house.html')

        # 创建房源信息
        house = HouseInfo(
            title=title,
            rooms=rooms,
            area=area,
            price=price,
            direction=direction,
            rent_type=rent_type,
            region=region,
            block=block,
            address=address,
            traffic=traffic,
            facilities=facilities,
            highlights=highlights,
            matching=matching,
            travel=travel,
            landlord=landlord,
            phone_num=phone_num,
            house_num=house_num,
            publish_time=int(datetime.now().timestamp()),
            is_available=True  # 管理员添加的房源默认审核通过
        )

        # 处理主图上传
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 保存相对路径到数据库
                house.image_url = f"static/img/{filename}"

        db.session.add(house)
        db.session.flush()  # 获取house.id

        # 处理多图上传
        image_files = request.files.getlist('images')
        for file in image_files:
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 创建图片记录
                house_image = HouseImage(
                    house_id=house.id,
                    image_url=f"static/img/{filename}"
                )
                db.session.add(house_image)

        db.session.commit()

        flash('房源添加成功')
        return redirect(url_for('admin_houses'))

    return render_template('admin/add_house.html')


@app.route('/admin/appointments')
@login_required
@admin_required
def admin_appointments():
    """预约管理"""
    # 获取搜索参数
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()

    # 构建查询
    query = db.session.query(HouseAppointment)\
        .join(UserInfo, HouseAppointment.user_id == UserInfo.id)\
        .join(HouseInfo, HouseAppointment.house_id == HouseInfo.id)

    # 应用搜索条件
    if keyword:
        query = query.filter(
            db.or_(
                HouseInfo.title.like(f'%{keyword}%'),
                UserInfo.name.like(f'%{keyword}%')
            )
        )

    # 应用状态筛选
    if status:
        query = query.filter(HouseAppointment.status == status)

    # 排序
    appointments = query.order_by(HouseAppointment.created_at.desc()).all()

    return render_template('admin/appointments.html', appointments=appointments)


@app.route('/admin/approve_house/<int:house_id>')
@login_required
@admin_required
def approve_house(house_id):
    """审核通过房源"""
    house = HouseInfo.query.get_or_404(house_id)
    house.is_available = True
    db.session.commit()
    flash('房源已审核通过')
    return redirect(url_for('admin_houses'))


@app.route('/admin/reject_house/<int:house_id>')
@login_required
@admin_required
def reject_house(house_id):
    """审核不通过房源"""
    house = HouseInfo.query.get_or_404(house_id)
    house.is_available = False
    db.session.commit()
    flash('房源已下架')
    return redirect(url_for('admin_houses'))


@app.route('/admin/delete_house/<int:house_id>')
@login_required
@admin_required
def admin_delete_house(house_id):
    """删除房源"""
    house = HouseInfo.query.get_or_404(house_id)
    db.session.delete(house)
    db.session.commit()
    flash('房源已删除')
    return redirect(url_for('admin_houses'))


@app.route('/admin/delete_user/<int:user_id>')
@login_required
@admin_required
def admin_delete_user(user_id):
    """删除用户"""
    user = UserInfo.query.get_or_404(user_id)
    if user.is_admin:
        flash('不能删除管理员用户')
        return redirect(url_for('admin_users'))

    # 删除用户相关的预约记录
    HouseAppointment.query.filter_by(user_id=user_id).delete()

    db.session.delete(user)
    db.session.commit()
    flash('用户已删除')
    return redirect(url_for('admin_users'))


@app.route('/admin/update_appointment_status/<int:appointment_id>', methods=['POST'])
@login_required
@admin_required
def update_appointment_status(appointment_id):
    """更新预约状态"""
    appointment = HouseAppointment.query.get_or_404(appointment_id)
    new_status = request.form.get('status')

    if new_status in ['pending', 'confirmed', 'cancelled']:
        appointment.status = new_status
        db.session.commit()
        flash('预约状态已更新')
    else:
        flash('无效的状态')

    return redirect(url_for('admin_appointments'))


@app.route('/admin/make_admin/<int:user_id>')
@login_required
@admin_required
def make_admin(user_id):
    """设置为管理员"""
    user = UserInfo.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f'用户 {user.name} 已成为管理员')
    return redirect(url_for('admin_users'))


@app.route('/admin/remove_admin/<int:user_id>')
@login_required
@admin_required
def remove_admin(user_id):
    """取消管理员权限"""
    user = UserInfo.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能取消自己的管理员权限')
        return redirect(url_for('admin_users'))

    user.is_admin = False
    db.session.commit()
    flash(f'用户 {user.name} 的管理员权限已取消')
    return redirect(url_for('admin_users'))


# 在 app.py 中添加批量操作路由
@app.route('/admin/batch_approve', methods=['POST'])
@login_required
@admin_required
def batch_approve_houses():
    """批量审核通过房源"""
    try:
        data = request.get_json()
        house_ids = data.get('house_ids', [])

        if not house_ids:
            return jsonify({'success': False, 'message': '请至少选择一个房源'}), 400

        # 批量审核通过
        HouseInfo.query.filter(HouseInfo.id.in_(house_ids)).update(
            {HouseInfo.is_available: True}, synchronize_session=False
        )
        db.session.commit()

        return jsonify({'success': True, 'count': len(house_ids)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/batch_reject', methods=['POST'])
@login_required
@admin_required
def batch_reject_houses():
    """批量下架房源"""
    try:
        data = request.get_json()
        house_ids = data.get('house_ids', [])

        if not house_ids:
            return jsonify({'success': False, 'message': '请至少选择一个房源'}), 400

        # 批量下架
        HouseInfo.query.filter(HouseInfo.id.in_(house_ids)).update(
            {HouseInfo.is_available: False}, synchronize_session=False
        )
        db.session.commit()

        return jsonify({'success': True, 'count': len(house_ids)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/batch_delete', methods=['POST'])
@login_required
@admin_required
def batch_delete_houses():
    """批量删除房源"""
    try:
        data = request.get_json()
        house_ids = data.get('house_ids', [])

        if not house_ids:
            return jsonify({'success': False, 'message': '请至少选择一个房源'}), 400

        # 批量删除
        HouseInfo.query.filter(HouseInfo.id.in_(house_ids)).delete(synchronize_session=False)
        db.session.commit()

        return jsonify({'success': True, 'count': len(house_ids)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== 房源管理（房东） ==========
# app.py
@app.route('/publish_house', methods=['GET', 'POST'])
@login_required
def publish_house():
    """发布房源"""
    # 检查权限：只有房东或管理员才能发布房源
    if not current_user.is_landlord and not current_user.is_admin:
        flash('只有房东或管理员才能发布房源')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        rooms = request.form.get('rooms', '').strip()
        area = request.form.get('area', '').strip()
        price = request.form.get('price', '').strip()
        direction = request.form.get('direction', '').strip()
        rent_type = request.form.get('rent_type', '').strip()
        region = request.form.get('region', '').strip()
        block = request.form.get('block', '').strip()
        address = request.form.get('address', '').strip()
        traffic = request.form.get('traffic', '').strip()
        facilities = request.form.get('facilities', '').strip()
        highlights = request.form.get('highlights', '').strip()
        matching = request.form.get('matching', '').strip()
        travel = request.form.get('travel', '').strip()
        landlord = request.form.get('landlord', '').strip()
        phone_num = request.form.get('phone_num', '').strip()
        house_num = request.form.get('house_num', '').strip()

        # 验证必填字段
        if not title or not price or not region or not address:
            flash('请填写必填字段（标题、价格、区域、地址）')
            return render_template('publish_house.html')

        landlord_name = request.form.get('landlord', '').strip()
        if not landlord_name:
            landlord_name = current_user.name

        # 创建房源信息
        house = HouseInfo(
            title=title,
            rooms=rooms,
            area=area,
            price=price,
            direction=direction,
            rent_type=rent_type,
            region=region,
            block=block,
            address=address,
            traffic=traffic,
            facilities=facilities,
            highlights=highlights,
            matching=matching,
            travel=travel,
            landlord=landlord_name,
            phone_num=phone_num,
            house_num=house_num,
            publish_time=int(datetime.now().timestamp())
        )

        # 处理主图上传
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 保存相对路径到数据库
                house.image_url = f"static/img/{filename}"

        # 如果是管理员发布，则默认审核通过
        if current_user.is_admin:
            house.is_available = True

        db.session.add(house)
        db.session.flush()  # 获取house.id

        # 处理多图上传
        image_files = request.files.getlist('images')
        for file in image_files:
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 创建图片记录
                house_image = HouseImage(
                    house_id=house.id,
                    image_url=f"static/img/{filename}"
                )
                db.session.add(house_image)

        db.session.commit()

        flash('房源发布成功' + ('，等待管理员审核' if not current_user.is_admin else ''))
        return redirect(url_for('detail', house_id=house.id))

    return render_template('publish_house.html')


# app.py
@app.route('/house/edit/<int:house_id>', methods=['GET', 'POST'])
@login_required
def edit_house(house_id):
    """编辑房源"""
    house = HouseInfo.query.get_or_404(house_id)

    # 检查权限：只有管理员或房源的发布者才能编辑
    if not current_user.is_admin and house.landlord != current_user.name:
        flash('无权编辑此房源')
        return redirect(url_for('index'))

    if request.method == 'POST':
        house.title = request.form.get('title', '').strip()
        house.rooms = request.form.get('rooms', '').strip()
        house.area = request.form.get('area', '').strip()
        house.price = request.form.get('price', '').strip()
        house.direction = request.form.get('direction', '').strip()
        house.rent_type = request.form.get('rent_type', '').strip()
        house.region = request.form.get('region', '').strip()
        house.block = request.form.get('block', '').strip()
        house.address = request.form.get('address', '').strip()
        house.traffic = request.form.get('traffic', '').strip()
        house.facilities = request.form.get('facilities', '').strip()
        house.highlights = request.form.get('highlights', '').strip()
        house.matching = request.form.get('matching', '').strip()
        house.travel = request.form.get('travel', '').strip()
        house.landlord = request.form.get('landlord', '').strip()
        house.phone_num = request.form.get('phone_num', '').strip()
        house.house_num = request.form.get('house_num', '').strip()

        # 处理主图上传（如果提供了新图片）
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 更新图片URL
                house.image_url = f"static/img/{filename}"

        # 处理多图上传
        image_files = request.files.getlist('images')
        for file in image_files:
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                timestamp = int(datetime.now().timestamp())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                # 保存文件
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # 创建图片记录
                house_image = HouseImage(
                    house_id=house.id,
                    image_url=f"static/img/{filename}"
                )
                db.session.add(house_image)

        # 验证必填字段
        if not house.title or not house.price or not house.region or not house.address:
            flash('请填写必填字段（标题、价格、区域、地址）')
            return render_template('edit_house.html', house=house)

        # 如果是普通用户编辑，则需要重新审核
        if not current_user.is_admin:
            house.is_available = False

        db.session.commit()
        flash('房源信息已更新' + ('，等待管理员重新审核' if not current_user.is_admin else ''))
        return redirect(url_for('detail', house_id=house.id))

    return render_template('edit_house.html', house=house)

@app.route('/house/delete/<int:house_id>')
@login_required
def delete_house(house_id):
    """删除房源"""
    house = HouseInfo.query.get_or_404(house_id)

    # 检查权限：只有管理员或房源的发布者才能删除
    if not current_user.is_admin and house.landlord != current_user.name:
        flash('无权删除此房源')
        return redirect(url_for('index'))

    db.session.delete(house)
    db.session.commit()
    flash('房源已删除')
    return redirect(url_for('index'))


# ========== 房源管理（房东） ==========
# 在 app.py 中添加房东相关路由
@app.route('/landlord/houses')
@login_required
def landlord_houses():
    """房东房源管理"""
    # 检查权限：只有房东才能查看自己的房源
    if not current_user.is_landlord:
        flash('只有房东才能访问此页面')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 10

    # 查询房东的所有房源（包括待审核和已审核的）
    houses = HouseInfo.query.filter_by(landlord=current_user.name) \
        .order_by(HouseInfo.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('landlord/houses.html', houses=houses)


@app.route('/admin/make_landlord/<int:user_id>')
@login_required
@admin_required
def make_landlord(user_id):
    """设置为房东"""
    user = UserInfo.query.get_or_404(user_id)
    user.is_landlord = True
    db.session.commit()
    flash(f'用户 {user.name} 已成为房东')
    return redirect(url_for('admin_users'))


@app.route('/admin/remove_landlord/<int:user_id>')
@login_required
@admin_required
def remove_landlord(user_id):
    """取消房东权限"""
    user = UserInfo.query.get_or_404(user_id)
    user.is_landlord = False
    db.session.commit()
    flash(f'用户 {user.name} 的房东权限已取消')
    return redirect(url_for('admin_users'))

@app.route('/landlord/appointments')
@login_required
def landlord_appointments():
    """房东预约管理"""
    # 检查权限：只有房东才能查看自己的房源预约
    if not current_user.is_landlord:
        flash('只有房东才能访问此页面')
        return redirect(url_for('index'))

    # 查询房东所有房源的预约记录
    houses = HouseInfo.query.filter_by(landlord=current_user.name).all()
    house_ids = [house.id for house in houses]

    # 查询这些房源的所有预约
    appointments = HouseAppointment.query.filter(HouseAppointment.house_id.in_(house_ids)) \
        .order_by(HouseAppointment.created_at.desc()) \
        .all()

    return render_template('landlord/appointments.html', appointments=appointments)


if __name__ == '__main__':
    app.run(debug=True)
