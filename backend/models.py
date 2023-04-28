import sys
import os
import json
from datetime import datetime
from .extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)

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


class Scene(db.Model):
    __tablename__ = 'scenes'

    scene_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    img_url = db.Column(db.String(2000), nullable=True)
    prompt = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(255), nullable=False, comment='type包括mj,reface, sd等。\r\n如果是mj，直接调用prompt生成图片\r\n如果是reface，直接与上传的头像图片进行换脸\r\n')
    img_type = db.Column(db.String(255), nullable=False, comment='图片类型，包括男生、女生、多人、猫、狗')
    rate = db.Column(db.Float, nullable=True, comment='推荐评分，从0-10分，可以有小数点\r\n')
    
    name = db.Column(db.String(255), nullable=True)
    base_img_key = db.Column(db.String(2550), nullable=True)
    hint_img_list = db.Column(db.JSON, nullable=True)
    setup_status = db.Column(db.String(255), nullable=True)
    roi_list = db.Column(db.JSON, nullable=True)
    model_name = db.Column(db.String(2550), nullable=True)
    negative_prompt = db.Column(db.Text, nullable=True)
    params = db.Column(db.Text, nullable=True)
    collection_name = db.Column(db.String(255), nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    
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

    def update_result_img_key(self, result_img_key):
        self.result_img_key = result_img_key
        self.status = 'finish'
        db.session.commit()

    def get_person_id_list(self):
        if self.person_id_list is None:
            return []
        return json.loads(self.person_id_list)

    