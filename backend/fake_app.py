# Author: ChatGPT v4.0. Prompter: the humble Solesschong
import argparse
import oss2
from flask import Flask, request, jsonify, render_template
from backend.extensions import  app, db
from flask_cors import CORS
from sqlalchemy import func
from datetime import datetime, timedelta
import pytz
from flask import jsonify
import json
from PIL import Image
from core.resource_manager import *
from backend.models import User, Source, Person, GeneratedImage, Pack, Scene, Task, Payment, BdClick
from celery import Celery, chain, chord, group, signature
from backend.config import CELERY_CONFIG
from backend import utils
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from sqlalchemy import cast, Date, or_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from . import models
from io import BytesIO
from backend.app_community import app_community

app.app_context().push()

OSS_ACCESS_KEY_ID = 'LTAINBTpPolLKWoX'
OSS_ACCESS_KEY_SECRET = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'
OSS_BUCKET_NAME = 'photolab-test'
OSS_ENDPOINT = 'oss-cn-shenzhen.aliyuncs.com'

auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

app.register_blueprint(app_community)

def make_celery(app):
    celery = Celery('pipeline.core.celery_worker', broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app.config.update(
    **CELERY_CONFIG
)
celery = make_celery(app)
celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}


class ResourceType:
    LORA_MODEL = 1
    TRAIN_DATASET = 2

PATH_CONF = {
    'TRAIN_DATASET': 'train_dataset/'
}

def get_resource_oss_url(resource_type, id):
    match resource_type:
        case ResourceType.LORA_MODEL:
            return str('/models/lora/' + str(id) + '.safetensors')
        case ResourceType.TRAIN_DATASET:
            return str(PATH_CONF['TRAIN_DATASET'] + str(id) + '/')
        

@app.route('/')
def index():
    return render_template('fake_index.html')

#####################
## Scene Tab
@app.route('/list_scenes', methods=['GET'])
def list_scenes():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    collection_name_filter = request.args.get('collection_name_filter', '', type=str)
    non_tag = request.args.get('non_tag', 'false', type=str) == 'true'
    is_industry = request.args.get('is_industry', 0, type=int)
    scene_id_filter = request.args.get('scene_id_filter', 0, type=int)
    
    print(request.args, '  ', scene_id_filter)

    # Filter scenes based on the collection_name_filter if it's not empty
    if collection_name_filter:
        scenes_pagination = Scene.query.filter(Scene.is_industry== is_industry, Scene.collection_name.contains(collection_name_filter.replace('\\', '\\\\'))).order_by(Scene.scene_id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        scenes_pagination = Scene.query.filter(Scene.is_industry==is_industry).order_by(Scene.scene_id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if (scene_id_filter > 0):
        scenes_pagination = Scene.query.filter(Scene.scene_id==scene_id_filter).paginate(page=page, per_page=per_page, error_out=False)

    scenes = scenes_pagination.items
    total_pages = scenes_pagination.pages

    # Filter scenes that have tags if non_tag is true
    if non_tag:
        tmp_scenes = []
        for scene in scenes:
            if not models.TagScene.query.filter(models.TagScene.scene_id==scene.scene_id, models.TagScene.is_delete == 0).first():
                tmp_scenes.append(scene)
        scenes = tmp_scenes


    scene_list = [scene.to_dict() for scene in scenes]

    return jsonify({'scenes': scene_list, 'total_pages': total_pages})



@app.route('/api/scene/<int:scene_id>/update_params', methods=['POST'])
def update_scene_params(scene_id):
    data = request.get_json()  # Get JSON data from request
    updated_params = data.get('params')  # Get params from JSON data
    scene = Scene.query.get(scene_id)

    if scene is None:
        return jsonify({"error": "Scene not found"}), 404

    if updated_params == "":
        scene.params = None
    else:
        try:
            scene.params = json.loads(updated_params)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400

    db.session.commit()
    return jsonify({"success": True, "params": scene.params})

@app.route('/api/scene/<int:scene_id>/update_prompt', methods=['POST'])
def update_scene_prompt(scene_id):
    updated_prompt = request.form.get('prompt')
    scene = Scene.query.get(scene_id)

    if scene is None:
        return jsonify({"error": "Scene not found"}), 404

    scene.prompt = updated_prompt
    db.session.commit()
    return jsonify({"success": True, "prompt": scene.prompt})

@app.route('/list_tasks/<int:scene_id>', methods=['GET'])
def list_tasks_filtered(scene_id):
    tasks = Task.query.filter_by(scene_id=scene_id).all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)


#####################
## Task Tab 
@app.route('/list_tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 100

    collection_name_filter = request.args.get('collection_name', None)
    person_id_filter = request.args.get('person_id', None, type=int)

    tasks_query = Task.query.filter(Task.result_img_key != None)

    tasks_query = tasks_query.join(Scene, Task.scene_id == Scene.scene_id)

    if collection_name_filter:
        tasks_query = tasks_query.filter(Scene.collection_name == collection_name_filter)

    if person_id_filter:
        tasks_query = tasks_query.filter(func.JSON_CONTAINS(Task.person_id_list, str(person_id_filter)))

    # Add the scene rate and task rate to the query
    tasks_query = tasks_query.with_entities(
        Task.id,
        Task.scene_id,
        Task.result_img_key,
        Task.person_id_list,
        Task.pack_id,
        Task.user_id,
        Scene.rate.label('scene_rate'),  # Include the scene rate in the query
        Task.rate.label('task_rate')  # Include the task rate in the query
    )

    tasks_pagination = tasks_query.order_by(Task.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tasks = tasks_pagination.items
    total_pages = tasks_pagination.pages

    tasks_data = [
        {
            "id": task.id,
            "scene_id": task.scene_id,
            "result_img_key": task.result_img_key,
            "person_id_list": task.person_id_list,  # Access the person_id_list directly
            "pack_id": task.pack_id,
            "user_id": task.user_id,
            "scene_rate": task.scene_rate,  # Include the scene rate in the response
            "task_rate": task.task_rate  # Include the task rate in the response
        }
        for task in tasks
    ]

    return jsonify({"tasks": tasks_data, "total_pages": total_pages})


@app.route('/get_collections', methods=['GET'])
def get_collections():
    collections = Scene.query.with_entities(Scene.collection_name).distinct().all()
    return jsonify([collection[0] for collection in collections])

@app.route('/get_persons', methods=['GET'])
def get_persons():
    persons = Person.query.with_entities(Person.id, Person.name).order_by(Person.id.desc()).all()
    return jsonify([{"id": person[0], "name": person[1]} for person in persons])

@app.route('/generate_tasks', methods=['POST'])
def generate_tasks():

    app.config.update(
        **CELERY_CONFIG
    )
    # celery = make_celery(app)
    # celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}


    data = request.get_json()
    collection_name = data['collection_name']
    person_id = data['person_id']
    person_id_list = [int(person_id)]

    # Filter all scenes with collection_name
    scene_list = Scene.query.filter_by(collection_name=collection_name).all()

    # Create tasks with person_id and collection_name
    task_id_list = []
    for scene in scene_list:
        task = Task(scene_id=scene.scene_id, person_id_list=person_id_list, status='wait')
        db.session.add(task)
        db.session.flush()
        task_id_list.append(task.id)
    db.session.commit()

    # Send out Celery tasks
    # ch = chain(
    #     group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
    #     group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
    # )
    # ch.apply_async()

    return jsonify({"message": "Tasks generated and sent to the queue."})


@app.route('/create_person', methods=['POST'])
def create_person():
    celery = make_celery(app)
    celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}

    name = request.form.get('name')
    sex = request.form.get('sex')
    model_type = request.form.get('model_type')
    files = request.files.getlist('files')

    if not name or not sex or not files:
        return jsonify({"error": "Missing required fields"}), 400

    person = Person(name=name, sex=sex, model_type=model_type)
    db.session.add(person)
    db.session.commit()
    train_dataset_path = get_resource_oss_url(ResourceType.TRAIN_DATASET, person.id)

    training_img_keys = []
    for file in files:
        # Save the file to OSS and get the image_key
        oss_key = f'{train_dataset_path}{file.filename}'
        bucket.put_object(oss_key, file)
        training_img_keys.append(oss_key)

    person.training_img_key = training_img_keys
    db.session.commit()

    return jsonify({"success": "Person created successfully", "person_id": person.id}), 201

####################
### Stats tab
@app.route('/get_task_stats', methods=['GET'])
def task_stats():
    stats = ['wait', 'finish', 'fail']
    task_counts = {}
    for stat in stats:
        task_counts[stat] = Task.query.filter(Task.status == stat).count()
    return jsonify(task_counts)

@app.route('/get_scene_stats', methods=['GET'])
def scene_stats():
    setup_statuses = ['wait', 'finish', 'fail']
    scene_counts = {}
    for status in setup_statuses:
        scene_counts[status] = Scene.query.filter(Scene.setup_status == status).count()
    return jsonify(scene_counts)

@app.route('/get_person_stats', methods=['GET'])
def person_stats():
    today = date.today()
    new_person = Person.query.filter(cast(Person.update_time, Date) == today).count()
    lora_train_stats = {
        'wait': Person.query.filter(Person.lora_train_status == 'wait').count(),
        'finish': Person.query.filter(Person.lora_train_status == 'finish').count(),
        'processing': Person.query.filter(Person.lora_train_status == 'processing').count()
    }
    stats = {
        'newPerson': new_person,
        'loraTrainStatus': lora_train_stats
    }
    return jsonify(stats)

@app.route('/get_payment_stats', methods=['GET'])
def payment_stats():
    payments = Payment.query.order_by((Payment.id.desc())).limit(100).all()
    payment_stats = []
    for payment in payments:
        payment_stats.append({
            'id': payment.id,
            'user_id': payment.user_id,
            'payment_amount': payment.payment_amount,
            'pack_id': payment.pack_id,
            'product_id': payment.product_id
        })
    return jsonify(payment_stats)


@app.route('/get_all_stats', methods=['GET'])
def get_all_stats():
    # Task stats
    task_stats = {stat: Task.query.filter(Task.status == stat).count() for stat in ['wait', 'finish', 'fail']}
    
    # Scene stats
    scene_stats = {status: Scene.query.filter(Scene.setup_status == status).count() for status in ['wait', 'finish', 'fail']}
    
    # Person stats
    today = date.today()
    new_person = Person.query.filter(cast(Person.update_time, Date) == today).count()
    lora_train_stats = {status: Person.query.filter(Person.lora_train_status == status).count() for status in ['wait', 'finish', 'processing']}
    person_stats = {'newPerson': new_person, 'loraTrainStatus': lora_train_stats}
    
    # Payment stats
    payments = Payment.query.order_by((Payment.id.desc())).limit(100).all()
    utc_timezone = pytz.timezone('UTC')
    target_timezone = pytz.timezone('Asia/Shanghai')
    payment_stats = [{
            'id': payment.id, 'user_id': payment.user_id, 'payment_amount': payment.payment_amount, 
            'pack_id': payment.pack_id, 'product_id': payment.product_id, 
            'create_time': utc_timezone.localize(payment.create_time).astimezone(target_timezone).strftime('%Y-%m-%d %H:%M:%S')
        } for payment in payments]
    
    # Pack stats
    packs_created_today = Pack.query.filter(cast(Pack.start_time, Date) == today).count()
    packs_unlocked_or_have_unlock_num = Pack.query.filter(or_(Pack.unlock_num > 0, Pack.is_unlock > 0)).count()
    pack_stats = {'createdToday': packs_created_today, 'unlockedOrHaveUnlockNum': packs_unlocked_or_have_unlock_num}
    
    # All stats
    all_stats = {
        'taskStats': task_stats,
        'sceneStats': scene_stats,
        'personStats': person_stats,
        'paymentStats': payment_stats,
        'packStats': pack_stats,
    }
    return jsonify(all_stats)

####################
### Person Tab
@app.route('/list_persons', methods=['GET'])
def list_persons():
    persons = db.session.query(Person, User.ip).join(User, Person.user_id == User.user_id).order_by(Person.id.desc()).limit(100)
    persons_data = [{'id': p.id, 'name': p.name, 'user_id': p.user_id, 'ip': ip, 'lora_train_status': p.lora_train_status, 'dataset_quality': p.dataset_quality} for p, ip in persons]
    return jsonify(persons_data)



@app.route('/list_sources', methods=['GET'])
def list_sources():
    person_id = request.args.get('person_id', type=int)
    sources = Source.query.filter(Source.person_id == person_id).all()
    sources_data = [{'base_img_key': s.base_img_key} for s in sources]
    return jsonify(sources_data)

@app.route('/get_all_user', methods=['GET'])
def get_all_user():
    users = User.query.order_by(User.id.desc()).all()
    user_ids = [user.user_id for user in users]
    return jsonify({"data": {"user_ids": user_ids}})

# Other endpoints remain the same...

####################
### Create Scene Tab
@app.route('/api/create_scene', methods=['POST'])
def create_scene():
    form_data = request.form
    img_file: FileStorage = request.files.get('base_img_key')

    if img_file:
        img = Image.open(BytesIO(img_file.read()))
        img_key = 'scenes/sd_collection/' + form_data['collection_name'] + '/' + img_file.filename
        img_key = img_key.split('.')[0] + '.png'
        write_PILimg(img, img_key)

        scene = Scene(
            base_img_key=img_key,
            prompt=form_data['prompt'],
            action_type=form_data['action_type'],
            img_type=form_data['img_type'],
            negative_prompt=form_data['negative_prompt'],
            params=json.loads(form_data['params']) if form_data['params'] else None,
            collection_name=form_data['collection_name'],
            setup_status="wait",
            is_industry=form_data['industry'],
        )

        db.session.add(scene)
        db.session.commit()

        return jsonify({'scene_id': scene.scene_id})
    else:
        return jsonify({'error': 'No image file provided'}), 400
    
@app.route('/api/get_scene', methods=['GET'])
def get_scene():
    scene_id = request.args.get('scene_id', type=int)
    if not scene_id:
        return jsonify({'error': 'No scene ID provided'}), 400

    scene = Scene.query.filter_by(scene_id=scene_id).first()

    if scene:
        return jsonify(scene.to_dict())
    else:
        return jsonify({'error': 'Scene not found'}), 404

@app.route('/get_scene_tag_list/<int:scene_id>', methods=['GET'])
def get_scene_tag_list(scene_id):
    # Get all tag_scene entries for the given scene
    tag_scenes = models.TagScene.query.filter(models.TagScene.scene_id==scene_id, models.TagScene.is_delete==0 ).all()

    # Initialize empty list to hold tags
    tag_list = []

    # For each tag_scene entry, get the corresponding tag
    for tag_scene in tag_scenes:
        tag = models.Tag.query.get(tag_scene.tag_id)
        if tag:  # Check if tag exists
            tag_list.append({'tag_id': tag.id, 'tag_name': tag.tag_name})

    # Return the list of tags as JSON
    return jsonify(tag_list=tag_list)


@app.route('/update_scene_collection_name', methods=['GET'])
def update_scene_collection_name():
    scene_id = request.args.get('scene_id', type=int)
    new_collection_name = request.args.get('collection_name')

    # 参数检查
    if not scene_id or not new_collection_name:
        return jsonify({'error': 'Invalid scene_id or collection_name'}), 400

    # 查询并更新场景
    scene = Scene.query.get(scene_id)
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404

    scene.collection_name = new_collection_name
    db.session.commit()

    return jsonify({'message': 'Collection name updated successfully'}), 200

# 对于tag_list中的每个tag，首先检查tags表中是否存在相应的tag_name, 如果不存在则创建一个新的tag
# 然后在scene_tag表中查找是否存在(scene_id， tag_id）对，如果不存在就新建, 
@app.route('/update_tag/<int:scene_id>', methods=['POST'])
def update_tag(scene_id):
    tags = request.args.get('tags')
    is_collection = request.args.get('is_collection') == 'true'
    tag_list = tags.split(',')

    # 这里是你的逻辑，例如更新数据库...
    scenes = Scene.query.filter_by(scene_id=scene_id).all()
    if is_collection:
        scenes = Scene.query.filter_by(collection_name=scenes[0].collection_name).all()
    tag_id_list = []
    for scene in scenes:
        for tag in tag_list:
            if models.Tag.query.filter_by(tag_name=tag).first() is None:
                new_tag = models.Tag(tag_name=tag)
                db.session.add(new_tag)
                db.session.commit()
                tag_id = new_tag.id
            else:
                tag_id = models.Tag.query.filter_by(tag_name=tag).first().id
            
            tag_id_list.append(tag_id)
            tag_scene = models.TagScene.query.filter_by(scene_id=scene.scene_id, tag_id=tag_id).first()
            if tag_scene is None:
                new_tag_scene = models.TagScene(scene_id=scene.scene_id, tag_id=tag_id)
                db.session.add(new_tag_scene)
                db.session.commit()
            else:
                tag_scene.is_delete = 0
                db.session.commit()

    # 返回成功或失败的消息
    return jsonify({'message': 'Updated successfully'})


@app.route('/delete_tag/<scene_id>/<tag_id>/<is_apply_collection>', methods=['DELETE'])
def delete_tag(scene_id, tag_id, is_apply_collection):
    # Convert is_apply_collection to boolean
    is_apply_collection = is_apply_collection.lower() == 'true'
    
    # 这里是你的逻辑，例如更新数据库...
    scenes = Scene.query.filter_by(scene_id=scene_id).all()
    if is_apply_collection:
        scenes = Scene.query.filter_by(collection_name=scenes[0].collection_name).all()

    num = 0
    for scene in scenes:
        tag_scene = models.TagScene.query.filter_by(scene_id=scene.scene_id, tag_id=tag_id).first()
        if tag_scene is not None:
            if tag_scene.is_delete == 0:
                num += 1
                tag_scene.is_delete = 1
                db.session.commit()
    
    # Here, you would delete the tag from your database or wherever you're storing your data
    # I'm going to pretend I deleted the tag and return a success message
    return jsonify({
        'status': 'success',
        'message': f'Tag {tag_id} from scene {scene_id} has been deleted. is_apply_collection: {is_apply_collection}, total: {num}'
    })

@app.route('/update_scene_rate', methods=['GET'])
def update_scene_rate():
    scene_id = request.args.get('scene_id', type=int)
    rate = request.args.get('rate', type=float)

    # retrieve the scene from the database
    scene = Scene.query.get(scene_id)
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404

    # update the scene's rate
    scene.rate = rate
    db.session.commit()

    return jsonify({'success': 'Scene rate updated successfully'}), 200

@app.route('/get_all_tags', methods=['GET'])
def get_all_tags():
    # Get all tags
    tags = models.Tag.query.all()

    # Convert the list of Tag objects to a list of tag names
    tag_names = [tag.tag_name for tag in tags]

    # Return the list of tag names as JSON
    return jsonify(tag_names)

@app.route('/api/aggregated_data', methods=['GET'])
def aggregate_stats():
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    hourly_persons = db.session.query(func.date_format(Person.update_time, '%Y-%m-%d %H:00:00').label('hour'), func.count(Person.id).label('value'))\
        .filter(Person.update_time >= one_week_ago)\
        .group_by('hour').all()

    hourly_payments = db.session.query(func.date_format(Payment.create_time, '%Y-%m-%d %H:00:00').label('hour'), func.sum(Payment.payment_amount).label('value'))\
        .filter(Payment.create_time >= one_week_ago)\
        .group_by('hour').all()

    hourly_bdclicks = db.session.query(func.date_format(BdClick.create_time, '%Y-%m-%d %H:00:00').label('hour'), func.count(BdClick.id).label('value'))\
        .filter(BdClick.create_time >= one_week_ago)\
        .group_by('hour').all()
    
    hourly_packs = db.session.query(func.date_format(Pack.start_time, '%Y-%m-%d %H:00:00').label('hour'), func.count(Pack.pack_id).label('value'))\
        .filter(Pack.start_time >= one_week_ago)\
        .group_by('hour').all()

    response = {
        'persons': [{"hour": result[0], "value": result[1]} for result in hourly_persons],
        'payments': [{"hour": result[0], "value": result[1]} for result in hourly_payments],
        'bdclicks': [{"hour": result[0], "value": result[1]} for result in hourly_bdclicks],
        'packs': [{"hour": result[0], "value": result[1]} for result in hourly_packs]
    }

    return jsonify(response)

####################
### Tag Tab
# Add a route for getting all tags
@app.route('/api/get_all_tags', methods=['GET'])
def get_all_tags_tag_tab():
    tags = models.Tag.query.all()
    tag_data = [{'id': tag.id, 'tag_name': tag.tag_name, 'rate': tag.rate, 'img_key': tag.img_key} for tag in tags]
    response = {
        'code': 0,
        'msg': 'success',
        'data': tag_data
    }
    return jsonify(response)

@app.route('/api/filter_scenes_by_tag', methods=['POST'])
def filter_scenes_by_tag():
    data = request.get_json()
    tag_id = data.get('tag_id')
    tag = models.Tag.query.get(tag_id)
    scenes = db.session.query(models.Scene).join(models.TagScene, models.TagScene.scene_id == models.Scene.scene_id).filter(models.TagScene.tag_id == tag_id).all()
    scene_data = [{'id': scene.scene_id, 'img_key': scene.base_img_key} for scene in scenes]

    response = {
        'code': 0,
        'msg': 'success',
        'scenes': scene_data,
        'tag': {
            'tag_img_key': tag.img_key if tag else None,
            'tag_id': tag.id if tag else None,
            'tag_name': tag.tag_name if tag else None,
            'tag_rate': tag.rate if tag else None
        }
    }
    return jsonify(response)

@app.route('/upload_tag_image', methods=['POST'])
def upload_tag_image():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part in the request.'}), 400
    if 'tag_name' not in request.form:
        return jsonify({'success': False, 'error': 'No tag name in the request.'}), 400
    
    file = request.files['file']
    tag_name = request.form['tag_name']

    # If the file is one of the allowed types/extensions
    if file and file.filename != '':
        filename = secure_filename(file.filename)

        # Upload file to OSS
        oss_key = f'examples/tags/{tag_name}.png'
        # Pass file content to oss_put directly
        utils.oss_put(oss_key, file.stream.read())

        # Update Tag
        tag = db.session.query(models.Tag).filter(models.Tag.tag_name == tag_name).first()
        if tag is not None:
            tag.img_key = oss_key
            db.session.commit()

        return jsonify({'success': True, 'message': 'File successfully uploaded.'}), 200

    else:
        return jsonify({'success': False, 'error': 'Invalid file.'}), 400

if __name__ == '__main__':
    # Add argument parser: -p: port
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000, help='port to listen on')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
    # app.run(debug=True)