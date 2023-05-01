from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import secrets
import requests

from . import utils
from .utils import(get_signed_url, oss_put, db_execute)
from . import models
from sqlalchemy import and_


def meiyan_face(img_url): 
    url = 'https://api-cn.faceplusplus.com/facepp/v2/beautify'  # 替换为你的API endpoint

    data = {
        'api_key': 'nF8M_ebap8esjHo72acnNgtxaauansrM',
        'api_secret': 'Pc1BaJ6qZUfL02peelpc-rlnukU-ZhRD',
        'image_url': img_url  # 替换为你的图片URL
    }

    response = requests.post(url, data=data)

    # 检查请求是否成功
    if response.status_code == 200:
        print('face++ Request was successful.')
        return response.json()['result']
    else:
        print('Request failed.')
        print('Status code: ', response.status_code)
        print('Response: ', response.text)
    return None

def get_scenes():
    action_types = request.args.get('action_type', None)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    meiyan =  request.args.get('meiyan', 0, type=int)

    if action_types is None:
        return {"status": "error", "message": "Missing img_type or action_type parameters"}, 400

    result = []

    total = models.Scene.query.filter(and_(models.Scene.setup_status=='finish', models.Scene.action_type=='sd')).count()
    print(f'{total} scenes found')

    scenes = models.Scene.query.filter(and_(models.Scene.setup_status=='finish', models.Scene.action_type=='sd')).paginate(page=page, per_page=per_page, error_out=False)


    for scene in scenes:
        bb = {}
        if scene.base_img_key:
            bb['img_url'] = get_signed_url(scene.base_img_key)

        tasks = models.Task.query.filter_by(status='finish', scene_id = scene.scene_id).all()
        bb['task_img_list'] = []
        bb['meiyan_img_list'] = []
        for task in tasks:
            bb['task_img_list'].append(utils.get_signed_url(task.result_img_key))
            if meiyan == 1:
                bb['meiyan_img_list'].append(meiyan_face(utils.get_signed_url(task.result_img_key)))
        bb['params'] = scene.params
        bb['rate'] = scene.rate
        bb['scene_id'] = scene.scene_id

        result.append(bb)

    return jsonify(result)


def get_source():
    user_id = request.args.get('user_id', None)
    if user_id is None:
        return {"status": "error", "message": "Missing user_id"}, 400

    if user_id == "michaelfeng007":
        sources = models.Source.query.filter(models.Source.img_url != None).all()
    else:
        sources = models.Source.query.filter_by(user_id=user_id).filter(models.Source.img_url != None).all()
    
    sources_data = [{'source_id': source.source_id, 'img_url': utils.get_signed_url(source.img_url), 'user_id': source.user_id, 'type': source.type} for source in sources]
    return jsonify(sources_data)

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
        if action_type == 'sd':
            base_img_key = f'scenes/sd_collection/{collection_name}/{secrets.token_hex(8)}.png'
        elif action_type == 'example':
            base_img_key = f'scenes/example/{collection_name}_{secrets.token_hex(2)}.png'
        oss_put(base_img_key, utils.convert_to_png_bytes(file))

    # 将图片信息存入数据库
    query = "INSERT INTO scenes (base_img_key, action_type, img_type, prompt, rate, collection_name) VALUES (%s, %s, %s, %s, %s, %s)"
    db_execute(query, (base_img_key, action_type, img_type, prompt, rate, collection_name))
    
    return 'OK', 200

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