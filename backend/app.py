import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from utils import(get_signed_url, oss_put, db_execute)
import secrets
import utils
import random
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from extensions import  app, db
import celery_worker

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# CORS(app)

# db.init_app(app)
# migrate = Migrate(app, db)

import models

@app.route('/api/upload_source', methods=['POST'])
def upload_source():
    if 'img_file' not in request.files or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_file, user_id or person_name"}, 400

    img_file = request.files['img_file']
    user_id = request.form['user_id']
    source_type = request.form.get('type', None)
    person_name = request.form['person_name']

    # 查找 persons 表中是否存在相应的记录
    person = models.Persons.query.filter_by(user_id=user_id, name=person_name).first()
    if not person:
        # 如果不存在，创建一个新的 Person 对象并将其保存到数据库中
        new_person = models.Persons(name=person_name, user_id=user_id)
        db.session.add(new_person)
        db.session.commit()
        person_id = new_person.id
    else:
        person_id = person.id

    base_img_key = f'source/{user_id}/{person_id}/{secrets.token_hex(16)}.png'
    utils.oss_put(base_img_key, utils.convert_to_png_bytes(img_file))

    # 存储记录到数据库
    source = models.Source(base_img_key=base_img_key, user_id=user_id, type=source_type, person_id=person_id)
    db.session.add(source)
    db.session.commit()

    return {"status": "success", "message": "Image uploaded and record updated"}, 200

@app.route('/')
def index():
    return render_template('index.html')

# 获取场景列表
@app.route('/get_scenes', methods=['GET'])
def get_scenes():
    result = []
    for img_type in ['pet', 'girl', 'boy']:
        for action_type in ['reface', 'mj']:
            select_query = "SELECT * FROM scenes WHERE img_type=%s AND action_type=%s"
            scenes = utils.db_get(select_query, (img_type, action_type))
            for scene in scenes:
                if scene['img_url']:
                    scene['signed_url'] = get_signed_url(scene['img_url'])
                result.append(scene)
    return jsonify(result)


@app.route('/api/get_source', methods=['GET'])
def get_source():
    user_id = request.args.get('user_id', None)
    if user_id is None:
        return {"status": "error", "message": "Missing user_id"}, 400

    if user_id == "michaelfeng007":
        sources = models.Source.query.all()
    else:
        sources = models.Source.query.filter_by(user_id=user_id).all()

    sources_data = [{'source_id': source.source_id, 'img_url': utils.get_signed_url(source.img_url), 'user_id': source.user_id, 'type': source.type} for source in sources]
    return jsonify(sources_data)
    
# 上传图片
@app.route('/upload_scene', methods=['POST'])
def upload_scene():
    file = request.files.get('img_file', None)
    action_type = request.form.get('action_type')
    img_type = request.form.get('img_type')
    prompt = request.form.get('prompt', None)
    rate = request.form.get('rate', None)
    collection_name = request.form.get('collection_name') # 添加这一行
    
    base_img_key = None
    # 上传图片到OSS
    if file:
        base_img_key = f'scenes/sd_collection/{collection_name}/{secrets.token_hex(16)}.png'
        oss_put(base_img_key, utils.convert_to_png_bytes(file))

    # 将图片信息存入数据库
    query = "INSERT INTO scenes (base_img_key, action_type, img_type, prompt, rate, collection_name) VALUES (%s, %s, %s, %s, %s, %s)"
    db_execute(query, (base_img_key, action_type, img_type, prompt, rate, collection_name))
    
    return 'OK', 200


@app.route('/update_scene', methods=['POST'])
def update_scene():
    data = request.get_json()
    print(data)
    scene_id = data['scene_id']
    action_type = data['action_type']
    rate = data['rate']
    prompt = data['prompt']

    # 更新数据库中的场景信息
    query = "UPDATE scenes SET action_type=%s, rate=%s, prompt=%s WHERE scene_id=%s"
    utils.db_execute(query, (action_type, rate, prompt, scene_id))

    return 'OK', 200


# 获取某个用户的所有已经生成的图片，返回结果一个packs数组，
# python后端程序获取所有generated_images表中，符合user_id 的列。然后将获得的列，把相同的pack_id合并在一个pack项。pack项的值还包括
# pack_id,  description, total_img_num, finish_time_left和imgs.
# 其中pack_id,  description, total_img_num可以直接从数据库packs表中直接得到，finish_time_left计算公式为当前时间减去pack的start_time， imgs则为所有列对应img_url生成的oss可访问地址。
@app.route('/api/get_generated_images', methods=['GET'])
def get_generated_images():
    user_id = request.args.get('user_id')
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    images = models.GeneratedImage.query.filter(models.GeneratedImage.user_id == user_id, models.GeneratedImage.img_url != None).all()
    packs = models.Pack.query.filter_by(user_id=user_id).all()

    pack_dict = {}
    for pack in packs:
        pack_dict[pack.pack_id] = {
            "pack_id": pack.pack_id,
            "description": pack.description,
            "total_img_num": pack.total_img_num,
            "imgs": [],
            "finish_time_left": 30*60 - int((datetime.datetime.now() - pack.start_time).total_seconds())
        }

    for image in images:
        img_url = utils.get_signed_url(image.img_url)  # 使用你已经实现的get_oss_url函数替换
        pack_dict[image.pack_id]["imgs"].append(img_url)

    result = {"packs": list(pack_dict.values())}
    return jsonify(result), 200


# 根据上传的user_id、source_id与type，启动生成图片。 在python后端程序中：
# 1）从数据库scenes表获得所有img_type为type的scene
# 2）假设得到了n个scene， 这n个scene分别与source_id进行一次组合，查看generated_images表里是否存在这个组合，每一个不存在表里的组合，则待生成图片+1。
# 3）假设总共带生成图片为m个。如果m为0，则没有新需要生成的图片，返回false，message为”没有新生成图片“。如果m大于0，在packers表中插入一行，给定 user_id， description 值为"to add", total_img_num值为m， start_time为当前时间。 
# 4）如果m大于0，调用一个异步函数，启动专门生成图片任务。
@app.route('/api/start_generate', methods=['POST'])
def start_generate():
    user_id = request.form.get('user_id')
    source_id = request.form.get('source_id')
    img_type = request.form.get('type')

    if not all([user_id, source_id, img_type]):
        return jsonify({"error": "user_id, source_id and type are required"}), 400

    # 1) Get all scenes with the specified type
    scenes = models.Scene.query.filter_by(img_type=img_type).all()

    # 2) Check if the combination of each scene with source_id exists in the generated_images table
    new_combinations = []
    for scene in scenes:
        existing_image = models.GeneratedImage.query.filter_by(user_id=user_id, source_id=source_id, scene_id=scene.scene_id).first()
        if not existing_image:
            new_combinations.append(scene.scene_id)

    m = len(new_combinations)
    # 3) If m > 0, insert a new row in the packs table
    if m > 0:
        random.shuffle(new_combinations)
        new_combinations = new_combinations[:min(20, len(new_combinations))]
        new_pack = models.Pack(
            user_id=user_id,
            description="to add",
            total_img_num=m,
            start_time= datetime.datetime.now()
        )
        db.session.add(new_pack)
        db.session.commit()

        # 4) Call the async function to start the image generation task
        celery_worker.generate_images_task.delay(source_id, new_combinations, new_pack.pack_id, user_id)

        return jsonify({"success": True, "message": f"Started generating {len(new_combinations)} new images"}), 200
    else:
        return jsonify({"success": False, "message": "No new images to generate"}), 200

# Remember to add your imports and other necessary code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
