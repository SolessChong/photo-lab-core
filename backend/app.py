from backend import config
import argparse
from backend import bd_conversion_utils
from urllib.parse import urlparse, parse_qs

from datetime import datetime
import json
from flask import Flask, request, jsonify, render_template
import secrets
import random
import string
from celery import group, Celery, chain, chord
import logging
import requests
from .config import wait_status
from sqlalchemy import desc

from backend.extensions import  app, db
from . import aliyun_face_detector
from . import web_function
from . import utils
from . import models
from . import selector_other, selector_sd

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

    if 'X-Forwarded-For' in request.headers:
        user_ip = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    logging.info(f'create new user ip is {user_ip}, ua is {user_agent}')

    # Create a new user with the generated user_id
    new_user = models.User(user_id=user_id, ip = user_ip, ua = user_agent, group = config.user_group, min_img_num = config.min_image_num, max_img_num = 50)

    # Add the new user to the database and commit the changes
    db.session.add(new_user)
    db.session.commit()

    # send active request to toutiao
    click = models.BdClick.query.filter(models.BdClick.ip == user_ip, models.BdClick.con_status==0).order_by(models.BdClick.id.desc()).first()
    if click:
        try:
            requests.get(click.callback)
            click.con_status = 1
            click.user_id = user_id
            db.session.add(click)
            db.session.commit()
            logging.info(f'update click {click.id} to user {user_id}')
        except Exception as e:
            logging.error(f'update click {click.id} to user {user_id} error: {e}')
    else:
        logging.error(f'no click for ip {user_ip}')


    # Create the response object with the specified format
    response = {
        "code": 0,
        "msg": "create user successfully",
        "data": {
            "user_id": user_id,
            "min_img_num": new_user.min_img_num,
            "max_img_num": new_user.max_img_num,
            "pay_group": random.randint(1,3),
            "shot_num": 10,
            "shot_seconds:" : 10,
            "max_styles" : 1
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
        if person.head_img_key:
            head_img_url = utils.get_signed_url(person.head_img_key)
        else:
            head_img_url = None
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
    logger.info(f'upload_payment request args is {request.args}')
    missing_params = [param for param in ['user_id', 'payment_amount', 'receipt', 'pack_id', 'product_id'] 
                      if request.args.get(param) is None]
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

    user_id = request.args.get('user_id')
    payment_amount = request.args.get('payment_amount')
    receipt = request.args.get('receipt')
    pack_id = request.args.get('pack_id')
    product_id = request.args.get('product_id')
    # get unlock_num. If not provided, set to infinite, for backward compatibility
    unlock_num = request.args.get('unlock_num', 9999)
    
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
        pack.unlock_num += int(unlock_num)
        pack.is_unlock = pack.unlock_num >= pack.total_img_num
    else:
        return jsonify({"msg": "error: Pack not found", 'code': 1}), 404
    
    # Commit the changes
    db.session.commit()
    
    ############################
    # send payment callback request to toutiao
    user_ip = models.User.query.filter_by(user_id=user_id).first().ip
    click = models.BdClick.query.filter(models.BdClick.ip == user_ip, models.BdClick.con_status==0).order_by(models.BdClick.id.desc()).first()
    if click:
        try:
            """
            http://ad.toutiao.com/track/activate/?
            callback=B.ezpH241vFUgYLNheuhOp1SaTnA3WQSTLKKeSSTy0FvaRlPTV3rgqXBFKtVKr2to9lKmKrJ1JgQKVa4e59f6MrjaifaPsQJbaFIfBPD1PjtgLNs6mTog9Aayd418g7GLTapckqntVHQUlFyVg7LI2y7C
            &os=1
            &muid=C25C5AAA-7B24-4E56-9EE0-7FA89267B2FD
            """
            # extract callback param from click.callback
            parsed_url = urlparse(click.callback)
            params = parse_qs(parsed_url.query)
            callback_param = params.get('callback', [None])[0]
            post_data = bd_conversion_utils.generate_post_data("game_addiction", callback_param, float(payment_amount))
            rst = requests.post(config.BD_CONVERSION_POST_URL, json=post_data, timeout=5)
            
            logging.info(f"Report payment conversion of user {user_id} to BD: {rst.content.decode('utf8')}")
        except Exception as e:
            logging.error(f'update click {click.id} to user {user_id} error: {e}')
    else:
        logging.error(f'no click for ip {user_ip}')

    ###########################
    # Notify
    url = 'https://maker.ifttt.com/trigger/PicPayment/json/with/key/kvpqNPLePMIVcUkAuZiGy'
    payload = {
        "user_id": user_id,
        "payment_amount": payment_amount,
        "user_ip": user_ip,
        "pack_id": pack_id,
        "product_id": product_id,
        "unlock_num": unlock_num
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f'notify ifttt error: {e}')

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200

@app.route('/api/get_example_2', methods=['GET'])
def get_example_2():
    examples = models.Example.query.all()

    result = {
        'before': [],
        'after': [],
        'bad': [],
        'styles': []
    }

    for example in examples:
        img_height, img_width = utils.get_oss_image_size(example.img_key)

        rs = {
            'img_url': utils.get_signed_url(example.img_key, is_yasuo=True),
            'img_height': img_height,
            'img_width': img_width,
            'style': example.style,
            'id': example.id,
        }
        if example.type == 0:
            result['before'].append(rs)
        elif example.type == 1:
            result['after'].append(rs)
        elif example.type == 2:
            result['bad'].append(rs)
    
    tags = models.Tag.query.filter(models.Tag.img_key != None).filter(models.Tag.rate > 0).order_by(models.Tag.rate.desc()).all()
    for tag in tags:
        img_height, img_width = utils.get_oss_image_size(tag.img_key)
        rs = {
            'img_url': utils.get_signed_url(tag.img_key, is_yasuo=True),
            'img_height': img_height,
            'img_width': img_width,
            'style': tag.tag_name,
            'id': tag.id,
            'tag_id': tag.id
        }
        result['styles'].append(rs)

    response = {
        'data': result,
        'msg': '成功获取示例图片',
        'code': 200
    }
    return jsonify(response)

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
    user_id = request.form['user_id']

    logging.info(f'upload source request {user_id}')

    try: 
        png_img = utils.convert_to_png_bytes(img_file)
    except Exception as e:
        logging.info(f'{user_id} upload source fail {e}')
        # random generate 10 char as name
        random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        utils.oss_put(f'error/user_{user_id}-{random_id}.dat', img_file)
        return {"msg": f"上传失败，图片格式错误或中断导致无法打开", "code": 1, "data" : ''}, 200 

    png_img = utils.convert_to_png_bytes(img_file)
    jpg_img = utils.convert_to_jpg_bytes(png_img)

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
    
    logging.info(f'upload source success {user_id} {person_id} {person_name}')
    return jsonify(response)

@app.route('/api/upload_multiple_sources', methods = ['POST'])
def upload_multiple_sources():
    if 'img_oss_keys' not in request.form or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_oss_keys, user_id or person_name"}, 400
    img_oss_keys = request.form.get('img_oss_keys', None)
    user_id = request.form['user_id']
    person_name = request.form['person_name']
    source_type = request.form.get('type', None)
    not_filtration= request.form.get('not_filtration', type=int, default=0)
    person_id = request.form.get('person_id', type=str, default=None)
    
    logging.info(f'upload_multiple_sources request {user_id}, not_filtration {not_filtration}, source_type {source_type}')

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

    print(img_oss_keys, type(img_oss_keys))

    success_count = 0
    keys = json.loads(img_oss_keys)
    for key in keys:
        data = utils.oss_source_get(key)
        if (not_filtration==1) or aliyun_face_detector.one_face(data):
            utils.oss_put(key, data)
            source = models.Source(base_img_key=key, user_id=user_id, type=source_type, person_id=person_id)
            db.session.add(source)
            success_count += 1
    db.session.commit()

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": person_id,
            "person_name": person_name,
            "success_count": success_count,
            "checklist": [
            {
                "title": "背景多样性",
                "hint": "上传更多背景不同的照片",
                "score": 87,
                "is_ok": 1
            },
            {
                "title": "人物照片清晰度",
                "hint": "上传清晰的人物照片",
                "score": 43,
                "is_ok": 0
            },
            {
                "title": "人物角度多样性",
                "hint": "上传更多不同角度的人物照片",
                "score": 40,
                "is_ok": 0
            }]
        }
    }
    
    logging.info(f'upload source success {user_id} {person_id} {person_name}')
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
    tag_id_list = request.form.get('tag_id_list', None)
    if (tag_id_list):
        tag_id_list = json.loads(tag_id_list)
        try:
            tag_id_list = [int(tag_id) for tag_id in tag_id_list]
        except Exception as e:
            return {"status": "error", "message": "Invalid tag_id_list"}, 400
    
    pack = models.Pack(user_id=user_id, total_img_num=0, start_time= datetime.utcnow(), unlock_num = 0, description='合集')
    db.session.add(pack)
    db.session.commit()


    m = 0
    # --------------------------- SD 生成任务 ------------------------------------
    if (models.User.query.filter_by(user_id=user_id).first().group == 1):
        if (tag_id_list):
            logging.info(f'generate_sd_task_with_tag user_id: {user_id},  person_id_list: {person_id_list},  {category},  tag_id_list: {tag_id_list} {limit}')
            m += selector_sd.generate_sd_task_with_tag(category=category, person_id_list = person_id_list, user_id = user_id, pack_id=pack.pack_id, tag_ids = tag_id_list, limit=limit, wait_status=wait_status)
        else:
            m += selector_sd.generate_sd_task(category=category, person_id_list = person_id_list, user_id = user_id, pack_id=pack.pack_id, limit=limit, wait_status=wait_status)
        
        pack.total_seconds = 3*60*60

    # --------------------------- 以下是启动mj和reface的任务 ------------------------------
    else :
        limit = 5
        pack.total_seconds = 2*60
        # m += selector_other.generate_task(person_id=person_id_list[0], category=category, pack_id=pack.pack_id, user_id=user_id, action_type='mj', limit=limit, wait_status=wait_status)

        m += selector_other.generate_task(person_id=person_id_list[0], category=category, pack_id=pack.pack_id, user_id=user_id, action_type='reface', limit=limit, wait_status=wait_status)

    # --------------------------- 以下是返回结果 ----------------------------------
    response = {
        'code': 0, 
        'msg': f'启动{m}张照片的AI拍摄任务',
        'data': {
            "total_time_seconds": pack.total_seconds,
            "total_img_num": m,
            "des": f"AI拍摄完成后，您将获得{m}张照片"
        }
    }
    pack.total_img_num = m
    pack.description = f'合集{m}张'
    db.session.add(pack)
    db.session.commit()

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
            "thumb_imgs": [], 
            "finish_seconds_left": pack.total_seconds - int((datetime.utcnow() - pack.start_time).total_seconds()),
            'total_seconds': pack.total_seconds ,
            # 'banner_img_url': utils.get_signed_url('static/test1.png'),
            'banner_img_url': None,
            'heights': [],
            'widths': [],
            'price': pack.price,
            'unlock_num': pack.unlock_num,
        }
        if pack.banner_img_key:
            pack_dict[pack_id]['banner_img_url'] = utils.get_signed_url(pack.banner_img_key)
    # 依次添加图片，每次调用这个函数只添加一张照片，
    # 然后在这个函数里面查之前总共添加了多少张照片进来，再判断每张照片的水印、模糊状态
    # 前5张：           有水印，不模糊
    # 前unlock_num张：  无水印，无模糊
    # 后面的：          有水印，有模糊
    if img_key:
        # is_shuiyin = (not pack_dict[pack_id]['is_unlock'])
        # if len(pack_dict[pack_id]['imgs']) < pack_dict[pack_id]['unlock_num']:
        #     is_mohu = False
        # else:
        #     is_mohu = True
        is_shuiyin = is_mohu = True
        if len(pack_dict[pack_id]['imgs']) < 5:
            is_mohu = False
        if len(pack_dict[pack_id]['imgs']) < pack_dict[pack_id]['unlock_num']:
            is_shuiyin = False
            is_mohu = False

        img_url = utils.get_signed_url(img_key, is_shuiyin = is_shuiyin, is_yasuo = False, is_mohu=is_mohu)
        thumb_url = utils.get_signed_url(img_key, is_shuiyin = False, is_yasuo = True, is_mohu=is_mohu)
        # after change to new height, width. 10x faster!
        height, width = utils.get_oss_image_size(img_key)
        pack_dict[pack_id]["imgs"].append(img_url)
        pack_dict[pack_id]["thumb_imgs"].append(thumb_url)
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
    images = models.GeneratedImage.query.filter(models.GeneratedImage.user_id == user_id, models.GeneratedImage.img_oss_key != None).all()
    for image in images:
        create_new_pack(pack_dict, image.pack_id, image.img_oss_key)

    tasks = (db.session.query(models.Task, models.Scene)
                .join(models.Scene, models.Task.scene_id == models.Scene.scene_id)
                .filter(models.Task.user_id == user_id, models.Task.result_img_key != None)
                .order_by(desc(models.Scene.rate))
                .limit(300)
                .all())
    logging.info(f'adding tasks number: {len(tasks)}')
    for task, scene in tasks:
        create_new_pack(pack_dict, task.pack_id, task.result_img_key)

    packs = models.Pack.query.filter(models.Pack.user_id == user_id).all()
    for pack in packs:
        create_new_pack(pack_dict, pack.pack_id, None)
    

    response = {
        'code': 0,
        'msg': 'success',
        'data': {
            'packs': list([pack for pack in pack_dict.values() if len(pack['imgs']) > 0 or pack['finish_seconds_left'] > 0])
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
    parser.add_argument('--is_industry', action='store_true', help="Enable industry mode.")
    parser.add_argument('-i', '--image-num', type=int, default = 15,  help="min image num.")
    parser.add_argument('-u', '--user-group', type=int, default = 1,  help="user group.")
    args = parser.parse_args()
    config.is_industry = args.is_industry
    config.min_image_num = args.image_num
    config.user_group = args.user_group
    app.run(host='0.0.0.0', port=args.port)
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    logging.root.handlers = gunicorn_logger.handlers
    logging.root.setLevel(gunicorn_logger.level)
    logging.debug('logger setup.')

