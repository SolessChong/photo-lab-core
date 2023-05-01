from datetime import datetime
import json
from flask import Flask, request, jsonify, render_template
import secrets
import random
import string
from celery import group, Celery, chain, chord
import logging
import argparse

from backend.extensions import  app, db
from . import aliyun_face_detector
from . import web_function
from . import utils
from . import models
from . import selector_mj

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

    # Create the response object with the specified format
    response = {
        "code": 0,
        "msg": "create user successfully",
        "data": {
            "user_id": user_id
        }
    }

    # Return the response object as a JSON response
    return jsonify(response)

@app.route('/api/get_user', methods=['GET'])
def get_user():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    persons = models.Person.query.filter_by(user_id=user_id).all()

    result_persons = []

    for person in persons:
        if not person.head_img_key:
            person_source = models.Source.query.filter(models.Source.person_id==person.id, models.Source.base_img_key != None).first()

            if person_source:
                image_data = utils.oss_get(person_source.base_img_key)

                face_coordinates = aliyun_face_detector.get_face_coordinates(image_data)
                print(face_coordinates)
                cropped_face = aliyun_face_detector.crop_face_pil(image_data, face_coordinates)

                person.head_img_key = f'head_img/{person.name}.jpg'
                utils.oss_put(person.head_img_key, cropped_face)

                db.session.commit()

        head_img_url = utils.get_signed_url(person.head_img_key)
        result_persons.append({
            "person_id": person.id,
            "person_name": person.name,
            "head_img_url": head_img_url,
            "lora_train_status": person.lora_train_status,
        })
    
    response = {
        "data": {
            "persons": result_persons,
            "min_img_num": 10,
            "max_img_num": 20
        },
        "msg": "get user successfully",
        "code": 0
    }

    return jsonify(response), 200

@app.route('/api/upload_payment', methods=['GET'])
def upload_payment():
    missing_params = [param for param in ['user_id', 'payment_amount', 'receipt', 'pack_id', 'product_id'] 
                      if request.args.get(param) is None]
    if missing_params:
        return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

    user_id = request.args.get('user_id')
    payment_amount = request.args.get('payment_amount')
    receipt = request.args.get('receipt')
    pack_id = request.args.get('pack_id')
    product_id = request.args.get('product_id')
    
    # Create a new payment
    new_payment = models.Payment(
        user_id=user_id, 
        payment_amount=int(payment_amount) if payment_amount else None, 
        receipt=receipt, 
        pack_id=int(pack_id) if pack_id else None, 
        product_id=product_id
    )
    db.session.add(new_payment)

    # Update is_unlock to 1 for the pack with the given pack_id
    pack = models.Pack.query.get(pack_id)
    if pack:
        pack.is_unlock = 1
    else:
        return jsonify({"msg": "error: Pack not found", 'code': 1}), 404

    # Commit the changes
    db.session.commit()

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200

@app.route('/api/get_example_images', methods=['GET'])
def get_example_images():
    scenes = models.Scene.query.filter(models.Scene.action_type == 'example', models.Scene.base_img_key != None).all()
    result = []

    for scene in scenes:
        img_url = utils.get_signed_url(scene.base_img_key)
        img_height, img_width = utils.get_image_size(img_url)

        result.append({
            'img_url': img_url,
            'img_height': img_height,
            'img_width': img_width,
            'style_name': scene.collection_name,
            'id': scene.scene_id
        })

    response = {
        'data': result,
        'msg': '成功获取示例图片',
        'code': 200
    }
    return jsonify(response)

@app.route('/api/upload_source', methods=['POST'])
def upload_source():
    if 'img_file' not in request.files or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_file, user_id or person_name"}, 400
    img_file = request.files['img_file']
    png_img = utils.convert_to_png_bytes(img_file)
    jpg_img = utils.convert_to_jpg_bytes(png_img)

    user_id = request.form['user_id']
    source_type = request.form.get('type', None)
    person_name = request.form['person_name']


    face_count = aliyun_face_detector.detect_face(jpg_img)
    if face_count != 1:
        logging.info(f'{user_id}上传失败，图片中有{face_count}人脸')
        return {"msg": f"上传失败，图片中有{face_count}人脸", "code": 1, "data" : ''}, 200
    
    # 查找 persons 表中是否存在相应的记录
    person = models.Person.query.filter_by(user_id=user_id, name=person_name).first()
    if not person:
        # 如果不存在，创建一个新的 Person 对象并将其保存到数据库中
        new_person = models.Person(name=person_name, user_id=user_id)
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

    count = models.Source.query.filter(models.Source.person_id == person_id).count()

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": person_id,
            "person_name": person_name,
            "source_num": count
        }
    }
    return jsonify(response)

@app.route('/api/start_sd_generate', methods=['POST'])
def start_sd_generate():
    if 'user_id' not in request.form or 'person_id_list' not in request.form or 'category' not in request.form:
        return {"status": "error", "message": "Missing user_id, person_id_list or category"}, 400

    user_id = request.form['user_id']
    person_id_list = json.loads(request.form['person_id_list'])
    if (len(person_id_list) == 0):
        return {"status": "error", "message": "person_id_list is empty"}, 400
    try:
        person_id_list = [int(person_id) for person_id in person_id_list]
    except Exception as e:
        return {"status": "error", "message": "Invalid person_id_list"}, 400
    person_id_list.sort()
    category = request.form['category']
    limit = request.form.get('limit', 50, type=int)

    
    #TODO: use new method to choose which scene to render
    # 1. Get all scenes with the same category
    scenes = models.Scene.query.filter(
        models.Scene.img_type==category, 
        models.Scene.action_type=='sd', 
        models.Scene.setup_status == 'finish'
    ).order_by(models.Scene.rate.desc()).all()
    
    # 2. Check for existing tasks and calculate new combinations
    new_combinations = []
    for scene in scenes:
        if not models.Task.query.filter_by(scene_id=scene.scene_id, person_id_list=person_id_list, user_id=user_id).first():
            new_combinations.append((scene.scene_id, person_id_list))
    new_combinations = new_combinations[:limit]
    m = len(new_combinations)
    logger.info(f'{user_id} has new_combinations: {new_combinations}')
    
    # 3. start train lora 
    for person_id in person_id_list:
        person = models.Person.query.filter(models.Person.id == person_id).first()
        if not person:
            return {"status": "error", "message": f"person_id {person_id} not found"}, 400
        if person and person.lora_train_status is None:
            person.lora_train_status = 'wait' # 等待woker_manager启动训练任务
            db.session.commit()
            logger.info(f'{user_id} start to  train lora {person.id}')

    pack = models.Pack(user_id=user_id, total_img_num=m, start_time= datetime.utcnow(), description=f'合集{m}张')
    db.session.add(pack)
    db.session.commit()
    for scene_id, person_id_list in new_combinations:
        task = models.Task(
            user_id=user_id,
            scene_id=scene_id,
            person_id_list=person_id_list,
            status='wait',
            pack_id=pack.pack_id
        )
        db.session.add(task)
        db.session.commit()

    # --------------------------- 以上是SD 生成任务 -------------------------------

    # --------------------------- 以下是启动mj的任务 ------------------------------
    # m += selector_mj.generate_mj_task(person_id=person_id_list[0], category = category, pack_id=pack.pack_id, user_id=user_id)

    # --------------------------- 以下是返回结果 ----------------------------------
    response = {
        'code': 0, 
        'msg': f'启动{m}张照片的AI拍摄任务',
        'data': {
            "total_time_seconds":3600,
            "total_img_num": m,
            "des": f"AI拍摄完成后，您将获得{m}张照片"
        }
    }
    return jsonify(response)

# 为pack增加img图片，和单纯增加pack两种情况都会调用此函数
def create_new_pack(pack_dict, pack_id, img_key):
    if not pack_id in pack_dict:
        pack = models.Pack.query.filter_by(pack_id=pack_id).first()
        if img_key and (not pack.banner_img_key):
            image_data = utils.oss_get(img_key)
            face_coordinates = None
            try:
                face_coordinates = aliyun_face_detector.get_face_coordinates(image_data)
            except Exception as e:
                logging.error(f'get_face_coordinates error: {e}')
                        
            banner_img = aliyun_face_detector.crop_16_9_pil(image_data, face_coordinates)
            pack.banner_img_key = f'banner_img/{pack_id}.jpg'
            utils.oss_put(pack.banner_img_key , banner_img)
            db.session.commit()
            
        pack_dict[pack_id] = {
            "pack_id": pack.pack_id,
            "description": pack.description,
            "total_img_num": pack.total_img_num,
            "is_unlock": pack.is_unlock,
            "imgs": [],
            "finish_seconds_left": 60*60 - int((datetime.utcnow() - pack.start_time).total_seconds()),
            'total_seconds': 60*60,
            # 'banner_img_url': utils.get_signed_url('static/test1.png'),
            'banner_img_url': None,
            'heights': [],
            'widths': [],
            'price': pack.price,
        }
        if pack.banner_img_key:
            pack_dict[pack_id]['banner_img_url'] = utils.get_signed_url(pack.banner_img_key)

    if img_key:
        img_url = utils.get_signed_url(img_key, is_shuiyin= (not pack_dict[pack_id]['is_unlock']))
        # after change to new height, width. 10x faster!
        height, width = utils.get_oss_image_size(img_key)
        pack_dict[pack_id]["imgs"].append(img_url)
        pack_dict[pack_id]["heights"].append(height)
        pack_dict[pack_id]["widths"].append(width)

# 获取某个用户的所有已经生成的图片，返回结果一个packs数组，
# python后端程序获取所有generated_images表中，符合user_id 的列。然后将获得的列，把相同的pack_id合并在一个pack项。pack项的值还包括
# pack_id,  description, total_img_num, finish_time_left和imgs.
# 其中pack_id,  description, total_img_num可以直接从数据库packs表中直接得到，finish_time_left计算公式为当前时间减去pack的start_time， imgs则为所有列对应img_url生成的oss可访问地址。
@app.route('/api/get_generated_images', methods=['GET'])
def get_generated_images():
    user_id = request.args.get('user_id', None)
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    logging.info(f'get_generated_images user_id: {user_id}')
    pack_dict = {}
    images = models.GeneratedImage.query.filter(models.GeneratedImage.user_id == user_id, models.GeneratedImage.img_url != None).all()
    for image in images:
        create_new_pack(pack_dict, image.pack_id, image.img_url)

    tasks = models.Task.query.filter(models.Task.user_id == user_id, models.Task.result_img_key != None).all()
    logging.info(f'adding tasks number: {len(tasks)}')
    for task in tasks:
        create_new_pack(pack_dict, task.pack_id, task.result_img_key)

    packs = models.Pack.query.filter(models.Pack.user_id == user_id).all()
    for pack in packs:
        create_new_pack(pack_dict, pack.pack_id, None)
    

    response = {
        'code': 0,
        'msg': 'success',
        'data': {
            'packs': list(pack_dict.values())
        }
    }
    return jsonify(response), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scene_editor')
def scene_editor():
    return render_template('scene_editor.html')

@app.route('/meiyan_test')
def meiyan_test():
    return render_template('meiyan_test.html')

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

@app.route('/web/update_scene', methods=['POST'])
def update_scene():
    data = request.get_json()
    scene_id = data.get('scene_id')
    params = data.get('params')
    rate = data.get('rate')
    print(f'{scene_id}, {params}, {rate}')
    scene = models.Scene.query.get(scene_id)
    if scene:
        # scene.params = params
        scene.rate = rate
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Scene not found'}), 404
    
if __name__ == '__main__':
    # Add argument parser: -p: port
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000, help='port to listen on')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
