import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from extensions import db

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    pack_num = db.Column(db.Integer, nullable=True)
    source_num = db.Column(db.Integer, nullable=True)

class Source(db.Model):
    __tablename__ = 'source'
    img_url = db.Column(db.String(5000), nullable=True)
    user_id = db.Column(db.String(255), nullable=False)
    source_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(255), nullable=True)
    person_id = db.Column(db.Integer, nullable=True)
    base_img_key = db.Column(db.String(255), nullable=False)
    
class Persons(db.Model):
    __tablename__ = 'persons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True)
    model_type = db.Column(db.String(255), nullable=True)
    model_file_key = db.Column(db.String(2550), nullable=True)
    sex = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.String(255), nullable=True)

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

class Pack(db.Model):
    __tablename__ = 'packs'
    pack_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    total_img_num = db.Column(db.Integer, nullable=True)


class Scene(db.Model):
    __tablename__ = 'scenes'

    scene_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    img_url = db.Column(db.String(2000))
    prompt = db.Column(db.Text)
    action_type = db.Column(db.String(255), nullable=False)
    img_type =db.Column(db.String(255), nullable=False)
    rate = db.Column(db.Float)
    name = db.Column(db.String(255))
    base_img_key = db.Column(db.String(2550))
    hint_img_list = db.Column(db.JSON)
    roi_list = db.Column(db.JSON)
    model_name = db.Column(db.String(2550))
    negative_prompt = db.Column(db.Text)
    params = db.Column(db.Text)
    collection_name = db.Column(db.String(255))

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, nullable=True)
    scene_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(255), nullable=True)
    result_img_key = db.Column(db.String(2550), nullable=True)
    debug_img = db.Column(db.JSON, nullable=True)