# utils/database.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


db = SQLAlchemy()


class UserInfo(UserMixin, db.Model):
    __tablename__ = 'user_info'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    addr = db.Column(db.String(100))
    collect_id = db.Column(db.String(250))
    seen_id = db.Column(db.String(250))
    is_admin = db.Column(db.Boolean, default=False)
    is_landlord = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_url = db.Column(db.String(255), default='https://gitee.com/Cililin/rent-house/raw/master/static/img/default_avatar.png')
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_collected_houses(self):
        if self.collect_id:
            return [int(x) for x in self.collect_id.split(',') if x]
        return []

    def get_seen_houses(self):
        if self.seen_id:
            return [int(x) for x in self.seen_id.split(',') if x]
        return []


class HouseInfo(db.Model):
    __tablename__ = 'house_info'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    rooms = db.Column(db.String(100))
    area = db.Column(db.String(100))
    price = db.Column(db.String(100))
    direction = db.Column(db.String(100))
    rent_type = db.Column(db.String(100))
    region = db.Column(db.String(100))
    block = db.Column(db.String(100))
    address = db.Column(db.String(200))
    traffic = db.Column(db.String(100))
    publish_time = db.Column(db.Integer)
    facilities = db.Column(db.Text)
    highlights = db.Column(db.Text)
    matching = db.Column(db.Text)
    travel = db.Column(db.Text)
    page_views = db.Column(db.Integer)
    landlord = db.Column(db.String(30))
    phone_num = db.Column(db.String(100))
    house_num = db.Column(db.String(100))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'price': self.price,
            'region': self.region,
            'rooms': self.rooms,
            'area': self.area,
            'rent_type': self.rent_type,
            'address': self.address,
            'landlord': self.landlord,
            'phone_num': self.phone_num,
            'page_views': self.page_views,
            'image_url': self.image_url
        }


class HouseRecommend(db.Model):
    __tablename__ = 'house_recommend'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    house_id = db.Column(db.Integer)
    title = db.Column(db.String(100))
    address = db.Column(db.String(100))
    block = db.Column(db.String(100))
    score = db.Column(db.Integer)


class HouseAppointment(db.Model):
    __tablename__ = 'house_appointment'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    house_id = db.Column(db.Integer, nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    house = db.relationship('HouseInfo', foreign_keys=[house_id],
                           primaryjoin='HouseAppointment.house_id == HouseInfo.id',
                           backref=db.backref('appointments', lazy=True))

    user = db.relationship('UserInfo', foreign_keys=[user_id],
                          primaryjoin='HouseAppointment.user_id == UserInfo.id',
                          backref=db.backref('appointments', lazy=True))


class HouseReview(db.Model):
    __tablename__ = 'house_reviews'

    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house_info.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    house = db.relationship('HouseInfo', backref=db.backref('reviews', lazy=True))
    user = db.relationship('UserInfo', backref=db.backref('reviews', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'house_id': self.house_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_name': self.user.name
        }


class HouseImage(db.Model):
    __tablename__ = 'house_images'

    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house_info.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    house = db.relationship('HouseInfo', backref=db.backref('images', lazy=True))


class UserBehavior(db.Model):
    __tablename__ = 'user_behaviors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'))
    behavior_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer)
    target_type = db.Column(db.String(50))
    extra_data = db.Column(db.Text)  # 修改字段名从 metadata 到 extra_data
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('UserInfo', backref=db.backref('behaviors', lazy=True))
