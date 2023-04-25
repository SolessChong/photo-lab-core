import datetime
from flask import Flask, request, jsonify, render_template
import secrets
import random
import string
from celery import group, Celery, chain, chord
import logging

from backend.extensions import  app, db
from . import aliyun_face_detector
from . import web_function
from . import utils
from . import models

celery_app = Celery('myapp',
                    broker='redis://default:Yzkj8888!@r-wz9d9mt4zsofl3s0pn.redis.rds.aliyuncs.com:6379/0',
                    backend='redis://default:Yzkj8888!@r-wz9d9mt4zsofl3s0pn.redis.rds.aliyuncs.com:6379/0')

# Create the tasks as strings
task_train_lora_str = 'train_lora'
task_render_scene_str = 'render_scene'


logger = logging.getLogger(__name__)


@app.route('/api/create_user', methods=['GET'])
def create_user():
    # Generate a random user_id with 10 characters
    user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    # Create a new user with the generated user_id
    new_user = models.User(user_id=user_id)

    # Add the new user to the database and commit the changes
    db.session.add(new_user)
    db.session.commit()

    # Return the generated user_id as a JSON response
    response = {
        'user_id': user_id
    }
    return jsonify(response)

@app.route('/api/upload_source', methods=['POST'])
def upload_source():
    if 'img_file' not in request.files or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_file, user_id or person_name"}, 400
    img_file = request.files['img_file']
    png_img = utils.convert_to_png_bytes(img_file)
    if aliyun_face_detector.detect_face(png_img) != 1:
        return {"success" : False,  "message": "Not only one face in the picture"}, 200

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

    base_img_key = f'source/{user_id}/{person_name}/{secrets.token_hex(16)}.png'
    utils.oss_put(base_img_key, png_img)

    # 存储记录到数据库
    source = models.Source(base_img_key=base_img_key, user_id=user_id, type=source_type, person_id=person_id)
    db.session.add(source)
    db.session.commit()

    return {"success" : True, "message": f"upload source successfully"}, 200

@app.route('/api/start_sd_generate', methods=['POST'])
def start_sd_generate():
    if 'user_id' not in request.form or 'person_id_list' not in request.form or 'category' not in request.form:
        return {"status": "error", "message": "Missing user_id, person_id_list or category"}, 400

    user_id = request.form['user_id']
    person_id_list = request.form['person_id_list']
    category = request.form['category']

    # 1. Get all scenes with the same category
    scenes = models.Scene.query.filter(models.Scene.img_type==category, models.Scene.action_type=='sd', models.Scene.hint_img_list != None).all()

    # 2. Check for existing tasks and calculate new combinations
    new_combinations = []
    for scene in scenes:
        if not models.Task.query.filter_by(scene_id=scene.scene_id, person_id_list=person_id_list, user_id=user_id).first():
            new_combinations.append((scene.scene_id, person_id_list))
    m = len(new_combinations)
    logger.info(f'{user_id} has new_combinations: {new_combinations}')
    
    # 3. If there are new combinations, handle them based on lora_train_status
    if m == 0:
        return jsonify({'success': False, 'message': 'No new tasks were created'})
    
    persons = models.Person.query.filter(models.Person.id.in_(tuple(person_id_list))).all()
    train_lora_group = []
    for person in persons:
        if person.lora_train_status == 'pending':
            return jsonify({'success': False, 'message': '请等待之前的AI拍摄任务完成再开始'})

        elif person.lora_train_status == 'failed':
            return jsonify({'success': False, 'message': '数字人物训练失败，请选择其他数字人物或新创建数字人物'})

        elif person.lora_train_status is None:
            person.lora_train_status = 'pending'
            db.session.commit()
            sources = models.Source.query.filter_by(person_id=person.id).all()
            base_img_keys = [source.base_img_key for source in sources]
            train_lora_group.append(celery_app.signature(task_train_lora_str, args=(person.id, base_img_keys, )))
    logger.info(f'{user_id} has train_lora_group: {train_lora_group}')

    render_group = []
    pack = models.Pack(user_id=user_id, total_img_num=m, start_time= datetime.datetime.now())
    db.session.add(pack)
    db.session.commit()
    for scene_id, person_id_list in new_combinations:
        task = models.Task(
            user_id=user_id,
            scene_id=scene_id,
            person_id_list=person_id_list,
            status='pending',
            pack_id=pack.pack_id
        )
        db.session.add(task)
        db.session.commit()
        render_group.append(celery_app.signature(task_render_scene_str, args=(task.id, )))


    pipeline = chain(group(train_lora_group), group(render_group))
    pipeline.apply_async()

    # ch = chord(train_lora_group, body=group(render_group))
    # ch.apply_async()

    return jsonify({'success': True, 'message': f'{m} new tasks created for user {user_id}'})


# 获取某个用户的所有已经生成的图片，返回结果一个packs数组，
# python后端程序获取所有generated_images表中，符合user_id 的列。然后将获得的列，把相同的pack_id合并在一个pack项。pack项的值还包括
# pack_id,  description, total_img_num, finish_time_left和imgs.
# 其中pack_id,  description, total_img_num可以直接从数据库packs表中直接得到，finish_time_left计算公式为当前时间减去pack的start_time， imgs则为所有列对应img_url生成的oss可访问地址。
@app.route('/api/get_generated_images', methods=['GET'])
def get_generated_images():
    user_id = request.args.get('user_id')
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

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

    images = models.GeneratedImage.query.filter(models.GeneratedImage.user_id == user_id, models.GeneratedImage.img_url != None).all()
    for image in images:
        img_url = utils.get_signed_url(image.img_url)  # 使用你已经实现的get_oss_url函数替换
        pack_dict[image.pack_id]["imgs"].append(img_url)

    tasks = models.Task.query.filter(models.Task.user_id == user_id, models.Task.result_img_key != None).all()
    for task in tasks:
        img_url = utils.get_signed_url(task.result_img_key)
        pack_dict[task.pack_id]["imgs"].append(img_url)

    result = {"packs": list(pack_dict.values())}
    return jsonify(result), 200


# 1）从数据库scenes表获得所有img_type与person_name对应type相同的scene
# 2）假设得到了n个scene， 这n个scene分别与person_id进行一次组合，查看generated_images表里是否存在这个组合，每一个不存在表里的组合，则待生成图片+1。
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


@app.route('/')
def index():
    return render_template('index.html')

# 获取场景列表
@app.route('/get_scenes', methods=['GET'])
def get_scenes_route():
    return web_function.get_scenes()

@app.route('/api/get_source', methods=['GET'])
def get_source_route():
    return web_function.get_source()

# 上传图片
@app.route('/upload_scene', methods=['POST'])
def upload_scene_route():
    return web_function.upload_scene()

@app.route('/update_scene', methods=['POST'])
def update_scene_route():
    return web_function.update_scene()
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
