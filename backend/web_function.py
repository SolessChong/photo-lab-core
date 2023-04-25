from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import secrets

from . import utils
from .utils import(get_signed_url, oss_put, db_execute)
from . import models

def get_scenes():
    img_types = request.args.get('img_type', None)
    action_types = request.args.get('action_type', None)

    if img_types is None or action_types is None:
        return {"status": "error", "message": "Missing img_type or action_type parameters"}, 400

    result = []

    for img_type in img_types.split(','):
        for action_type in action_types.split(','):
            select_query = "SELECT * FROM scenes WHERE img_type=%s AND action_type=%s"
            scenes = utils.db_get(select_query, (img_type, action_type))
            for scene in scenes:
                if scene['img_url']:
                    scene['signed_url'] = get_signed_url(scene['img_url'])
                if scene['base_img_key']:
                    scene['signed_url'] = get_signed_url(scene['base_img_key'])
                result.append(scene)

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