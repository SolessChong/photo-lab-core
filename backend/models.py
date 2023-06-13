import sys
import os
import json
from datetime import datetime
from .extensions import db


class Example(db.Model):
    __tablename__ = 'example_table'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=True)
    img_key = db.Column(db.String(255), nullable=True)
    style = db.Column(db.String(255), nullable=True)
    tag_id = db.Column(db.Integer, nullable=True)

class BdClick(db.Model):
    __tablename__ = 'bd_clicks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip = db.Column(db.String(255), nullable=True)
    ua = db.Column(db.String(255), nullable=True)
    callback = db.Column(db.String(255), nullable=True)
    idfa = db.Column(db.String(255), nullable=True)
    create_time = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.String(255), nullable=True)
    con_status = db.Column(db.Integer, default=0)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(255), nullable=True)
    ua = db.Column(db.String(255), nullable=True)
    min_img_num = db.Column(db.Integer, nullable=True)
    group = db.Column(db.Integer, nullable=True)
    max_img_num = db.Column(db.Integer, nullable=True)
    subscribe_until = db.Column(db.DateTime, nullable=True)
    create_time = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    promo_code_id = db.Column(db.Integer, nullable=True)
    subscribe_info = db.Column(db.JSON, nullable=True, default=None)
    dna = db.Column(db.JSON, nullable=True, default=None)

class Source(db.Model):
    __tablename__ = 'source'
    img_url = db.Column(db.String(5000), nullable=True)
    user_id = db.Column(db.String(255), nullable=False)
    source_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(255), nullable=True)
    person_id = db.Column(db.Integer, nullable=True)
    base_img_key = db.Column(db.String(255), nullable=False)
    
class Person(db.Model):
    __tablename__ = 'persons'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    model_type = db.Column(db.String(255), nullable=True)
    model_file_key = db.Column(db.String(2550), nullable=True)
    sex = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.String(255), nullable=True)
    lora_train_status = db.Column(db.String(255), nullable=True)
    head_img_key = db.Column(db.String(255), nullable=True)
    train_note = db.Column(db.String(255), nullable=True)
    dataset_quality = db.Column(db.JSON, nullable=True)
    update_time = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    def update_model_file(self, modek_file_key):
        self.model_file_key = modek_file_key
        self.lora_train_status = "finish"
        db.session.commit()

class GeneratedImage(db.Model):
    __tablename__ = 'generated_images'
    img_url = db.Column(db.String(2000), nullable=True)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255), nullable=True)
    pack_id = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(255), nullable=True)
    prompt = db.Column(db.Text, nullable=True)
    source_id = db.Column(db.Integer, nullable=True)
    scene_id = db.Column(db.Integer, nullable=True)
    img_oss_key = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(255), nullable=True)
    create_time = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

class Pack(db.Model):
    __tablename__ = 'packs'
    pack_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    total_img_num = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Integer, nullable=True)
    is_unlock = db.Column(db.Integer, nullable=True, default=0, comment='0代表上锁，1代表已经付费解锁')
    banner_img_key = db.Column(db.String(2000), nullable=True)
    total_seconds = db.Column(db.Integer, nullable=True)
    unlock_num = db.Column(db.Integer, nullable=True, default=5)
    notify_count = db.Column(db.Integer, nullable=True, default=0)


class Scene(db.Model):
    __tablename__ = 'scenes'

    scene_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    img_url = db.Column(db.String(2000), nullable=True)
    prompt = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(255), nullable=False, comment='type包括mj,reface, sd等。\r\n如果是mj，直接调用prompt生成图片\r\n如果是reface，直接与上传的头像图片进行换脸\r\n')
    img_type = db.Column(db.String(255), nullable=False, comment='图片类型，包括男生、女生、多人、猫、狗')
    rate = db.Column(db.Float, nullable=True, default=0, comment='推荐评分，从0-10分，可以有小数点\r\n')
    
    name = db.Column(db.String(255), nullable=True)
    base_img_key = db.Column(db.String(2550), nullable=True)
    hint_img_list = db.Column(db.JSON, nullable=True)
    setup_status = db.Column(db.String(255), nullable=True)
    roi_list = db.Column(db.JSON, nullable=True)
    model_name = db.Column(db.String(2550), nullable=True)
    negative_prompt = db.Column(db.Text, nullable=True)
    params = db.Column(db.JSON, nullable=True)  # usually dict
    collection_name = db.Column(db.String(255), nullable=True)
    tags = db.Column(db.String(255), nullable=True)

    is_industry = db.Column(db.Integer, nullable=True, default=0, comment='是否是行业包，0代表不是，1代表是')
    
    def update_pose_img(self, pose_img_url):
        if self.hint_img_list is None:
            self.hint_img_list = [pose_img_url]
        else:
            self.hint_img_list[0] = pose_img_url
        db.session.commit()

    def get_pose_img(self):
        if self.hint_img_list is None:
            return None
        return self.hint_img_list[0]
    
    def update_setup_status(self, setup_status):
        self.setup_status = setup_status
        db.session.commit()
    
    def to_dict(self):
        return {
            'scene_id': self.scene_id,
            'base_img_key': self.base_img_key,
            'hint_img_list': self.hint_img_list,
            'collection_name': self.collection_name,
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt,
            'params': self.params,
            'rate': 0 if self.rate is None else self.rate,
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id_list = db.Column(db.JSON, nullable=True, comment="可能有多个用户，因此用JSONArray存储所有person_ids")
    scene_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(255), nullable=True)
    result_img_key = db.Column(db.String(2550), nullable=True)
    debug_img = db.Column(db.JSON, nullable=True)
    pack_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.String(255), nullable=True)
    rate = db.Column(db.Integer, nullable=True)

    def update_result_img_key(self, result_img_key):
        self.result_img_key = result_img_key
        self.status = 'finish'
        db.session.commit()

    def task_fail(self):
        self.status = 'fail'
        db.session.commit()

    def get_person_id_list(self):
        if self.person_id_list is None:
            return []
        return self.person_id_list

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(45), nullable=True)
    payment_amount = db.Column(db.Integer, nullable=True)
    # receipt 类型是mysql text
    receipt = db.Column(db.Text, nullable=True)
    pack_id = db.Column(db.Integer, nullable=True)
    product_id = db.Column(db.String(45), nullable=True)
    create_time = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_name = db.Column(db.String(255), nullable=True)
    rate = db.Column(db.Integer, nullable=True, default=0)
    img_key = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.JSON, nullable=True)

class TagScene(db.Model):
    __tablename__ = 'tag_scene'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scene_id = db.Column(db.Integer, nullable=True)
    tag_id = db.Column(db.Integer, nullable=True)
    is_delete = db.Column(db.SmallInteger, nullable=True, default=0)
    
class GlobalConfig(db.Model):
    __tablename__ = 'global_config'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), nullable=True)
    value = db.Column(db.Text, nullable=True)
    is_delete = db.Column(db.SmallInteger, nullable=True, default=0)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    user_id = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    wechat = db.Column(db.String(50))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Contact {self.id}>"
    

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.String(255))
    '''
    images: {
        'img_url': 'https://xxx.jpg',
        'img_size': [100, 200]  # (width, height)
    }
    '''
    images = db.Column(db.JSON)
    text = db.Column(db.String(512))
    scene_id = db.Column(db.Integer)
    scene_tag_id_list = db.Column(db.JSON)
    rate = db.Column(db.Integer, default=0)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'images': self.images,
            'text': self.text,
            'rate': self.rate,
            'create_time': self.create_time
        }
    
class PromoCode(db.Model):
    # define available promo code types: 'subscribe_week', 'subscribe_month', 'balance', 'discount'
    class Type:
        subscribe_week = 'subscribe_week'
        subscribe_month = 'subscribe_month'
        subscribe_year = 'subscribe_year'
        balance = 'balance'
        discount = 'discount'

    __tablename__ = 'promo_codes'
    id = db.Column(db.Integer, primary_key=True)
    '''unique code'''
    code = db.Column(db.String(128), unique=True)
    '''subscribe_week, subscribe_month, balance, discount'''
    type = db.Column(db.String(255))
    value = db.Column(db.Integer)
    used_count = db.Column(db.Integer, default=0)
    max_use_count = db.Column(db.Integer, default=1)
    '''user_id who use this code. when max_userd_count > 1, this field is None'''
    user_id = db.Column(db.String(255))
    referer_user_id = db.Column(db.String(255))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    expire_time = db.Column(db.DateTime, default=datetime.utcnow)
    '''when this code is used, update this field. when max_userd_count > 1, this field is last used time'''
    use_time = db.Column(db.DateTime, default=datetime.utcnow)
    '''reseller name'''
    reseller = db.Column(db.String(255))

    def is_valid(self):
        return self.expire_time > datetime.utcnow() and self.used_count < self.max_use_count

    def use(self, user_id):
        self.used_count += 1
        if self.max_use_count == 1:
            self.user_id = user_id
        self.use_time = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'type': self.type,
            'value': self.value,
            'used_count': self.used_count,
            'max_use_count': self.max_use_count,
            'user_id': self.user_id,
            'referer_user_id': self.referer_user_id,
            'create_time': self.create_time,
            'expire_time': self.expire_time,
            'use_time': self.use_time,
            'reseller': self.reseller
        }
